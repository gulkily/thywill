-- Migration 009 Down: Remove token_type column and related indexes

-- Drop indexes first
DROP INDEX IF EXISTS idx_invitetoken_type_creator;
DROP INDEX IF EXISTS idx_invitetoken_token_type;

-- Remove the token_type column
ALTER TABLE invitetoken DROP COLUMN token_type;