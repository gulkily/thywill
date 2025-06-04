"""
Database utility functions extracted from app.py
This module contains database migration and management functions.
"""

import sqlite3


def migrate_database():
    """Add new columns to existing database if they don't exist"""
    db_path = "thywill.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if new Session columns exist
        cursor.execute("PRAGMA table_info(session)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add missing columns to Session table
        if 'auth_request_id' not in columns:
            cursor.execute("ALTER TABLE session ADD COLUMN auth_request_id TEXT")
            print("✅ Added auth_request_id column to session table")
            
        if 'device_info' not in columns:
            cursor.execute("ALTER TABLE session ADD COLUMN device_info TEXT")
            print("✅ Added device_info column to session table")
            
        if 'ip_address' not in columns:
            cursor.execute("ALTER TABLE session ADD COLUMN ip_address TEXT")
            print("✅ Added ip_address column to session table")
            
        if 'is_fully_authenticated' not in columns:
            cursor.execute("ALTER TABLE session ADD COLUMN is_fully_authenticated BOOLEAN DEFAULT 1")
            print("✅ Added is_fully_authenticated column to session table")
        
        # Check if new User columns exist for invite tree
        cursor.execute("PRAGMA table_info(user)")
        user_columns = [column[1] for column in cursor.fetchall()]
        
        if 'invited_by_user_id' not in user_columns:
            cursor.execute("ALTER TABLE user ADD COLUMN invited_by_user_id TEXT")
            print("✅ Added invited_by_user_id column to user table")
            
        if 'invite_token_used' not in user_columns:
            cursor.execute("ALTER TABLE user ADD COLUMN invite_token_used TEXT")
            print("✅ Added invite_token_used column to user table")
        
        # Check if new InviteToken columns exist for invite tree
        cursor.execute("PRAGMA table_info(invitetoken)")
        invite_columns = [column[1] for column in cursor.fetchall()]
        
        if 'used_by_user_id' not in invite_columns:
            cursor.execute("ALTER TABLE invitetoken ADD COLUMN used_by_user_id TEXT")
            print("✅ Added used_by_user_id column to invitetoken table")
        
        # Check if SecurityLog table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='securitylog'")
        if not cursor.fetchone():
            cursor.execute("""
                CREATE TABLE securitylog (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    user_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    details TEXT,
                    created_at TIMESTAMP NOT NULL
                )
            """)
            print("✅ Created SecurityLog table")
        
        conn.commit()
        print("✅ Database migration completed successfully")
        
    except Exception as e:
        print(f"Database migration error: {e}")
        conn.rollback()
    finally:
        conn.close()