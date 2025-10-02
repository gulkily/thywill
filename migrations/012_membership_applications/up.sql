-- Create table to store membership applications submitted by prospective members

CREATE TABLE IF NOT EXISTS membership_application (
    id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    essay TEXT NOT NULL,
    contact_info TEXT,
    ip_address TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at DATETIME NOT NULL,
    processed_at DATETIME,
    processed_by_user_id TEXT,
    invite_token TEXT,
    text_file_path TEXT,
    FOREIGN KEY (processed_by_user_id) REFERENCES user(display_name),
    FOREIGN KEY (invite_token) REFERENCES invitetoken(token)
);

CREATE INDEX IF NOT EXISTS idx_membership_application_status ON membership_application(status);
CREATE INDEX IF NOT EXISTS idx_membership_application_created_at ON membership_application(created_at);
