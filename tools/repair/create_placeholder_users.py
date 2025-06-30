#!/usr/bin/env python3
"""
Create Placeholder Users for Orphaned IDs

This script creates placeholder users for orphaned user IDs found in prayers
and prayer marks, so the database constraints are satisfied and the UI can
display something meaningful instead of errors.
"""

import os
import sys
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import engine, User, Prayer, PrayerMark
from sqlmodel import Session, select

def main():
    parser = argparse.ArgumentParser(description='Create placeholder users for orphaned IDs')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes only')
    parser.add_argument('--execute', action='store_true', help='Create the placeholder users')
    
    args = parser.parse_args()
    
    if not args.dry_run and not args.execute:
        print("Must specify --dry-run or --execute")
        return 1
    
    print("=== Creating Placeholder Users for Orphaned IDs ===")
    
    with Session(engine) as session:
        # Find all user IDs that exist
        existing_users = session.exec(select(User)).all()
        existing_user_ids = {user.id for user in existing_users}
        
        print(f"Found {len(existing_user_ids)} existing users")
        
        # Find all orphaned user IDs from prayers and marks
        all_prayers = session.exec(select(Prayer)).all()
        all_marks = session.exec(select(PrayerMark)).all()
        
        orphaned_ids = set()
        
        # Collect orphaned IDs from prayers
        for prayer in all_prayers:
            if prayer.author_id and prayer.author_id not in existing_user_ids:
                orphaned_ids.add(prayer.author_id)
        
        # Collect orphaned IDs from prayer marks
        for mark in all_marks:
            if mark.user_id and mark.user_id not in existing_user_ids:
                orphaned_ids.add(mark.user_id)
        
        print(f"Found {len(orphaned_ids)} unique orphaned user IDs")
        
        if not orphaned_ids:
            print("No orphaned IDs found - nothing to fix!")
            return 0
        
        # Show what we'll create
        for i, user_id in enumerate(sorted(orphaned_ids), 1):
            prayer_count = sum(1 for p in all_prayers if p.author_id == user_id)
            mark_count = sum(1 for m in all_marks if m.user_id == user_id)
            
            placeholder_name = f"DeletedUser{i}"
            print(f"  {user_id} -> '{placeholder_name}' ({prayer_count} prayers, {mark_count} marks)")
        
        if args.dry_run:
            print("\\n*** DRY RUN - No users created ***")
            return 0
        
        if args.execute:
            print("\\nCreating placeholder users...")
            
            created_count = 0
            for i, user_id in enumerate(sorted(orphaned_ids), 1):
                placeholder_name = f"DeletedUser{i}"
                
                try:
                    # Create placeholder user with the exact orphaned ID
                    placeholder_user = User(
                        id=user_id,  # Use the orphaned ID
                        display_name=placeholder_name,
                        religious_preference='unspecified',
                        created_at=datetime.now()
                    )
                    
                    session.add(placeholder_user)
                    session.commit()
                    
                    print(f"  ✅ Created {placeholder_name} with ID {user_id}")
                    created_count += 1
                    
                except Exception as e:
                    session.rollback()
                    print(f"  ❌ Failed to create {placeholder_name}: {e}")
            
            print(f"\\n=== Created {created_count} placeholder users ===")
            
            # Verify the fix worked
            print("\\nVerifying fix...")
            
            # Check prayers
            remaining_orphaned_prayers = []
            for prayer in all_prayers:
                if prayer.author_id and prayer.author_id not in existing_user_ids:
                    # Check if we just created this user
                    user = session.get(User, prayer.author_id)
                    if not user:
                        remaining_orphaned_prayers.append(prayer)
            
            # Check marks
            remaining_orphaned_marks = []
            for mark in all_marks:
                if mark.user_id and mark.user_id not in existing_user_ids:
                    # Check if we just created this user
                    user = session.get(User, mark.user_id)
                    if not user:
                        remaining_orphaned_marks.append(mark)
            
            if remaining_orphaned_prayers or remaining_orphaned_marks:
                print(f"  ⚠️  Still have {len(remaining_orphaned_prayers)} orphaned prayers and {len(remaining_orphaned_marks)} orphaned marks")
            else:
                print("  ✅ All orphaned references should now be resolved!")
                print("  ✅ Your UI should no longer show 'None' or missing authors!")
        
        return 0

if __name__ == '__main__':
    sys.exit(main())