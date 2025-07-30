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

# Database path is now configured automatically in models.py

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import engine, User, Session as UserSession
from sqlmodel import Session, select

def _parse_system_snapshot(snapshot_file):
    """Parse system archive snapshot format to extract session data."""
    sessions = []
    
    with open(snapshot_file, 'r') as f:
        content = f.read()
    
    current_session = {}
    for line in content.split('\n'):
        original_line = line
        line = line.strip()
        
        if not line or line.startswith('#'):
            continue
            
        # Session header
        if line.startswith('Session ') and line.endswith(':'):
            # Process previous session if exists
            if current_session:
                sessions.append(_convert_snapshot_to_export_format(current_session))
            
            # Start new session
            session_id = line.replace('Session ', '').replace(':', '')
            current_session = {'id': session_id}
        
        # Session attributes - use original line to preserve indentation
        elif original_line.startswith('  ') and ':' in original_line:
            key, value = line.strip().split(':', 1)
            key = key.strip()
            value = value.strip()
            
            if key == 'User':
                # Extract username from "ilyag (ID: ilyag)" format
                current_session['username'] = value.split(' ')[0]
            elif key == 'Created':
                # Convert from datetime format to ISO format, handle microseconds
                if value and value != 'None':
                    current_session['created_at'] = value.replace(' ', 'T')
                else:
                    current_session['created_at'] = None
            elif key == 'Expires':
                # Convert from datetime format to ISO format, handle microseconds
                if value and value != 'None':
                    current_session['expires_at'] = value.replace(' ', 'T')
                else:
                    current_session['expires_at'] = None
            elif key == 'IP':
                current_session['ip_address'] = value if value != 'None' else None
            elif key == 'Device':
                current_session['device_info'] = value if value != 'Unknown' else None
            elif key == 'Fully authenticated':
                current_session['is_fully_authenticated'] = (value == 'True')
    
    # Process last session
    if current_session:
        sessions.append(_convert_snapshot_to_export_format(current_session))
    
    return sessions

def _convert_snapshot_to_export_format(session_data):
    """Convert snapshot format to export format."""
    return {
        'session_id': session_data.get('id'),
        'username': session_data.get('username'),
        'created_at': session_data.get('created_at'),
        'expires_at': session_data.get('expires_at'),
        'ip_address': session_data.get('ip_address'),
        'device_info': session_data.get('device_info'),
        'auth_request_id': None,  # Not available in snapshot
        'is_fully_authenticated': session_data.get('is_fully_authenticated', True)
    }

def main():
    print("=== Exporting Active User Sessions ===")
    
    with Session(engine) as session:
        # Get all sessions from database (don't filter by user existence)
        sessions = session.exec(select(UserSession)).all()
        
        # Export session data - include ALL sessions, not just ones with existing users
        session_export = []
        
        for user_session in sessions:
            session_data = {
                'session_id': user_session.id,
                'username': user_session.username,  # This is what we'll use to restore
                'created_at': user_session.created_at.isoformat(),
                'expires_at': user_session.expires_at.isoformat(),
                'ip_address': user_session.ip_address,
                'device_info': user_session.device_info,
                'auth_request_id': user_session.auth_request_id,
                'is_fully_authenticated': user_session.is_fully_authenticated
            }
            session_export.append(session_data)
        
        # Also try to include sessions from system archive snapshot (most recent ones)
        system_snapshot_file = "text_archives/system/current_state/active_sessions.txt"
        if os.path.exists(system_snapshot_file):
            print("  📄 Including sessions from system archive snapshot...")
            snapshot_sessions = _parse_system_snapshot(system_snapshot_file)
            
            # Add sessions that aren't already in the database export
            existing_ids = {s['session_id'] for s in session_export}
            for snapshot_session in snapshot_sessions:
                if snapshot_session['session_id'] not in existing_ids:
                    session_export.append(snapshot_session)
                    print(f"    ✅ Added session {snapshot_session['session_id'][:8]}... from snapshot")
        
        # Save to file
        with open('sessions_backup.json', 'w') as f:
            json.dump({
                'exported_at': datetime.now().isoformat(),
                'total_sessions': len(session_export),
                'sessions': session_export
            }, f, indent=2)
        
        print(f"Exported {len(session_export)} active sessions to sessions_backup.json")
        
        # Show summary
        active_users = set(s['username'] for s in session_export if s['username'])
        print(f"Active users: {sorted(active_users)}")
        
        # Show session IDs for debugging
        print("Session IDs exported:")
        for s in session_export:
            print(f"  - {s['session_id'][:8]}... ({s['username']}) expires {s['expires_at']}")

if __name__ == '__main__':
    main()