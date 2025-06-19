-- Remove text archive tracking columns

-- Remove text_file_path from prayer_activity_log table
ALTER TABLE prayer_activity_log DROP COLUMN text_file_path;

-- Remove text_file_path from prayer_attributes table
ALTER TABLE prayer_attributes DROP COLUMN text_file_path;

-- Remove text_file_path from prayermark table
ALTER TABLE prayermark DROP COLUMN text_file_path;

-- Remove text_file_path from prayer table
ALTER TABLE prayer DROP COLUMN text_file_path;

-- Remove text_file_path from user table
ALTER TABLE user DROP COLUMN text_file_path;