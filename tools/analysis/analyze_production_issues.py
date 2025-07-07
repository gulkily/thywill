#!/usr/bin/env python3
"""
Script to analyze production data integrity issues after heal-archives.

This script will identify specific problems that healing might have missed.
"""

import os
import sys
from sqlmodel import Session, select, text
from collections import defaultdict, Counter

# Database path is now configured automatically in models.py

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from models import engine, User, Prayer, PrayerMark, PrayerAttribute

def analyze_data_integrity():
    """Analyze the current state of the database for integrity issues."""
    results = {
        'users': {},
        'prayers': {},
        'prayer_marks': {},
        'prayer_attributes': {},
        'archive_paths': {},
        'integrity_issues': []
    }
    
    with Session(engine) as session:
        # User analysis
        users = list(session.exec(select(User)))
        results['users']['total'] = len(users)
        results['users']['with_archive_paths'] = len([u for u in users if u.text_file_path])
        results['users']['without_archive_paths'] = len([u for u in users if not u.text_file_path])
        
        # Religious preference distribution
        religious_prefs = Counter(u.religious_preference or 'unspecified' for u in users)
        results['users']['religious_preferences'] = dict(religious_prefs)
        
        # Invite tree analysis
        results['users']['with_inviter'] = len([u for u in users if u.invited_by_user_id])
        results['users']['without_inviter'] = len([u for u in users if not u.invited_by_user_id])
        
        # Prayer analysis
        prayers = list(session.exec(select(Prayer)))
        results['prayers']['total'] = len(prayers)
        results['prayers']['with_archive_paths'] = len([p for p in prayers if p.text_file_path])
        results['prayers']['without_archive_paths'] = len([p for p in prayers if not p.text_file_path])
        results['prayers']['flagged'] = len([p for p in prayers if p.flagged])
        
        # Target audience distribution
        target_audiences = Counter(p.target_audience for p in prayers)
        results['prayers']['target_audiences'] = dict(target_audiences)
        
        # Author relationship integrity
        author_ids = set(p.author_id for p in prayers)
        user_ids = set(u.id for u in users)
        orphaned_prayer_authors = author_ids - user_ids
        results['prayers']['orphaned_authors'] = len(orphaned_prayer_authors)
        
        if orphaned_prayer_authors:
            results['integrity_issues'].append(f"Found {len(orphaned_prayer_authors)} prayers with missing authors")
            # Find specific orphaned prayers
            orphaned_prayers = [p for p in prayers if p.author_id in orphaned_prayer_authors]
            results['prayers']['orphaned_prayers'] = [
                {
                    'id': p.id,
                    'author_id': p.author_id,
                    'target_audience': p.target_audience,
                    'text_preview': p.text[:50] + "..." if len(p.text) > 50 else p.text
                }
                for p in orphaned_prayers[:5]  # Show first 5 examples
            ]
        
        # Prayer marks analysis
        prayer_marks = list(session.exec(select(PrayerMark)))
        results['prayer_marks']['total'] = len(prayer_marks)
        results['prayer_marks']['with_archive_paths'] = len([pm for pm in prayer_marks if pm.text_file_path])
        
        # Mark integrity - check for orphaned marks
        mark_prayer_ids = set(pm.prayer_id for pm in prayer_marks)
        prayer_ids = set(p.id for p in prayers)
        orphaned_mark_prayers = mark_prayer_ids - prayer_ids
        results['prayer_marks']['orphaned_prayer_refs'] = len(orphaned_mark_prayers)
        
        mark_user_ids = set(pm.user_id for pm in prayer_marks)
        orphaned_mark_users = mark_user_ids - user_ids
        results['prayer_marks']['orphaned_user_refs'] = len(orphaned_mark_users)
        
        if orphaned_mark_prayers:
            results['integrity_issues'].append(f"Found {len(orphaned_mark_prayers)} prayer marks referencing non-existent prayers")
        if orphaned_mark_users:
            results['integrity_issues'].append(f"Found {len(orphaned_mark_users)} prayer marks referencing non-existent users")
        
        # Prayer attributes analysis
        prayer_attributes = list(session.exec(select(PrayerAttribute)))
        results['prayer_attributes']['total'] = len(prayer_attributes)
        results['prayer_attributes']['with_archive_paths'] = len([pa for pa in prayer_attributes if pa.text_file_path])
        
        # Attribute type distribution
        attribute_names = Counter(pa.attribute_name for pa in prayer_attributes)
        results['prayer_attributes']['types'] = dict(attribute_names)
        
        # Attribute integrity - check for orphaned attributes
        attr_prayer_ids = set(pa.prayer_id for pa in prayer_attributes)
        orphaned_attr_prayers = attr_prayer_ids - prayer_ids
        results['prayer_attributes']['orphaned_prayer_refs'] = len(orphaned_attr_prayers)
        
        if orphaned_attr_prayers:
            results['integrity_issues'].append(f"Found {len(orphaned_attr_prayers)} prayer attributes referencing non-existent prayers")
        
        # Visibility analysis - find prayers that might not be visible
        invisible_prayers = []
        for prayer in prayers:
            if prayer.flagged:
                continue  # Flagged prayers are intentionally hidden
                
            # Check if prayer is archived
            is_archived = any(pa.attribute_name == 'archived' for pa in prayer_attributes if pa.prayer_id == prayer.id)
            if is_archived:
                continue  # Archived prayers are intentionally hidden from main feeds
            
            # Check if prayer has compatible viewers
            has_viewers = False
            if prayer.target_audience == 'all':
                has_viewers = len(users) > 0
            elif prayer.target_audience == 'christians_only':
                christian_users = [u for u in users if u.religious_preference == 'christian']
                has_viewers = len(christian_users) > 0
            
            if not has_viewers:
                invisible_prayers.append({
                    'id': prayer.id,
                    'target_audience': prayer.target_audience,
                    'author_id': prayer.author_id,
                    'text_preview': prayer.text[:50] + "..." if len(prayer.text) > 50 else prayer.text
                })
        
        results['prayers']['invisible'] = len(invisible_prayers)
        results['prayers']['invisible_examples'] = invisible_prayers[:5]
        
        if invisible_prayers:
            results['integrity_issues'].append(f"Found {len(invisible_prayers)} prayers that are invisible (no compatible viewers)")
        
        # Archive path analysis
        archive_paths = []
        for item in users + prayers + prayer_marks + prayer_attributes:
            if hasattr(item, 'text_file_path') and item.text_file_path:
                archive_paths.append(item.text_file_path)
        
        results['archive_paths']['total'] = len(archive_paths)
        results['archive_paths']['unique'] = len(set(archive_paths))
        
        # Check for missing archive files
        missing_files = []
        for path in set(archive_paths):
            if path and not path.startswith('disabled_archive_') and not os.path.exists(path):
                missing_files.append(path)
        
        results['archive_paths']['missing_files'] = len(missing_files)
        results['archive_paths']['missing_examples'] = missing_files[:5]
        
        if missing_files:
            results['integrity_issues'].append(f"Found {len(missing_files)} database records pointing to missing archive files")
    
    return results

def print_analysis_report(results):
    """Print a formatted analysis report."""
    print("🔍 Production Data Integrity Analysis")
    print("=" * 50)
    print()
    
    # User summary
    print("👥 USERS")
    print("-" * 20)
    print(f"Total users: {results['users']['total']}")
    print(f"With archive paths: {results['users']['with_archive_paths']}")
    print(f"Without archive paths: {results['users']['without_archive_paths']}")
    print(f"With inviter: {results['users']['with_inviter']}")
    print(f"Without inviter: {results['users']['without_inviter']}")
    print(f"Religious preferences: {results['users']['religious_preferences']}")
    print()
    
    # Prayer summary
    print("🙏 PRAYERS")
    print("-" * 20)
    print(f"Total prayers: {results['prayers']['total']}")
    print(f"With archive paths: {results['prayers']['with_archive_paths']}")
    print(f"Without archive paths: {results['prayers']['without_archive_paths']}")
    print(f"Flagged: {results['prayers']['flagged']}")
    print(f"Orphaned authors: {results['prayers']['orphaned_authors']}")
    print(f"Invisible (no viewers): {results['prayers']['invisible']}")
    print(f"Target audiences: {results['prayers']['target_audiences']}")
    print()
    
    if results['prayers'].get('orphaned_prayers'):
        print("Orphaned Prayer Examples:")
        for prayer in results['prayers']['orphaned_prayers']:
            print(f"  • Prayer {prayer['id'][:8]}... by {prayer['author_id'][:8]}... ({prayer['target_audience']})")
            print(f"    Text: {prayer['text_preview']}")
        print()
    
    if results['prayers'].get('invisible_examples'):
        print("Invisible Prayer Examples:")
        for prayer in results['prayers']['invisible_examples']:
            print(f"  • Prayer {prayer['id'][:8]}... ({prayer['target_audience']})")
            print(f"    Text: {prayer['text_preview']}")
        print()
    
    # Prayer marks summary
    print("✓ PRAYER MARKS")
    print("-" * 20)
    print(f"Total marks: {results['prayer_marks']['total']}")
    print(f"With archive paths: {results['prayer_marks']['with_archive_paths']}")
    print(f"Orphaned prayer refs: {results['prayer_marks']['orphaned_prayer_refs']}")
    print(f"Orphaned user refs: {results['prayer_marks']['orphaned_user_refs']}")
    print()
    
    # Prayer attributes summary
    print("🏷️  PRAYER ATTRIBUTES")
    print("-" * 20)
    print(f"Total attributes: {results['prayer_attributes']['total']}")
    print(f"With archive paths: {results['prayer_attributes']['with_archive_paths']}")
    print(f"Orphaned prayer refs: {results['prayer_attributes']['orphaned_prayer_refs']}")
    print(f"Attribute types: {results['prayer_attributes']['types']}")
    print()
    
    # Archive paths summary
    print("📁 ARCHIVE PATHS")
    print("-" * 20)
    print(f"Total archive path references: {results['archive_paths']['total']}")
    print(f"Unique archive files: {results['archive_paths']['unique']}")
    print(f"Missing archive files: {results['archive_paths']['missing_files']}")
    
    if results['archive_paths'].get('missing_examples'):
        print("Missing Archive File Examples:")
        for path in results['archive_paths']['missing_examples']:
            print(f"  • {path}")
        print()
    
    # Integrity issues summary
    print("⚠️  INTEGRITY ISSUES")
    print("-" * 30)
    if results['integrity_issues']:
        for issue in results['integrity_issues']:
            print(f"❌ {issue}")
        print()
        print("🔧 RECOMMENDED ACTIONS:")
        print("1. Run heal-orphaned-prayers to fix prayers with no compatible viewers")
        print("2. Clean up orphaned database references")
        print("3. Verify or recreate missing archive files")
        print("4. Check user invite tree integrity")
        print()
    else:
        print("✅ No integrity issues detected!")
        print()

if __name__ == "__main__":
    try:
        results = analyze_data_integrity()
        print_analysis_report(results)
        
        # Exit with error code if issues found
        if results['integrity_issues']:
            sys.exit(1)
        else:
            print("🎉 Database integrity looks good!")
            sys.exit(0)
            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)