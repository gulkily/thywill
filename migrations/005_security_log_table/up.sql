-- Create SecurityLog table for tracking security events

CREATE TABLE IF NOT EXISTS securitylog (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    user_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    details TEXT,
    created_at TIMESTAMP NOT NULL
);