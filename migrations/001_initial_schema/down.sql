-- Rollback script for initial schema migration
-- WARNING: This will completely remove all tables and data

-- Drop indexes first
DROP INDEX IF EXISTS idx_user_invite_token;
DROP INDEX IF EXISTS idx_invitetoken_used_by;
DROP INDEX IF EXISTS idx_user_invited_by;
DROP INDEX IF EXISTS idx_prayer_activity_prayer_id;
DROP INDEX IF EXISTS idx_prayers_author_id;
DROP INDEX IF EXISTS idx_prayers_created_at;
DROP INDEX IF EXISTS idx_prayer_marks_user_id;
DROP INDEX IF EXISTS idx_prayer_marks_prayer_id;
DROP INDEX IF EXISTS idx_prayer_attributes_attr_name;
DROP INDEX IF EXISTS idx_prayer_attributes_prayer_attr;

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS changelogentry;
DROP TABLE IF EXISTS securitylog;
DROP TABLE IF EXISTS invitetoken;
DROP TABLE IF EXISTS notification_state;
DROP TABLE IF EXISTS session;
DROP TABLE IF EXISTS authauditlog;
DROP TABLE IF EXISTS authapproval;
DROP TABLE IF EXISTS authenticationrequest;
DROP TABLE IF EXISTS prayerskip;
DROP TABLE IF EXISTS prayermark;
DROP TABLE IF EXISTS prayer_activity_log;
DROP TABLE IF EXISTS prayer_attributes;
DROP TABLE IF EXISTS prayer;
DROP TABLE IF EXISTS user_roles;
DROP TABLE IF EXISTS role;
DROP TABLE IF EXISTS user;