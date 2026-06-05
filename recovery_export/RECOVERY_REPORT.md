# ThyWill — Recovered Data: What's Preserved & What Isn't

*The thywill.live backend shut down permanently with no server backups. This data was recovered from local browser caches (service-worker page cache + IndexedDB feed snapshots) across several browser profiles, then merged and deduplicated by prayer id into a single set. All device/browser provenance has been collapsed away — what remains below is the union.*

---
## 1. Headline

| Metric | Value |
|---|---|
| **Unique prayers** | **259** |
| Distinct authors | 16 |
| Date range | 2025-06-11 → 2025-12-26 |
| Prayers with generated prayer text | 259 / 259 |
| Prayers with original-request text | 257 / 259 |
| Answered (praise reports) | 23 |
| …with testimony text | 20 |
| Daily-priority flagged | 37 |
| Archived | 20 |
| Aggregate prayer-marks (counts) | 1086 |
| Prayers with a full named who-prayed log | 4 (partial) |

## 2. Authors

`Mark` is the recovery user's own account (their prayers rendered as “by you” in the cache, re-attributed here). `ilyag` is the most active other community member.

| Author | Prayers |
|---|---:|
| ilyag | 138 |
| Mark | 101 |
| Esmony | 4 |
| NinaC | 3 |
| lisonok | 2 |
| Joshua | 1 |
| Benjamin Paine | 1 |
| ffanderson | 1 |
| Plant | 1 |
| D Cu | 1 |
| Bryan | 1 |
| JohnCassian | 1 |
| Maya | 1 |
| michaelweagley | 1 |
| Nelson | 1 |
| bmg | 1 |

**Supporters detected:** Mark, ilyag, lisonok (badge ⭐/♥ seen in cache; supporter *type* not recoverable).

## 3. Engagement

Prayer-mark counts are real aggregates from each card. The distribution:

| Times prayed | # prayers |
|---:|---:|
| 0 | 1 |
| 1 | 5 |
| 2 | 21 |
| 3 | 27 |
| 4 | 121 |
| 5 | 51 |
| 6 | 22 |
| 7 | 5 |
| 8 | 2 |
| 9 | 4 |

For **4 prayers** a per-person who-prayed log was additionally recovered (those prayers' `/marks` pages were cached), but each is **truncated** to the most recent marks (e.g. 118 of 197 on the busiest). See `data/prayer_mark_logs.csv`.

## 4. Other content preserved (reference HTML, not prayer data)

| Page | Bytes |
|---|---:|
| `/` | 34,356 |
| `/api/session/info` | 178 |
| `/auth/notifications` | 899 |
| `/auth/pending` | 20,008 |
| `/auth/status` | 0 |
| `/auth/status-check` | 2,127 |
| `/changelog` | 68,205 |
| `/donate` | 23,207 |
| `/login` | 7,242 |
| `/manifest.webmanifest` | 638 |
| `/menu` | 42,031 |
| `/nicene-creed` | 20,318 |
| `/prayer/20956027ab50484aa8b71a17be2bac29/marks` | 56,533 |
| `/prayer/2316a1c9ff24490290cff8e91073ad22/marks` | 22,009 |
| `/prayer/793adcde65634ffe8ab3058da4dab295/marks` | 112,714 |
| `/prayer/b5d95a86d4f24fac9b253cbe5eeae936/marks` | 29,055 |
| `/profile` | 32,603 |

## 5. What was NOT preserved

1. **Prayers posted after 2025-12-26** — no feed was fetched from the live server past that date, so later prayers aren't here.
2. **Who prayed each prayer, and when — mostly lost.** Aggregate counts survive for all 259 prayers, but per-user mark logs were cached for only **4** of them (and even those are truncated). For the rest, the named history is gone.
3. **Individual prayer detail pages** (`/prayer/<id>`) were never cached (we have content from the feed cards, not the standalone pages).
4. **Other users' profiles, the full user roster, invite tokens, auth/admin records, role assignments** — none of this lives in a client cache.
5. **Comments / activity logs / attribute history** beyond what a feed card rendered.
6. **2 prayers' original-request text** was not in the cache (the generated prayer survives).
7. **Real user registration dates / invite tree** — unknown (see fidelity note).

## 6. Import fidelity / synthetic & derived data (read before importing)

- **User accounts are scaffolded.** Join dates are **synthetic** (set to the earliest recovered prayer date, 2025-06-11) EXCEPT `Mark`, whose real join date `2025-07-02` and admin+supporter status were recovered from the profile page. Re-creating users is required because prayers can't import without their authors existing.
- **`Mark` attribution is inferred:** 101 prayers rendered as “by you” in the logged-in cache (session displayName `Mark` on every device) and are attributed to Mark.
- **Prayer-mark counts are NOT re-created as rows** (we won't fabricate who/when). Only the 4 prayers with a recovered named log get real `PrayerMark` rows (in the import files); all other counts live in `data/prayers.json` / `prayers.csv` only.
- **`daily_priority` and `archived` flags are carried in `data/prayers.json` only**, not in the per-prayer import files (they don't fit the single-prayer archive grammar). Apply separately if wanted.
- **Timestamps in the import files are minute-precision** (the archive format's resolution); exact second-precision marks for the 4 logged prayers are in `data/prayer_mark_logs.csv`.
- **Original request / generated prayer were whitespace-collapsed to single lines** during recovery (original line breaks not preserved).
- **1 prayer's request contains a colon**, which the native `import prayer` parser skips — its full text is preserved in `data/prayers.json`.
