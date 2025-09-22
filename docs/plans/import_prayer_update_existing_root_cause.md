# Root Cause Analysis: `thywill import prayer --update-existing`

## Observed behaviour
- Running `./thywill import prayer <file> --update-existing` replaces the text of the targeted prayer, but additional activity rows appear.
- The duplicates show identical prayer/action metadata while the timestamps differ only in the seconds field (one row ends with `:00`, another keeps the original second value such as `:56`).

## What the importer currently does
1. `cmd_import_prayer` routes to `ImportService.import_single_prayer_file(...)` (`thywill:915-934`, `app_helpers/services/import_service.py:1233-1510`).
2. When the prayer already exists and `--update-existing` is passed, the importer updates the prayer text, then unconditionally calls `_import_single_prayer_activities(...)` to replay every activity from the text archive (`app_helpers/services/import_service.py:1298-1300`).
3. `_import_single_prayer_activities` tries to prevent duplicates by querying for an existing row with the same `created_at` timestamp before inserting a `PrayerMark`, `PrayerAttribute`, or `PrayerActivityLog` (`app_helpers/services/import_service.py:1403-1465`).
4. The timestamp parser only keeps minute precision: the archive string like `"June 14 2024 at 14:45"` is parsed with `%H:%M`, and on failure it falls back to the *current* time (`app_helpers/services/import_service.py:1477-1485`).
5. Text archives themselves store timestamps truncated to minutes (`app_helpers/services/text_archive_service.py:184-207`), while the live database rows keep whatever `datetime.utcnow()` recorded, including seconds (`models.py:211-224,294-302`).

## Root cause
- Existing activity rows were originally written with full second precision (for example `2024-06-14 14:45:56`).
- During an update import we recreate the same activity from the archive, but the recreated timestamp is rounded down to `2024-06-14 14:45:00` because the archive only stores minutes.
- The duplicate-check query compares timestamps for exact equality down to the second, so `14:45:00` fails to match the already-present `14:45:56`. A second copy of the row is inserted with `:00` seconds.
- If `_parse_single_timestamp` ever falls back to `datetime.now()` (e.g., unexpected AM/PM strings), the dedupe check definitely misses and the "duplicate" row is stamped with whatever seconds were on the clock when the command ran.

## Recommended fix
1. When `update_existing` is true, normalise timestamps to the archive’s resolution when checking for existing rows. Examples:
   - Compare on a truncated-to-minute expression (e.g., `func.strftime('%Y-%m-%d %H:%M', PrayerMark.created_at)` in SQLite) rather than full equality.
   - Or fetch existing rows for the same user/action and treat them as duplicates if the difference between timestamps is < 60 seconds.
2. Apply the same minute-level comparison to `PrayerAttribute` and `PrayerActivityLog` dedupe checks so every activity path behaves consistently.
3. Optional hardening: broaden `_parse_single_timestamp` to recognise seconds and common alternate formats to avoid the fallback-to-now path.

## Verification plan
- Seed a prayer with at least one mark/activity that includes non-zero seconds.
- Run `./thywill import prayer <file> --update-existing` and confirm:
  - The prayer text updates.
  - No additional rows are inserted for `PrayerMark`, `PrayerAttribute`, or `PrayerActivityLog`.
  - Re-running the command remains idempotent.
