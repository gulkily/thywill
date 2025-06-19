-- Remove invite tree tracking columns

-- Remove usage tracking column from invitetoken table
ALTER TABLE invitetoken DROP COLUMN used_by_user_id;

-- Remove invite tree columns from user table
ALTER TABLE user DROP COLUMN invite_token_used;
ALTER TABLE user DROP COLUMN invited_by_user_id;