-- Migration 009: Add token_type to invitetoken table for intent-based authentication
-- This enables distinguishing between new user registration and multi-device login tokens

-- Add token_type column with default value
ALTER TABLE invitetoken ADD COLUMN token_type VARCHAR(20) DEFAULT 'new_user';

-- Update any existing NULL values to 'new_user' for backward compatibility
UPDATE invitetoken SET token_type = 'new_user' WHERE token_type IS NULL;

-- Add index for performance on token_type queries
CREATE INDEX idx_invitetoken_token_type ON invitetoken(token_type);

-- Add index for token_type + created_by_user for efficient queries
CREATE INDEX idx_invitetoken_type_creator ON invitetoken(token_type, created_by_user);