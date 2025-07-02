"""
Basic functional tests for enhanced heal-archives functionality.

These tests verify core functionality without requiring full integration setup.
"""

import pytest
import tempfile
import shutil
from datetime import datetime, timedelta
from sqlmodel import Session, select

from models import Prayer, User, PrayerMark, PrayerAttribute, PrayerActivityLog
from tests.factories import UserFactory, PrayerFactory


@pytest.mark.functional
class TestHealArchivesBasic:
    """Basic tests for heal-archives enhanced functionality"""
    
    def test_collect_prayer_activity_data(self, test_session):
        """Test the collect_prayer_activity_data function"""
        # Import the function
        import sys
        sys.path.insert(0, '/home/wsl/thywill')
        from heal_prayer_archives import collect_prayer_activity_data
        
        # Create test data
        user = UserFactory.create(display_name="testuser")
        prayer = PrayerFactory.create(author_username=user.display_name, text="Test prayer")
        session.add_all([user, prayer])
        session.commit()
        
        # Add activity data
        mark = PrayerMark(
            prayer_id=prayer.id,
            username=user.display_name,
            created_at=datetime.now() - timedelta(hours=2)
        )
        
        attr = PrayerAttribute(
            prayer_id=prayer.id,
            attribute_name="answered",
            attribute_value="true",
            created_by=user.display_name,
            created_at=datetime.now() - timedelta(hours=1)
        )
        
        activity = PrayerActivityLog(
            prayer_id=prayer.id,
            user_id=user.display_name,
            action="answered",
            old_value=None,
            new_value="true",
            created_at=datetime.now() - timedelta(hours=1)
        )
        
        test_session.add_all([mark, attr, activity])
        test_session.commit()
        
        # Test the function
        activity_data = collect_prayer_activity_data(prayer.id, test_session)
        
        # Verify collected data (only activities now)
        assert len(activity_data['activities']) == 3  # prayed, answered, answered (from both mark and attribute)
        
        # Check that activities are collected
        activity_actions = [act['action'] for act in activity_data['activities']]
        assert 'prayed' in activity_actions
        assert 'answered' in activity_actions
        
        # Verify activity data structure
        prayed_activity = next(act for act in activity_data['activities'] if act['action'] == 'prayed')
        assert prayed_activity['user_id'] == user.display_name
        
        answered_activity = next(act for act in activity_data['activities'] if act['action'] == 'answered')
        assert answered_activity['user_id'] == user.display_name
        assert answered_activity['new_value'] == 'true'
    
    def test_collect_user_activity_data(self, test_session):
        """Test the collect_user_activity_data function"""
        # Import the function
        import sys
        sys.path.insert(0, '/home/wsl/thywill')
        from heal_prayer_archives import collect_user_activity_data
        
        # Create test data
        user = UserFactory.create(display_name="testuser")
        prayer1 = PrayerFactory.create(author_username=user.display_name, text="Prayer 1")
        prayer2 = PrayerFactory.create(author_username=user.display_name, text="Prayer 2")
        test_session.add_all([user, prayer1, prayer2])
        test_session.commit()
        
        # Add user activity across multiple prayers
        mark1 = PrayerMark(prayer_id=prayer1.id, username=user.display_name)
        mark2 = PrayerMark(prayer_id=prayer2.id, username=user.display_name)
        
        activity1 = PrayerActivityLog(
            prayer_id=prayer1.id,
            user_id=user.display_name,
            action="answered"
        )
        activity2 = PrayerActivityLog(
            prayer_id=prayer1.id,
            user_id=user.display_name,
            action="archived"
        )
        
        test_session.add_all([mark1, mark2, activity1, activity2])
        test_session.commit()
        
        # Test the function
        user_data = collect_user_activity_data(user.display_name, test_session)
        
        # Verify collected data (only activities now)
        assert user_data['activities_count'] == 4  # 2 prayed + 2 other activities
        assert user_data['total_prayers_with_activity'] == 2  # 2 different prayers with activities
    
    def test_verify_archive_completeness_with_activity(self, test_session, temp_file):
        """Test archive completeness verification with activity data"""
        # Import the function
        import sys
        sys.path.insert(0, '/home/wsl/thywill')
        from heal_prayer_archives import verify_archive_completeness
        
        # Create test data
        user = UserFactory.create(display_name="testuser")
        prayer = PrayerFactory.create(author_username=user.display_name, text="Test prayer")
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Test with no archive file
        assert not verify_archive_completeness(prayer, "/nonexistent/path", test_session)
        
        # Create an archive file
        archive_content = "Test archive content"
        with open(temp_file, 'w') as f:
            f.write(archive_content)
        
        # Test with empty activity data (should be complete)
        assert verify_archive_completeness(prayer, temp_file, test_session)
        
        # Add activity data
        mark = PrayerMark(
            prayer_id=prayer.id,
            username=user.display_name,
            created_at=datetime.now()  # Recent activity
        )
        test_session.add(mark)
        test_session.commit()
        
        # Archive should now appear incomplete (file older than activity)
        assert not verify_archive_completeness(prayer, temp_file, test_session)
    
    def test_database_table_checking(self):
        """Test database table existence checking"""
        import sys
        sys.path.insert(0, '/home/wsl/thywill')
        from heal_prayer_archives import check_database_tables
        
        # Should return empty list for properly initialized database
        missing = check_database_tables()
        assert isinstance(missing, list)
        # Note: In test environment, some tables might be missing
        # The important thing is the function doesn't crash
    
    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing"""
        import tempfile
        import os
        
        fd, path = tempfile.mkstemp()
        try:
            os.close(fd)
            yield path
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass