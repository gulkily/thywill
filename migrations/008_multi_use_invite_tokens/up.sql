-- Migration 008: Multi-use invite tokens - Forward migration
-- Add support for multi-use invite tokens with usage tracking

-- Add new columns to invitetoken table
ALTER TABLE invitetoken ADD COLUMN usage_count INTEGER DEFAULT 0;
ALTER TABLE invitetoken ADD COLUMN max_uses INTEGER DEFAULT NULL;

-- Create table to track individual token usage
CREATE TABLE invite_token_usage (
    id TEXT PRIMARY KEY,
    invite_token_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    claimed_at TIMESTAMP NOT NULL,
    ip_address TEXT,
    FOREIGN KEY (invite_token_id) REFERENCES invitetoken (token),
    FOREIGN KEY (user_id) REFERENCES user (display_name)
);

-- Set default max_uses for existing tokens (will be 1 to maintain backward compatibility)
-- Note: The actual value comes from DEFAULT_INVITE_MAX_USES environment variable
-- This is handled in the Python migration script

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_invite_token_usage_token ON invite_token_usage(invite_token_id);
CREATE INDEX IF NOT EXISTS idx_invite_token_usage_user ON invite_token_usage(user_id);