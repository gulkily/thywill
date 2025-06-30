#!/usr/bin/env python3
"""
Debug Archive Structure

This script examines the actual structure and content of text archives
to understand why the restoration script isn't finding data.
"""

import os
import sys
from pathlib import Path

def main():
    print("=== Text Archive Structure Debug ===")
    
    archive_dir = Path("./text_archives")
    
    if not archive_dir.exists():
        print(f"❌ Archive directory not found: {archive_dir.absolute()}")
        return
    
    print(f"✅ Archive directory found: {archive_dir.absolute()}")
    
    # Show top-level structure
    print(f"\nTop-level directories:")
    for item in sorted(archive_dir.iterdir()):
        if item.is_dir():
            file_count = len(list(item.glob("*")))
            print(f"  📁 {item.name}/ ({file_count} items)")
        else:
            print(f"  📄 {item.name}")
    
    # Check users directory
    users_dir = archive_dir / "users"
    if users_dir.exists():
        print(f"\n📁 Users directory:")
        user_files = list(users_dir.glob("*.txt"))
        print(f"  Found {len(user_files)} .txt files")
        
        for user_file in user_files[:3]:  # Show first 3
            print(f"  📄 {user_file.name}")
            try:
                content = user_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                print(f"     {len(lines)} lines, first few:")
                for line in lines[:5]:
                    if line.strip():
                        print(f"     '{line}'")
            except Exception as e:
                print(f"     Error reading: {e}")
    else:
        print(f"\n❌ No users directory found")
    
    # Check prayers directory
    prayers_dir = archive_dir / "prayers"
    if prayers_dir.exists():
        print(f"\n📁 Prayers directory:")
        
        # Show year structure
        year_dirs = [d for d in prayers_dir.iterdir() if d.is_dir()]
        print(f"  Found {len(year_dirs)} year directories: {[d.name for d in year_dirs]}")
        
        total_prayer_files = 0
        for year_dir in year_dirs:
            month_dirs = [d for d in year_dir.iterdir() if d.is_dir()]
            print(f"  📁 {year_dir.name}/ has {len(month_dirs)} month directories")
            
            for month_dir in month_dirs:
                prayer_files = list(month_dir.glob("*.txt"))
                total_prayer_files += len(prayer_files)
                print(f"    📁 {month_dir.name}/ has {len(prayer_files)} prayer files")
                
                # Show sample prayer file
                if prayer_files:
                    sample_file = prayer_files[0]
                    print(f"      📄 Sample: {sample_file.name}")
                    try:
                        content = sample_file.read_text(encoding='utf-8')
                        lines = content.split('\n')
                        print(f"         {len(lines)} lines, first few:")
                        for line in lines[:10]:
                            if line.strip():
                                print(f"         '{line}'")
                    except Exception as e:
                        print(f"         Error reading: {e}")
                    break
            
            if total_prayer_files > 0:
                break  # Only show details for first year with data
        
        print(f"  Total prayer files found: {total_prayer_files}")
    else:
        print(f"\n❌ No prayers directory found")
    
    # Check activity directory
    activity_dir = archive_dir / "activity"
    if activity_dir.exists():
        print(f"\n📁 Activity directory:")
        activity_files = list(activity_dir.glob("*.txt"))
        print(f"  Found {len(activity_files)} activity files")
        
        if activity_files:
            sample_file = activity_files[0]
            print(f"  📄 Sample: {sample_file.name}")
            try:
                content = sample_file.read_text(encoding='utf-8')
                lines = content.split('\n')
                print(f"     {len(lines)} lines, first few:")
                for line in lines[:5]:
                    if line.strip():
                        print(f"     '{line}'")
            except Exception as e:
                print(f"     Error reading: {e}")
    else:
        print(f"\n❌ No activity directory found")
    
    print(f"\n=== Summary ===")
    print(f"The restoration script expects:")
    print(f"  - text_archives/users/*.txt files with user registrations")
    print(f"  - text_archives/prayers/YYYY/MM/*.txt files with individual prayers")
    print(f"  - Prayer files should start with 'Prayer <id> by <username>'")
    print(f"  - User files should have lines like 'Date - username joined...'")

if __name__ == '__main__':
    main()