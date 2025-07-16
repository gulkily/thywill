-- Add supporter status tracking fields to user table
-- Migration 010: supporter_fields

ALTER TABLE user ADD COLUMN is_supporter BOOLEAN DEFAULT FALSE;
ALTER TABLE user ADD COLUMN supporter_since DATETIME DEFAULT NULL;
ALTER TABLE user ADD COLUMN supporter_type VARCHAR DEFAULT NULL;

-- Update existing records to have the default supporter status
UPDATE user SET is_supporter = FALSE WHERE is_supporter IS NULL;