#!/usr/bin/env python3
"""
Restore Active User Sessions

This script restores user sessions that were exported before database reconstruction.
It maps the old session data to the new database schema (username-based or UUID-based).
"""

import os
import sys
import json
from datetime import datetime

# Set production mode for database access
os.environ['PRODUCTION_MODE'] = '1'

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import engine, User, Session as UserSession
from sqlmodel import Session, select

def main():
    print("=== Restoring Active User Sessions ===")
    
    # Check for sessions backup file
    backup_file = 'sessions_backup.json'
    if not os.path.exists(backup_file):
        print(f"❌ No sessions backup found: {backup_file}")
        print("Run 'python tools/export_active_sessions.py' before database restoration")
        return 1
    
    # Load exported sessions
    with open(backup_file, 'r') as f:
        session_data = json.load(f)
    
    sessions = session_data.get('sessions', [])
    exported_at = session_data.get('exported_at', 'unknown')
    
    print(f"📄 Found {len(sessions)} exported sessions from {exported_at}")
    
    if not sessions:
        print("✅ No sessions to restore")
        return 0
    
    with Session(engine) as db_session:
        # Check current database schema to determine restoration approach
        schema_type = detect_schema_type(db_session)
        
        print(f"🔍 Detected database schema: {schema_type}")
        
        if schema_type == 'username_based':
            restored_count = restore_sessions_username_based(db_session, sessions)
        else:
            restored_count = restore_sessions_uuid_based(db_session, sessions)
        
        print(f"✅ Restored {restored_count} user sessions")
        
        # Show which users can skip re-login
        if restored_count > 0:
            print(f"👥 Users who can skip re-login:")
            for sess in sessions[:restored_count]:
                print(f"   - {sess['username']}")
        
        return 0

def detect_schema_type(session):
    """Detect whether database uses username-based or UUID-based schema"""
    try:
        # Try to query session table structure
        result = session.exec(select(UserSession)).first()
        if result and hasattr(result, 'username'):
            return 'username_based'
        elif result and hasattr(result, 'user_id'):
            return 'uuid_based'
        else:
            # Check if table is empty - examine schema
            from sqlmodel import text
            columns = session.exec(text("PRAGMA table_info(session)")).all()
            column_names = [col[1] for col in columns]  # col[1] is column name
            
            if 'username' in column_names:
                return 'username_based'
            elif 'user_id' in column_names:
                return 'uuid_based'
            else:
                return 'unknown'
    except Exception as e:
        print(f"Warning: Could not detect schema type: {e}")
        return 'unknown'

def restore_sessions_username_based(db_session, sessions):
    """Restore sessions for username-based database schema"""
    print("📝 Restoring sessions for username-based schema...")
    
    restored_count = 0
    
    for sess_data in sessions:
        username = sess_data['username']
        
        # Check if user exists in new database
        user = db_session.exec(
            select(User).where(User.display_name == username)
        ).first()
        
        if not user:
            print(f"   ⚠️  User '{username}' not found in database - skipping session")
            continue
        
        try:
            # Create session record with username foreign key
            new_session = UserSession(
                id=sess_data['session_id'],
                username=username,  # Use username instead of user_id
                created_at=datetime.fromisoformat(sess_data['created_at']),
                expires_at=datetime.fromisoformat(sess_data['expires_at']),
                auth_request_id=sess_data.get('auth_request_id'),
                ip_address=sess_data.get('ip_address'),
                device_info=sess_data.get('device_info'),
                is_fully_authenticated=sess_data.get('is_fully_authenticated', True)
            )
            
            db_session.add(new_session)
            db_session.commit()
            
            print(f"   ✅ Restored session for {username}")
            restored_count += 1
            
        except Exception as e:
            db_session.rollback()
            print(f"   ❌ Failed to restore session for {username}: {e}")
    
    return restored_count

def restore_sessions_uuid_based(db_session, sessions):
    """Restore sessions for UUID-based database schema"""
    print("📝 Restoring sessions for UUID-based schema...")
    
    # Build username to user_id mapping
    users = db_session.exec(select(User)).all()
    username_to_id = {user.display_name: user.id for user in users}
    
    restored_count = 0
    
    for sess_data in sessions:
        username = sess_data['username']
        user_id = username_to_id.get(username)
        
        if not user_id:
            print(f"   ⚠️  User '{username}' not found in database - skipping session")
            continue
        
        try:
            # Create session record with user_id foreign key
            new_session = UserSession(
                id=sess_data['session_id'],
                user_id=user_id,  # Use user_id instead of username
                created_at=datetime.fromisoformat(sess_data['created_at']),
                expires_at=datetime.fromisoformat(sess_data['expires_at']),
                auth_request_id=sess_data.get('auth_request_id'),
                ip_address=sess_data.get('ip_address'),
                device_info=sess_data.get('device_info'),
                is_fully_authenticated=sess_data.get('is_fully_authenticated', True)
            )
            
            db_session.add(new_session)
            db_session.commit()
            
            print(f"   ✅ Restored session for {username}")
            restored_count += 1
            
        except Exception as e:
            db_session.rollback()
            print(f"   ❌ Failed to restore session for {username}: {e}")
    
    return restored_count

if __name__ == '__main__':
    sys.exit(main())