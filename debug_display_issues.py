#!/usr/bin/env python3
"""
Debug Display Issues Tool

This script investigates why prayers show no author names and why "None" 
appears in the "Who Has Prayed This Prayer" lists, even when the database
relationships appear correct.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import engine, User, Prayer, PrayerMark
from sqlmodel import Session, select

def main():
    print("=== Display Issues Debug Analysis ===")
    
    with Session(engine) as session:
        # Get a sample prayer and check its author resolution
        prayers = session.exec(select(Prayer)).all()[:5]
        
        print(f"\n1. Prayer Author Resolution Test:")
        print(f"Found {len(prayers)} prayers to test")
        
        for prayer in prayers:
            print(f"\nPrayer {prayer.id}:")
            print(f"  author_id: {prayer.author_id}")
            
            if prayer.author_id:
                # Try to get the author
                author = session.get(User, prayer.author_id)
                if author:
                    print(f"  ✅ Author found: '{author.display_name}'")
                else:
                    print(f"  ❌ Author NOT FOUND for ID: {prayer.author_id}")
            else:
                print(f"  ❌ author_id is NULL")
        
        # Check prayer marks resolution
        print(f"\n2. Prayer Mark User Resolution Test:")
        
        # Get prayer marks for the first prayer
        if prayers:
            test_prayer = prayers[0]
            marks = session.exec(
                select(PrayerMark).where(PrayerMark.prayer_id == test_prayer.id)
            ).all()
            
            print(f"Prayer {test_prayer.id} has {len(marks)} prayer marks:")
            
            for mark in marks:
                print(f"\n  Mark {mark.id}:")
                print(f"    user_id: {mark.user_id}")
                
                if mark.user_id:
                    user = session.get(User, mark.user_id)
                    if user:
                        print(f"    ✅ User found: '{user.display_name}'")
                    else:
                        print(f"    ❌ User NOT FOUND for ID: {mark.user_id}")
                else:
                    print(f"    ❌ user_id is NULL")
        
        # Check for common query patterns used in the app
        print(f"\n3. Common App Query Patterns Test:")
        
        # Test the pattern likely used in templates - JOIN query
        try:
            # This mimics how the app might query prayers with authors
            result = session.exec(
                select(Prayer, User)
                .join(User, Prayer.author_id == User.id, isouter=True)
            ).all()
            
            print(f"JOIN query returned {len(result)} results")
            
            # Check first few results
            for i, (prayer, user) in enumerate(result[:3]):
                if user:
                    print(f"  Prayer {prayer.id}: author='{user.display_name}'")
                else:
                    print(f"  Prayer {prayer.id}: author=NULL (this causes display issues!)")
                    
                    # For NULL authors, let's see if there's actually an author_id
                    if prayer.author_id:
                        actual_user = session.get(User, prayer.author_id)
                        if actual_user:
                            print(f"    🐛 BUG: Prayer has author_id {prayer.author_id} ('{actual_user.display_name}') but JOIN returned NULL!")
                        else:
                            print(f"    Expected: author_id {prayer.author_id} doesn't exist")
                    
        except Exception as e:
            print(f"  JOIN query failed: {e}")
        
        # Test prayer mark query pattern
        print(f"\n4. Prayer Mark Query Pattern Test:")
        
        if prayers:
            test_prayer = prayers[0]
            try:
                # This mimics how the app queries prayer marks with users
                mark_results = session.exec(
                    select(PrayerMark, User)
                    .join(User, PrayerMark.user_id == User.id, isouter=True)
                    .where(PrayerMark.prayer_id == test_prayer.id)
                ).all()
                
                print(f"Prayer {test_prayer.id} mark JOIN query returned {len(mark_results)} results")
                
                for mark, user in mark_results:
                    if user:
                        print(f"  Mark {mark.id}: user='{user.display_name}'")
                    else:
                        print(f"  Mark {mark.id}: user=NULL (this shows as 'None' in UI!)")
                        
                        # Check if there's actually a user_id
                        if mark.user_id:
                            actual_user = session.get(User, mark.user_id)
                            if actual_user:
                                print(f"    🐛 BUG: Mark has user_id {mark.user_id} ('{actual_user.display_name}') but JOIN returned NULL!")
                            else:
                                print(f"    Expected: user_id {mark.user_id} doesn't exist")
                                
            except Exception as e:
                print(f"  Prayer mark JOIN query failed: {e}")
        
        print(f"\n=== SUMMARY ===")
        print("If you see '🐛 BUG' messages above, that indicates the database has")
        print("valid relationships but the JOIN queries are failing, which would")
        print("cause the display issues you're seeing.")

if __name__ == '__main__':
    main()