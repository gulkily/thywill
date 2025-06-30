#!/usr/bin/env python3
"""
Fix Orphaned User ID References

This script finds prayers and prayer marks that reference user IDs that no longer
exist in the users table and either creates the missing users from archives or
sets the references to NULL for proper handling.
"""

import os
import sys
import argparse
from pathlib import Path
import re

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import engine, User, Prayer, PrayerMark
from sqlmodel import Session, select
from app_helpers.services.text_archive_service import TextArchiveService

def main():
    parser = argparse.ArgumentParser(description='Fix orphaned user ID references')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes only')
    parser.add_argument('--nullify', action='store_true', help='Set orphaned references to NULL')
    parser.add_argument('--create-users', action='store_true', help='Try to create missing users from archives')
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.nullify and not args.create_users:
        print("Must specify --dry-run, --nullify, or --create-users")
        return 1
    
    print("=== Fixing Orphaned User ID References ===")
    
    with Session(engine) as session:
        # Find all user IDs that exist
        existing_users = session.exec(select(User)).all()
        existing_user_ids = {user.id for user in existing_users}
        
        print(f"Found {len(existing_user_ids)} existing users")
        
        # Find prayers with orphaned author_ids
        all_prayers = session.exec(select(Prayer)).all()
        orphaned_prayers = []
        
        for prayer in all_prayers:
            if prayer.author_id and prayer.author_id not in existing_user_ids:
                orphaned_prayers.append(prayer)
        
        print(f"Found {len(orphaned_prayers)} prayers with orphaned author_ids")
        
        # Find prayer marks with orphaned user_ids
        all_marks = session.exec(select(PrayerMark)).all()
        orphaned_marks = []
        
        for mark in all_marks:
            if mark.user_id and mark.user_id not in existing_user_ids:
                orphaned_marks.append(mark)
        
        print(f"Found {len(orphaned_marks)} prayer marks with orphaned user_ids")
        
        # Show unique orphaned IDs
        orphaned_prayer_ids = {p.author_id for p in orphaned_prayers}
        orphaned_mark_ids = {m.user_id for m in orphaned_marks}
        all_orphaned_ids = orphaned_prayer_ids | orphaned_mark_ids
        
        print(f"\\nUnique orphaned user IDs: {len(all_orphaned_ids)}")
        for user_id in sorted(all_orphaned_ids):
            prayer_count = sum(1 for p in orphaned_prayers if p.author_id == user_id)
            mark_count = sum(1 for m in orphaned_marks if m.user_id == user_id)
            print(f"  {user_id}: {prayer_count} prayers, {mark_count} marks")
        
        if args.dry_run:
            print("\\n*** DRY RUN - No changes made ***")
            return 0
        
        if args.create_users:
            print("\\nAttempting to create missing users from archives...")
            created_count = create_missing_users_from_archives(session, all_orphaned_ids)
            print(f"Created {created_count} users from archives")
        
        if args.nullify:
            print("\\nSetting orphaned references to NULL...")
            
            # Nullify prayer author_ids
            for prayer in orphaned_prayers:
                if prayer.author_id not in existing_user_ids:  # Double check
                    print(f"  Nullifying prayer {prayer.id} author_id: {prayer.author_id}")
                    prayer.author_id = None
                    session.add(prayer)
            
            # Nullify prayer mark user_ids  
            for mark in orphaned_marks:
                if mark.user_id not in existing_user_ids:  # Double check
                    print(f"  Nullifying prayer mark {mark.id} user_id: {mark.user_id}")
                    mark.user_id = None
                    session.add(mark)
            
            session.commit()
            print(f"Nullified {len(orphaned_prayers)} prayer references and {len(orphaned_marks)} mark references")
        
        print("\\n=== Fix completed ===")
        return 0

def create_missing_users_from_archives(session, orphaned_ids):
    """Try to create missing users by searching archives for usernames"""
    archive_service = TextArchiveService()
    created_count = 0
    
    # Extract usernames from archives
    archive_users = extract_users_from_archives(archive_service.base_dir)
    
    print(f"Found {len(archive_users)} users in archives")
    
    # For each orphaned ID, see if we can find a username in archives
    # This is tricky because we need to match old IDs to usernames
    # For now, we'll create users with placeholder names
    
    for user_id in orphaned_ids:
        # Try to find this user in archives by checking prayer files
        username = find_username_for_id_in_archives(user_id, archive_service.base_dir)
        
        if username:
            print(f"  Creating user {user_id} with name '{username}'")
            try:
                user = User(
                    id=user_id,  # Use the original ID
                    display_name=username,
                    religious_preference='unspecified'
                )
                session.add(user)
                session.commit()
                created_count += 1
            except Exception as e:
                print(f"    Failed to create user: {e}")
                session.rollback()
        else:
            print(f"  Could not find username for ID {user_id}")
    
    return created_count

def extract_users_from_archives(archive_dir):
    """Extract usernames from archive files"""
    users = {}
    
    # Scan prayer archives for usernames
    prayers_dir = Path(archive_dir) / "prayers"
    if prayers_dir.exists():
        for year_dir in prayers_dir.iterdir():
            if year_dir.is_dir():
                for month_dir in year_dir.iterdir():
                    if month_dir.is_dir():
                        for prayer_file in month_dir.glob("*.txt"):
                            try:
                                content = prayer_file.read_text(encoding='utf-8')
                                # Look for "Prayer <id> by <username>"
                                match = re.search(r'Prayer\\s+[a-f0-9]+\\s+by\\s+(.+)', content)
                                if match:
                                    username = match.group(1).strip()
                                    if username and username != 'None':
                                        users[username] = {'source': 'prayer'}
                            except Exception:
                                continue
    
    return users

def find_username_for_id_in_archives(user_id, archive_dir):
    """Try to find the username for a specific user ID by looking in archives"""
    # This is a heuristic approach - look for prayers with this ID in the filename or content
    prayers_dir = Path(archive_dir) / "prayers"
    
    if not prayers_dir.exists():
        return None
    
    # Search through prayer files for references to this user ID
    for year_dir in prayers_dir.iterdir():
        if year_dir.is_dir():
            for month_dir in year_dir.iterdir():
                if month_dir.is_dir():
                    for prayer_file in month_dir.glob("*.txt"):
                        try:
                            content = prayer_file.read_text(encoding='utf-8')
                            
                            # Look for the user ID in the content (maybe in activity logs)
                            if user_id in content:
                                # Try to extract username from the same file
                                match = re.search(r'Prayer\\s+[a-f0-9]+\\s+by\\s+(.+)', content)
                                if match:
                                    username = match.group(1).strip()
                                    if username and username != 'None':
                                        return username
                        except Exception:
                            continue
    
    return None

if __name__ == '__main__':
    sys.exit(main())