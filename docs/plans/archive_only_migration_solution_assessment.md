# Archive-Only Migration Strategy Assessment

## Objective
Evaluate whether ThyWill can retire SQL migration scripts entirely and rely on archive-driven rebuilds (drop database → reconstruct from text archives) for schema evolution and deployments.

## Current Capabilities
- **Archive-first writes**: Prayers, user registrations, activity logs, and related metadata are written to text archives before the database (`app_helpers/services/archive_first_service.py`).
- **Importer + reconstructor**: `TextImporterService` and `CompleteSystemRecovery` (`app_helpers/services/database_recovery.py`) can rebuild most tables, including roles, invites, authentication, and notifications. CLI wrappers (`./thywill full-recovery`, `./thywill reconstruct-from-archives`) automate the process.
- **Defensive schema validation**: `validate_schema_compatibility()` adds missing columns at runtime, offering safety nets when the DB lags behind the archive schema.

## Benefits of Dropping Migrations
1. **Single source of truth** – Eliminates drift between SQL migrations and archive-first models; archives already record every authoritative change.
2. **Simpler deploys** – Deployment flow becomes "ship code + ensure archives are healthy", avoiding ordering/rollback issues with SQL scripts.
3. **Disaster recovery parity** – The same process used for post-incident rebuilds handles schema upgrades, so recovery paths stay tested.
4. **Less legacy debt** – Removes failing legacy scripts (`001_initial_schema`, duplicate-user merge) that no longer reflect the username-based schema.

## Risks & Requirements
| Area | Considerations |
| --- | --- |
| **Archive completeness** | Every table required for runtime must be represented in archives (see coverage report). Gaps (e.g., `PrayerSkip`, `InviteTokenUsage`) must be addressed before deleting migrations. |
| **Rebuild time** | Full reconstruction is slower than incremental migrations. Need benchmarks for production-size datasets to understand downtime. |
| **Operational tooling** | Must have scripted flow: export DB → drop → rebuild from archives → run verification (`validate_archive_consistency.py`, `recovery_report`). |
| **Testing discipline** | Schema changes must include archive schema updates + importer logic; PR review needs to enforce this since we lose database migration coverage. |
| **Roll-forward only** | Archive format changes should stay backward-compatible or ship conversion scripts; otherwise rebuilds on old archives may fail. |
| **Transactional windows** | Rebuild wipes sessions and transient state. Need process for staging downtime (announce, freeze writes, run rebuild, restore sessions if exported). |

## Feasibility Verdict
- **Technically feasible once archive gaps close.** The recovery tooling already exists and the database is largely a cache/index over the archives. However, outstanding coverage gaps and lack of automation make an immediate cutover risky.
- **Recommended path:**
  1. Archive coverage is complete (see `docs/diagnostics/text_archive_coverage.md`). Keep the matrix up to date with future schema changes.
  2. Build a scripted “archive migration” flow (backup DB, validate archives, wipe DB, run recovery, run post-checks).
  3. Pilot the archive-only process in staging; record timings and required manual steps.
  4. After successful pilot + documentation, deprecate legacy migrations and guard startup behind archive health checks instead.

## Next Actions
1. Write a runbook for archive-only schema upgrades, including downtime, command sequence, and validation.
2. Update CI to run recovery scripts in test mode so regressions surface before deploys.
3. Once above are complete, mark SQL migrations as deprecated and remove them from the startup pipeline.
