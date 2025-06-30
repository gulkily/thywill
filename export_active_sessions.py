#!/usr/bin/env python3
"""
Export Active User Sessions

This script exports active user sessions before database restoration,
so they can be restored afterward and users don't need to re-authenticate.
"""

import os
import sys
import json
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import engine, User, Session as UserSession
from sqlmodel import Session, select

def main():
    print("=== Exporting Active User Sessions ===")
    
    with Session(engine) as session:
        # Get all active sessions with user info
        sessions = session.exec(select(UserSession)).all()
        users = session.exec(select(User)).all()
        
        # Create user lookup by ID
        user_lookup = {user.id: user for user in users}
        
        # Export session data
        session_export = []
        
        for user_session in sessions:
            user = user_lookup.get(user_session.user_id)
            if user:
                session_data = {
                    'session_id': user_session.id,
                    'username': user.display_name,  # This is what we'll use to restore
                    'user_id': user_session.user_id,
                    'created_at': user_session.created_at.isoformat(),
                    'last_activity': user_session.last_activity.isoformat() if user_session.last_activity else None,
                    'ip_address': user_session.ip_address,
                    'device_info': user_session.device_info,
                    'is_fully_authenticated': user_session.is_fully_authenticated
                }
                session_export.append(session_data)
        
        # Save to file
        with open('sessions_backup.json', 'w') as f:
            json.dump({
                'exported_at': datetime.now().isoformat(),
                'total_sessions': len(session_export),
                'sessions': session_export
            }, f, indent=2)
        
        print(f"Exported {len(session_export)} active sessions to sessions_backup.json")
        
        # Show summary
        active_users = set(s['username'] for s in session_export)
        print(f"Active users: {sorted(active_users)}")

if __name__ == '__main__':
    main()