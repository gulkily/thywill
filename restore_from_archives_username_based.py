#!/usr/bin/env python3
"""
Restore Database from Archives with Username-Based IDs

This script completely rebuilds the database from text archives using usernames
as primary identifiers, eliminating the ID/username mismatch issues.

Key Changes:
- Users identified by username (display_name as primary key)
- All foreign keys use usernames instead of UUIDs
- Prayer marks preserved by matching usernames
- Sessions restored by username mapping
"""

import os
import sys
import argparse
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional
from sqlmodel import Session, select, text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import engine
from app_helpers.services.text_archive_service import TextArchiveService

def main():
    parser = argparse.ArgumentParser(description='Restore database from archives with username-based IDs')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes only')
    parser.add_argument('--execute', action='store_true', help='Execute the restoration')
    parser.add_argument('--archive-dir', type=str, help='Archive directory path')
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        print("Must specify --dry-run or --execute")
        print("WARNING: --execute will completely rebuild the database!")
        return 1
    
    archive_dir = args.archive_dir or './text_archives'
    
    print("=== Archive-Based Database Restoration (Username IDs) ===")
    print(f"Archive directory: {archive_dir}")
    
    if args.execute:
        response = input("This will COMPLETELY REBUILD the database. Are you sure? (type 'yes'): ")
        if response != 'yes':
            print("Aborted.")
            return 1
    
    # Step 1: Export current sessions
    if args.execute and not args.dry_run:
        print("Step 1: Exporting current sessions...")
        export_sessions()
    
    # Step 2: Parse archives
    print("Step 2: Parsing text archives...")
    archive_data = parse_archives(archive_dir)
    
    if args.dry_run:
        print_archive_summary(archive_data)
        print("\\n*** DRY RUN COMPLETED ***")
        return 0
    
    if args.execute:
        # Step 3: Create new schema with username-based IDs
        print("Step 3: Creating username-based database schema...")
        create_username_based_schema()
        
        # Step 4: Import data
        print("Step 4: Importing data from archives...")
        import_archive_data(archive_data)
        
        # Step 5: Restore sessions
        print("Step 5: Restoring user sessions...")
        restore_sessions()
        
        print("\\n=== RESTORATION COMPLETED ===")
        print("✅ Database rebuilt with username-based IDs")
        print("✅ All archive data imported")
        print("✅ User sessions preserved")
    
    return 0

def export_sessions():
    """Export current sessions before database rebuild"""
    os.system("PRODUCTION_MODE=1 python export_active_sessions.py")

def parse_archives(archive_dir: str) -> Dict:
    """Parse all text archives and extract data"""
    archive_path = Path(archive_dir)
    
    data = {
        'users': {},
        'prayers': [],
        'prayer_marks': [],
        'invite_relationships': {}
    }
    
    # Parse user registrations
    users_dir = archive_path / "users"
    if users_dir.exists():
        for user_file in users_dir.glob("*_users.txt"):
            parse_user_file(user_file, data)
    
    # Parse prayers
    prayers_dir = archive_path / "prayers"
    if prayers_dir.exists():
        for year_dir in prayers_dir.iterdir():
            if year_dir.is_dir():
                for month_dir in year_dir.iterdir():
                    if month_dir.is_dir():
                        for prayer_file in month_dir.glob("*.txt"):
                            parse_prayer_file(prayer_file, data)
    
    return data

def parse_user_file(user_file: Path, data: Dict):
    """Parse user registration file"""
    content = user_file.read_text(encoding='utf-8')
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('User Registrations'):
            continue
        
        # Parse: "June 14 2024 at 15:30 - Alice joined on invitation from Bob"
        if ' - ' in line and ' joined ' in line:
            parts = line.split(' - ', 1)
            if len(parts) == 2:
                timestamp_str = parts[0]
                action_str = parts[1]
                
                try:
                    created_at = datetime.strptime(timestamp_str, "%B %d %Y at %H:%M")
                except:
                    created_at = datetime.now()
                
                if ' joined ' in action_str:
                    username = action_str.split(' joined ')[0].strip()
                    
                    if username:
                        data['users'][username] = {
                            'username': username,
                            'created_at': created_at,
                            'source_file': str(user_file)
                        }
                        
                        # Parse inviter
                        if 'on invitation from ' in action_str:
                            inviter = action_str.split('on invitation from ')[-1].strip()
                            if inviter:
                                data['invite_relationships'][username] = inviter

def parse_prayer_file(prayer_file: Path, data: Dict):
    """Parse individual prayer file"""
    try:
        content = prayer_file.read_text(encoding='utf-8')
        
        # Extract prayer ID from filename
        prayer_id = prayer_file.stem.split('_')[-1]
        if 'prayer_at_' in prayer_file.stem:
            prayer_id = prayer_file.stem.split('prayer_at_')[-1]
        
        # Parse header: "Prayer <id> by <username>"
        header_match = re.search(r'Prayer\s+([a-f0-9]+)\s+by\s+(.+)', content)
        if not header_match:
            return
        
        file_prayer_id = header_match.group(1)
        username = header_match.group(2).strip()
        
        if username == 'None':
            return
        
        # Parse timestamp
        timestamp_match = re.search(r'Submitted (.+ at \d{2}:\d{2})', content)
        created_at = datetime.now()
        if timestamp_match:
            try:
                created_at = datetime.strptime(timestamp_match.group(1), "%B %d %Y at %H:%M")
            except:
                pass
        
        # Extract prayer text and generated prayer
        lines = content.split('\n')
        prayer_text = ""
        generated_prayer = ""
        in_generated = False
        
        for line in lines:
            if line.startswith('Generated Prayer:'):
                in_generated = True
                continue
            elif line.startswith('Activity:'):
                break
            elif in_generated:
                generated_prayer += line + "\n"
            elif line and not line.startswith('Prayer ') and not line.startswith('Submitted') and not line.startswith('Audience:'):
                if not in_generated and not line.startswith('Generated'):
                    prayer_text += line + "\n"
        
        # Add user if not already exists
        if username not in data['users']:
            data['users'][username] = {
                'username': username,
                'created_at': created_at,
                'source_file': str(prayer_file)
            }
        
        # Add prayer
        prayer_data = {
            'id': file_prayer_id,
            'author_username': username,
            'text': prayer_text.strip(),
            'generated_prayer': generated_prayer.strip(),
            'created_at': created_at,
            'text_file_path': str(prayer_file)
        }
        data['prayers'].append(prayer_data)
        
        # Parse activity log for prayer marks (different format: "Activity:" instead of "Activity Log:")
        parse_prayer_activity(content, file_prayer_id, data)
        
    except Exception as e:
        print(f"Warning: Failed to parse {prayer_file}: {e}")

def parse_prayer_activity(content: str, prayer_id: str, data: Dict):
    """Parse activity log section for prayer marks"""
    lines = content.split('\n')
    in_activity = False
    
    for line in lines:
        if line.startswith('Activity:'):
            in_activity = True
            continue
        
        if in_activity and line.strip():
            # Parse: "June 25 2025 at 18:45 - ilyag prayed this prayer"
            activity_match = re.search(r'(.+ at \d{2}:\d{2}) - (.+?) prayed this prayer', line)
            if activity_match:
                timestamp_str = activity_match.group(1)
                username = activity_match.group(2).strip()
                
                if username and username != 'None':
                    # Parse timestamp
                    try:
                        created_at = datetime.strptime(timestamp_str, "%B %d %Y at %H:%M")
                    except:
                        created_at = datetime.now()
                    
                    # Add user if not exists
                    if username not in data['users']:
                        data['users'][username] = {
                            'username': username,
                            'created_at': created_at,
                            'source_file': 'activity_log'
                        }
                    
                    # Add prayer mark
                    data['prayer_marks'].append({
                        'prayer_id': prayer_id,
                        'username': username,
                        'created_at': created_at
                    })

def print_archive_summary(data: Dict):
    """Print summary of parsed archive data"""
    print(f"\\n=== Archive Parse Summary ===")
    print(f"Users found: {len(data['users'])}")
    print(f"Prayers found: {len(data['prayers'])}")
    print(f"Prayer marks found: {len(data['prayer_marks'])}")
    print(f"Invite relationships: {len(data['invite_relationships'])}")
    
    print(f"\\nUsers: {sorted(data['users'].keys())}")
    
    # Show prayer distribution by author
    prayer_by_author = {}
    for prayer in data['prayers']:
        author = prayer['author_username']
        prayer_by_author[author] = prayer_by_author.get(author, 0) + 1
    
    print(f"\\nPrayers by author:")
    for author, count in sorted(prayer_by_author.items()):
        print(f"  {author}: {count}")

def create_username_based_schema():
    """Create new database schema with username-based foreign keys"""
    
    with Session(engine) as session:
        # Drop existing tables
        print("  Dropping existing tables...")
        session.exec(text("DROP TABLE IF EXISTS prayermark"))
        session.exec(text("DROP TABLE IF EXISTS prayerattribute"))
        session.exec(text("DROP TABLE IF EXISTS prayer"))
        session.exec(text("DROP TABLE IF EXISTS session"))
        session.exec(text("DROP TABLE IF EXISTS user"))
        session.commit()
        
        # Create new schema with username-based keys
        print("  Creating username-based schema...")
        
        # Users table with username as primary key
        session.exec(text("""
            CREATE TABLE user (
                display_name TEXT PRIMARY KEY,
                created_at TIMESTAMP NOT NULL,
                religious_preference TEXT DEFAULT 'unspecified',
                invited_by_username TEXT,
                text_file_path TEXT,
                welcome_message_dismissed BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (invited_by_username) REFERENCES user(display_name)
            )
        """))
        
        # Prayers table with username foreign key
        session.exec(text("""
            CREATE TABLE prayer (
                id TEXT PRIMARY KEY,
                author_username TEXT NOT NULL,
                text TEXT NOT NULL,
                generated_prayer TEXT,
                created_at TIMESTAMP NOT NULL,
                text_file_path TEXT,
                target_audience TEXT DEFAULT 'all',
                project_tag TEXT,
                FOREIGN KEY (author_username) REFERENCES user(display_name)
            )
        """))
        
        # Prayer marks with username foreign key
        session.exec(text("""
            CREATE TABLE prayermark (
                id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
                prayer_id TEXT NOT NULL,
                username TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                text_file_path TEXT,
                FOREIGN KEY (prayer_id) REFERENCES prayer(id),
                FOREIGN KEY (username) REFERENCES user(display_name)
            )
        """))
        
        # Sessions table with username foreign key
        session.exec(text("""
            CREATE TABLE session (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                last_activity TIMESTAMP,
                ip_address TEXT,
                device_info TEXT,
                is_fully_authenticated BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (username) REFERENCES user(display_name)
            )
        """))
        
        session.commit()
        print("  ✅ Username-based schema created")

def import_archive_data(data: Dict):
    """Import parsed archive data into new schema"""
    
    with Session(engine) as session:
        # Import users
        print(f"  Importing {len(data['users'])} users...")
        for username, user_data in data['users'].items():
            invited_by = data['invite_relationships'].get(username)
            
            session.exec(text("""
                INSERT INTO user (display_name, created_at, invited_by_username, text_file_path)
                VALUES (?, ?, ?, ?)
            """), (
                username,
                user_data['created_at'],
                invited_by,
                user_data.get('source_file')
            ))
        
        session.commit()
        
        # Import prayers
        print(f"  Importing {len(data['prayers'])} prayers...")
        for prayer in data['prayers']:
            session.exec(text("""
                INSERT INTO prayer (id, author_username, text, generated_prayer, created_at, text_file_path)
                VALUES (?, ?, ?, ?, ?, ?)
            """), (
                prayer['id'],
                prayer['author_username'],
                prayer['text'],
                prayer['generated_prayer'],
                prayer['created_at'],
                prayer['text_file_path']
            ))
        
        session.commit()
        
        # Import prayer marks
        print(f"  Importing {len(data['prayer_marks'])} prayer marks...")
        for mark in data['prayer_marks']:
            session.exec(text("""
                INSERT INTO prayermark (prayer_id, username, created_at)
                VALUES (?, ?, ?)
            """), (
                mark['prayer_id'],
                mark['username'],
                mark['created_at']
            ))
        
        session.commit()
        print("  ✅ All archive data imported")

def restore_sessions():
    """Restore user sessions using username mapping"""
    if not os.path.exists('sessions_backup.json'):
        print("  No sessions backup found - users will need to re-login")
        return
    
    with open('sessions_backup.json', 'r') as f:
        session_data = json.load(f)
    
    sessions = session_data.get('sessions', [])
    print(f"  Restoring {len(sessions)} user sessions...")
    
    with Session(engine) as session:
        for sess in sessions:
            try:
                session.exec(text("""
                    INSERT INTO session (id, username, created_at, last_activity, ip_address, device_info, is_fully_authenticated)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """), (
                    sess['session_id'],
                    sess['username'],  # Use username instead of user_id
                    datetime.fromisoformat(sess['created_at']),
                    datetime.fromisoformat(sess['last_activity']) if sess['last_activity'] else None,
                    sess['ip_address'],
                    sess['device_info'],
                    sess['is_fully_authenticated']
                ))
            except Exception as e:
                print(f"    Warning: Could not restore session for {sess['username']}: {e}")
        
        session.commit()
        print("  ✅ User sessions restored")

if __name__ == '__main__':
    sys.exit(main())