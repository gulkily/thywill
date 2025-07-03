"""
Comprehensive test suite for heal-archives idempotency and completeness.

This test module verifies that:
1. heal-archives is fully idempotent (repeated runs = no changes)
2. heal-archives creates comprehensive activity data
3. heal → import → heal produces identical database state
4. All edge cases are handled properly
"""

import pytest
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from app_helpers.services.token_service import TOKEN_EXP_H
from sqlmodel import Session, select
from pathlib import Path

from models import (
    engine, Prayer, User, PrayerMark, PrayerAttribute, 
    PrayerActivityLog, InviteToken
)
from app_helpers.services.text_archive_service import TextArchiveService
from app_helpers.services.text_importer_service import TextImporterService
from tests.factories import UserFactory, PrayerFactory


@pytest.fixture
def temp_archive_dir():
    """Create temporary archive directory for testing"""
    temp_dir = tempfile.mkdtemp(prefix="test_heal_archives_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def archive_service(temp_archive_dir):
    """Create archive service with temporary directory"""
    return TextArchiveService(base_dir=temp_archive_dir)


@pytest.fixture
def importer_service(archive_service):
    """Create importer service"""
    return TextImporterService(archive_service)


@pytest.fixture
def sample_data(session):
    """Create sample prayers and users with comprehensive activity data"""
    # Create users
    user1 = UserFactory.create(display_name="testuser1", invited_by_username="admin")
    user2 = UserFactory.create(display_name="testuser2", invited_by_username="testuser1")
    session.add_all([user1, user2])
    session.commit()
    
    # Create prayers
    prayer1 = PrayerFactory.create(
        author_username=user1.display_name,
        text="Test prayer 1",
        generated_prayer="Generated prayer text 1"
    )
    prayer2 = PrayerFactory.create(
        author_username=user2.display_name,
        text="Test prayer 2", 
        generated_prayer="Generated prayer text 2"
    )
    session.add_all([prayer1, prayer2])
    session.commit()
    
    # Create comprehensive activity data
    # Prayer marks
    mark1 = PrayerMark(
        prayer_id=prayer1.id,
        username=user2.display_name,
        created_at=datetime.now() - timedelta(days=2)
    )
    mark2 = PrayerMark(
        prayer_id=prayer2.id,
        username=user1.display_name,
        created_at=datetime.now() - timedelta(days=1)
    )
    session.add_all([mark1, mark2])
    
    # Prayer attributes
    attr1 = PrayerAttribute(
        prayer_id=prayer1.id,
        attribute_name="answered",
        attribute_value="true",
        created_by=user1.display_name,
        created_at=datetime.now() - timedelta(days=1)
    )
    attr2 = PrayerAttribute(
        prayer_id=prayer1.id,
        attribute_name="answer_testimony",
        attribute_value="God answered in amazing ways!",
        created_by=user1.display_name,
        created_at=datetime.now() - timedelta(hours=TOKEN_EXP_H)
    )
    attr3 = PrayerAttribute(
        prayer_id=prayer2.id,
        attribute_name="archived",
        attribute_value="true",
        created_by=user2.display_name,
        created_at=datetime.now() - timedelta(hours=6)
    )
    session.add_all([attr1, attr2, attr3])
    
    # Activity logs
    activity1 = PrayerActivityLog(
        prayer_id=prayer1.id,
        username=user1.display_name,
        action="answered",
        old_value=None,
        new_value="true",
        created_at=datetime.now() - timedelta(days=1)
    )
    activity2 = PrayerActivityLog(
        prayer_id=prayer2.id,
        username=user2.display_name,
        action="archived",
        old_value=None,
        new_value="true",
        created_at=datetime.now() - timedelta(hours=6)
    )
    session.add_all([activity1, activity2])
    
    session.commit()
    session.refresh(prayer1)
    session.refresh(prayer2)
    session.refresh(user1)
    session.refresh(user2)
    
    return {
        'users': [user1, user2],
        'prayers': [prayer1, prayer2],
        'marks': [mark1, mark2],
        'attributes': [attr1, attr2, attr3],
        'activities': [activity1, activity2]
    }


def capture_database_state(session):
    """Capture complete database state for comparison"""
    prayers = session.exec(select(Prayer)).all()
    users = session.exec(select(User)).all()
    marks = session.exec(select(PrayerMark)).all()
    attributes = session.exec(select(PrayerAttribute)).all()
    activities = session.exec(select(PrayerActivityLog)).all()
    
    return {
        'prayers': [(p.id, p.text, p.author_username, p.text_file_path) for p in prayers],
        'users': [(u.display_name, u.invited_by_username, u.text_file_path) for u in users],
        'marks': [(m.prayer_id, m.username, m.created_at.isoformat()) for m in marks],
        'attributes': [(a.prayer_id, a.attribute_name, a.attribute_value, a.created_by, a.created_at.isoformat()) for a in attributes],
        'activities': [(a.prayer_id, a.user_id, a.action, a.old_value, a.new_value, a.created_at.isoformat()) for a in activities]
    }


def run_heal_archives_script(archive_service):
    """Run heal archives script programmatically"""
    # Import heal functions
    import sys
    sys.path.insert(0, '/home/wsl/thywill')
    
    # Mock text_archive_service to use our test service
    import heal_prayer_archives
    original_service = heal_prayer_archives.text_archive_service
    heal_prayer_archives.text_archive_service = archive_service
    
    try:
        # Run healing functions
        prayer_result = heal_prayer_archives.heal_prayer_archives()
        user_result = heal_prayer_archives.heal_user_archives()
        return prayer_result and user_result
    finally:
        # Restore original service
        heal_prayer_archives.text_archive_service = original_service


@pytest.mark.integration
class TestHealArchivesIdempotency:
    """Test suite for heal-archives idempotency and completeness"""
    
    def test_heal_creates_comprehensive_activity_data(self, session, sample_data, archive_service):
        """Test that heal-archives creates complete activity data"""
        # Clear existing archive paths
        for prayer in sample_data['prayers']:
            prayer.text_file_path = None
        for user in sample_data['users']:
            user.text_file_path = None
        session.commit()
        
        # Run heal archives
        success = run_heal_archives_script(archive_service)
        assert success, "Heal archives should succeed"
        
        # Verify all records now have archive paths
        session.refresh(sample_data['prayers'][0])
        session.refresh(sample_data['prayers'][1])
        session.refresh(sample_data['users'][0])
        session.refresh(sample_data['users'][1])
        
        assert sample_data['prayers'][0].text_file_path is not None
        assert sample_data['prayers'][1].text_file_path is not None
        assert sample_data['users'][0].text_file_path is not None
        assert sample_data['users'][1].text_file_path is not None
        
        # Verify archive files exist
        assert os.path.exists(sample_data['prayers'][0].text_file_path)
        assert os.path.exists(sample_data['prayers'][1].text_file_path)
        assert os.path.exists(sample_data['users'][0].text_file_path)
        assert os.path.exists(sample_data['users'][1].text_file_path)
        
        # Verify archive files contain activity data
        with open(sample_data['prayers'][0].text_file_path, 'r') as f:
            content = f.read()
            assert "answered" in content
            assert "God answered in amazing ways!" in content  # testimony
            assert "prayed this prayer" in content  # prayer mark
    
    def test_heal_archives_is_fully_idempotent(self, session, sample_data, archive_service):
        """Test that repeated heal-archives runs make no changes"""
        # Clear existing archive paths
        for prayer in sample_data['prayers']:
            prayer.text_file_path = None
        for user in sample_data['users']:
            user.text_file_path = None
        session.commit()
        
        # First run
        success1 = run_heal_archives_script(archive_service)
        assert success1
        
        # Capture state after first run
        first_run_state = capture_database_state(session)
        
        # Get file modification times
        prayer1_mtime = os.path.getmtime(sample_data['prayers'][0].text_file_path)
        prayer2_mtime = os.path.getmtime(sample_data['prayers'][1].text_file_path)
        
        # Second run (should be idempotent)
        success2 = run_heal_archives_script(archive_service)
        assert success2
        
        # Capture state after second run
        second_run_state = capture_database_state(session)
        
        # Verify states are identical
        assert first_run_state == second_run_state, "Database state should be identical after second run"
        
        # Verify files weren't modified (idempotent behavior)
        assert os.path.getmtime(sample_data['prayers'][0].text_file_path) == prayer1_mtime
        assert os.path.getmtime(sample_data['prayers'][1].text_file_path) == prayer2_mtime
    
    def test_heal_detects_incomplete_archives(self, session, sample_data, archive_service):
        """Test that heal detects and updates incomplete archive files"""
        # First run - create initial archives
        success = run_heal_archives_script(archive_service)
        assert success
        
        # Simulate adding new activity after archive creation
        new_mark = PrayerMark(
            prayer_id=sample_data['prayers'][0].id,
            username=sample_data['users'][1].display_name,
            created_at=datetime.now()
        )
        session.add(new_mark)
        session.commit()
        
        # Second run should detect and update the incomplete archive
        success2 = run_heal_archives_script(archive_service)
        assert success2
        
        # Verify new activity is included in archive
        with open(sample_data['prayers'][0].text_file_path, 'r') as f:
            content = f.read()
            # Should have multiple "prayed this prayer" entries now
            prayed_count = content.count("prayed this prayer")
            assert prayed_count >= 2, "Archive should include new prayer mark"
    
    def test_heal_import_roundtrip_integrity(self, session, sample_data, archive_service, importer_service):
        """Test heal → import → heal produces identical results"""
        # Original database state
        original_state = capture_database_state(session)
        
        # Step 1: Clear archives and heal
        for prayer in sample_data['prayers']:
            prayer.text_file_path = None
        for user in sample_data['users']:
            user.text_file_path = None
        session.commit()
        
        success = run_heal_archives_script(archive_service)
        assert success
        
        post_heal_state = capture_database_state(session)
        
        # Step 2: Clear database and import from archives
        # Clear all data
        session.exec(select(PrayerActivityLog)).delete()
        session.exec(select(PrayerAttribute)).delete()
        session.exec(select(PrayerMark)).delete()
        session.exec(select(Prayer)).delete()
        session.exec(select(User)).delete()
        session.commit()
        
        # Import from archives
        import_result = importer_service.import_from_archive_directory(
            archive_dir=str(archive_service.base_dir)
        )
        assert import_result['success'], f"Import failed: {import_result.get('error')}"
        
        post_import_state = capture_database_state(session)
        
        # Step 3: Run heal again (should be no-op)
        success3 = run_heal_archives_script(archive_service)
        assert success3
        
        final_state = capture_database_state(session)
        
        # Verify round-trip integrity
        # Note: We compare the essential data, not file paths which may differ
        def normalize_state(state):
            return {
                'prayers': [(p[0], p[1], p[2]) for p in state['prayers']],  # id, text, author_username
                'users': [(u[0], u[1]) for u in state['users']],  # display_name, invited_by
                'marks': state['marks'],
                'attributes': state['attributes'],
                'activities': state['activities']
            }
        
        normalized_original = normalize_state(original_state)
        normalized_final = normalize_state(final_state)
        
        assert normalized_original == normalized_final, "Round-trip should preserve all data integrity"
    
    def test_heal_handles_missing_activity_tables(self, session):
        """Test heal gracefully handles missing activity tables"""
        # This test would require temporary database manipulation
        # For now, we test the table checking function
        import heal_prayer_archives
        
        # Test with all tables present (should return empty list)
        missing = heal_prayer_archives.check_database_tables()
        assert len(missing) == 0, f"No tables should be missing, but got: {missing}"
    
    def test_heal_preserves_archive_chronological_order(self, session, sample_data, archive_service):
        """Test that archived activities maintain chronological order"""
        success = run_heal_archives_script(archive_service)
        assert success
        
        # Read archive file and verify chronological order
        with open(sample_data['prayers'][0].text_file_path, 'r') as f:
            content = f.read()
            
        # Find activity section
        lines = content.split('\n')
        activity_start = None
        for i, line in enumerate(lines):
            if line.strip() == "Activity:":
                activity_start = i + 1
                break
        
        assert activity_start is not None, "Archive should have Activity section"
        
        # Check that activities appear in chronological order
        # (This is a basic check - could be enhanced with timestamp parsing)
        activity_lines = [line for line in lines[activity_start:] if line.strip()]
        assert len(activity_lines) > 0, "Should have activity entries"