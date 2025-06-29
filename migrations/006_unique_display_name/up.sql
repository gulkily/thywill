-- Migration: Add unique constraint to display_name
-- Note: Duplicate user merging is handled by startup migration in app.py

-- Create table to log duplicate merges for audit trail  
CREATE TABLE IF NOT EXISTS user_merge_log (
    id VARCHAR(32) PRIMARY KEY,
    primary_user_id VARCHAR(32) NOT NULL,
    merged_user_id VARCHAR(32) NOT NULL,
    original_display_name VARCHAR NOT NULL,
    merge_timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    prayers_transferred INTEGER DEFAULT 0,
    sessions_transferred INTEGER DEFAULT 0,
    invites_transferred INTEGER DEFAULT 0,
    merge_reason VARCHAR(255) DEFAULT 'duplicate_display_name'
);

-- This constraint addition will be handled by the startup migration system
-- to ensure duplicates are merged first
-- CREATE UNIQUE INDEX IF NOT EXISTS idx_user_display_name_unique ON user(display_name);