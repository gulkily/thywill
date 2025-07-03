#!/usr/bin/env python3
"""
Comprehensive backup and restore integration test

This test demonstrates the complete backup and restore workflow:
1. Create sample data using normal application flow
2. Verify data is backed up to text archives  
3. Simulate data loss (clear database)
4. Restore data from text archives
5. Verify complete data integrity

This test simulates real-world disaster recovery scenarios.
"""

import tempfile
import shutil
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Mock the configuration before importing services
os.environ['TEXT_ARCHIVE_ENABLED'] = 'true'
os.environ['TEXT_ARCHIVE_BASE_DIR'] = tempfile.mkdtemp()

from app_helpers.services.text_archive_service import TextArchiveService
from app_helpers.services.text_importer_service import TextImporterService
from app_helpers.services.archive_first_service import create_user_with_text_archive, create_prayer_with_text_archive
from models import engine, User, Prayer, PrayerMark, PrayerAttribute, PrayerActivityLog
from sqlmodel import Session, select


class BackupRestoreIntegrationTest:
    """Comprehensive backup and restore integration test"""
    
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.archive_service = TextArchiveService(base_dir=self.temp_dir)
        self.importer_service = TextImporterService(self.archive_service)
        self.test_data = {}
        
        # Override the global archive service to use our test directory
        import app_helpers.services.archive_first_service
        self.original_global_service = app_helpers.services.archive_first_service.text_archive_service
        app_helpers.services.archive_first_service.text_archive_service = self.archive_service
        
        print(f"Testing backup/restore in directory: {self.temp_dir}")
    
    def cleanup(self):
        """Clean up test directory"""
        # Restore original global service
        import app_helpers.services.archive_first_service
        app_helpers.services.archive_first_service.text_archive_service = self.original_global_service
        
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(f"Cleaned up test directory: {self.temp_dir}")
    
    def step_1_create_sample_community(self):
        """Step 1: Create a sample prayer community with realistic data"""
        print("\\n🏗️  Step 1: Creating sample prayer community...")
        
        # Create community members
        users_data = [
            {
                'display_name': 'Pastor_John',
                'religious_preference': 'christian',
                'prayer_style': 'traditional',
                'role': 'community_leader'
            },
            {
                'display_name': 'Sister_Mary',
                'invited_by_display_name': 'Pastor_John',
                'religious_preference': 'christian',
                'prayer_style': 'contemplative',
                'role': 'prayer_warrior'
            },
            {
                'display_name': 'Young_David',
                'invited_by_display_name': 'Sister_Mary',
                'religious_preference': 'christian',
                'prayer_style': 'contemporary',
                'role': 'youth_member'
            },
            {
                'display_name': 'Grandmother_Sarah',
                'invited_by_display_name': 'Pastor_John',
                'religious_preference': 'christian',
                'prayer_style': 'traditional',
                'role': 'elder'
            },
            {
                'display_name': 'New_Believer_Mike',
                'invited_by_display_name': 'Young_David',
                'religious_preference': 'exploring',
                'prayer_style': 'simple',
                'role': 'newcomer'
            }
        ]
        
        # Create users with archive-first approach
        created_users = {}
        for i, user_data in enumerate(users_data):
            import uuid
            user_id = f"backup_test_user_{i+1}_{uuid.uuid4().hex[:6]}"
            user, user_archive = create_user_with_text_archive(user_data, user_id)
            created_users[user_data['display_name']] = user
            
            # Also create user registration archive for importer to find
            inviter_name = user_data.get('invited_by_display_name', '')
            self.archive_service.append_user_registration(user_data['display_name'], inviter_name)
            
            print(f"  ✅ Created user: {user.display_name}")
        
        self.test_data['users'] = created_users
        
        # Create prayer requests representing common community needs
        prayers_data = [
            {
                'author': 'Pastor_John',
                'text': 'Please pray for our church building fund. We need $50,000 to repair the roof before winter.',
                'generated_prayer': 'Heavenly Father, we lift up our church community and ask for your provision...',
                'project_tag': 'church_building',
                'target_audience': 'all',
                'submitted_time': datetime.now() - timedelta(days=30)
            },
            {
                'author': 'Sister_Mary',
                'text': 'My mother is in the hospital with pneumonia. Please pray for her healing and recovery.',
                'generated_prayer': 'Lord Jesus, Great Physician, we bring Sister Mary\'s mother before you...',
                'project_tag': 'health',
                'target_audience': 'adults',
                'submitted_time': datetime.now() - timedelta(days=25)
            },
            {
                'author': 'Young_David',
                'text': 'Struggling with college applications and need wisdom about my future career path.',
                'generated_prayer': 'God of wisdom, guide David as he seeks direction for his future...',
                'project_tag': 'guidance',
                'target_audience': 'youth',
                'submitted_time': datetime.now() - timedelta(days=20)
            },
            {
                'author': 'Grandmother_Sarah',
                'text': 'Please pray for my grandson who has been deployed overseas. Keep him safe.',
                'generated_prayer': 'Father, we place Sarah\'s grandson in your protective hands...',
                'project_tag': 'military',
                'target_audience': 'all',
                'submitted_time': datetime.now() - timedelta(days=15)
            },
            {
                'author': 'New_Believer_Mike',
                'text': 'I\'m new to faith and sometimes doubt. Pray for strength in my spiritual journey.',
                'generated_prayer': 'Lord, strengthen Mike\'s faith and surround him with your love...',
                'project_tag': 'spiritual_growth',
                'target_audience': 'all',
                'submitted_time': datetime.now() - timedelta(days=10)
            }
        ]
        
        # Create prayers using archive-first approach
        created_prayers = {}
        for i, prayer_data in enumerate(prayers_data):
            import uuid
            prayer_id = f"backup_test_prayer_{i+1}_{uuid.uuid4().hex[:6]}"
            author_user = created_users[prayer_data['author']]
            
            # Prepare data for archive-first creation
            archive_prayer_data = {
                'author_id': author_user.id,
                'author_display_name': author_user.display_name,
                'text': prayer_data['text'],
                'generated_prayer': prayer_data['generated_prayer'],
                'project_tag': prayer_data['project_tag'],
                'target_audience': prayer_data['target_audience'],
                'created_at': prayer_data['submitted_time']
            }
            
            # Create prayer using archive-first approach (creates both archive and database record)
            prayer, prayer_file = create_prayer_with_text_archive(archive_prayer_data)
            
            # Update the prayer ID to our test ID
            with Session(engine) as s:
                prayer = s.get(Prayer, prayer.id)
                if prayer:
                    # Update prayer to use our test ID (for consistency in testing)
                    # Note: In real usage, we'd use the auto-generated ID
                    pass  # Keep the auto-generated ID for now
            
            created_prayers[prayer.id] = {
                'data': prayer_data,
                'file': prayer_file,
                'author': author_user,
                'prayer': prayer
            }
            print(f"  ✅ Created prayer: {prayer_data['project_tag']} by {prayer_data['author']}")
            print(f"     Archive file: {prayer_file}")
            print(f"     Database ID: {prayer.id}")
        
        self.test_data['prayers'] = created_prayers
        
        print(f"✅ Created community with {len(created_users)} users and {len(created_prayers)} prayers")
        return True
    
    def step_2_simulate_community_activity(self):
        """Step 2: Simulate realistic community prayer interactions"""
        print("\\n🙏 Step 2: Simulating community prayer interactions...")
        
        # Simulate prayer interactions over time
        interactions = [
            # Week 1: Pastor John's building fund prayer
            {'prayer': 'backup_test_prayer_1', 'action': 'prayed', 'user': 'Sister_Mary'},
            {'prayer': 'backup_test_prayer_1', 'action': 'prayed', 'user': 'Grandmother_Sarah'},
            {'prayer': 'backup_test_prayer_1', 'action': 'prayed', 'user': 'Young_David'},
            
            # Week 2: Sister Mary's mother health prayer
            {'prayer': 'backup_test_prayer_2', 'action': 'prayed', 'user': 'Pastor_John'},
            {'prayer': 'backup_test_prayer_2', 'action': 'prayed', 'user': 'Grandmother_Sarah'},
            {'prayer': 'backup_test_prayer_2', 'action': 'prayed', 'user': 'Young_David'},
            {'prayer': 'backup_test_prayer_2', 'action': 'prayed', 'user': 'New_Believer_Mike'},
            
            # Week 3: Young David's guidance prayer gets answered
            {'prayer': 'backup_test_prayer_3', 'action': 'prayed', 'user': 'Pastor_John'},
            {'prayer': 'backup_test_prayer_3', 'action': 'prayed', 'user': 'Sister_Mary'},
            {'prayer': 'backup_test_prayer_3', 'action': 'answered', 'user': 'Young_David'},
            {'prayer': 'backup_test_prayer_3', 'action': 'testimony', 'user': 'Young_David', 
             'extra': 'God opened doors I never expected! Got accepted to my dream program with a scholarship.'},
            
            # Week 4: Grandmother Sarah's military prayer
            {'prayer': 'backup_test_prayer_4', 'action': 'prayed', 'user': 'Pastor_John'},
            {'prayer': 'backup_test_prayer_4', 'action': 'prayed', 'user': 'Sister_Mary'},
            {'prayer': 'backup_test_prayer_4', 'action': 'prayed', 'user': 'New_Believer_Mike'},
            
            # Current week: New believer gets support
            {'prayer': 'backup_test_prayer_5', 'action': 'prayed', 'user': 'Pastor_John'},
            {'prayer': 'backup_test_prayer_5', 'action': 'prayed', 'user': 'Sister_Mary'},
            {'prayer': 'backup_test_prayer_5', 'action': 'prayed', 'user': 'Grandmother_Sarah'},
            
            # Some prayers get multiple marks from same person
            {'prayer': 'backup_test_prayer_1', 'action': 'prayed', 'user': 'Sister_Mary'},  # Second time
            {'prayer': 'backup_test_prayer_2', 'action': 'answered', 'user': 'Sister_Mary'},
            {'prayer': 'backup_test_prayer_2', 'action': 'testimony', 'user': 'Sister_Mary',
             'extra': 'Mom is home from the hospital and doing much better! Thank you all for your prayers.'},
            
            # Administrative actions
            {'prayer': 'backup_test_prayer_1', 'action': 'archived', 'user': 'Pastor_John'},  # Archived after funding goal met
        ]
        
        # Apply interactions to prayer archives
        # Map the interaction prayer names to actual prayer IDs
        prayer_id_map = {}
        for prayer_id, prayer_info in self.test_data['prayers'].items():
            prayer_data = prayer_info['data']
            if prayer_data['project_tag'] == 'church_building':
                prayer_id_map['backup_test_prayer_1'] = prayer_id
            elif prayer_data['project_tag'] == 'health':
                prayer_id_map['backup_test_prayer_2'] = prayer_id
            elif prayer_data['project_tag'] == 'guidance':
                prayer_id_map['backup_test_prayer_3'] = prayer_id
            elif prayer_data['project_tag'] == 'military':
                prayer_id_map['backup_test_prayer_4'] = prayer_id
            elif prayer_data['project_tag'] == 'spiritual_growth':
                prayer_id_map['backup_test_prayer_5'] = prayer_id
        
        for interaction in interactions:
            interaction_prayer_name = interaction['prayer']
            actual_prayer_id = prayer_id_map.get(interaction_prayer_name)
            
            if actual_prayer_id and actual_prayer_id in self.test_data['prayers']:
                prayer_file = self.test_data['prayers'][actual_prayer_id]['file']
                user_name = interaction['user']
                action = interaction['action']
                extra = interaction.get('extra', '')
                
                self.archive_service.append_prayer_activity(prayer_file, action, user_name, extra)
                
                # Also log to monthly activity
                activity_text = f"{action} prayer {actual_prayer_id}"
                if action == 'prayed':
                    activity_text = f"prayed for prayer {actual_prayer_id}"
                elif action == 'answered':
                    activity_text = f"marked prayer {actual_prayer_id} as answered"
                
                self.archive_service.append_monthly_activity(activity_text, user_name, actual_prayer_id)
        
        print(f"✅ Simulated {len(interactions)} community interactions")
        
        # Log some community-wide activities
        community_activities = [
            {'action': 'joined the community', 'user': 'Pastor_John'},
            {'action': 'joined the community', 'user': 'Sister_Mary'},
            {'action': 'joined the community', 'user': 'Young_David'},
            {'action': 'joined the community', 'user': 'Grandmother_Sarah'},
            {'action': 'joined the community', 'user': 'New_Believer_Mike'},
            {'action': 'started monthly prayer group', 'user': 'Pastor_John'},
            {'action': 'organized youth prayer night', 'user': 'Young_David'},
        ]
        
        for activity in community_activities:
            self.archive_service.append_monthly_activity(activity['action'], activity['user'])
        
        print(f"✅ Logged {len(community_activities)} community activities")
        return True
    
    def step_3_verify_backup_integrity(self):
        """Step 3: Verify that all data is properly backed up in text archives"""
        print("\\n📋 Step 3: Verifying backup integrity...")
        
        archive_structure = {}
        
        # Check prayer archives
        prayers_dir = Path(self.temp_dir) / "prayers"
        print(f"  🔍 Checking prayers directory: {prayers_dir}")
        print(f"  🔍 Directory exists: {prayers_dir.exists()}")
        
        if prayers_dir.exists():
            print(f"  🔍 Contents: {list(prayers_dir.iterdir())}")
            prayer_files = []
            for year_dir in prayers_dir.iterdir():
                if year_dir.is_dir():
                    print(f"    📁 Year dir: {year_dir}")
                    for month_dir in year_dir.iterdir():
                        if month_dir.is_dir():
                            print(f"      📁 Month dir: {month_dir}")
                            month_files = list(month_dir.glob("*.txt"))
                            print(f"        📄 Files: {month_files}")
                            prayer_files.extend(month_files)
            
            archive_structure['prayer_files'] = len(prayer_files)
            
            # Parse each prayer file and verify content
            total_activities = 0
            for prayer_file in prayer_files:
                parsed_data, parsed_activities = self.archive_service.parse_prayer_archive(str(prayer_file))
                total_activities += len(parsed_activities)
            
            archive_structure['total_prayer_activities'] = total_activities
            print(f"  ✅ Found {len(prayer_files)} prayer archive files with {total_activities} total activities")
        
        # Check user registration archives
        users_dir = Path(self.temp_dir) / "users"
        if users_dir.exists():
            user_files = list(users_dir.glob("*_users.txt"))
            archive_structure['user_files'] = len(user_files)
            
            total_registrations = 0
            for user_file in user_files:
                content = user_file.read_text()
                print(f"    📄 User file content ({user_file.name}):")
                print(f"        Content preview: {content[:200]}...")
                # Count registration lines
                registrations = len([line for line in content.split('\\n') 
                                   if ' joined ' in line and ' - ' in line])
                print(f"        Registration lines found: {registrations}")
                total_registrations += registrations
            
            archive_structure['total_user_registrations'] = total_registrations
            print(f"  ✅ Found {len(user_files)} user registration files with {total_registrations} registrations")
        
        # Check monthly activity archives
        activity_dir = Path(self.temp_dir) / "activity"
        if activity_dir.exists():
            activity_files = list(activity_dir.glob("activity_*.txt"))
            archive_structure['activity_files'] = len(activity_files)
            
            total_monthly_activities = 0
            for activity_file in activity_files:
                content = activity_file.read_text()
                # Count activity lines (lines with timestamp and user)
                activities = len([line for line in content.split('\\n') 
                                if ' - ' in line and ':' in line])
                total_monthly_activities += activities
            
            archive_structure['total_monthly_activities'] = total_monthly_activities
            print(f"  ✅ Found {len(activity_files)} monthly activity files with {total_monthly_activities} activities")
        
        self.test_data['archive_structure'] = archive_structure
        
        # Display backup summary
        print("\\n📊 Backup Summary:")
        print(f"  • Prayer archives: {archive_structure.get('prayer_files', 0)} files")
        print(f"  • Prayer activities: {archive_structure.get('total_prayer_activities', 0)} logged")
        print(f"  • User registrations: {archive_structure.get('total_user_registrations', 0)} logged") 
        print(f"  • Monthly activities: {archive_structure.get('total_monthly_activities', 0)} logged")
        
        return True
    
    def step_4_simulate_data_loss(self):
        """Step 4: Simulate catastrophic data loss (database corruption/deletion)"""
        print("\\n💥 Step 4: Simulating catastrophic data loss...")
        
        # Count records before deletion
        with Session(engine) as s:
            users_before = len(s.exec(select(User)).all())
            prayers_before = len(s.exec(select(Prayer)).all())
            marks_before = len(s.exec(select(PrayerMark)).all())
            attributes_before = len(s.exec(select(PrayerAttribute)).all())
            activities_before = len(s.exec(select(PrayerActivityLog)).all())
        
        print(f"  📊 Database state before disaster:")
        print(f"    • Users: {users_before}")
        print(f"    • Prayers: {prayers_before}")
        print(f"    • Prayer marks: {marks_before}")
        print(f"    • Prayer attributes: {attributes_before}")
        print(f"    • Activity logs: {activities_before}")
        
        # Store original counts for comparison
        self.test_data['original_counts'] = {
            'users': users_before,
            'prayers': prayers_before,
            'marks': marks_before,
            'attributes': attributes_before,
            'activities': activities_before
        }
        
        # Simulate database corruption by clearing all tables
        # WARNING: This is destructive! Only for testing!
        print("  ⚠️  Simulating database corruption...")
        
        try:
            # Clear all application data (simulate complete data loss)
            # Use SQLModel queries to safely delete records
            with Session(engine) as s:
                # Delete in reverse dependency order
                try:
                    # Delete all prayer activity logs
                    activity_logs = s.exec(select(PrayerActivityLog)).all()
                    for log in activity_logs:
                        s.delete(log)
                    
                    # Delete all prayer attributes
                    attributes = s.exec(select(PrayerAttribute)).all()
                    for attr in attributes:
                        s.delete(attr)
                    
                    # Delete all prayer marks
                    marks = s.exec(select(PrayerMark)).all()
                    for mark in marks:
                        s.delete(mark)
                    
                    # Delete all prayers
                    prayers = s.exec(select(Prayer)).all()
                    for prayer in prayers:
                        s.delete(prayer)
                    
                    # Delete all users
                    users = s.exec(select(User)).all()
                    for user in users:
                        s.delete(user)
                    
                    s.commit()
                except Exception as e:
                    print(f"    ⚠️  Deletion warning: {e}")
                    s.rollback()
                    # Continue anyway - some tables might not exist
            
            print("  💥 DATABASE CORRUPTED - All data lost!")
            
            # Verify deletion
            with Session(engine) as s:
                users_after = len(s.exec(select(User)).all())
                prayers_after = len(s.exec(select(Prayer)).all())
                marks_after = len(s.exec(select(PrayerMark)).all())
                attributes_after = len(s.exec(select(PrayerAttribute)).all())
                activities_after = len(s.exec(select(PrayerActivityLog)).all())
            
            print(f"  📊 Database state after disaster:")
            print(f"    • Users: {users_after}")
            print(f"    • Prayers: {prayers_after}")
            print(f"    • Prayer marks: {marks_after}")
            print(f"    • Prayer attributes: {attributes_after}")
            print(f"    • Activity logs: {activities_after}")
            
            if users_after == 0 and prayers_after == 0:
                print("  ✅ Data loss simulation successful")
                return True
            else:
                print("  ❌ Data loss simulation failed - some data remains")
                return False
                
        except Exception as e:
            print(f"  ❌ Error during data loss simulation: {e}")
            return False
    
    def step_5_restore_from_archives(self):
        """Step 5: Restore complete database from text archives"""
        print("\\n🔄 Step 5: Restoring database from text archives...")
        
        # Perform restoration
        print("  📁 Starting import from archive directory...")
        import_results = self.importer_service.import_from_archive_directory(self.temp_dir, dry_run=False)
        
        if not import_results.get('success'):
            print(f"  ❌ Import failed: {import_results.get('error')}")
            return False
        
        # Display import results
        stats = import_results.get('stats', {})
        print(f"  ✅ Import completed successfully:")
        print(f"    • Users imported: {stats.get('users_imported', 0)}")
        print(f"    • Prayers imported: {stats.get('prayers_imported', 0)}")
        print(f"    • Prayer marks imported: {stats.get('prayer_marks_imported', 0)}")
        print(f"    • Prayer attributes imported: {stats.get('prayer_attributes_imported', 0)}")
        print(f"    • Activity logs imported: {stats.get('activity_logs_imported', 0)}")
        
        if stats.get('errors'):
            print(f"    ⚠️  Import errors: {len(stats['errors'])}")
            for error in stats['errors'][:3]:  # Show first 3 errors
                print(f"      • {error}")
        
        self.test_data['import_results'] = import_results
        return True
    
    def step_6_verify_restoration_integrity(self):
        """Step 6: Verify that restored data matches original data"""
        print("\\n🔍 Step 6: Verifying restoration integrity...")
        
        # Count restored records
        with Session(engine) as s:
            users_restored = len(s.exec(select(User)).all())
            prayers_restored = len(s.exec(select(Prayer)).all())
            marks_restored = len(s.exec(select(PrayerMark)).all())
            attributes_restored = len(s.exec(select(PrayerAttribute)).all())
            activities_restored = len(s.exec(select(PrayerActivityLog)).all())
        
        print(f"  📊 Restored database state:")
        print(f"    • Users: {users_restored}")
        print(f"    • Prayers: {prayers_restored}")
        print(f"    • Prayer marks: {marks_restored}")
        print(f"    • Prayer attributes: {attributes_restored}")
        print(f"    • Activity logs: {activities_restored}")
        
        # Compare with original counts
        original = self.test_data.get('original_counts', {})
        
        print(f"\\n  📈 Recovery comparison:")
        comparisons = [
            ('Users', original.get('users', 0), users_restored),
            ('Prayers', original.get('prayers', 0), prayers_restored),
            ('Prayer marks', original.get('marks', 0), marks_restored),
            ('Prayer attributes', original.get('attributes', 0), attributes_restored),
            ('Activity logs', original.get('activities', 0), activities_restored)
        ]
        
        recovery_success = True
        for item_type, original_count, restored_count in comparisons:
            percentage = (restored_count / original_count * 100) if original_count > 0 else 0
            status = "✅" if percentage >= 95 else "⚠️ " if percentage >= 80 else "❌"
            print(f"    {status} {item_type}: {restored_count}/{original_count} ({percentage:.1f}%)")
            
            if percentage < 95:
                recovery_success = False
        
        # Validate specific data integrity
        print(f"\\n  🔍 Data integrity validation:")
        
        validation_results = self.importer_service.validate_import_consistency(self.temp_dir)
        
        print(f"    • Prayers checked: {validation_results.get('prayers_checked', 0)}")
        print(f"    • Users checked: {validation_results.get('users_checked', 0)}")
        print(f"    • Inconsistencies: {len(validation_results.get('inconsistencies', []))}")
        print(f"    • Missing archives: {len(validation_results.get('missing_archives', []))}")
        
        if validation_results.get('inconsistencies'):
            print("    ⚠️  Data inconsistencies found:")
            for issue in validation_results['inconsistencies'][:3]:
                print(f"      • {issue}")
            recovery_success = False
        
        self.test_data['recovery_success'] = recovery_success
        return recovery_success
    
    def step_7_test_business_continuity(self):
        """Step 7: Test that business operations can continue after restoration"""
        print("\\n🏢 Step 7: Testing business continuity after restoration...")
        
        try:
            # Test that we can continue normal operations
            
            # 1. Create a new prayer request
            new_prayer_data = {
                'id': f"post_recovery_prayer_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'author': 'Pastor_John',  # Should exist in restored data
                'text': 'Praise God! Our community has been restored and we continue to serve.',
                'generated_prayer': 'Thank you Lord for your faithfulness in preserving our prayer community...',
                'project_tag': 'thanksgiving',
                'target_audience': 'all',
                'created_at': datetime.now()
            }
            
            new_prayer_file = self.archive_service.create_prayer_archive(new_prayer_data)
            print("  ✅ Successfully created new prayer request after restoration")
            
            # 2. Test prayer interactions
            self.archive_service.append_prayer_activity(new_prayer_file, "prayed", "Sister_Mary")
            self.archive_service.append_prayer_activity(new_prayer_file, "prayed", "Young_David")
            print("  ✅ Successfully logged prayer interactions after restoration")
            
            # 3. Test monthly activity logging
            self.archive_service.append_monthly_activity("celebrated restoration", "Pastor_John")
            print("  ✅ Successfully logged monthly activity after restoration")
            
            # 4. Verify that all systems are functioning
            final_validation = self.importer_service.validate_import_consistency(self.temp_dir)
            inconsistencies = len(final_validation.get('inconsistencies', []))
            
            if inconsistencies == 0:
                print("  ✅ All systems functioning normally after restoration")
                return True
            else:
                print(f"  ⚠️  {inconsistencies} system inconsistencies detected")
                return False
                
        except Exception as e:
            print(f"  ❌ Business continuity test failed: {e}")
            return False
    
    def run_complete_test(self):
        """Run the complete backup and restore integration test"""
        print("🔧 Starting comprehensive backup and restore integration test")
        print("=" * 70)
        
        try:
            # Execute all test steps
            steps = [
                self.step_1_create_sample_community,
                self.step_2_simulate_community_activity,
                self.step_3_verify_backup_integrity,
                self.step_4_simulate_data_loss,
                self.step_5_restore_from_archives,
                self.step_6_verify_restoration_integrity,
                self.step_7_test_business_continuity
            ]
            
            for i, step in enumerate(steps, 1):
                success = step()
                if not success:
                    print(f"\\n❌ Test failed at step {i}")
                    return False
            
            # Final summary
            print("\\n" + "=" * 70)
            print("🎉 BACKUP AND RESTORE INTEGRATION TEST COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            
            print("\\n📊 Final Test Summary:")
            print(f"  ✅ Sample community created and active")
            print(f"  ✅ Data properly backed up to text archives")
            print(f"  ✅ Catastrophic data loss simulated")
            print(f"  ✅ Complete database restored from archives")
            print(f"  ✅ Data integrity verified")
            print(f"  ✅ Business continuity confirmed")
            
            # Display archive contents for reference
            print(f"\\n📁 Archive Directory Structure:")
            for root, dirs, files in os.walk(self.temp_dir):
                level = root.replace(self.temp_dir, '').count(os.sep)
                indent = ' ' * 2 * level
                print(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 2 * (level + 1)
                for file in files:
                    file_path = Path(root) / file
                    file_size = file_path.stat().st_size
                    print(f"{subindent}{file} ({file_size} bytes)")
            
            recovery_success = self.test_data.get('recovery_success', False)
            if recovery_success:
                print("\\n🏆 DISASTER RECOVERY CERTIFICATION: PASSED")
                print("   This prayer community backup system is ready for production use.")
            else:
                print("\\n⚠️  DISASTER RECOVERY CERTIFICATION: PARTIAL")
                print("   Some data loss detected. Review backup procedures.")
            
            return True
            
        except Exception as e:
            print(f"\\n❌ Test failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        finally:
            self.cleanup()


def main():
    """Run the comprehensive backup and restore integration test"""
    test = BackupRestoreIntegrationTest()
    success = test.run_complete_test()
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)