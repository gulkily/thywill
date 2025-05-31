"""Unit tests for prayer lifecycle management"""
import pytest
from datetime import datetime, timedelta
from sqlmodel import Session, select

from models import Prayer, PrayerAttribute, PrayerActivityLog
from tests.factories import UserFactory, PrayerFactory, PrayerAttributeFactory


@pytest.mark.unit
class TestArchiveWorkflow:
    """Test prayer archive and restore functionality"""
    
    def test_archive_prayer_workflow(self, test_session):
        """Test complete archive workflow"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Initially prayer should not be archived
        assert prayer.is_archived(test_session) == False
        
        # Archive the prayer
        prayer.set_attribute('archived', 'true', user.id, test_session)
        test_session.commit()
        
        # Verify prayer is archived
        assert prayer.is_archived(test_session) == True
        assert prayer.get_attribute('archived', test_session) == 'true'
        
        # Restore the prayer
        prayer.remove_attribute('archived', test_session, user.id)
        test_session.commit()
        
        # Verify prayer is no longer archived
        assert prayer.is_archived(test_session) == False
    
    def test_archive_preserves_other_attributes(self, test_session):
        """Test that archiving doesn't affect other attributes"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Set prayer as answered first
        prayer.set_attribute('answered', 'true', user.id, test_session)
        prayer.set_attribute('answer_testimony', 'God is faithful!', user.id, test_session)
        test_session.commit()
        
        # Then archive it
        prayer.set_attribute('archived', 'true', user.id, test_session)
        test_session.commit()
        
        # Should have both answered and archived attributes
        assert prayer.is_answered(test_session) == True
        assert prayer.is_archived(test_session) == True
        assert prayer.answer_testimony(test_session) == 'God is faithful!'
    
    def test_restore_only_removes_archive_attribute(self, test_session):
        """Test that restoring only removes archive attribute"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Set multiple attributes including archive
        prayer.set_attribute('answered', 'true', user.id, test_session)
        prayer.set_attribute('archived', 'true', user.id, test_session)
        prayer.set_attribute('answer_testimony', 'Blessed!', user.id, test_session)
        test_session.commit()
        
        # Restore (remove archive)
        prayer.remove_attribute('archived', test_session, user.id)
        test_session.commit()
        
        # Archive should be gone, others should remain
        assert prayer.is_archived(test_session) == False
        assert prayer.is_answered(test_session) == True
        assert prayer.answer_testimony(test_session) == 'Blessed!'


@pytest.mark.unit
class TestAnsweredWorkflow:
    """Test answered prayer functionality"""
    
    def test_mark_prayer_answered_basic(self, test_session):
        """Test basic answered prayer workflow"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Initially prayer should not be answered
        assert prayer.is_answered(test_session) == False
        
        # Mark as answered
        answer_date = datetime.utcnow().isoformat()
        prayer.set_attribute('answered', 'true', user.id, test_session)
        prayer.set_attribute('answer_date', answer_date, user.id, test_session)
        test_session.commit()
        
        # Verify prayer is answered
        assert prayer.is_answered(test_session) == True
        assert prayer.answer_date(test_session) == answer_date
    
    def test_mark_prayer_answered_with_testimony(self, test_session):
        """Test answered prayer with testimony"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Mark as answered with testimony
        testimony = "God provided exactly what I needed at the perfect time!"
        answer_date = datetime.utcnow().isoformat()
        
        prayer.set_attribute('answered', 'true', user.id, test_session)
        prayer.set_attribute('answer_date', answer_date, user.id, test_session)
        prayer.set_attribute('answer_testimony', testimony, user.id, test_session)
        test_session.commit()
        
        # Verify all answered prayer data
        assert prayer.is_answered(test_session) == True
        assert prayer.answer_date(test_session) == answer_date
        assert prayer.answer_testimony(test_session) == testimony
    
    def test_answered_prayer_can_be_archived(self, test_session):
        """Test that answered prayers can also be archived"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Mark as answered
        prayer.set_attribute('answered', 'true', user.id, test_session)
        prayer.set_attribute('answer_date', datetime.utcnow().isoformat(), user.id, test_session)
        test_session.commit()
        
        # Then archive it
        prayer.set_attribute('archived', 'true', user.id, test_session)
        test_session.commit()
        
        # Should have both statuses
        assert prayer.is_answered(test_session) == True
        assert prayer.is_archived(test_session) == True
    
    def test_testimony_can_be_updated(self, test_session):
        """Test that testimony can be updated after initial answer"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Initial testimony
        prayer.set_attribute('answered', 'true', user.id, test_session)
        prayer.set_attribute('answer_testimony', 'Initial testimony', user.id, test_session)
        test_session.commit()
        
        assert prayer.answer_testimony(test_session) == 'Initial testimony'
        
        # Update testimony
        prayer.set_attribute('answer_testimony', 'Updated testimony with more details', user.id, test_session)
        test_session.commit()
        
        assert prayer.answer_testimony(test_session) == 'Updated testimony with more details'


@pytest.mark.unit
class TestStatusTransitions:
    """Test valid and invalid status transitions"""
    
    def test_any_status_can_be_added_to_active_prayer(self, test_session):
        """Test that any status can be added to an active prayer"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Should be able to set any status on active prayer
        prayer.set_attribute('archived', 'true', user.id, test_session)
        test_session.commit()
        assert prayer.is_archived(test_session) == True
        
        prayer.set_attribute('answered', 'true', user.id, test_session)
        test_session.commit()
        assert prayer.is_answered(test_session) == True
        
        # Even flagged (though typically done by different users)
        prayer.set_attribute('flagged', 'true', user.id, test_session)
        test_session.commit()
        assert prayer.is_flagged_attr(test_session) == True
    
    def test_statuses_can_be_combined_freely(self, test_session):
        """Test that statuses can be combined in any way"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Set all possible combinations
        prayer.set_attribute('archived', 'true', user.id, test_session)
        prayer.set_attribute('answered', 'true', user.id, test_session)
        prayer.set_attribute('flagged', 'true', user.id, test_session)
        test_session.commit()
        
        # All should be active
        assert prayer.is_archived(test_session) == True
        assert prayer.is_answered(test_session) == True
        assert prayer.is_flagged_attr(test_session) == True
    
    def test_statuses_can_be_removed_independently(self, test_session):
        """Test that statuses can be removed independently"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Set all statuses
        prayer.set_attribute('archived', 'true', user.id, test_session)
        prayer.set_attribute('answered', 'true', user.id, test_session)
        prayer.set_attribute('flagged', 'true', user.id, test_session)
        test_session.commit()
        
        # Remove archived only
        prayer.remove_attribute('archived', test_session, user.id)
        test_session.commit()
        
        # Should still have answered and flagged
        assert prayer.is_archived(test_session) == False
        assert prayer.is_answered(test_session) == True
        assert prayer.is_flagged_attr(test_session) == True


@pytest.mark.unit
class TestActivityLogging:
    """Test activity logging for status changes"""
    
    def test_set_attribute_creates_activity_log(self, test_session):
        """Test that setting attributes creates activity logs"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Count initial logs
        initial_count = len(test_session.exec(select(PrayerActivityLog)).all())
        
        # Set attribute
        prayer.set_attribute('archived', 'true', user.id, test_session)
        test_session.commit()
        
        # Should have created log
        logs = test_session.exec(select(PrayerActivityLog)).all()
        assert len(logs) == initial_count + 1
        
        # Verify log details
        log = logs[-1]  # Get the latest log
        assert log.prayer_id == prayer.id
        assert log.user_id == user.id
        assert log.action == 'set_archived'
        assert log.old_value is None
        assert log.new_value == 'true'
    
    def test_update_attribute_logs_old_value(self, test_session):
        """Test that updating attributes logs the old value"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Set initial value
        prayer.set_attribute('answer_testimony', 'Initial testimony', user.id, test_session)
        test_session.commit()
        
        # Update value
        prayer.set_attribute('answer_testimony', 'Updated testimony', user.id, test_session)
        test_session.commit()
        
        # Get the update log (latest)
        logs = test_session.exec(
            select(PrayerActivityLog)
            .where(PrayerActivityLog.prayer_id == prayer.id)
            .where(PrayerActivityLog.action == 'set_answer_testimony')
            .order_by(PrayerActivityLog.created_at.desc())
        ).all()
        
        update_log = logs[0]  # Most recent
        assert update_log.old_value == 'Initial testimony'
        assert update_log.new_value == 'Updated testimony'
    
    def test_remove_attribute_creates_activity_log(self, test_session):
        """Test that removing attributes creates activity logs"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Set attribute first
        prayer.set_attribute('archived', 'true', user.id, test_session)
        test_session.commit()
        
        # Count logs before removal
        initial_count = len(test_session.exec(select(PrayerActivityLog)).all())
        
        # Remove attribute
        prayer.remove_attribute('archived', test_session, user.id)
        test_session.commit()
        
        # Should have created removal log
        logs = test_session.exec(select(PrayerActivityLog)).all()
        assert len(logs) == initial_count + 1
        
        # Verify removal log
        removal_log = logs[-1]
        assert removal_log.prayer_id == prayer.id
        assert removal_log.user_id == user.id
        assert removal_log.action == 'remove_archived'
        assert removal_log.old_value == 'true'
        assert removal_log.new_value is None
    
    def test_activity_log_chronological_order(self, test_session):
        """Test that activity logs maintain chronological order"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Perform series of actions
        prayer.set_attribute('archived', 'true', user.id, test_session)
        test_session.commit()
        
        prayer.set_attribute('answered', 'true', user.id, test_session)
        test_session.commit()
        
        prayer.remove_attribute('archived', test_session, user.id)
        test_session.commit()
        
        # Get logs in chronological order
        logs = test_session.exec(
            select(PrayerActivityLog)
            .where(PrayerActivityLog.prayer_id == prayer.id)
            .order_by(PrayerActivityLog.created_at.asc())
        ).all()
        
        assert len(logs) == 3
        assert logs[0].action == 'set_archived'
        assert logs[1].action == 'set_answered'
        assert logs[2].action == 'remove_archived'
        
        # Verify timestamps are in order
        assert logs[0].created_at <= logs[1].created_at <= logs[2].created_at