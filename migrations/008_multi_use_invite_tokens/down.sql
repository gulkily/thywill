-- Migration 008: Multi-use invite tokens - Rollback migration
-- Remove multi-use invite token support and restore original schema

-- Drop the usage tracking table
DROP TABLE IF EXISTS invite_token_usage;

-- Note: SQLite doesn't support DROP COLUMN, so we need to recreate the table
-- This is handled in the Python migration script's rollback() function

-- The rollback process:
-- 1. Drop current invitetoken table
-- 2. Rename backup table (invitetoken_backup_008) back to invitetoken
-- 3. Recreate original indexes

-- This comment serves as documentation for the rollback process
-- The actual rollback is implemented in migrate.py