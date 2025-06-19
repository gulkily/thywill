-- Add authentication and device tracking columns to session table

-- Add auth_request_id column to link sessions to authentication requests
ALTER TABLE session ADD COLUMN auth_request_id TEXT;

-- Add device_info column for browser/device identification
ALTER TABLE session ADD COLUMN device_info TEXT;

-- Add ip_address column for security tracking
ALTER TABLE session ADD COLUMN ip_address TEXT;

-- Add is_fully_authenticated flag for partial authentication states
ALTER TABLE session ADD COLUMN is_fully_authenticated BOOLEAN DEFAULT 1;