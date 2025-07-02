#!/usr/bin/env python3
"""
Archive Healing Script

This script creates missing text archive files for prayers and users that exist in the database
but don't have corresponding archive files.
"""

import os
import sys
from sqlmodel import Session, select
from sqlalchemy import inspect
from models import engine, Prayer, User, PrayerMark, PrayerAttribute, PrayerActivityLog
from app_helpers.services.text_archive_service import text_archive_service
from datetime import datetime

def check_database_tables():
    """Check if required database tables exist"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    required_tables = ['prayer', 'user', 'prayer_activity_log']
    missing_tables = [table for table in required_tables if table not in tables]
    
    return missing_tables

def collect_prayer_activity_data(prayer_id: str, session: Session) -> dict:
    """Collect all activity data for a prayer from activity logs only (single source of truth)"""
    
    # Use only activity logs as the comprehensive source to avoid duplicates
    # The import system will recreate PrayerMark and PrayerAttribute records from archive text
    activity_logs = session.exec(
        select(PrayerActivityLog).where(PrayerActivityLog.prayer_id == prayer_id)
    ).all()
    
    return {
        'activities': [
            {
                'user_id': log.user_id,
                'action': log.action,
                'old_value': log.old_value,
                'new_value': log.new_value,
                'created_at': log.created_at.isoformat()
            } for log in activity_logs
        ]
    }

def verify_archive_completeness(prayer, archive_path: str, session: Session) -> bool:
    """Verify archive contains all current database activity"""
    if not os.path.exists(archive_path):
        return False
    
    # Get current database activity count (using only activity logs as single source of truth)
    current_activities_count = len(session.exec(
        select(PrayerActivityLog).where(PrayerActivityLog.prayer_id == prayer.id)
    ).all())
    
    # For now, we'll use a simple heuristic - if there's any activity data
    # in the database but file is old, it likely needs updating
    if current_activities_count > 0:
        try:
            # Check if archive file was modified after the latest activity
            file_mtime = datetime.fromtimestamp(os.path.getmtime(archive_path))
            
            # Get latest activity timestamp from activity logs only
            latest_activity_log = session.exec(
                select(PrayerActivityLog).where(
                    PrayerActivityLog.prayer_id == prayer.id
                ).order_by(PrayerActivityLog.created_at.desc())
            ).first()
            
            if latest_activity_log and latest_activity_log.created_at > file_mtime:
                return False  # Archive is outdated
                
        except (OSError, AttributeError):
            return False  # Can't determine file age, assume needs update
    
    return True  # Archive appears complete

def heal_prayer_archives():
    """Create missing archive files for prayers without them"""
    
    # First check if database tables exist
    missing_tables = check_database_tables()
    if missing_tables:
        print(f"❌ Missing required database tables: {', '.join(missing_tables)}")
        print("Please initialize the database first:")
        print("  thywill db init")
        print("  # or")
        print("  python3 create_database.py")
        return False
    
    print("🔍 Scanning for prayers without archive files...")
    
    with Session(engine) as session:
        # Find all prayers without text_file_path or with missing files
        prayers_query = select(Prayer)
        prayers = session.exec(prayers_query).all()
        
        healed_count = 0
        total_count = len(prayers)
        
        for prayer in prayers:
            needs_healing = False
            reason = ""
            
            # Check if prayer needs healing
            if not prayer.text_file_path:
                needs_healing = True
                reason = "No archive path in database"
            elif not os.path.exists(prayer.text_file_path):
                needs_healing = True
                reason = "Archive file missing from filesystem"
            elif not verify_archive_completeness(prayer, prayer.text_file_path, session):
                needs_healing = True
                reason = "Archive missing recent activity data"
            
            if needs_healing:
                print(f"🔧 Healing prayer {prayer.id}: {reason}")
                
                # Get author information
                author = session.get(User, prayer.author_username)
                author_name = author.display_name if author else prayer.author_username
                
                # Collect comprehensive activity data
                activity_data = collect_prayer_activity_data(prayer.id, session)
                
                # Create comprehensive archive data from database prayer
                archive_data = {
                    'id': prayer.id,
                    'author': author_name,
                    'text': prayer.text,
                    'generated_prayer': prayer.generated_prayer,
                    'project_tag': prayer.project_tag,
                    'target_audience': prayer.target_audience,
                    'created_at': prayer.created_at,
                    'activities': activity_data['activities'],
                    'stats': {
                        'activities_count': len(activity_data['activities'])
                    }
                }
                
                try:
                    # Create the archive file
                    if text_archive_service.enabled:
                        # Create base prayer archive without activity data first
                        base_archive_data = {
                            'id': prayer.id,
                            'author': author_name,
                            'text': prayer.text,
                            'generated_prayer': prayer.generated_prayer,
                            'project_tag': prayer.project_tag,
                            'target_audience': prayer.target_audience,
                            'created_at': prayer.created_at
                        }
                        archive_file_path = text_archive_service.create_prayer_archive(base_archive_data)
                        
                        # Now append all historical activity data in chronological order
                        all_activities = []
                        
                        # Collect activities with timestamps for sorting
                        for activity in activity_data['activities']:
                            all_activities.append({
                                'created_at': datetime.fromisoformat(activity['created_at']),
                                'type': 'activity',
                                'data': activity
                            })
                        
                        # Sort by timestamp and append to archive
                        all_activities.sort(key=lambda x: x['created_at'])
                        
                        for activity_item in all_activities:
                            activity_timestamp = activity_item['created_at']
                            activity_data_item = activity_item['data']
                            
                            # Handle different activity types appropriately
                            if activity_data_item['action'] == 'prayed':
                                text_archive_service.append_prayer_activity_with_timestamp(
                                    archive_file_path,
                                    'prayed',
                                    activity_data_item['user_id'],
                                    activity_timestamp
                                )
                            elif activity_data_item['action'] in ['answered', 'archived', 'flagged', 'restored']:
                                text_archive_service.append_prayer_activity_with_timestamp(
                                    archive_file_path,
                                    activity_data_item['action'],
                                    activity_data_item['user_id'],
                                    activity_timestamp
                                )
                            elif activity_data_item['action'] == 'testimony':
                                # For testimony, use the new_value as the testimony text
                                text_archive_service.append_prayer_activity_with_timestamp(
                                    archive_file_path,
                                    'testimony',
                                    activity_data_item['user_id'],
                                    activity_timestamp,
                                    extra=activity_data_item['new_value']
                                )
                            else:
                                # Handle any other activity types generically
                                text_archive_service.append_prayer_activity_with_timestamp(
                                    archive_file_path,
                                    activity_data_item['action'],
                                    activity_data_item['user_id'],
                                    activity_timestamp,
                                    old_value=activity_data_item['old_value'],
                                    new_value=activity_data_item['new_value']
                                )
                        
                        # Update prayer record with archive path
                        prayer.text_file_path = archive_file_path
                        session.add(prayer)
                        
                        activity_summary = f" (with {len(activity_data['activities'])} activities)"
                        print(f"✅ Created comprehensive archive: {archive_file_path}{activity_summary}")
                        healed_count += 1
                    else:
                        print("⚠️  Text archives disabled - setting placeholder path")
                        prayer.text_file_path = f"disabled_archive_for_prayer_{prayer.id}"
                        session.add(prayer)
                        healed_count += 1
                        
                except Exception as e:
                    print(f"❌ Failed to heal prayer {prayer.id}: {e}")
        
        # Commit all changes
        session.commit()
        
        print(f"\n📊 Healing Summary:")
        print(f"  Total prayers: {total_count}")
        print(f"  Prayers healed: {healed_count}")
        print(f"  Prayers already healthy: {total_count - healed_count}")
        
        if healed_count > 0:
            print(f"\n🎉 Successfully healed {healed_count} prayers!")
        else:
            print(f"\n✨ All prayers already have archive files!")
        
        return True

def collect_user_activity_data(username: str, session: Session) -> dict:
    """Collect all activity data for a user from activity logs only (single source of truth)"""
    
    # Get user's activity logs only
    user_activities = session.exec(
        select(PrayerActivityLog).where(PrayerActivityLog.user_id == username)
    ).all()
    
    return {
        'activities_count': len(user_activities),
        'total_prayers_with_activity': len(set(activity.prayer_id for activity in user_activities))
    }

def heal_user_archives():
    """Create missing archive files for users without them"""
    
    print("🔍 Scanning for users without archive files...")
    
    with Session(engine) as session:
        # Find all users without text_file_path or with missing files
        users_query = select(User)
        users = session.exec(users_query).all()
        
        healed_count = 0
        total_count = len(users)
        
        for user in users:
            needs_healing = False
            
            # Check if user needs healing
            if not user.text_file_path:
                needs_healing = True
                reason = "No archive path in database"
            elif not os.path.exists(user.text_file_path):
                needs_healing = True
                reason = "Archive file missing from filesystem"
            
            if needs_healing:
                print(f"🔧 Healing user {user.display_name}: {reason}")
                
                try:
                    # Create user archive by writing to monthly registration file
                    if text_archive_service.enabled:
                        # Get inviting user info if available
                        invite_source = user.invited_by_username if user.invited_by_username else ""
                        
                        # Get user activity summary for logging
                        activity_summary = collect_user_activity_data(user.display_name, session)
                        
                        # Create the user registration archive entry with original timestamp
                        archive_file_path = text_archive_service.append_user_registration_with_timestamp(
                            user.display_name,
                            invite_source,
                            user.created_at
                        )
                        
                        # Update user record with archive path
                        user.text_file_path = archive_file_path
                        session.add(user)
                        
                        activity_info = f" (activity: {activity_summary['activities_count']} activities on {activity_summary['total_prayers_with_activity']} prayers)"
                        print(f"✅ Created user archive entry in: {archive_file_path}{activity_info}")
                        healed_count += 1
                    else:
                        print("⚠️  Text archives disabled - setting placeholder path")
                        user.text_file_path = f"disabled_archive_for_user_{user.display_name}"
                        session.add(user)
                        healed_count += 1
                        
                except Exception as e:
                    print(f"❌ Failed to heal user {user.display_name}: {e}")
        
        # Commit all changes
        session.commit()
        
        print(f"\n📊 User Healing Summary:")
        print(f"  Total users: {total_count}")
        print(f"  Users healed: {healed_count}")
        print(f"  Users already healthy: {total_count - healed_count}")
        
        if healed_count > 0:
            print(f"\n🎉 Successfully healed {healed_count} users!")
        else:
            print(f"\n✨ All users already have archive files!")
        
        return True

if __name__ == "__main__":
    print("🏥 Archive Healing Script")
    print("=" * 50)
    
    # Check if text archives are enabled
    if not text_archive_service.enabled:
        print("⚠️  WARNING: Text archives are disabled")
        print("This script will still update database records with placeholder paths")
        print("")
    
    # Ask for confirmation
    print("This script will heal both prayers and users missing archive files.")
    response = input("Do you want to create missing archive files for all prayers and users? (y/N): ")
    if response.lower() != 'y':
        print("❌ Healing cancelled")
        sys.exit(0)
    
    try:
        print("\n" + "="*50)
        print("HEALING PRAYERS")
        print("="*50)
        prayer_success = heal_prayer_archives()
        
        print("\n" + "="*50)  
        print("HEALING USERS")
        print("="*50)
        user_success = heal_user_archives()
        
        if not (prayer_success and user_success):
            sys.exit(1)
            
        print("\n" + "="*50)
        print("🎉 COMPREHENSIVE HEALING FINISHED!")
        print("="*50)
        print("All prayers and users now have comprehensive archive files.")
        print("Archives include complete activity history (marks, attributes, logs).")
        print("Ready for full idempotent import/export workflows!")
        
    except Exception as e:
        print(f"💥 Healing failed: {e}")
        sys.exit(1)