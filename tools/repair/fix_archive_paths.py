#!/usr/bin/env python3
"""
Script to fix archive paths in the database.

This script corrects database records that point to temporary/incorrect archive paths
and updates them to point to the actual archive files in text_archives/.
"""

import os
import sys
from pathlib import Path
from sqlmodel import Session, select

# Database path is now configured automatically in models.py

from models import engine, User, Prayer, PrayerMark, PrayerAttribute

def find_actual_archive_file(expected_path: str) -> str:
    """
    Given an expected archive path, try to find the actual file in text_archives/.
    
    Args:
        expected_path: The path stored in the database (might be wrong)
        
    Returns:
        Actual path if found, empty string if not found
    """
    if not expected_path:
        return ""
    
    # Extract filename from the expected path
    expected_filename = Path(expected_path).name
    
    # Search for this filename in text_archives/
    text_archives_base = Path("text_archives")
    
    # Search in prayers subdirectories
    for prayer_file in text_archives_base.rglob("*.txt"):
        if prayer_file.name == expected_filename:
            return str(prayer_file)
    
    return ""

def fix_archive_paths(dry_run: bool = False) -> dict:
    """
    Fix incorrect archive paths in the database.
    
    Args:
        dry_run: If True, only report what would be changed
        
    Returns:
        Dictionary with fix results and statistics
    """
    results = {
        'users_fixed': 0,
        'prayers_fixed': 0,
        'prayer_marks_fixed': 0,
        'prayer_attributes_fixed': 0,
        'users_not_found': 0,
        'prayers_not_found': 0,
        'prayer_marks_not_found': 0,
        'prayer_attributes_not_found': 0,
        'total_examined': 0,
        'changes': []
    }
    
    with Session(engine) as session:
        # Fix User archive paths
        users = list(session.exec(select(User)))
        for user in users:
            results['total_examined'] += 1
            
            if user.text_file_path and not os.path.exists(user.text_file_path):
                actual_path = find_actual_archive_file(user.text_file_path)
                
                if actual_path:
                    change_info = {
                        'type': 'User',
                        'id': user.id,
                        'name': user.display_name,
                        'old_path': user.text_file_path,
                        'new_path': actual_path
                    }
                    results['changes'].append(change_info)
                    
                    if not dry_run:
                        user.text_file_path = actual_path
                        session.add(user)
                    
                    results['users_fixed'] += 1
                else:
                    results['users_not_found'] += 1
        
        # Fix Prayer archive paths
        prayers = list(session.exec(select(Prayer)))
        for prayer in prayers:
            results['total_examined'] += 1
            
            if prayer.text_file_path and not os.path.exists(prayer.text_file_path):
                actual_path = find_actual_archive_file(prayer.text_file_path)
                
                if actual_path:
                    change_info = {
                        'type': 'Prayer',
                        'id': prayer.id,
                        'old_path': prayer.text_file_path,
                        'new_path': actual_path
                    }
                    results['changes'].append(change_info)
                    
                    if not dry_run:
                        prayer.text_file_path = actual_path
                        session.add(prayer)
                    
                    results['prayers_fixed'] += 1
                else:
                    results['prayers_not_found'] += 1
        
        # Fix PrayerMark archive paths
        prayer_marks = list(session.exec(select(PrayerMark)))
        for prayer_mark in prayer_marks:
            results['total_examined'] += 1
            
            if prayer_mark.text_file_path and not os.path.exists(prayer_mark.text_file_path):
                actual_path = find_actual_archive_file(prayer_mark.text_file_path)
                
                if actual_path:
                    change_info = {
                        'type': 'PrayerMark',
                        'id': prayer_mark.id,
                        'old_path': prayer_mark.text_file_path,
                        'new_path': actual_path
                    }
                    results['changes'].append(change_info)
                    
                    if not dry_run:
                        prayer_mark.text_file_path = actual_path
                        session.add(prayer_mark)
                    
                    results['prayer_marks_fixed'] += 1
                else:
                    results['prayer_marks_not_found'] += 1
        
        # Fix PrayerAttribute archive paths
        prayer_attributes = list(session.exec(select(PrayerAttribute)))
        for prayer_attr in prayer_attributes:
            results['total_examined'] += 1
            
            if prayer_attr.text_file_path and not os.path.exists(prayer_attr.text_file_path):
                actual_path = find_actual_archive_file(prayer_attr.text_file_path)
                
                if actual_path:
                    change_info = {
                        'type': 'PrayerAttribute',
                        'id': prayer_attr.id,
                        'old_path': prayer_attr.text_file_path,
                        'new_path': actual_path
                    }
                    results['changes'].append(change_info)
                    
                    if not dry_run:
                        prayer_attr.text_file_path = actual_path
                        session.add(prayer_attr)
                    
                    results['prayer_attributes_fixed'] += 1
                else:
                    results['prayer_attributes_not_found'] += 1
        
        # Commit all changes
        if not dry_run:
            session.commit()
    
    return results

def print_fix_report(results: dict, dry_run: bool):
    """Print a formatted fix report."""
    print("🔧 Archive Path Fix Report")
    print("=" * 40)
    print()
    
    if dry_run:
        print("⚠️  DRY RUN MODE - No changes made")
        print()
    
    print(f"📊 Summary:")
    print(f"  Total records examined: {results['total_examined']}")
    print(f"  Users fixed: {results['users_fixed']}")
    print(f"  Prayers fixed: {results['prayers_fixed']}")
    print(f"  Prayer marks fixed: {results['prayer_marks_fixed']}")
    print(f"  Prayer attributes fixed: {results['prayer_attributes_fixed']}")
    print()
    
    not_found_total = (results['users_not_found'] + results['prayers_not_found'] + 
                      results['prayer_marks_not_found'] + results['prayer_attributes_not_found'])
    
    if not_found_total > 0:
        print(f"⚠️  Archive files not found:")
        print(f"  Users: {results['users_not_found']}")
        print(f"  Prayers: {results['prayers_not_found']}")
        print(f"  Prayer marks: {results['prayer_marks_not_found']}")
        print(f"  Prayer attributes: {results['prayer_attributes_not_found']}")
        print()
    
    if results['changes']:
        print("📝 Changes made:" if not dry_run else "📝 Changes that would be made:")
        print()
        
        # Group changes by type
        changes_by_type = {}
        for change in results['changes']:
            change_type = change['type']
            if change_type not in changes_by_type:
                changes_by_type[change_type] = []
            changes_by_type[change_type].append(change)
        
        for change_type, changes in changes_by_type.items():
            print(f"  {change_type} fixes ({len(changes)}):")
            for change in changes[:5]:  # Show first 5 examples
                print(f"    • {change['id'][:8]}...")
                print(f"      Old: {change['old_path']}")
                print(f"      New: {change['new_path']}")
            
            if len(changes) > 5:
                print(f"    ... and {len(changes) - 5} more")
            print()
    
    total_fixes = (results['users_fixed'] + results['prayers_fixed'] + 
                   results['prayer_marks_fixed'] + results['prayer_attributes_fixed'])
    
    if total_fixes > 0:
        if not dry_run:
            print("✅ Archive path fixes completed successfully!")
            print()
            print("💡 Next steps:")
            print("  • Run analyze_production_issues.py to verify fixes")
            print("  • Test archive download functionality")
        else:
            print("✅ Fix analysis completed!")
            print()
            print("💡 To apply these fixes, run:")
            print("  python3 fix_archive_paths.py --apply")
    else:
        print("✅ No archive path fixes needed!")

if __name__ == "__main__":
    try:
        # Check command line arguments
        dry_run = True
        if len(sys.argv) > 1 and sys.argv[1] == "--apply":
            dry_run = False
            print("⚠️  APPLYING FIXES - Database will be modified")
            print()
        
        results = fix_archive_paths(dry_run=dry_run)
        print_fix_report(results, dry_run)
        
        # Exit with error code if some files couldn't be found
        not_found_total = (results['users_not_found'] + results['prayers_not_found'] + 
                          results['prayer_marks_not_found'] + results['prayer_attributes_not_found'])
        
        if not_found_total > 0:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Fix failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)