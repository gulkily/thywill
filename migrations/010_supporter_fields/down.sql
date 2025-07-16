-- Remove supporter status tracking fields from user table
-- Migration 010 rollback: supporter_fields

-- Note: SQLite doesn't support DROP COLUMN, so we would need to recreate the table
-- This is a one-way migration in SQLite
-- For rollback, you would need to export data, drop table, recreate without columns, and reimport

-- This rollback is not implemented due to SQLite limitations
-- Manual rollback would require:
-- 1. Export all user data
-- 2. DROP TABLE user
-- 3. Recreate user table without supporter fields
-- 4. Reimport user data