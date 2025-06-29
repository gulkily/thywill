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
        valid_prayers = session.exec(
            select(Prayer).where(Prayer.author_id.is_not(None))
        ).limit(3).all()
        
        print(f'\nValid prayers (for comparison): {len(valid_prayers)} total')
        for p in valid_prayers:
            author = session.get(User, p.author_id)
            author_name = author.display_name if author else "UNKNOWN"
            print(f'  Prayer {p.id}: author_id={p.author_id} ("{author_name}")')

if __name__ == '__main__':
    main()