-- Initial schema migration for ThyWill application
-- This represents the current state of all tables as of the schema-only migration implementation

-- Note: PRAGMA statements are handled outside of transactions in the models.py file

-- User table
CREATE TABLE IF NOT EXISTS user (
    id VARCHAR PRIMARY KEY,
    display_name VARCHAR NOT NULL,
    created_at DATETIME NOT NULL,
    religious_preference VARCHAR(50) DEFAULT 'unspecified',
    prayer_style VARCHAR(100),
    invited_by_user_id VARCHAR,
    invite_token_used VARCHAR,
    welcome_message_dismissed BOOLEAN DEFAULT 0,
    text_file_path VARCHAR
);

-- Role table
CREATE TABLE IF NOT EXISTS role (
    id VARCHAR PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255),
    permissions VARCHAR NOT NULL,
    created_at DATETIME NOT NULL,
    created_by VARCHAR,
    is_system_role BOOLEAN NOT NULL,
    FOREIGN KEY (created_by) REFERENCES user (id)
);

-- User roles junction table
CREATE TABLE IF NOT EXISTS user_roles (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    role_id VARCHAR NOT NULL,
    granted_by VARCHAR,
    granted_at DATETIME NOT NULL,
    expires_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES user (id),
    FOREIGN KEY (role_id) REFERENCES role (id),
    FOREIGN KEY (granted_by) REFERENCES user (id)
);

-- Prayer table
CREATE TABLE IF NOT EXISTS prayer (
    id VARCHAR PRIMARY KEY,
    author_id VARCHAR NOT NULL,
    text VARCHAR NOT NULL,
    generated_prayer TEXT,
    project_tag VARCHAR,
    created_at DATETIME NOT NULL,
    flagged BOOLEAN NOT NULL DEFAULT 0,
    target_audience VARCHAR(50) DEFAULT 'all',
    text_file_path VARCHAR,
    is_foundational BOOLEAN DEFAULT 0,
    foundational_category VARCHAR(50),
    spiritual_purpose VARCHAR(255),
    prayer_context TEXT
);

-- Prayer attributes table (flexible metadata system)
CREATE TABLE IF NOT EXISTS prayer_attributes (
    id VARCHAR PRIMARY KEY,
    prayer_id VARCHAR NOT NULL,
    attribute_name VARCHAR(50) NOT NULL,
    attribute_value VARCHAR(255) DEFAULT 'true',
    created_at DATETIME NOT NULL,
    created_by VARCHAR,
    text_file_path VARCHAR,
    FOREIGN KEY (prayer_id) REFERENCES prayer (id),
    FOREIGN KEY (created_by) REFERENCES user (id)
);

-- Prayer activity log
CREATE TABLE IF NOT EXISTS prayer_activity_log (
    id VARCHAR PRIMARY KEY,
    prayer_id VARCHAR NOT NULL,
    user_id VARCHAR NOT NULL,
    action VARCHAR(50) NOT NULL,
    old_value VARCHAR(255),
    new_value VARCHAR(255),
    created_at DATETIME NOT NULL,
    text_file_path VARCHAR,
    FOREIGN KEY (prayer_id) REFERENCES prayer (id),
    FOREIGN KEY (user_id) REFERENCES user (id)
);

-- Prayer marks (user interactions)
CREATE TABLE IF NOT EXISTS prayermark (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    prayer_id VARCHAR NOT NULL,
    created_at DATETIME NOT NULL,
    text_file_path VARCHAR
);

-- Prayer skips (user interactions)
CREATE TABLE IF NOT EXISTS prayerskip (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    prayer_id VARCHAR NOT NULL,
    created_at DATETIME NOT NULL
);

-- Authentication system
CREATE TABLE IF NOT EXISTS authenticationrequest (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    device_info VARCHAR,
    ip_address VARCHAR,
    verification_code TEXT,
    created_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',
    approved_by_user_id VARCHAR,
    approved_at DATETIME
);

-- Authentication approvals
CREATE TABLE IF NOT EXISTS authapproval (
    id VARCHAR PRIMARY KEY,
    auth_request_id VARCHAR NOT NULL,
    approver_user_id VARCHAR NOT NULL,
    created_at DATETIME NOT NULL
);

-- Authentication audit log
CREATE TABLE IF NOT EXISTS authauditlog (
    id VARCHAR PRIMARY KEY,
    auth_request_id VARCHAR NOT NULL,
    action VARCHAR NOT NULL,
    actor_user_id VARCHAR,
    actor_type VARCHAR,
    details VARCHAR,
    ip_address VARCHAR,
    user_agent VARCHAR,
    created_at DATETIME NOT NULL
);

-- Session management
CREATE TABLE IF NOT EXISTS session (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    created_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    auth_request_id VARCHAR,
    device_info VARCHAR,
    ip_address VARCHAR,
    is_fully_authenticated BOOLEAN DEFAULT 1
);

-- Notification state tracking
CREATE TABLE IF NOT EXISTS notification_state (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    auth_request_id VARCHAR NOT NULL,
    notification_type VARCHAR(50) DEFAULT 'auth_request',
    is_read BOOLEAN DEFAULT 0,
    created_at DATETIME NOT NULL,
    read_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES user (id),
    FOREIGN KEY (auth_request_id) REFERENCES authenticationrequest (id)
);

-- Invite system
CREATE TABLE IF NOT EXISTS invitetoken (
    token VARCHAR PRIMARY KEY,
    created_by_user VARCHAR NOT NULL,
    used BOOLEAN DEFAULT 0,
    expires_at DATETIME NOT NULL,
    used_by_user_id VARCHAR
);

-- Security logging
CREATE TABLE IF NOT EXISTS securitylog (
    id VARCHAR PRIMARY KEY,
    event_type VARCHAR NOT NULL,
    user_id VARCHAR,
    ip_address VARCHAR,
    user_agent VARCHAR,
    details VARCHAR,
    created_at DATETIME NOT NULL
);

-- Changelog entries
CREATE TABLE IF NOT EXISTS changelogentry (
    commit_id VARCHAR(40) PRIMARY KEY,
    original_message VARCHAR NOT NULL,
    friendly_description VARCHAR,
    change_type VARCHAR(20),
    commit_date DATETIME NOT NULL,
    created_at DATETIME NOT NULL
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_prayer_attributes_prayer_attr ON prayer_attributes(prayer_id, attribute_name);
CREATE INDEX IF NOT EXISTS idx_prayer_attributes_attr_name ON prayer_attributes(attribute_name);
CREATE INDEX IF NOT EXISTS idx_prayer_marks_prayer_id ON prayermark(prayer_id);
CREATE INDEX IF NOT EXISTS idx_prayer_marks_user_id ON prayermark(user_id);
CREATE INDEX IF NOT EXISTS idx_prayers_created_at ON prayer(created_at);
CREATE INDEX IF NOT EXISTS idx_prayers_author_id ON prayer(author_id);
CREATE INDEX IF NOT EXISTS idx_prayer_activity_prayer_id ON prayer_activity_log(prayer_id);
CREATE INDEX IF NOT EXISTS idx_user_invited_by ON user(invited_by_user_id);
CREATE INDEX IF NOT EXISTS idx_invitetoken_used_by ON invitetoken(used_by_user_id);
CREATE INDEX IF NOT EXISTS idx_user_invite_token ON user(invite_token_used);