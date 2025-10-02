-- Drop membership application table and its supporting indexes

DROP INDEX IF EXISTS idx_membership_application_status;
DROP INDEX IF EXISTS idx_membership_application_created_at;
DROP TABLE IF EXISTS membership_application;
