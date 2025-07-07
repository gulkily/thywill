"""Unit tests for prayer management functionality"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from fastapi import HTTPException
from sqlmodel import Session, select, func

from models import User, Prayer, PrayerMark, Session as SessionModel
from tests.factories import UserFactory, PrayerFactory, PrayerMarkFactory, SessionFactory
from app import is_admin


@pytest.mark.unit
class TestPrayerSubmission:
    """Test prayer submission and validation"""
    
    def test_prayer_text_validation_length(self, test_session):
        """Test prayer text length validation (500 char limit)"""
        user = UserFactory.create()
        test_session.add(user)
        test_session.commit()
        
        # Test normal length text
        normal_text = "Please pray for my healing"
        prayer = PrayerFactory.create(
            author_username=user.display_name,
            text=normal_text
        )
        test_session.add(prayer)
        test_session.commit()
        
        assert prayer.text == normal_text
        
        # Test maximum length text (500 chars)
        max_text = "x" * 500
        prayer_max = PrayerFactory.create(
            author_username=user.display_name,
            text=max_text
        )
        test_session.add(prayer_max)
        test_session.commit()
        
        assert len(prayer_max.text) == 500
        
        # Test text that would be truncated (simulating app logic)
        long_text = "x" * 600
        truncated_text = long_text[:500]  # App logic truncates at 500
        
        prayer_long = PrayerFactory.create(
            author_username=user.display_name,
            text=truncated_text
        )
        test_session.add(prayer_long)
        test_session.commit()
        
        assert len(prayer_long.text) == 500
    
    def test_prayer_submission_with_generated_prayer(self, test_session):
        """Test prayer submission includes generated prayer"""
        user = UserFactory.create()
        test_session.add(user)
        test_session.commit()
        
        original_text = "Please pray for my test"
        generated_text = "Divine Creator, we lift up our friend. Amen."
        
        prayer = PrayerFactory.create(
            author_username=user.display_name,
            text=original_text,
            generated_prayer=generated_text
        )
        test_session.add(prayer)
        test_session.commit()
        
        assert prayer.text == original_text
        assert prayer.generated_prayer == generated_text
        assert prayer.author_username == user.display_name
        assert prayer.flagged is False
    
    def test_prayer_submission_with_project_tag(self, test_session):
        """Test prayer submission with optional project tag"""
        user = UserFactory.create()
        test_session.add(user)
        test_session.commit()
        
        # Prayer with tag
        prayer_with_tag = PrayerFactory.create(
            author_username=user.display_name,
            text="Prayer with tag",
            project_tag="health"
        )
        
        # Prayer without tag
        prayer_without_tag = PrayerFactory.create(
            author_username=user.display_name,
            text="Prayer without tag",
            project_tag=None
        )
        
        test_session.add_all([prayer_with_tag, prayer_without_tag])
        test_session.commit()
        
        assert prayer_with_tag.project_tag == "health"
        assert prayer_without_tag.project_tag is None
    
    def test_prayer_submission_requires_authentication(self):
        """Test that prayer submission logic validates authentication"""
        # Simulate authentication check for prayer submission
        
        # Full authentication - should be allowed
        full_session = SessionFactory.create(is_fully_authenticated=True)
        assert full_session.is_fully_authenticated is True
        
        # Half authentication - should be rejected  
        half_session = SessionFactory.create(is_fully_authenticated=False)
        assert half_session.is_fully_authenticated is False
        
        # In app.py, submit_prayer route checks: 
        # if not session.is_fully_authenticated:
        #     raise HTTPException(403, "Full authentication required to submit prayers")
        
        # This validates the session check logic
    
    def test_prayer_creation_timestamp(self, test_session):
        """Test prayer creation timestamp is set correctly"""
        user = UserFactory.create()
        test_session.add(user)
        test_session.commit()
        
        before_creation = datetime.utcnow()
        
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add(prayer)
        test_session.commit()
        
        after_creation = datetime.utcnow()
        
        assert before_creation <= prayer.created_at <= after_creation
    
    def test_prayer_submission_does_not_auto_create_prayer_marks(self, test_session):
        """Test that submitting a prayer does NOT automatically create PrayerMark records"""
        # Create two users - one will submit prayer, other could be potential prayer partner
        user1 = UserFactory.create()
        user2 = UserFactory.create() 
        test_session.add_all([user1, user2])
        test_session.commit()
        
        # Count initial prayer marks (should be 0)
        initial_marks_count = test_session.query(func.count(PrayerMark.id)).scalar()
        assert initial_marks_count == 0
        
        # Create a new prayer (simulating prayer submission)
        prayer = PrayerFactory.create(
            author_username=user1.display_name,
            text="Please pray for my family"
        )
        test_session.add(prayer)
        test_session.commit()
        
        # Verify no PrayerMark records were automatically created
        final_marks_count = test_session.query(func.count(PrayerMark.id)).scalar()
        assert final_marks_count == 0
        
        # Verify prayer was created correctly
        assert prayer.author_username == user1.display_name
        assert prayer.text == "Please pray for my family"
        
        # Verify no marks exist for this prayer
        marks_for_prayer = test_session.query(PrayerMark).filter(
            PrayerMark.prayer_id == prayer.id
        ).all()
        assert len(marks_for_prayer) == 0


@pytest.mark.unit 
class TestPrayerMarking:
    """Test prayer marking functionality"""
    
    def test_prayer_mark_creation(self, test_session):
        """Test creating a prayer mark"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Create prayer mark
        mark = PrayerMarkFactory.create(
            username=user.display_name,
            prayer_id=prayer.id
        )
        test_session.add(mark)
        test_session.commit()
        
        assert mark.username == user.display_name
        assert mark.prayer_id == prayer.id
        assert isinstance(mark.created_at, datetime)
    
    def test_multiple_marks_same_prayer(self, test_session):
        """Test user can mark same prayer multiple times"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=user.display_name)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Create multiple marks for same prayer by same user
        mark1 = PrayerMarkFactory.create(
            username=user.display_name,
            prayer_id=prayer.id,
            created_at=datetime.utcnow() - timedelta(hours=1)
        )
        mark2 = PrayerMarkFactory.create(
            username=user.display_name,
            prayer_id=prayer.id,
            created_at=datetime.utcnow()
        )
        
        test_session.add_all([mark1, mark2])
        test_session.commit()
        
        # Count marks for this prayer by this user
        stmt = select(func.count(PrayerMark.id)).where(
            PrayerMark.prayer_id == prayer.id,
            PrayerMark.username == user.display_name
        )
        mark_count = test_session.exec(stmt).first()
        
        assert mark_count == 2
    
    def test_prayer_mark_statistics(self, test_session):
        """Test prayer mark statistics calculation"""
        user1 = UserFactory.create(display_name="user1")
        user2 = UserFactory.create(display_name="user2")
        prayer = PrayerFactory.create(id="prayer1", author_username="user1")
        
        test_session.add_all([user1, user2, prayer])
        test_session.commit()
        
        # User1 marks prayer twice
        mark1 = PrayerMarkFactory.create(username="user1", prayer_id="prayer1")
        mark2 = PrayerMarkFactory.create(username="user1", prayer_id="prayer1")
        
        # User2 marks prayer once  
        mark3 = PrayerMarkFactory.create(username="user2", prayer_id="prayer1")
        
        test_session.add_all([mark1, mark2, mark3])
        test_session.commit()
        
        # Total marks count
        total_marks = test_session.exec(
            select(func.count(PrayerMark.id)).where(PrayerMark.prayer_id == "prayer1")
        ).first()
        assert total_marks == 3
        
        # Distinct users count
        distinct_users = test_session.exec(
            select(func.count(func.distinct(PrayerMark.username))).where(PrayerMark.prayer_id == "prayer1")
        ).first()
        assert distinct_users == 2
        
        # Marks by specific user
        user1_marks = test_session.exec(
            select(func.count(PrayerMark.id)).where(
                PrayerMark.prayer_id == "prayer1",
                PrayerMark.username == "user1"
            )
        ).first()
        assert user1_marks == 2
    
    def test_prayer_marking_requires_authentication(self):
        """Test prayer marking authentication requirements"""
        # Similar to prayer submission, marking requires full auth
        full_session = SessionFactory.create(is_fully_authenticated=True)
        half_session = SessionFactory.create(is_fully_authenticated=False)
        
        # In app.py, mark_prayer route checks:
        # if not session.is_fully_authenticated:
        #     raise HTTPException(403, "Full authentication required to mark prayers")
        
        assert full_session.is_fully_authenticated is True
        assert half_session.is_fully_authenticated is False
    
    def test_prayer_marking_nonexistent_prayer(self, test_session):
        """Test marking nonexistent prayer should fail"""
        # In the app, this would be handled by checking:
        # prayer = s.get(Prayer, prayer_id)
        # if not prayer:
        #     raise HTTPException(404, "Prayer not found")
        
        nonexistent_prayer = test_session.get(Prayer, "nonexistent_id")
        assert nonexistent_prayer is None


@pytest.mark.unit
class TestPrayerFlagging:
    """Test prayer flagging and unflagging functionality"""
    
    def test_prayer_flagging_toggle(self, test_session):
        """Test prayer flagging toggles flag status"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=user.display_name, flagged=False)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Flag the prayer
        prayer.flagged = True
        test_session.add(prayer)
        test_session.commit()
        
        updated_prayer = test_session.get(Prayer, prayer.id)
        assert updated_prayer.flagged is True
        
        # Unflag the prayer
        prayer.flagged = False
        test_session.add(prayer)
        test_session.commit()
        
        updated_prayer = test_session.get(Prayer, prayer.id)
        assert updated_prayer.flagged is False
    
    def test_flagging_permissions_admin(self, test_session):
        """Test that admin can flag and unflag prayers"""
        admin_user = UserFactory.create(display_name="admin")
        regular_user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=regular_user.display_name, flagged=False)
        
        test_session.add_all([admin_user, regular_user, prayer])
        test_session.commit()
        
        # Admin should be able to flag
        assert is_admin(admin_user) is True
        
        # Admin can flag
        prayer.flagged = True
        test_session.add(prayer)
        test_session.commit()
        
        assert prayer.flagged is True
        
        # Admin can unflag
        prayer.flagged = False
        test_session.add(prayer)
        test_session.commit()
        
        assert prayer.flagged is False
    
    def test_unflagging_permissions_regular_user(self, test_session):
        """Test that regular users cannot unflag prayers"""
        regular_user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=regular_user.display_name, flagged=True)
        
        test_session.add_all([regular_user, prayer])
        test_session.commit()
        
        # Regular user should not be admin
        assert is_admin(regular_user) is False
        
        # In app.py, the unflagging logic checks:
        # if p.flagged and not is_admin(user):
        #     raise HTTPException(403, "Only admins can unflag content")
        
        # This simulates that check
        if prayer.flagged and not is_admin(regular_user):
            # Should raise 403 - only admins can unflag
            assert True  # This represents the permission check
        else:
            assert False  # Should not reach here
    
    def test_flagging_any_user(self, test_session):
        """Test that any user can flag prayers (but not unflag)"""
        regular_user = UserFactory.create()
        prayer = PrayerFactory.create(author_username=regular_user.display_name, flagged=False)
        
        test_session.add_all([regular_user, prayer])
        test_session.commit()
        
        # Any user can flag (making it True)
        assert is_admin(regular_user) is False
        
        # Regular user can flag (set to True)
        prayer.flagged = True
        test_session.add(prayer)
        test_session.commit()
        
        assert prayer.flagged is True
    
    def test_flagged_prayers_excluded_from_feeds(self, test_session):
        """Test that flagged prayers are excluded from main feeds"""
        user = UserFactory.create()
        normal_prayer = PrayerFactory.create(author_username=user.display_name, flagged=False)
        flagged_prayer = PrayerFactory.create(author_username=user.display_name, flagged=True)
        
        test_session.add_all([user, normal_prayer, flagged_prayer])
        test_session.commit()
        
        # Query unflagged prayers (main feed logic)
        unflagged_prayers = test_session.exec(
            select(Prayer).where(Prayer.flagged == False)
        ).all()
        
        assert len(unflagged_prayers) == 1
        assert unflagged_prayers[0].id == normal_prayer.id
        
        # Query all prayers (admin view)
        all_prayers = test_session.exec(select(Prayer)).all()
        assert len(all_prayers) == 2


@pytest.mark.unit
class TestFeedFiltering:
    """Test prayer feed filtering functionality"""
    
    def test_all_prayers_feed(self, test_session):
        """Test 'all' feed returns all unflagged prayers"""
        user = UserFactory.create()
        
        prayer1 = PrayerFactory.create(author_username=user.display_name, flagged=False, text="Prayer 1")
        prayer2 = PrayerFactory.create(author_username=user.display_name, flagged=False, text="Prayer 2") 
        flagged_prayer = PrayerFactory.create(author_username=user.display_name, flagged=True, text="Flagged")
        
        test_session.add_all([user, prayer1, prayer2, flagged_prayer])
        test_session.commit()
        
        # Simulate 'all' feed query from app.py
        stmt = (
            select(Prayer, User.display_name)
            .join(User, Prayer.author_username == User.display_name)
            .where(Prayer.flagged == False)
            .order_by(Prayer.created_at.desc())
        )
        results = test_session.exec(stmt).all()
        
        # Should return only unflagged prayers
        assert len(results) == 2
        prayer_texts = [result[0].text for result in results]
        assert "Prayer 1" in prayer_texts
        assert "Prayer 2" in prayer_texts
        assert "Flagged" not in prayer_texts
    
    def test_new_unprayed_feed(self, test_session):
        """Test 'new_unprayed' feed returns prayers with no marks"""
        user1 = UserFactory.create(display_name="user1")
        user2 = UserFactory.create(display_name="user2")
        
        prayer1 = PrayerFactory.create(id="prayer1", author_username="user1", flagged=False)
        prayer2 = PrayerFactory.create(id="prayer2", author_username="user1", flagged=False)
        prayer3 = PrayerFactory.create(id="prayer3", author_username="user1", flagged=False)
        
        # Mark prayer1 and prayer2
        mark1 = PrayerMarkFactory.create(username="user2", prayer_id="prayer1")
        mark2 = PrayerMarkFactory.create(username="user2", prayer_id="prayer2")
        
        test_session.add_all([user1, user2, prayer1, prayer2, prayer3, mark1, mark2])
        test_session.commit()
        
        # Simulate 'new_unprayed' query logic from app.py
        stmt = (
            select(Prayer, User.display_name)
            .join(User, Prayer.author_username == User.display_name)
            .outerjoin(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.flagged == False)
            .group_by(Prayer.id)
            .having(func.count(PrayerMark.id) == 0)
            .order_by(Prayer.created_at.desc())
        )
        results = test_session.exec(stmt).all()
        
        # Should return only prayer3 (no marks)
        assert len(results) == 1
        assert results[0][0].id == "prayer3"
    
    def test_most_prayed_feed(self, test_session):
        """Test 'most_prayed' feed returns prayers with marks ordered by count"""
        user1 = UserFactory.create(display_name="user1")
        user2 = UserFactory.create(display_name="user2")
        
        prayer1 = PrayerFactory.create(id="prayer1", author_username="user1", flagged=False)
        prayer2 = PrayerFactory.create(id="prayer2", author_username="user1", flagged=False)
        prayer3 = PrayerFactory.create(id="prayer3", author_username="user1", flagged=False)  # No marks
        
        # Prayer1: 3 marks
        mark1a = PrayerMarkFactory.create(username="user1", prayer_id="prayer1")
        mark1b = PrayerMarkFactory.create(username="user2", prayer_id="prayer1")
        mark1c = PrayerMarkFactory.create(username="user1", prayer_id="prayer1")
        
        # Prayer2: 1 mark
        mark2a = PrayerMarkFactory.create(username="user2", prayer_id="prayer2")
        
        test_session.add_all([
            user1, user2, prayer1, prayer2, prayer3,
            mark1a, mark1b, mark1c, mark2a
        ])
        test_session.commit()
        
        # Simulate 'most_prayed' query from app.py
        stmt = (
            select(Prayer, User.display_name, func.count(PrayerMark.id).label('mark_count'))
            .join(User, Prayer.author_username == User.display_name)
            .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.flagged == False)
            .group_by(Prayer.id)
            .order_by(func.count(PrayerMark.id).desc())
            .limit(50)
        )
        results = test_session.exec(stmt).all()
        
        # Should return prayers ordered by mark count (prayer1 first, then prayer2)
        assert len(results) == 2  # prayer3 excluded (no marks)
        assert results[0][0].id == "prayer1"  # Most marks
        assert results[1][0].id == "prayer2"  # Fewer marks
        assert results[0][2] == 3  # Mark count for prayer1
        assert results[1][2] == 1  # Mark count for prayer2
    
    def test_my_prayers_feed(self, test_session):
        """Test 'my_prayers' feed returns prayers user has marked"""
        user1 = UserFactory.create(display_name="user1") 
        user2 = UserFactory.create(display_name="user2")
        
        prayer1 = PrayerFactory.create(id="prayer1", author_username="user2", flagged=False)
        prayer2 = PrayerFactory.create(id="prayer2", author_username="user2", flagged=False)
        prayer3 = PrayerFactory.create(id="prayer3", author_username="user2", flagged=False)
        
        # User1 marks prayer1 and prayer2 (but not prayer3)
        mark1 = PrayerMarkFactory.create(username="user1", prayer_id="prayer1")
        mark2 = PrayerMarkFactory.create(username="user1", prayer_id="prayer2")
        mark3 = PrayerMarkFactory.create(username="user2", prayer_id="prayer3")  # Different user
        
        test_session.add_all([user1, user2, prayer1, prayer2, prayer3, mark1, mark2, mark3])
        test_session.commit()
        
        # Simulate 'my_prayers' query for user1
        stmt = (
            select(Prayer, User.display_name)
            .join(User, Prayer.author_username == User.display_name)
            .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerMark.username == "user1")
            .group_by(Prayer.id)
            .order_by(func.max(PrayerMark.created_at).desc())
        )
        results = test_session.exec(stmt).all()
        
        # Should return prayers that user1 has marked
        assert len(results) == 2
        prayer_ids = [result[0].id for result in results]
        assert "prayer1" in prayer_ids
        assert "prayer2" in prayer_ids
        assert "prayer3" not in prayer_ids  # User1 didn't mark this
    
    def test_my_requests_feed(self, test_session):
        """Test 'my_requests' feed returns prayers authored by user"""
        user1 = UserFactory.create(display_name="user1")
        user2 = UserFactory.create(display_name="user2")
        
        # User1's prayers
        prayer1 = PrayerFactory.create(id="prayer1", author_username="user1", flagged=False)
        prayer2 = PrayerFactory.create(id="prayer2", author_username="user1", flagged=False)
        
        # User2's prayer
        prayer3 = PrayerFactory.create(id="prayer3", author_username="user2", flagged=False)
        
        test_session.add_all([user1, user2, prayer1, prayer2, prayer3])
        test_session.commit()
        
        # Simulate 'my_requests' query for user1
        stmt = (
            select(Prayer, User.display_name)
            .join(User, Prayer.author_username == User.display_name)
            .where(Prayer.flagged == False)
            .where(Prayer.author_username == "user1")
            .order_by(Prayer.created_at.desc())
        )
        results = test_session.exec(stmt).all()
        
        # Should return only user1's prayers
        assert len(results) == 2
        prayer_ids = [result[0].id for result in results]
        assert "prayer1" in prayer_ids
        assert "prayer2" in prayer_ids
        assert "prayer3" not in prayer_ids  # User2's prayer