-- Add auto-archive date fields to prayer table
-- Migration 012: auto_archive_date

-- Auto-archive suggestion fields
ALTER TABLE prayer ADD COLUMN suggested_archive_date DATETIME DEFAULT NULL;
ALTER TABLE prayer ADD COLUMN archive_suggestion_dismissed BOOLEAN DEFAULT FALSE;

-- Create index for efficient querying of approaching archive dates
CREATE INDEX IF NOT EXISTS idx_prayer_suggested_archive_date ON prayer(suggested_archive_date);

-- Initialize existing prayers with safe defaults
UPDATE prayer SET 
    suggested_archive_date = NULL,
    archive_suggestion_dismissed = FALSE
WHERE 
    suggested_archive_date IS NULL 
    OR archive_suggestion_dismissed IS NULL;