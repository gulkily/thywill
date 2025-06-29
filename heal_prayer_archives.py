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
from models import engine, Prayer, User
from app_helpers.services.text_archive_service import text_archive_service
from datetime import datetime

def check_database_tables():
    """Check if required database tables exist"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    required_tables = ['prayer', 'user']
    missing_tables = [table for table in required_tables if table not in tables]
    
    return missing_tables

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
            
            # Check if prayer needs healing
            if not prayer.text_file_path:
                needs_healing = True
                reason = "No archive path in database"
            elif not os.path.exists(prayer.text_file_path):
                needs_healing = True
                reason = "Archive file missing from filesystem"
            
            if needs_healing:
                print(f"🔧 Healing prayer {prayer.id}: {reason}")
                
                # Get author information
                author = session.get(User, prayer.author_id)
                author_name = author.display_name if author else "Unknown User"
                
                # Create archive data from database prayer
                archive_data = {
                    'id': prayer.id,
                    'author': author_name,
                    'text': prayer.text,
                    'generated_prayer': prayer.generated_prayer,
                    'project_tag': prayer.project_tag,
                    'target_audience': prayer.target_audience,
                    'created_at': prayer.created_at
                }
                
                try:
                    # Create the archive file
                    if text_archive_service.enabled:
                        archive_file_path = text_archive_service.create_prayer_archive(archive_data)
                        
                        # Update prayer record with archive path
                        prayer.text_file_path = archive_file_path
                        session.add(prayer)
                        
                        print(f"✅ Created archive: {archive_file_path}")
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
                print(f"🔧 Healing user {user.id} ({user.display_name}): {reason}")
                
                try:
                    # Create user archive by writing to monthly registration file
                    if text_archive_service.enabled:
                        # Get inviting user info if available
                        inviting_user = None
                        if user.invited_by_user_id:
                            inviting_user = session.get(User, user.invited_by_user_id)
                        
                        invite_source = inviting_user.display_name if inviting_user else ""
                        
                        # Create the user registration archive entry
                        archive_file_path = text_archive_service.append_user_registration(
                            user.display_name,
                            invite_source
                        )
                        
                        # Update user record with archive path
                        user.text_file_path = archive_file_path
                        session.add(user)
                        
                        print(f"✅ Created user archive entry in: {archive_file_path}")
                        healed_count += 1
                    else:
                        print("⚠️  Text archives disabled - setting placeholder path")
                        user.text_file_path = f"disabled_archive_for_user_{user.id}"
                        session.add(user)
                        healed_count += 1
                        
                except Exception as e:
                    print(f"❌ Failed to heal user {user.id}: {e}")
        
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
        print("🎉 COMPLETE HEALING FINISHED!")
        print("="*50)
        print("All prayers and users now have archive files.")
        print("You can now export complete archives that include all users.")
        
    except Exception as e:
        print(f"💥 Healing failed: {e}")
        sys.exit(1)