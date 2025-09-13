"""
Tests for PublicPrayerService
"""

import pytest
from sqlmodel import Session
from models import Prayer, PrayerAttribute, User, engine
from app_helpers.services.public_prayer_service import PublicPrayerService
import uuid


@pytest.mark.unit
def test_is_prayer_public_eligible():
    """Test the prayer eligibility filtering logic"""
    
    with Session(engine) as session:
        # Create test user
        test_user = User(display_name=f"testuser_{uuid.uuid4().hex[:8]}")
        session.add(test_user)
        session.commit()
        
        # Test 1: Regular prayer (should be eligible)
        prayer1 = Prayer(
            author_username=test_user.display_name,
            text="Please pray for my test",
            flagged=False
        )
        session.add(prayer1)
        session.commit()
        
        assert PublicPrayerService._is_prayer_public_eligible(prayer1, session) == True
        
        # Test 2: Flagged prayer (should not be eligible)
        prayer2 = Prayer(
            author_username=test_user.display_name,
            text="Flagged prayer",
            flagged=True
        )
        session.add(prayer2)
        session.commit()
        
        assert PublicPrayerService._is_prayer_public_eligible(prayer2, session) == False
        
        # Test 3: Archived prayer without praise report (should not be eligible)
        prayer3 = Prayer(
            author_username=test_user.display_name,
            text="Archived prayer",
            flagged=False
        )
        session.add(prayer3)
        session.commit()
        
        # Add archived attribute
        archived_attr = PrayerAttribute(
            prayer_id=prayer3.id,
            attribute_name="archived",
            attribute_value="true"
        )
        session.add(archived_attr)
        session.commit()
        
        assert PublicPrayerService._is_prayer_public_eligible(prayer3, session) == False
        
        # Test 4: Archived prayer with praise report (should be eligible)
        prayer4 = Prayer(
            author_username=test_user.display_name,
            text="Archived prayer with praise",
            flagged=False
        )
        session.add(prayer4)
        session.commit()
        
        # Add both archived and answered attributes
        archived_attr2 = PrayerAttribute(
            prayer_id=prayer4.id,
            attribute_name="archived",
            attribute_value="true"
        )
        answered_attr = PrayerAttribute(
            prayer_id=prayer4.id,
            attribute_name="answered",
            attribute_value="true"
        )
        session.add_all([archived_attr2, answered_attr])
        session.commit()
        
        assert PublicPrayerService._is_prayer_public_eligible(prayer4, session) == True
        
        # Cleanup
        session.delete(prayer1)
        session.delete(prayer2)
        session.delete(prayer3)
        session.delete(prayer4)
        session.delete(archived_attr)
        session.delete(archived_attr2)
        session.delete(answered_attr)
        session.delete(test_user)
        session.commit()


@pytest.mark.unit  
def test_get_public_prayers_pagination():
    """Test pagination functionality"""
    
    with Session(engine) as session:
        # Create test user
        test_user = User(display_name=f"testuser_{uuid.uuid4().hex[:8]}")
        session.add(test_user)
        session.commit()
        
        # Create multiple test prayers
        prayers = []
        for i in range(5):
            prayer = Prayer(
                author_username=test_user.display_name,
                text=f"Test prayer {i}",
                flagged=False
            )
            prayers.append(prayer)
            session.add(prayer)
        
        session.commit()
        
        try:
            # Test pagination with page_size=2
            result = PublicPrayerService.get_public_prayers(page=1, page_size=2, session=session)
            
            assert len(result['prayers']) <= 2
            assert result['pagination']['page'] == 1
            assert result['pagination']['page_size'] == 2
            assert result['pagination']['total_count'] >= 5
            
            # Test second page
            result_page2 = PublicPrayerService.get_public_prayers(page=2, page_size=2, session=session)
            assert result_page2['pagination']['page'] == 2
            
        finally:
            # Cleanup
            for prayer in prayers:
                session.delete(prayer)
            session.delete(test_user)
            session.commit()


@pytest.mark.unit
def test_get_public_prayer_by_id():
    """Test retrieving individual prayer by ID"""
    
    with Session(engine) as session:
        # Create test user
        test_user = User(display_name=f"testuser_{uuid.uuid4().hex[:8]}")
        session.add(test_user)
        session.commit()
        
        # Create test prayer
        prayer = Prayer(
            author_username=test_user.display_name,
            text="Test prayer for ID lookup",
            flagged=False
        )
        session.add(prayer)
        session.commit()
        
        try:
            # Test successful retrieval
            retrieved_prayer = PublicPrayerService.get_public_prayer_by_id(prayer.id, session)
            assert retrieved_prayer is not None
            assert retrieved_prayer.id == prayer.id
            assert retrieved_prayer.text == "Test prayer for ID lookup"
            
            # Test non-existent ID
            fake_id = uuid.uuid4().hex
            assert PublicPrayerService.get_public_prayer_by_id(fake_id, session) is None
            
        finally:
            # Cleanup
            session.delete(prayer)
            session.delete(test_user)
            session.commit()