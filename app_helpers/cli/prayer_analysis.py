#!/usr/bin/env python3
"""
Prayer Analysis CLI Module

Analyzes prayers for orphaned status and provides healing recommendations.
Can be run independently or called from the CLI script.
"""

import sys
from typing import List, Dict, Any
from collections import defaultdict
from sqlmodel import Session, select, and_
from models import engine, User, Prayer, PrayerAttribute


def analyze_orphaned_prayers() -> Dict[str, Any]:
    """
    Analyze prayers to find orphaned ones (prayers with no compatible viewers).
    
    Returns:
        Dict containing analysis results including orphaned prayers and statistics
    """
    results = {
        'total_prayers': 0,
        'orphaned_prayers': [],
        'user_preferences': {},
        'prayer_audiences': {},
        'visibility_rate': 0.0
    }
    
    with Session(engine) as session:
        # Get all prayers and users
        all_prayers = list(session.exec(select(Prayer)))
        all_users = list(session.exec(select(User)))
        
        results['total_prayers'] = len(all_prayers)
        
        # Analyze user religious preferences
        users_by_pref = defaultdict(int)
        for user in all_users:
            users_by_pref[user.religious_preference or 'unspecified'] += 1
        results['user_preferences'] = dict(users_by_pref)
        
        # Analyze prayer target audiences
        prayers_by_audience = defaultdict(int)
        for prayer in all_prayers:
            prayers_by_audience[prayer.target_audience] += 1
        results['prayer_audiences'] = dict(prayers_by_audience)
        
        # Find orphaned prayers
        orphaned_prayers = []
        
        for prayer in all_prayers:
            # Skip flagged prayers (they should be hidden)
            if prayer.flagged:
                continue
                
            # Skip archived prayers (they should be hidden from public feeds)
            stmt = select(PrayerAttribute).where(
                and_(
                    PrayerAttribute.prayer_id == prayer.id,
                    PrayerAttribute.attribute_name == 'archived'
                )
            )
            if session.exec(stmt).first():
                continue
            
            # Check if prayer has compatible viewers
            has_viewers = False
            
            if prayer.target_audience == 'all':
                # All users can see 'all' prayers
                has_viewers = len(all_users) > 0
            elif prayer.target_audience == 'christians_only':
                # Only Christian users can see Christian prayers
                christian_users = [u for u in all_users if u.religious_preference == 'christian']
                has_viewers = len(christian_users) > 0
            
            if not has_viewers:
                orphaned_prayers.append({
                    'id': prayer.id,
                    'target_audience': prayer.target_audience,
                    'created_at': prayer.created_at.isoformat() if prayer.created_at else None,
                    'text_preview': prayer.text[:50] + "..." if len(prayer.text) > 50 else prayer.text
                })
        
        results['orphaned_prayers'] = orphaned_prayers
        
        # Calculate visibility rate
        if results['total_prayers'] > 0:
            results['visibility_rate'] = ((results['total_prayers'] - len(orphaned_prayers)) / results['total_prayers']) * 100
        
        return results


def print_analysis_report(results: Dict[str, Any]) -> None:
    """Print a formatted analysis report to stdout."""
    print('🔍 Orphaned Prayer Analysis')
    print('=' * 50)
    print()
    
    print(f'📊 Total Prayers: {results["total_prayers"]}')
    print()
    
    # User religious preferences
    print('👥 User Religious Preferences:')
    for pref, count in results['user_preferences'].items():
        print(f'   {pref}: {count} users')
    print()
    
    # Prayer target audiences
    print('🎯 Prayer Target Audiences:')
    for audience, count in results['prayer_audiences'].items():
        print(f'   {audience}: {count} prayers')
    print()
    
    # Orphaned prayers analysis
    print('🔍 Orphaning Analysis:')
    print('-' * 30)
    
    orphaned_prayers = results['orphaned_prayers']
    
    if orphaned_prayers:
        print(f'❌ Found {len(orphaned_prayers)} orphaned prayers:')
        print()
        for prayer in orphaned_prayers:
            print(f'   Prayer ID: {prayer["id"][:8]}...')
            print(f'   Target Audience: {prayer["target_audience"]}')
            print(f'   Created: {prayer["created_at"]}')
            print(f'   Text: {prayer["text_preview"]}')
            print()
        
        print('🔧 Healing Options:')
        christian_only_count = len([p for p in orphaned_prayers if p['target_audience'] == 'christians_only'])
        if christian_only_count > 0:
            print(f'   • Create Christian user to view {christian_only_count} Christian-only prayers')
            print(f'   • Generate invites for Christian users')
        print(f'   • Flag {len(orphaned_prayers)} prayers for admin review')
        print()
        print('💡 Run "thywill heal-orphaned-prayers" to fix these issues')
        
    else:
        print('✅ No orphaned prayers found!')
        print('   All prayers have compatible viewers')
    
    print()
    print('📋 Summary:')
    print(f'   Total prayers: {results["total_prayers"]}')
    print(f'   Orphaned prayers: {len(orphaned_prayers)}')
    print(f'   Visibility rate: {results["visibility_rate"]:.1f}%')


def main():
    """Main entry point when run as a standalone script."""
    try:
        results = analyze_orphaned_prayers()
        print_analysis_report(results)
        
        # Exit with error code if orphaned prayers found
        if results['orphaned_prayers']:
            sys.exit(1)
        
    except Exception as e:
        print(f'❌ Analysis failed: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()