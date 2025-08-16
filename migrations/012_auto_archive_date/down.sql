-- Remove auto-archive date fields from prayer table
-- Migration 012 rollback: auto_archive_date

-- Drop indexes
DROP INDEX IF EXISTS idx_prayer_suggested_archive_date;

-- Remove columns
ALTER TABLE prayer DROP COLUMN suggested_archive_date;
ALTER TABLE prayer DROP COLUMN archive_suggestion_dismissed;