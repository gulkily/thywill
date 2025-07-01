#!/usr/bin/env python3
"""
Bulk fix common schema migration patterns across multiple files.
This applies safe, predictable fixes to avoid manual repetition.
"""

import os
import re
from pathlib import Path

def apply_fixes_to_file(file_path):
    """Apply common schema fixes to a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Enhanced safe replacements for comprehensive fixing
        replacements = [
            # Prayer field fixes
            (r'\.author_id\b', '.author_username'),
            (r'prayer\.author_id', 'prayer.author_username'),
            (r'Prayer\.author_id', 'Prayer.author_username'),
            (r'p\.author_id', 'p.author_username'),
            
            # PrayerMark field fixes for PrayerMark specifically
            (r'PrayerMark\.user_id', 'PrayerMark.username'),
            (r'mark\.user_id', 'mark.username'),
            
            # PrayerSkip field fixes for PrayerSkip specifically
            (r'PrayerSkip\.user_id', 'PrayerSkip.username'),
            
            # User ID fixes - comprehensive patterns
            (r'user\.id\b(?!\s*==\s*"admin")', 'user.display_name'),
            (r'User\.id\b(?!\s*==\s*"admin")', 'User.display_name'),
            (r'existing_user\.id\b', 'existing_user.display_name'),
            (r'current_user\.id\b', 'current_user.display_name'),
            (r'profile_user\.id\b', 'profile_user.display_name'),
            (r'first_user\.id\b', 'first_user.display_name'),
            (r'auth_user\.id\b', 'auth_user.display_name'),
            (r'requester\.id\b', 'requester.display_name'),
            (r'approver\.id\b', 'approver.display_name'),
            (r'author_user\.id\b', 'author_user.display_name'),
            (r'inviter\.id\b', 'inviter.display_name'),
            
            # Query fixes for Prayer joins
            (r'Prayer\.author_id\s*==\s*User\.id', 'Prayer.author_username == User.display_name'),
            (r'Prayer\.author_id\s*==\s*User\.display_name', 'Prayer.author_username == User.display_name'),
            
            # PrayerMark query fixes - comprehensive
            (r'PrayerMark\.user_id\s*==\s*user\.id', 'PrayerMark.username == user.display_name'),
            (r'PrayerMark\.user_id\s*==\s*existing_user\.id', 'PrayerMark.username == existing_user.display_name'),
            (r'PrayerMark\.user_id\s*==\s*current_user\.id', 'PrayerMark.username == current_user.display_name'),
            (r'PrayerMark\.user_id\s*==\s*profile_user\.id', 'PrayerMark.username == profile_user.display_name'),
            (r'PrayerMark\.user_id\s*==\s*User\.id', 'PrayerMark.username == User.display_name'),
            
            # PrayerSkip query fixes
            (r'PrayerSkip\.user_id\s*==\s*user\.id', 'PrayerSkip.username == user.display_name'),
            (r'PrayerSkip\.user_id\s*==\s*existing_user\.id', 'PrayerSkip.username == existing_user.display_name'),
            (r'PrayerSkip\.user_id\s*==\s*current_user\.id', 'PrayerSkip.username == current_user.display_name'),
            (r'PrayerSkip\.user_id\s*==\s*profile_user\.id', 'PrayerSkip.username == profile_user.display_name'),
            (r'PrayerSkip\.user_id\s*==\s*user\.display_name', 'PrayerSkip.username == user.display_name'),
            
            # AuthenticationRequest fixes (these should stay as user_id for database compatibility)
            # But we need to update the values being compared
            (r'AuthenticationRequest\.user_id\s*==\s*user\.id', 'AuthenticationRequest.user_id == user.display_name'),
            (r'AuthenticationRequest\.user_id\s*==\s*existing_user\.id', 'AuthenticationRequest.user_id == existing_user.display_name'),
            (r'auth_req\.user_id\s*==\s*user\.id', 'auth_req.user_id == user.display_name'),
            (r'auth_req\.user_id\s*==\s*existing_user\.id', 'auth_req.user_id == existing_user.display_name'),
            
            # Session fixes (these should stay as username for database compatibility)
            (r'SessionModel\.user_id', 'SessionModel.username'),
            (r'session\.user_id', 'session.username'),
            (r'sess\.user_id', 'sess.username'),
            
            # Function parameter fixes for common functions
            (r'user_id=user\.id\b', 'username=user.display_name'),
            (r'user_id=existing_user\.id\b', 'username=existing_user.display_name'),
            (r'user_id=current_user\.id\b', 'username=current_user.display_name'),
            (r'user_id=profile_user\.id\b', 'username=profile_user.display_name'),
            (r'user_id=auth_user\.id\b', 'username=auth_user.display_name'),
            
            # Specific auth function fixes
            (r'actor_user_id=user\.id', 'actor_user_id=user.display_name'),
            (r'approved_by_user_id\s*=\s*user\.id', 'approved_by_user_id = user.display_name'),
            (r'approver_user_id\s*==\s*user\.id', 'approver_user_id == user.display_name'),
            
            # Prayer author query fixes
            (r'Prayer\.author_id\s*==\s*user\.id', 'Prayer.author_username == user.display_name'),
            (r'Prayer\.author_id\s*==\s*existing_user\.id', 'Prayer.author_username == existing_user.display_name'),
            (r'Prayer\.author_id\s*==\s*current_user\.id', 'Prayer.author_username == current_user.display_name'),
            (r'Prayer\.author_id\s*==\s*profile_user\.id', 'Prayer.author_username == profile_user.display_name'),
            
            # Filter fixes
            (r'filter_by\(author_id=user_id\)', 'filter_by(author_username=user_id)'),
            
            # Constructor fixes
            (r'author_id=([^,\s]+)', r'author_username=\1'),
            (r'created_by_user=user\.id', 'created_by_user=user.display_name'),
            
            # Invited by fixes
            (r'invited_by_user_id', 'invited_by_username'),
            
            # Function call fixes
            (r'get_unread_auth_notifications\(user\.id\)', 'get_unread_auth_notifications(user.display_name)'),
            (r'mark_notification_read\(([^,]+),\s*user\.id\)', r'mark_notification_read(\1, user.display_name)'),
            (r'check_rate_limit\(existing_user\.id', 'check_rate_limit(existing_user.display_name'),
            (r'is_user_deactivated\(existing_user\.id', 'is_user_deactivated(existing_user.display_name'),
            (r'is_user_deactivated\(profile_user\.id', 'is_user_deactivated(profile_user.display_name'),
            (r'get_user_invite_path\(user\.id\)', 'get_user_invite_path(user.display_name)'),
            
            # Admin function fixes but preserve admin == "admin" comparisons
            (r'user\.id\s*==\s*"admin"', 'user.display_name == "admin"'),
            (r'return\s+user\.id\s*==\s*"admin"', 'return user.display_name == "admin"'),
            
            # Database index fixes
            (r'idx_user_invited_by.*user\(invited_by_user_id\)', 'idx_user_invited_by ON user(invited_by_username)'),
            
            # Additional specific patterns from remaining issues
            # UserRole.user_id patterns - these should stay as user_id but compared to display_name
            (r'UserRole\.user_id\s*==\s*user\.id', 'UserRole.user_id == user.display_name'),
            (r'UserRole\.user_id\s*==\s*existing_user\.id', 'UserRole.user_id == existing_user.display_name'),
            (r'UserRole\.user_id\s*==\s*self\.id', 'UserRole.user_id == self.display_name'),
            
            # AuthenticationRequest specific patterns
            (r'approver_id\s*==\s*auth_req\.user_id', 'approver_id == auth_req.user_id'),  # This one is correct
            (r'req\.user_id(?!\s*==)', 'req.user_id'),  # Keep as is for database field access
            
            # More specific User.id patterns 
            (r'session\.get\(User,\s*req\.user_id\)', 'session.exec(select(User).where(User.display_name == req.user_id)).first()'),
            
            # Additional join patterns
            (r'join\(User,\s*AuthenticationRequest\.user_id\s*==\s*User\.id\)', 'join(User, AuthenticationRequest.user_id == User.display_name)'),
            (r'outerjoin\(User,\s*AuthenticationRequest\.user_id\s*==\s*User\.id\)', 'outerjoin(User, AuthenticationRequest.user_id == User.display_name)'),
            
            # Template fixes for Jinja2 templates
            (r'profile_user\.id\b', 'profile_user.display_name'),
            (r'user\.id\b(?=\s*[}\]|[:"\s])', 'user.display_name'),
            (r'inviter\.id\b', 'inviter.display_name'),
            (r'\.author_id\b(?=\s*[}\]|[:"\s])', '.author_username'),
        ]
        
        changes_made = []
        for pattern, replacement in replacements:
            old_content = content
            content = re.sub(pattern, replacement, content)
            if content != old_content:
                changes_made.append(f"  - {pattern} -> {replacement}")
        
        # Only write if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return changes_made
        
        return []
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []

def main():
    """Apply bulk fixes to priority files"""
    
    priority_files = [
        # Phase 1: Already fixed
        'app_helpers/routes/prayer/prayer_status.py',
        'app_helpers/routes/prayer/prayer_crud.py', 
        'app_helpers/routes/prayer/prayer_mode.py',
        'app_helpers/routes/prayer/prayer_moderation.py',
        'app_helpers/routes/user_routes.py',
        'app_helpers/routes/prayer/feed_operations.py',
        'app_helpers/services/prayer_helpers.py',
        'app_helpers/services/archive_download_service.py',
        
        # Phase 2: High priority auth routes
        'app_helpers/routes/auth/login_routes.py',
        'app_helpers/routes/auth/multi_device_routes.py',
        'app_helpers/routes/auth/notification_routes.py',
        'app_helpers/routes/auth/verification_routes.py',
        'app_helpers/routes/invite_routes.py',
        
        # Phase 3: Service layer
        'app_helpers/services/auth/token_helpers.py',
        'app_helpers/services/auth/validation_helpers.py',
        'app_helpers/services/invite_helpers.py',
        'app_helpers/services/system_archive_service.py',
        'app_helpers/services/text_importer_service.py',
        'app_helpers/services/archive_first_service.py',
        
        # Phase 4: Admin routes
        'app_helpers/routes/admin/dashboard.py',
        'app_helpers/routes/admin/user_management.py',
        'app_helpers/routes/admin/auth_management.py',
        'app_helpers/routes/admin_routes_backup.py',
        
        # Phase 5: Infrastructure
        'app_helpers/services/database_recovery.py',
        'models.py',
        
        # Phase 6: Utils and remaining helpers
        'app_helpers/utils/user_management.py',
        'app_helpers/utils/invite_tree_validation.py',
    ]
    
    root_dir = Path('/home/wsl/thywill')
    
    print("🔧 Applying Bulk Schema Fixes")
    print("=" * 40)
    
    total_files_changed = 0
    total_changes = 0
    
    for file_path in priority_files:
        full_path = root_dir / file_path
        if full_path.exists():
            changes = apply_fixes_to_file(full_path)
            if changes:
                print(f"\n📁 {file_path}")
                for change in changes[:5]:  # Limit to first 5 changes shown
                    print(change)
                if len(changes) > 5:
                    print(f"  ... and {len(changes) - 5} more changes")
                total_files_changed += 1
                total_changes += len(changes)
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print(f"\n📊 Summary:")
    print(f"  Files changed: {total_files_changed}")
    print(f"  Total changes: {total_changes}")
    
    if total_changes > 0:
        print(f"\n✅ Bulk fixes applied! Test with: python debug_helper.py")
    else:
        print(f"\n💡 No changes needed - files may already be fixed!")

if __name__ == "__main__":
    main()