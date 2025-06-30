#!/usr/bin/env python3
"""
Import Missing Users from Text Archives

This script identifies and imports users that exist in text archives but are missing
from the database after a restoration process.
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Set
from sqlmodel import Session, select, text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import engine

def main():
    parser = argparse.ArgumentParser(description='Import missing users from text archives')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes only')
    parser.add_argument('--execute', action='store_true', help='Execute the import')
    parser.add_argument('--archive-dir', type=str, default='./text_archives', help='Archive directory path')
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        print("Must specify --dry-run or --execute")
        return 1
    
    print("=== Missing User Import Tool ===")
    print(f"Archive directory: {args.archive_dir}")
    
    # Step 1: Get current users from database
    current_users = get_current_users()
    print(f"Current users in database: {len(current_users)}")
    
    # Step 2: Parse users from archives
    archive_users = parse_archive_users(args.archive_dir)
    print(f"Users found in archives: {len(archive_users)}")
    
    # Step 3: Find missing users
    missing_users = find_missing_users(current_users, archive_users)
    print(f"Missing users to import: {len(missing_users)}")
    
    if not missing_users:
        print("✅ No missing users found - all archive users are in database")
        return 0
    
    # Step 4: Show missing users
    print("\nMissing users:")
    for username, data in missing_users.items():
        invited_by = data.get('invited_by', 'None')
        created_at = data['created_at'].strftime('%B %d %Y at %H:%M')
        print(f"  - {username} (joined {created_at}, invited by {invited_by})")
    
    if args.dry_run:
        print("\n*** DRY RUN COMPLETED ***")
        return 0
    
    if args.execute:
        print(f"\nImporting {len(missing_users)} missing users...")
        import_missing_users(missing_users)
        print("✅ Missing users imported successfully")
    
    return 0

def get_current_users() -> Set[str]:
    """Get set of usernames currently in database"""
    with Session(engine) as session:
        result = session.exec(select(text('display_name')).select_from(text('user')))
        return set(result.all())

def parse_archive_users(archive_dir: str) -> Dict[str, Dict]:
    """Parse all users from text archives"""
    archive_path = Path(archive_dir)
    users = {}
    
    # Parse user registration files
    users_dir = archive_path / "users"
    if users_dir.exists():
        for user_file in users_dir.glob("*_users.txt"):
            print(f"Parsing: {user_file}")
            parse_user_file(user_file, users)
    
    return users

def parse_user_file(user_file: Path, users: Dict[str, Dict]):
    """Parse individual user registration file"""
    try:
        content = user_file.read_text(encoding='utf-8')
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('User Registrations'):
                continue
            
            # Parse: "June 16 2025 at 06:30 - Max joined on invitation from ilyag"
            if ' - ' in line and ' joined ' in line:
                parts = line.split(' - ', 1)
                if len(parts) == 2:
                    timestamp_str = parts[0]
                    action_str = parts[1]
                    
                    # Parse timestamp
                    try:
                        created_at = datetime.strptime(timestamp_str, "%B %d %Y at %H:%M")
                    except ValueError as e:
                        print(f"Warning: Could not parse timestamp '{timestamp_str}': {e}")
                        created_at = datetime.now()
                    
                    # Parse username and action
                    if ' joined ' in action_str:
                        username = action_str.split(' joined ')[0].strip()
                        
                        if username:
                            users[username] = {
                                'username': username,
                                'created_at': created_at,
                                'source_file': str(user_file)
                            }
                            
                            # Parse inviter
                            if 'on invitation from ' in action_str:
                                inviter = action_str.split('on invitation from ')[-1].strip()
                                if inviter:
                                    users[username]['invited_by'] = inviter
                            elif 'joined directly' in action_str:
                                users[username]['invited_by'] = None
    
    except Exception as e:
        print(f"Error parsing {user_file}: {e}")

def find_missing_users(current_users: Set[str], archive_users: Dict[str, Dict]) -> Dict[str, Dict]:
    """Find users that exist in archives but not in database"""
    missing = {}
    
    for username, data in archive_users.items():
        if username not in current_users:
            missing[username] = data
    
    return missing

def import_missing_users(missing_users: Dict[str, Dict]):
    """Import missing users into database"""
    with Session(engine) as session:
        for username, data in missing_users.items():
            try:
                # Check if inviter exists in database
                invited_by = data.get('invited_by')
                if invited_by:
                    inviter_exists = session.exec(
                        select(text('1')).select_from(text('user')).where(text('display_name = ?')),
                        (invited_by,)
                    ).first()
                    
                    if not inviter_exists:
                        print(f"Warning: Inviter '{invited_by}' not found for user '{username}' - setting as orphaned")
                        invited_by = None
                
                # Insert user
                session.exec(text("""
                    INSERT INTO user (display_name, created_at, invited_by_username, text_file_path)
                    VALUES (?, ?, ?, ?)
                """), (
                    username,
                    data['created_at'],
                    invited_by,
                    data.get('source_file')
                ))
                
                print(f"  ✅ Imported: {username}")
                
            except Exception as e:
                print(f"  ❌ Failed to import {username}: {e}")
        
        session.commit()

if __name__ == '__main__':
    sys.exit(main())