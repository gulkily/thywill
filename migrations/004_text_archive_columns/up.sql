-- Add text archive tracking columns for audit trail preservation

-- Add text_file_path to user table for registration tracking
ALTER TABLE user ADD COLUMN text_file_path TEXT;

-- Add text_file_path to prayer table for prayer archive tracking
ALTER TABLE prayer ADD COLUMN text_file_path TEXT;

-- Add text_file_path to prayermark table for interaction tracking
ALTER TABLE prayermark ADD COLUMN text_file_path TEXT;

-- Add text_file_path to prayer_attributes table for attribute change tracking
ALTER TABLE prayer_attributes ADD COLUMN text_file_path TEXT;

-- Add text_file_path to prayer_activity_log table for activity tracking
ALTER TABLE prayer_activity_log ADD COLUMN text_file_path TEXT;