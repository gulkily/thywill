#!/usr/bin/env python3
"""
Migration script to copy session data from backup database to current database.
Handles the schema change from user_id to username.
"""

import sqlite3
import sys
from datetime import datetime

def migrate_sessions():
    """Copy session data from backup to current database, mapping user_id to username."""
    
    backup_db = 'backup/thywill.1751474527.db'
    current_db = 'thywill.db'
    
    try:
        # Connect to both databases
        backup_conn = sqlite3.connect(backup_db)
        current_conn = sqlite3.connect(current_db)
        
        backup_cursor = backup_conn.cursor()
        current_cursor = current_conn.cursor()
        
        print("Connected to databases successfully")
        
        # First, create a mapping from user_id to display_name using the backup database
        print("Building user_id to display_name mapping...")
        backup_cursor.execute("SELECT id, display_name FROM user")
        user_mapping = {user_id: display_name for user_id, display_name in backup_cursor.fetchall()}
        print(f"Found {len(user_mapping)} users in backup")
        
        # Get all sessions from backup
        backup_cursor.execute("""
            SELECT id, user_id, created_at, expires_at, auth_request_id, 
                   device_info, ip_address, is_fully_authenticated 
            FROM session
        """)
        backup_sessions = backup_cursor.fetchall()
        print(f"Found {len(backup_sessions)} sessions in backup")
        
        # Get existing session IDs from current database to avoid duplicates
        current_cursor.execute("SELECT id FROM session")
        existing_session_ids = {row[0] for row in current_cursor.fetchall()}
        print(f"Found {len(existing_session_ids)} existing sessions in current database")
        
        # Prepare to insert sessions
        inserted_count = 0
        skipped_count = 0
        
        for session in backup_sessions:
            session_id, user_id, created_at, expires_at, auth_request_id, device_info, ip_address, is_fully_authenticated = session
            
            # Skip if session already exists
            if session_id in existing_session_ids:
                skipped_count += 1
                continue
                
            # Map user_id to display_name
            display_name = user_mapping.get(user_id)
            if not display_name:
                print(f"Warning: Could not find display_name for user_id {user_id}, skipping session {session_id}")
                skipped_count += 1
                continue
            
            # Insert session into current database
            current_cursor.execute("""
                INSERT INTO session (id, username, created_at, expires_at, auth_request_id, 
                                   device_info, ip_address, is_fully_authenticated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, display_name, created_at, expires_at, auth_request_id, 
                  device_info, ip_address, is_fully_authenticated))
            
            inserted_count += 1
        
        # Commit changes
        current_conn.commit()
        
        print(f"\nMigration completed:")
        print(f"  - Inserted: {inserted_count} sessions")
        print(f"  - Skipped: {skipped_count} sessions (duplicates or missing users)")
        
        # Verify final count
        current_cursor.execute("SELECT COUNT(*) FROM session")
        final_count = current_cursor.fetchone()[0]
        print(f"  - Total sessions in current database: {final_count}")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        sys.exit(1)
    finally:
        if 'backup_conn' in locals():
            backup_conn.close()
        if 'current_conn' in locals():
            current_conn.close()

if __name__ == "__main__":
    print("Starting session migration...")
    migrate_sessions()
    print("Migration finished.")