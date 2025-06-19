-- Add invite tree tracking columns

-- Add invite tree columns to user table
ALTER TABLE user ADD COLUMN invited_by_user_id TEXT;
ALTER TABLE user ADD COLUMN invite_token_used TEXT;

-- Add usage tracking column to invitetoken table
ALTER TABLE invitetoken ADD COLUMN used_by_user_id TEXT;