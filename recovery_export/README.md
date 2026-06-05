# ThyWill Prayer Recovery — Handoff

Recovered, merged, deduplicated prayer data from thywill.live (backend permanently down, no server backups). **259 unique prayers**, 2025-06-11 → 2025-12-26. Read `RECOVERY_REPORT.md` for exactly what is and isn't preserved.

## Files

```
recovery_export/
  README.md               # this file
  RECOVERY_REPORT.md      # preserved / NOT-preserved / fidelity caveats
  data/
    prayers.json          # SOURCE OF TRUTH: 259 complete merged prayers
    prayers.csv           # same, spreadsheet-friendly
    prayer_mark_logs.csv  # the 4 partial named who-prayed logs (second-precision)
    users.json            # 20 users + supporter/admin/join-date flags
  import_payload/         # native ThyWill text-archive files
    prayers/<YYYY>/<MM>/*.txt
    users/2025_06_users.txt
    users/user_attributes.txt
```

## Recommended import (into a ThyWill instance)

```bash
# from the root of a ThyWill checkout/instance
cp -r recovery_export/import_payload/* text_archives/
./thywill import-all --dry-run     # preview
./thywill import-all               # apply (creates users, then prayers + activities)
```

If `import-all` does not auto-create the users, create them first from `data/users.json` (`display_name`, `is_supporter`, `supporter_since`, real vs synthetic `join_date`), then re-run. Each prayer `.txt` already encodes its answered/testimony status and, for 4 prayers, the partial named prayer-marks.

## Not carried by the native import (apply from `data/prayers.json` if wanted)

- `daily_priority` flags (37 prayers) and `archived` flags (20)
- Aggregate prayer-mark **counts** for the 255 prayers without a recovered named log (counts only — not attributable rows)

## Caveats (full list in RECOVERY_REPORT.md §6)
- User join dates are synthetic except `Mark` (the recovery user, real date 2025-07-02).
- `Mark` = the logged-in recovery account; 101 “by you” prayers attributed to it.
- Mark-count numbers aren't re-created as DB rows (no fabricated who/when).
- Import timestamps are minute-precision; nothing after 2025-12-26 exists in this data.
