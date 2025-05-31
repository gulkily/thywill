"""Edge case tests for prayer attributes system"""
import pytest
from datetime import datetime, timedelta
from sqlmodel import Session, select

from models import Prayer, PrayerAttribute, PrayerActivityLog, User
from tests.factories import UserFactory, PrayerFactory, PrayerAttributeFactory


@pytest.mark.unit
class TestAttributeEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_setting_attribute_on_nonexistent_prayer(self, test_session):
        """Test setting attribute on prayer that doesn't exist in session"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        # Don't add prayer to session
        
        test_session.add(user)
        test_session.commit()
        
        # Should handle gracefully or raise appropriate error
        with pytest.raises(Exception):
            prayer.set_attribute('archived', 'true', user.id, test_session)
    
    def test_very_long_attribute_values(self, test_session):
        """Test handling of very long attribute values"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Very long testimony
        long_testimony = "A" * 10000  # 10k characters
        prayer.set_attribute('answer_testimony', long_testimony, user.id, test_session)
        test_session.commit()
        
        # Should store and retrieve correctly
        assert prayer.answer_testimony(test_session) == long_testimony
    
    def test_special_characters_in_attribute_values(self, test_session):
        """Test handling of special characters in attribute values"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Special characters and unicode
        special_testimony = "God's love is amazing! 🙏✝️ \"Blessed are the meek\" & more..."
        prayer.set_attribute('answer_testimony', special_testimony, user.id, test_session)
        test_session.commit()
        
        assert prayer.answer_testimony(test_session) == special_testimony
    
    def test_concurrent_attribute_modifications(self, test_session):
        """Test handling of concurrent attribute modifications"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Simulate concurrent updates to same attribute
        prayer.set_attribute('answer_testimony', 'First testimony', user.id, test_session)
        prayer.set_attribute('answer_testimony', 'Updated testimony', user.id, test_session)
        test_session.commit()
        
        # Latest value should win
        assert prayer.answer_testimony(test_session) == 'Updated testimony'
        
        # Should have activity logs for both changes
        logs = test_session.exec(
            select(PrayerActivityLog)
            .where(PrayerActivityLog.prayer_id == prayer.id)
            .where(PrayerActivityLog.action == 'set_answer_testimony')
            .order_by(PrayerActivityLog.created_at.asc())
        ).all()
        
        assert len(logs) == 2
        assert logs[0].new_value == 'First testimony'
        assert logs[1].old_value == 'First testimony'
        assert logs[1].new_value == 'Updated testimony'
    
    def test_removing_nonexistent_attribute(self, test_session):
        """Test removing attribute that doesn't exist"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Try to remove attribute that was never set
        prayer.remove_attribute('nonexistent', test_session, user.id)
        test_session.commit()
        
        # Should handle gracefully (no error, no activity log)
        logs = test_session.exec(
            select(PrayerActivityLog)
            .where(PrayerActivityLog.prayer_id == prayer.id)
        ).all()
        
        assert len(logs) == 0
    
    def test_setting_empty_attribute_values(self, test_session):
        """Test setting empty or None attribute values"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Empty string
        prayer.set_attribute('answer_testimony', '', user.id, test_session)
        test_session.commit()
        assert prayer.answer_testimony(test_session) == ''
        
        # None should be converted to string
        prayer.set_attribute('answer_testimony', None, user.id, test_session)
        test_session.commit()
        assert prayer.answer_testimony(test_session) == 'None'
    
    def test_invalid_attribute_names(self, test_session):
        """Test handling of invalid attribute names"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Very long attribute name
        long_name = "a" * 1000
        prayer.set_attribute(long_name, 'value', user.id, test_session)
        test_session.commit()
        
        assert prayer.get_attribute(long_name, test_session) == 'value'
        
        # Special characters in name
        special_name = "test-attribute_with.special/chars"
        prayer.set_attribute(special_name, 'value2', user.id, test_session)
        test_session.commit()
        
        assert prayer.get_attribute(special_name, test_session) == 'value2'


@pytest.mark.unit
class TestStatusCombinationEdgeCases:
    """Test edge cases with status combinations"""
    
    def test_all_possible_status_combinations(self, test_session):
        """Test all combinations of archived, answered, and flagged"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Test all 8 combinations (2^3)
        combinations = [
            (False, False, False),  # none
            (True, False, False),   # archived only
            (False, True, False),   # answered only
            (False, False, True),   # flagged only
            (True, True, False),    # archived + answered
            (True, False, True),    # archived + flagged
            (False, True, True),    # answered + flagged
            (True, True, True),     # all three
        ]
        
        for archived, answered, flagged in combinations:
            # Clear all attributes
            prayer.remove_attribute('archived', test_session, user.id)
            prayer.remove_attribute('answered', test_session, user.id)
            prayer.remove_attribute('flagged', test_session, user.id)
            
            # Set desired combination
            if archived:
                prayer.set_attribute('archived', 'true', user.id, test_session)
            if answered:
                prayer.set_attribute('answered', 'true', user.id, test_session)
            if flagged:
                prayer.set_attribute('flagged', 'true', user.id, test_session)
            
            test_session.commit()
            
            # Verify combination
            assert prayer.is_archived(test_session) == archived
            assert prayer.is_answered(test_session) == answered
            assert prayer.is_flagged_attr(test_session) == flagged
    
    def test_transitioning_between_all_states(self, test_session):
        """Test transitioning through all possible states"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Start with active prayer
        assert not prayer.is_archived(test_session)
        assert not prayer.is_answered(test_session)
        
        # Archive it
        prayer.set_attribute('archived', 'true', user.id, test_session)
        test_session.commit()
        assert prayer.is_archived(test_session)
        
        # Mark as answered while archived
        prayer.set_attribute('answered', 'true', user.id, test_session)
        test_session.commit()
        assert prayer.is_archived(test_session)
        assert prayer.is_answered(test_session)
        
        # Restore but keep answered
        prayer.remove_attribute('archived', test_session, user.id)
        test_session.commit()
        assert not prayer.is_archived(test_session)
        assert prayer.is_answered(test_session)
        
        # Archive again
        prayer.set_attribute('archived', 'true', user.id, test_session)
        test_session.commit()
        assert prayer.is_archived(test_session)
        assert prayer.is_answered(test_session)
        
        # All transitions should be logged
        logs = test_session.exec(
            select(PrayerActivityLog)
            .where(PrayerActivityLog.prayer_id == prayer.id)
            .order_by(PrayerActivityLog.created_at.asc())
        ).all()
        
        # Should have logs for: set_archived, set_answered, remove_archived, set_archived
        actions = [log.action for log in logs]
        assert 'set_archived' in actions
        assert 'set_answered' in actions
        assert 'remove_archived' in actions
        assert actions.count('set_archived') == 2  # Set twice
    
    def test_answered_prayer_with_multiple_testimony_updates(self, test_session):
        """Test answered prayer with multiple testimony updates"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Mark as answered with initial testimony
        prayer.set_attribute('answered', 'true', user.id, test_session)
        prayer.set_attribute('answer_testimony', 'Initial testimony', user.id, test_session)
        test_session.commit()
        
        # Update testimony multiple times
        testimonies = [
            'Updated with more details',
            'Added even more praise',
            'Final version with complete story'
        ]
        
        for testimony in testimonies:
            prayer.set_attribute('answer_testimony', testimony, user.id, test_session)
            test_session.commit()
        
        # Should have final testimony
        assert prayer.answer_testimony(test_session) == 'Final version with complete story'
        
        # Should maintain answered status throughout
        assert prayer.is_answered(test_session) == True
        
        # Should have activity log for each update
        testimony_logs = test_session.exec(
            select(PrayerActivityLog)
            .where(PrayerActivityLog.prayer_id == prayer.id)
            .where(PrayerActivityLog.action == 'set_answer_testimony')
            .order_by(PrayerActivityLog.created_at.asc())
        ).all()
        
        assert len(testimony_logs) == 4  # Initial + 3 updates


@pytest.mark.unit
class TestDatabaseConstraintEdgeCases:
    """Test database constraint and integrity edge cases"""
    
    def test_duplicate_attribute_handling(self, test_session):
        """Test handling of potential duplicate attributes"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Set attribute normally
        prayer.set_attribute('archived', 'true', user.id, test_session)
        test_session.commit()
        
        # Try to create duplicate manually (this should be prevented by unique constraint)
        duplicate_attr = PrayerAttributeFactory.create(
            prayer_id=prayer.id,
            attribute_name='archived',
            attribute_value='false'  # Different value
        )
        test_session.add(duplicate_attr)
        
        # Should raise integrity error
        with pytest.raises(Exception):
            test_session.commit()
        
        # Session should be in error state, need to rollback
        test_session.rollback()
        
        # Original value should still be there
        assert prayer.get_attribute('archived', test_session) == 'true'
    
    def test_prayer_deletion_with_attributes(self, test_session):
        """Test what happens when prayer with attributes is deleted"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Add some attributes
        prayer.set_attribute('archived', 'true', user.id, test_session)
        prayer.set_attribute('answered', 'true', user.id, test_session)
        test_session.commit()
        
        prayer_id = prayer.id
        
        # Verify attributes exist
        attrs_before = test_session.exec(
            select(PrayerAttribute).where(PrayerAttribute.prayer_id == prayer_id)
        ).all()
        assert len(attrs_before) == 2
        
        # Delete prayer
        test_session.delete(prayer)
        test_session.commit()
        
        # Attributes should still exist (no cascade delete)
        # This tests our foreign key constraint behavior
        attrs_after = test_session.exec(
            select(PrayerAttribute).where(PrayerAttribute.prayer_id == prayer_id)
        ).all()
        
        # Behavior depends on foreign key constraints
        # If we have CASCADE, attrs_after would be empty
        # If we don't, we'd get orphaned attributes
        # This test documents the current behavior
        print(f"Attributes after prayer deletion: {len(attrs_after)}")
    
    def test_user_deletion_with_activity_logs(self, test_session):
        """Test what happens when user who created activity logs is deleted"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Create some activity
        prayer.set_attribute('archived', 'true', user.id, test_session)
        test_session.commit()
        
        # Verify activity log exists
        logs_before = test_session.exec(
            select(PrayerActivityLog).where(PrayerActivityLog.user_id == user.id)
        ).all()
        assert len(logs_before) == 1
        
        user_id = user.id
        
        # Delete user
        test_session.delete(user)
        test_session.commit()
        
        # Activity logs should still exist (important for audit trail)
        logs_after = test_session.exec(
            select(PrayerActivityLog).where(PrayerActivityLog.user_id == user_id)
        ).all()
        
        # This preserves audit trail even if user is deleted
        assert len(logs_after) == 1


@pytest.mark.unit
class TestBoundaryConditions:
    """Test boundary conditions and limits"""
    
    def test_maximum_attributes_per_prayer(self, test_session):
        """Test setting many attributes on single prayer"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Set many different attributes
        for i in range(100):
            prayer.set_attribute(f'custom_attr_{i}', f'value_{i}', user.id, test_session)
        
        test_session.commit()
        
        # All should be retrievable
        for i in range(100):
            assert prayer.get_attribute(f'custom_attr_{i}', test_session) == f'value_{i}'
    
    def test_attribute_creation_timestamps(self, test_session):
        """Test that attribute timestamps are accurate and ordered"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        start_time = datetime.utcnow()
        
        # Set attributes with small delays
        import time
        
        prayer.set_attribute('first', 'value1', user.id, test_session)
        test_session.commit()
        time.sleep(0.01)  # 10ms delay
        
        prayer.set_attribute('second', 'value2', user.id, test_session)
        test_session.commit()
        time.sleep(0.01)
        
        prayer.set_attribute('third', 'value3', user.id, test_session)
        test_session.commit()
        
        end_time = datetime.utcnow()
        
        # Get attributes ordered by creation time
        attrs = test_session.exec(
            select(PrayerAttribute)
            .where(PrayerAttribute.prayer_id == prayer.id)
            .order_by(PrayerAttribute.created_at.asc())
        ).all()
        
        assert len(attrs) == 3
        assert attrs[0].attribute_name == 'first'
        assert attrs[1].attribute_name == 'second'
        assert attrs[2].attribute_name == 'third'
        
        # Timestamps should be in order and within test timeframe
        assert start_time <= attrs[0].created_at <= end_time
        assert attrs[0].created_at <= attrs[1].created_at <= attrs[2].created_at
    
    def test_activity_log_chronological_ordering(self, test_session):
        """Test that activity logs maintain strict chronological order"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Perform rapid sequence of operations
        operations = [
            ('set', 'archived', 'true'),
            ('set', 'answered', 'true'),
            ('set', 'answer_testimony', 'First testimony'),
            ('set', 'answer_testimony', 'Updated testimony'),
            ('remove', 'archived', None),
            ('set', 'archived', 'true'),
        ]
        
        for op_type, attr_name, value in operations:
            if op_type == 'set':
                prayer.set_attribute(attr_name, value, user.id, test_session)
            else:
                prayer.remove_attribute(attr_name, test_session, user.id)
            test_session.commit()
        
        # Get all activity logs in chronological order
        logs = test_session.exec(
            select(PrayerActivityLog)
            .where(PrayerActivityLog.prayer_id == prayer.id)
            .order_by(PrayerActivityLog.created_at.asc())
        ).all()
        
        # Should have one log per operation
        assert len(logs) == len(operations)
        
        # Timestamps should be strictly increasing
        for i in range(1, len(logs)):
            assert logs[i-1].created_at <= logs[i].created_at
        
        # Actions should match operation sequence
        expected_actions = []
        for op_type, attr_name, value in operations:
            if op_type == 'set':
                expected_actions.append(f'set_{attr_name}')
            else:
                expected_actions.append(f'remove_{attr_name}')
        
        actual_actions = [log.action for log in logs]
        assert actual_actions == expected_actions