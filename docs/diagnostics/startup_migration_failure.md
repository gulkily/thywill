# Startup Migration Failure Report

## Symptoms
- During `./thywill start`, the enhanced migration runner reports:
  - `Migration 001_initial_schema failed: no such column: user_id`
  - `Duplicate user migration failed: 'User' object has no attribute 'id'`
- Despite the errors, the app continues booting with defensive schema validation.

## Investigation Summary
1. **Initial migration script review** (`migrations/001_initial_schema/up.sql:1`).
   - The SQL definitions assume legacy column names such as `user.id`, `prayer.author_id`, `prayermark.user_id`, etc.
   - Current SQLModel models (for example `models.py:8` and `models.py:220`) use `display_name` as the `user` primary key, `prayer.author_username`, and `prayermark.username`.
   - When the auto-migrator reaches the index section (`migrations/001_initial_schema/up.sql:160`), SQLite raises `no such column: user_id` because those columns no longer exist.

2. **Duplicate-user helper review** (`migrations/duplicate_user_migration.py:57`).
   - The script selects `User` rows, then references `primary_user.id` and issues `UPDATE ... SET author_id = ...` (see lines ~75–120).
   - The current ORM model exposes `display_name` only (no `id` attribute) and the `prayer` table stores `author_username`; therefore every update statement targets non-existent fields, triggering `'User' object has no attribute 'id'`.

## Root Cause
Legacy migration artifacts were left behind after the schema pivot to username-based identifiers. The enhanced migration runner still attempts to rerun those files on startup when `AUTO_MIGRATE_ON_STARTUP=true`. Because the scripts reference obsolete columns, SQLite raises the observed errors. The accompanying duplicate-user cleanup script was also not updated for the new schema, so it fails for the same reason.

## Recommended Fixes
1. **Short-term (clear the startup noise quickly):**
   - Disable the automatic execution of these legacy migrations by setting `AUTO_MIGRATE_ON_STARTUP=false` in `.env`, and (optionally) gating the duplicate-user helper in `app.py` behind the same flag until the scripts are rewritten.
   - This keeps the existing defensive schema validation (`validate_schema_compatibility`) while stopping the failing migration attempts.

2. **Long-term (align tooling with the current schema):**
   - Update `migrations/001_initial_schema/up.sql` to match the live SQLModel field names (`display_name`, `author_username`, `prayermark.username`, etc.) *or* retire the file in favour of a fresh dump generated from the current models.
   - Refactor `migrations/duplicate_user_migration.py` to use `display_name` and the new column names (`session.username`, `prayer.author_username`, `InviteToken.created_by_user`, etc.).
   - After the SQL is corrected, re-enable `AUTO_MIGRATE_ON_STARTUP` if automated migrations are still desired.

## Status
- No code changes have been applied yet; the repository still contains the legacy scripts.
- Apply the short-term mitigation immediately to stop the warnings, then schedule the long-term cleanup to restore automated migrations.
