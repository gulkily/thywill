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
        
        # Add text_file_path column to user table for text archive tracking
        if 'text_file_path' not in user_columns:
            cursor.execute("ALTER TABLE user ADD COLUMN text_file_path TEXT")
            print("✅ Added text_file_path column to user table")
        
        # Check if new Prayer columns exist for text archive tracking
        cursor.execute("PRAGMA table_info(prayer)")
        prayer_columns = [column[1] for column in cursor.fetchall()]
        
        if 'text_file_path' not in prayer_columns:
            cursor.execute("ALTER TABLE prayer ADD COLUMN text_file_path TEXT")
            print("✅ Added text_file_path column to prayer table")
        
        # Check if new PrayerMark columns exist for text archive tracking
        cursor.execute("PRAGMA table_info(prayermark)")
        prayer_mark_columns = [column[1] for column in cursor.fetchall()]
        
        if 'text_file_path' not in prayer_mark_columns:
            cursor.execute("ALTER TABLE prayermark ADD COLUMN text_file_path TEXT")
            print("✅ Added text_file_path column to prayermark table")
        
        # Check if new PrayerAttribute columns exist for text archive tracking
        cursor.execute("PRAGMA table_info(prayer_attributes)")
        prayer_attribute_columns = [column[1] for column in cursor.fetchall()]
        
        if 'text_file_path' not in prayer_attribute_columns:
            cursor.execute("ALTER TABLE prayer_attributes ADD COLUMN text_file_path TEXT")
            print("✅ Added text_file_path column to prayer_attributes table")
        
        # Check if new PrayerActivityLog columns exist for text archive tracking
        cursor.execute("PRAGMA table_info(prayer_activity_log)")
        prayer_activity_log_columns = [column[1] for column in cursor.fetchall()]
        
        if 'text_file_path' not in prayer_activity_log_columns:
            cursor.execute("ALTER TABLE prayer_activity_log ADD COLUMN text_file_path TEXT")
            print("✅ Added text_file_path column to prayer_activity_log table")
        
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