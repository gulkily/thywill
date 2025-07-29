-- Remove prayer categorization fields from prayer table
-- Migration 011 rollback: prayer_categorization

-- Drop indexes first
DROP INDEX IF EXISTS idx_prayer_safety;
DROP INDEX IF EXISTS idx_prayer_categories;
DROP INDEX IF EXISTS idx_prayer_category;

-- Note: SQLite doesn't support DROP COLUMN, so this would require table recreation
-- This is noted as a limitation for future rollback consideration

-- For a complete rollback, you would need to:
-- 1. Export all prayer data (excluding categorization fields)
-- 2. DROP TABLE prayer
-- 3. Recreate prayer table without categorization fields
-- 4. Reimport prayer data

-- This rollback is marked as not implemented due to SQLite limitations
-- However, the categorization fields are designed to be non-breaking
-- and can safely remain with default values if the feature is disabled