#!/usr/bin/env python3
"""
Production Database Debug Tool

This script examines the current state of the production database to diagnose
data integrity issues. It shows orphaned prayers, prayer marks, and all users.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import engine, User, Prayer, PrayerMark
from sqlmodel import Session, select

def main():
    print("=== Production Database State Analysis ===")
    
    with Session(engine) as session:
        # Count and show orphaned prayers
        orphaned = session.exec(select(Prayer).where(Prayer.author_id.is_(None))).all()
        print(f'\nOrphaned prayers: {len(orphaned)}')
        
        if orphaned:
            print("First few orphaned prayers:")
            for p in orphaned[:5]:
                print(f'  Prayer {p.id}: author_id={p.author_id}, file_path={p.text_file_path}')
        
        # Count and show orphaned prayer marks
        orphaned_marks = session.exec(select(PrayerMark).where(PrayerMark.user_id.is_(None))).all()
        print(f'\nOrphaned prayer marks: {len(orphaned_marks)}')
        
        if orphaned_marks:
            print("First few orphaned prayer marks:")
            for m in orphaned_marks[:5]:
                print(f'  Mark {m.id}: user_id={m.user_id}, prayer_id={m.prayer_id}')
        
        # Show all users
        users = session.exec(select(User)).all()
        print(f'\nTotal users: {len(users)}')
        print("All users in database:")
        for u in users:
            print(f'  "{u.display_name}" -> {u.id}')
        
        # Show some prayers with valid authors for comparison
        all_valid_prayers = session.exec(
            select(Prayer).where(Prayer.author_id.is_not(None))
        ).all()
        
        print(f'\nValid prayers: {len(all_valid_prayers)} total')
        
        # Show first 3 prayers
        for p in all_valid_prayers[:3]:
            author = session.get(User, p.author_id)
            author_name = author.display_name if author else "UNKNOWN"
            print(f'  Prayer {p.id}: author_id={p.author_id} ("{author_name}")')
        
        # Check for prayers with invalid author_ids (exist but point to deleted users)
        print(f'\nChecking for prayers with invalid author references...')
        invalid_refs = 0
        for p in all_valid_prayers[:10]:  # Check first 10
            author = session.get(User, p.author_id)
            if not author:
                print(f'  Prayer {p.id}: author_id={p.author_id} -> USER NOT FOUND!')
                invalid_refs += 1
        
        if invalid_refs == 0:
            print("  All checked prayers have valid user references")
        
        # Show total counts
        total_prayers = len(all_valid_prayers)
        print(f'\nSUMMARY:')
        print(f'  Total prayers: {total_prayers}')
        print(f'  Orphaned prayers: {len(orphaned)}')
        print(f'  Valid prayers: {total_prayers}')
        print(f'  Users: {len(users)}')

if __name__ == '__main__':
    main()