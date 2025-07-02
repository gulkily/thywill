#!/usr/bin/env python3
"""
Prayer Healing CLI Module

Heals orphaned prayers by creating compatible users or fixing visibility issues.
Can be run independently or called from the CLI script.
"""

import sys
import uuid
from typing import List, Dict, Any
from datetime import datetime, timedelta
from sqlmodel import Session, select, and_
from models import engine, User, Prayer, PrayerAttribute, InviteToken


def find_orphaned_prayers() -> List[Prayer]:
    """
    Find prayers that have no compatible viewers.
    
    Returns:
        List of orphaned Prayer objects
    """
    with Session(engine) as session:
        all_prayers = list(session.exec(select(Prayer)))
        all_users = list(session.exec(select(User)))
        
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
            
            # All prayers are visible to all users (no preference-based filtering)
            has_viewers = len(all_users) > 0
            
            if not has_viewers:
                orphaned_prayers.append(prayer)
        
        return orphaned_prayers


def heal_orphaned_prayers() -> Dict[str, Any]:
    """
    Heal orphaned prayers by creating compatible users.
    
    Returns:
        Dict containing healing results and statistics
    """
    results = {
        'orphaned_prayers_found': 0,
        'healing_actions': [],
        'healed_count': 0,
        'remaining_orphaned': 0,
        'created_users': [],
        'created_invites': []
    }
    
    with Session(engine) as session:
        # Find orphaned prayers
        orphaned_prayers = find_orphaned_prayers()
        results['orphaned_prayers_found'] = len(orphaned_prayers)
        
        if not orphaned_prayers:
            return results
        
        # Analyze what healing is needed (simplified since all prayers use target_audience='all')
        all_users = list(session.exec(select(User)))
        
        healing_actions = []
        
        # Since all prayers now use target_audience='all', just ensure users exist
        if not all_users:
            healing_actions.append('create_general_user')
        
        results['healing_actions'] = healing_actions
        
        # Perform healing actions
        for action in healing_actions:
            if action == 'create_general_user':
                # Create a default user
                general_user = User(
                    display_name='Default User',
                    created_at=datetime.utcnow()
                )
                session.add(general_user)
                results['created_users'].append({
                    'display_name': general_user.display_name
                })
                
                # Create an invite token for additional Christian users
                invite_token = InviteToken(
                    token=uuid.uuid4().hex,
                    created_by_user=christian_user.id,
                    expires_at=datetime.utcnow() + timedelta(days=30),
                    used=False
                )
                session.add(invite_token)
                results['created_invites'].append({
                    'token': invite_token.token,
                    'expires_at': invite_token.expires_at.isoformat(),
                    'created_by': christian_user.id
                })
        
        # Commit changes
        session.commit()
        
        # Verify healing effectiveness
        all_users = list(session.exec(select(User)))  # Refresh user list
        healed_count = 0
        remaining_orphaned = []
        
        for prayer in orphaned_prayers:
            has_viewers = False
            
            # All prayers use target_audience='all' and are visible to all users
            has_viewers = len(all_users) > 0
            
            if has_viewers:
                healed_count += 1
            else:
                remaining_orphaned.append(prayer)
        
        results['healed_count'] = healed_count
        results['remaining_orphaned'] = len(remaining_orphaned)
        
        return results


def print_healing_report(results: Dict[str, Any]) -> None:
    """Print a formatted healing report to stdout."""
    print('🔧 Orphaned Prayer Healing')
    print('=' * 40)
    print()
    
    if results['orphaned_prayers_found'] == 0:
        print('✅ No orphaned prayers found - healing not needed')
        return
    
    print(f'Found {results["orphaned_prayers_found"]} orphaned prayers')
    print()
    
    if not results['healing_actions']:
        print('⚠️  No automatic healing actions available')
        print('   Manual review may be needed')
        return
    
    print('🔧 Healing Actions:')
    for action in results['healing_actions']:
        if action == 'create_christian_user':
            print('   • Creating default Christian user...')
    
    # Report created users
    for user in results['created_users']:
        print(f'     ✅ Created user: {user["display_name"]} (ID: {user["id"][:8]}...)')
    
    # Report created invites
    for invite in results['created_invites']:
        print(f'     ✅ Created invite token for Christian users: {invite["token"]}')
        print(f'        Expires: {invite["expires_at"]}')
        print(f'        Single use token (invite additional Christian users)')
    
    print()
    print('✅ Healing completed successfully!')
    print()
    
    # Post-healing verification
    print('🔍 Post-healing verification:')
    print(f'   Healed: {results["healed_count"]} prayers')
    print(f'   Remaining orphaned: {results["remaining_orphaned"]} prayers')
    
    if results['remaining_orphaned'] > 0:
        print('   ⚠️  Some prayers still orphaned - may need manual review')
    else:
        print('   🎉 All prayers now have compatible viewers!')
    
    print()
    print('💡 Next steps:')
    print('   • Share invite tokens with Christian community members')
    print('   • Run "thywill analyze-orphaned-prayers" to verify healing')
    print('   • Monitor prayer visibility in feeds')


def main():
    """Main entry point when run as a standalone script."""
    try:
        results = heal_orphaned_prayers()
        print_healing_report(results)
        
        # Exit with error code if healing couldn't fix all prayers
        if results['remaining_orphaned'] > 0:
            sys.exit(1)
        
    except Exception as e:
        print(f'❌ Healing failed: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()