# Prayer Activity Deduplication Runbook

Use this runbook when historical imports or the `./thywill import prayer … --update-existing` workflow create duplicate `PrayerMark`, `PrayerAttribute`, or `PrayerActivityLog` rows that only differ by the seconds component of their timestamp.

## Signals
- Admin dashboard or ad-hoc queries show doubled counts for a prayer’s marks/attributes/logs with identical users and minute-granularity timestamps.
- `./thywill heal-prayer-activities --dry-run` reports `rows_deleted > 0`.

## Prerequisites
1. Recent database backup (`./thywill backup` or `./thywill backup --label <tag>`).
2. Confirm no long-running imports are modifying prayer activity (pause cron jobs if applicable).
3. Shell access to the environment’s ThyWill checkout.

## Procedure
1. **Preview the cleanup**
   ```bash
   ./thywill heal-prayer-activities --dry-run --show-details
   ```
   - Review sample groups in the output.
   - If the preview lists unexpected rows, stop and investigate before proceeding.
2. **Execute deduplication**
   ```bash
   ./thywill heal-prayer-activities
   ```
   - The script removes minute-rounded duplicates and keeps the original second-precision row. It also normalizes `text_file_path` pointers for the surviving records.
3. **Verify results**
   - Re-run the dry-run to ensure zero further changes are reported.
   - Spot check affected prayers in the app or with SQL:
     ```sql
     SELECT prayer_id, username, COUNT(*)
     FROM prayermark
     GROUP BY prayer_id, username
     HAVING COUNT(*) > 1;
     ```
   - Ensure prayer activity counts match expectations.
4. **Document the action**
   - Record the run in change logs / incident notes (include command output, timestamp, operator).

## Rollback Plan
- Restore the latest backup (`./thywill restore <backup-file>`) if the cleanup removed legitimate activity.

## Related References
- `app_helpers/services/import_service.py` minute-level dedupe logic.
- `tools/repair/deduplicate_prayer_activities.py` implementation.
- `docs/diagnostics/text_archive_coverage.md` for archive coverage status.
