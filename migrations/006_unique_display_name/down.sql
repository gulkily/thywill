-- Rollback: Remove unique constraint on display_name
-- Note: This does not un-merge users - that would require manual intervention

-- Remove unique constraint
DROP INDEX IF EXISTS idx_user_display_name_unique;

-- Optionally keep merge log table for audit purposes
-- DROP TABLE IF EXISTS user_merge_log;