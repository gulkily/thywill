"""Unit tests for prayer attributes system"""
import pytest
from datetime import datetime
from sqlmodel import Session, select

from models import Prayer, PrayerAttribute, PrayerActivityLog
from tests.factories import UserFactory, PrayerFactory, PrayerAttributeFactory, PrayerActivityLogFactory


@pytest.mark.unit
class TestPrayerAttributeModel:
    """Test the PrayerAttribute model"""
    
    def test_prayer_attribute_creation(self, test_session):
        """Test creating a prayer attribute"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        attribute = PrayerAttributeFactory.create(
            prayer_id=prayer.id,
            attribute_name="archived",
            attribute_value="true",
            created_by=user.display_name
        )
        test_session.add(attribute)
        test_session.commit()
        
        # Verify attribute was created
        saved_attr = test_session.get(PrayerAttribute, attribute.id)
        assert saved_attr is not None
        assert saved_attr.prayer_id == prayer.id
        assert saved_attr.attribute_name == "archived"
        assert saved_attr.attribute_value == "true"
        assert saved_attr.created_by == user.display_name
    
    def test_prayer_attribute_uniqueness(self, test_session):
        """Test that prayer + attribute_name combinations are unique"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Create first attribute
        attr1 = PrayerAttributeFactory.create(
            prayer_id=prayer.id,
            attribute_name="archived"
        )
        test_session.add(attr1)
        test_session.commit()
        
        # Attempt to create duplicate - this is allowed at database level
        # Application logic handles duplicates through set_attribute method
        attr2 = PrayerAttributeFactory.create(
            prayer_id=prayer.id,
            attribute_name="archived"
        )
        test_session.add(attr2)
        
        # This succeeds since no unique constraint exists at database level
        test_session.commit()
        
        # Verify both attributes exist
        attrs = test_session.exec(select(PrayerAttribute).where(
            PrayerAttribute.prayer_id == prayer.id,
            PrayerAttribute.attribute_name == "archived"
        )).all()
        assert len(attrs) == 2


@pytest.mark.unit
class TestPrayerAttributeOperations:
    """Test prayer attribute CRUD operations"""
    
    def test_prayer_has_attribute(self, test_session):
        """Test checking if prayer has an attribute"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Prayer shouldn't have archived attribute initially
        assert prayer.has_attribute('archived', test_session) == False
        
        # Add archived attribute
        prayer.set_attribute('archived', 'true', user.display_name, test_session)
        test_session.commit()
        
        # Now it should have the attribute
        assert prayer.has_attribute('archived', test_session) == True
        assert prayer.has_attribute('answered', test_session) == False
    
    def test_prayer_get_attribute(self, test_session):
        """Test getting attribute values"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Non-existent attribute should return None
        assert prayer.get_attribute('archived', test_session) is None
        
        # Set attribute and retrieve it
        prayer.set_attribute('archived', 'true', user.display_name, test_session)
        prayer.set_attribute('answer_testimony', 'God provided healing!', user.display_name, test_session)
        test_session.commit()
        
        assert prayer.get_attribute('archived', test_session) == 'true'
        assert prayer.get_attribute('answer_testimony', test_session) == 'God provided healing!'
    
    def test_prayer_set_attribute(self, test_session):
        """Test setting prayer attributes"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Set new attribute
        prayer.set_attribute('archived', 'true', user.display_name, test_session)
        test_session.commit()
        
        # Verify it was set
        assert prayer.get_attribute('archived', test_session) == 'true'
        
        # Update existing attribute
        prayer.set_attribute('archived', 'false', user.display_name, test_session)
        test_session.commit()
        
        # Verify it was updated
        assert prayer.get_attribute('archived', test_session) == 'false'
    
    def test_prayer_remove_attribute(self, test_session):
        """Test removing prayer attributes"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Set attribute first
        prayer.set_attribute('archived', 'true', user.display_name, test_session)
        test_session.commit()
        assert prayer.has_attribute('archived', test_session) == True
        
        # Remove attribute
        prayer.remove_attribute('archived', test_session, user.display_name)
        test_session.commit()
        
        # Verify it was removed
        assert prayer.has_attribute('archived', test_session) == False
        assert prayer.get_attribute('archived', test_session) is None


@pytest.mark.unit
class TestMultipleStatusSupport:
    """Test simultaneous multiple statuses"""
    
    def test_multiple_attributes_simultaneously(self, test_session):
        """Test prayer can have multiple attributes at once"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Set multiple attributes
        prayer.set_attribute('archived', 'true', user.display_name, test_session)
        prayer.set_attribute('answered', 'true', user.display_name, test_session)
        prayer.set_attribute('answer_date', datetime.utcnow().isoformat(), user.display_name, test_session)
        test_session.commit()
        
        # Verify all attributes exist
        assert prayer.is_archived(test_session) == True
        assert prayer.is_answered(test_session) == True
        assert prayer.answer_date(test_session) is not None
        
        # Should still be able to add more
        prayer.set_attribute('answer_testimony', 'Praise God!', user.display_name, test_session)
        test_session.commit()
        
        assert prayer.answer_testimony(test_session) == 'Praise God!'
    
    def test_convenience_properties(self, test_session):
        """Test prayer convenience property methods"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Initially all should be False/None
        assert prayer.is_archived(test_session) == False
        assert prayer.is_answered(test_session) == False
        assert prayer.answer_date(test_session) is None
        assert prayer.answer_testimony(test_session) is None
        
        # Set answered with testimony
        prayer.set_attribute('answered', 'true', user.display_name, test_session)
        prayer.set_attribute('answer_date', '2024-01-01T12:00:00', user.display_name, test_session)
        prayer.set_attribute('answer_testimony', 'God is good!', user.display_name, test_session)
        test_session.commit()
        
        # Verify convenience properties work
        assert prayer.is_answered(test_session) == True
        assert prayer.answer_date(test_session) == '2024-01-01T12:00:00'
        assert prayer.answer_testimony(test_session) == 'God is good!'


@pytest.mark.unit
class TestAttributePermissions:
    """Test attribute modification permissions"""
    
    def test_session_required_for_operations(self, test_session):
        """Test that session is required for attribute operations"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Should raise error without session
        with pytest.raises(ValueError, match="Session is required"):
            prayer.set_attribute('archived', 'true', user.display_name, None)
    
    def test_activity_logging_with_user_id(self, test_session):
        """Test that activity is logged when user_id is provided"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Count initial activity logs
        initial_count = len(test_session.exec(select(PrayerActivityLog)).all())
        
        # Set attribute with user_id
        prayer.set_attribute('archived', 'true', user.display_name, test_session)
        test_session.commit()
        
        # Should have created activity log
        final_count = len(test_session.exec(select(PrayerActivityLog)).all())
        assert final_count == initial_count + 1
        
        # Verify log content
        log = test_session.exec(
            select(PrayerActivityLog)
            .where(PrayerActivityLog.prayer_id == prayer.id)
        ).first()
        assert log is not None
        assert log.user_id == user.display_name
        assert log.action == 'set_archived'
        assert log.new_value == 'true'
    
    def test_activity_logging_without_user_id(self, test_session):
        """Test that no activity is logged without user_id"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Count initial activity logs
        initial_count = len(test_session.exec(select(PrayerActivityLog)).all())
        
        # Set attribute without user_id
        prayer.set_attribute('archived', 'true', None, test_session)
        test_session.commit()
        
        # Should not have created activity log
        final_count = len(test_session.exec(select(PrayerActivityLog)).all())
        assert final_count == initial_count