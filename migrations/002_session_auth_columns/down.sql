-- Remove authentication and device tracking columns from session table

-- Remove is_fully_authenticated column
ALTER TABLE session DROP COLUMN is_fully_authenticated;

-- Remove ip_address column
ALTER TABLE session DROP COLUMN ip_address;

-- Remove device_info column
ALTER TABLE session DROP COLUMN device_info;

-- Remove auth_request_id column
ALTER TABLE session DROP COLUMN auth_request_id;