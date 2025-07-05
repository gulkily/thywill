-- Migration 007 Rollback: Restore religious preference system
--
-- WARNING: This rollback cannot fully restore the religious preference system
-- because the original data has been permanently removed.
--
-- This rollback would require:
-- 1. Restoring from backup data (if available)
-- 2. Re-adding the columns to the database schema
-- 3. Updating application code to support religious preferences again
--
-- For safety, this rollback is not implemented as it would require
-- extensive application changes and data restoration.

-- Rollback not supported for this migration
SELECT 'ERROR: Migration 007 rollback not supported - would require manual data restoration and application changes' as error;

-- Uncommenting the lines below would restore the schema but not the data:
-- ALTER TABLE user ADD COLUMN religious_preference VARCHAR;
-- ALTER TABLE user ADD COLUMN prayer_style VARCHAR;  
-- ALTER TABLE prayer ADD COLUMN target_audience VARCHAR DEFAULT 'all';