"""Unit tests for basic database CRUD operations"""
import pytest
from datetime import datetime, timedelta
from sqlmodel import Session, select

from models import User, Prayer, Session as SessionModel, InviteToken, PrayerMark
from tests.factories import UserFactory, PrayerFactory, SessionFactory, InviteTokenFactory, PrayerMarkFactory


@pytest.mark.unit
class TestUserCRUD:
    """Test User model CRUD operations"""
    
    def test_create_user(self, test_session):
        """Test creating a user in the database"""
        user = UserFactory.create(display_name="John Doe")
        test_session.add(user)
        test_session.commit()
        
        # Verify user was created
        retrieved_user = test_session.get(User, user.id)
        assert retrieved_user is not None
        assert retrieved_user.display_name == "John Doe"
        assert retrieved_user.id == user.id
    
    def test_read_user(self, test_session):
        """Test reading a user from the database"""
        user = UserFactory.create(display_name="Jane Smith")
        test_session.add(user)
        test_session.commit()
        
        # Read by ID
        retrieved_user = test_session.get(User, user.id)
        assert retrieved_user.display_name == "Jane Smith"
        
        # Read by query
        stmt = select(User).where(User.display_name == "Jane Smith")
        queried_user = test_session.exec(stmt).first()
        assert queried_user.id == user.id
    
    def test_update_user(self, test_session):
        """Test updating a user in the database"""
        user = UserFactory.create(display_name="Original Name")
        test_session.add(user)
        test_session.commit()
        
        # Update the user
        user.display_name = "Updated Name"
        test_session.add(user)
        test_session.commit()
        
        # Verify update
        updated_user = test_session.get(User, user.id)
        assert updated_user.display_name == "Updated Name"
    
    def test_delete_user(self, test_session):
        """Test deleting a user from the database"""
        user = UserFactory.create()
        test_session.add(user)
        test_session.commit()
        
        user_id = user.id
        
        # Delete the user
        test_session.delete(user)
        test_session.commit()
        
        # Verify deletion
        deleted_user = test_session.get(User, user_id)
        assert deleted_user is None
    
    def test_list_all_users(self, test_session):
        """Test listing all users"""
        user1 = UserFactory.create(display_name="User One")
        user2 = UserFactory.create(display_name="User Two")
        test_session.add_all([user1, user2])
        test_session.commit()
        
        # Get all users
        stmt = select(User)
        all_users = test_session.exec(stmt).all()
        
        assert len(all_users) == 2
        display_names = [u.display_name for u in all_users]
        assert "User One" in display_names
        assert "User Two" in display_names


@pytest.mark.unit
class TestPrayerCRUD:
    """Test Prayer model CRUD operations"""
    
    def test_create_prayer(self, test_session):
        """Test creating a prayer in the database"""
        # First create a user
        user = UserFactory.create()
        test_session.add(user)
        test_session.commit()
        
        prayer = PrayerFactory.create(
            author_id=user.id,
            text="Please pray for healing",
            project_tag="health"
        )
        test_session.add(prayer)
        test_session.commit()
        
        # Verify prayer was created
        retrieved_prayer = test_session.get(Prayer, prayer.id)
        assert retrieved_prayer is not None
        assert retrieved_prayer.text == "Please pray for healing"
        assert retrieved_prayer.project_tag == "health"
        assert retrieved_prayer.author_id == user.id
    
    def test_read_prayers_by_author(self, test_session):
        """Test reading prayers by author"""
        user = UserFactory.create()
        test_session.add(user)
        test_session.commit()
        
        prayer1 = PrayerFactory.create(author_id=user.id, text="Prayer 1")
        prayer2 = PrayerFactory.create(author_id=user.id, text="Prayer 2")
        test_session.add_all([prayer1, prayer2])
        test_session.commit()
        
        # Read prayers by author
        stmt = select(Prayer).where(Prayer.author_id == user.id)
        author_prayers = test_session.exec(stmt).all()
        
        assert len(author_prayers) == 2
        prayer_texts = [p.text for p in author_prayers]
        assert "Prayer 1" in prayer_texts
        assert "Prayer 2" in prayer_texts
    
    def test_update_prayer_flag_status(self, test_session):
        """Test updating prayer flag status"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id, flagged=False)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        # Flag the prayer
        prayer.flagged = True
        test_session.add(prayer)
        test_session.commit()
        
        # Verify update
        updated_prayer = test_session.get(Prayer, prayer.id)
        assert updated_prayer.flagged is True
    
    def test_delete_prayer(self, test_session):
        """Test deleting a prayer"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        test_session.add_all([user, prayer])
        test_session.commit()
        
        prayer_id = prayer.id
        
        # Delete the prayer
        test_session.delete(prayer)
        test_session.commit()
        
        # Verify deletion
        deleted_prayer = test_session.get(Prayer, prayer_id)
        assert deleted_prayer is None
    
    def test_filter_unflagged_prayers(self, test_session):
        """Test filtering unflagged prayers"""
        user = UserFactory.create()
        prayer1 = PrayerFactory.create(author_id=user.id, flagged=False, text="Normal prayer")
        prayer2 = PrayerFactory.create(author_id=user.id, flagged=True, text="Flagged prayer")
        test_session.add_all([user, prayer1, prayer2])
        test_session.commit()
        
        # Get only unflagged prayers
        stmt = select(Prayer).where(Prayer.flagged == False)
        unflagged_prayers = test_session.exec(stmt).all()
        
        assert len(unflagged_prayers) == 1
        assert unflagged_prayers[0].text == "Normal prayer"


@pytest.mark.unit
class TestSessionCRUD:
    """Test Session model CRUD operations"""
    
    def test_create_session(self, test_session):
        """Test creating a session in the database"""
        user = UserFactory.create()
        session = SessionFactory.create(user_id=user.id)
        test_session.add_all([user, session])
        test_session.commit()
        
        # Verify session was created
        retrieved_session = test_session.get(SessionModel, session.id)
        assert retrieved_session is not None
        assert retrieved_session.user_id == user.id
        assert retrieved_session.is_fully_authenticated is True
    
    def test_read_sessions_by_user(self, test_session):
        """Test reading sessions by user"""
        user = UserFactory.create()
        session1 = SessionFactory.create(user_id=user.id)
        session2 = SessionFactory.create(user_id=user.id)
        test_session.add_all([user, session1, session2])
        test_session.commit()
        
        # Read sessions by user
        stmt = select(SessionModel).where(SessionModel.user_id == user.id)
        user_sessions = test_session.exec(stmt).all()
        
        assert len(user_sessions) == 2
        for session in user_sessions:
            assert session.user_id == user.id
    
    def test_update_session_authentication_status(self, test_session):
        """Test updating session authentication status"""
        user = UserFactory.create()
        session = SessionFactory.create(user_id=user.id, is_fully_authenticated=False)
        test_session.add_all([user, session])
        test_session.commit()
        
        # Update authentication status
        session.is_fully_authenticated = True
        test_session.add(session)
        test_session.commit()
        
        # Verify update
        updated_session = test_session.get(SessionModel, session.id)
        assert updated_session.is_fully_authenticated is True
    
    def test_filter_expired_sessions(self, test_session):
        """Test filtering expired sessions"""
        user = UserFactory.create()
        past_time = datetime.utcnow() - timedelta(days=1)
        future_time = datetime.utcnow() + timedelta(days=1)
        
        expired_session = SessionFactory.create(user_id=user.id, expires_at=past_time)
        valid_session = SessionFactory.create(user_id=user.id, expires_at=future_time)
        test_session.add_all([user, expired_session, valid_session])
        test_session.commit()
        
        # Get only valid sessions
        now = datetime.utcnow()
        stmt = select(SessionModel).where(SessionModel.expires_at > now)
        valid_sessions = test_session.exec(stmt).all()
        
        assert len(valid_sessions) == 1
        assert valid_sessions[0].id == valid_session.id


@pytest.mark.unit
class TestInviteTokenCRUD:
    """Test InviteToken model CRUD operations"""
    
    def test_create_invite_token(self, test_session):
        """Test creating an invite token"""
        token = InviteTokenFactory.create(created_by_user="admin")
        test_session.add(token)
        test_session.commit()
        
        # Verify token was created
        retrieved_token = test_session.get(InviteToken, token.token)
        assert retrieved_token is not None
        assert retrieved_token.created_by_user == "admin"
        assert retrieved_token.used is False
    
    def test_mark_token_as_used(self, test_session):
        """Test marking a token as used"""
        token = InviteTokenFactory.create(used=False)
        test_session.add(token)
        test_session.commit()
        
        # Mark as used
        token.used = True
        test_session.add(token)
        test_session.commit()
        
        # Verify update
        updated_token = test_session.get(InviteToken, token.token)
        assert updated_token.used is True
    
    def test_filter_unused_tokens(self, test_session):
        """Test filtering unused tokens"""
        used_token = InviteTokenFactory.create(used=True)
        unused_token = InviteTokenFactory.create(used=False)
        test_session.add_all([used_token, unused_token])
        test_session.commit()
        
        # Get only unused tokens
        stmt = select(InviteToken).where(InviteToken.used == False)
        unused_tokens = test_session.exec(stmt).all()
        
        assert len(unused_tokens) == 1
        assert unused_tokens[0].token == unused_token.token
    
    def test_filter_expired_tokens(self, test_session):
        """Test filtering expired tokens"""
        past_time = datetime.utcnow() - timedelta(hours=1)
        future_time = datetime.utcnow() + timedelta(hours=1)
        
        expired_token = InviteTokenFactory.create(expires_at=past_time)
        valid_token = InviteTokenFactory.create(expires_at=future_time)
        test_session.add_all([expired_token, valid_token])
        test_session.commit()
        
        # Get only valid tokens
        now = datetime.utcnow()
        stmt = select(InviteToken).where(InviteToken.expires_at > now)
        valid_tokens = test_session.exec(stmt).all()
        
        assert len(valid_tokens) == 1
        assert valid_tokens[0].token == valid_token.token


@pytest.mark.unit
class TestPrayerMarkCRUD:
    """Test PrayerMark model CRUD operations"""
    
    def test_create_prayer_mark(self, test_session):
        """Test creating a prayer mark"""
        user = UserFactory.create()
        prayer = PrayerFactory.create(author_id=user.id)
        mark = PrayerMarkFactory.create(user_id=user.id, prayer_id=prayer.id)
        test_session.add_all([user, prayer, mark])
        test_session.commit()
        
        # Verify mark was created
        retrieved_mark = test_session.get(PrayerMark, mark.id)
        assert retrieved_mark is not None
        assert retrieved_mark.user_id == user.id
        assert retrieved_mark.prayer_id == prayer.id
    
    def test_count_marks_per_prayer(self, test_session):
        """Test counting marks per prayer"""
        user1 = UserFactory.create(display_name="User 1")
        user2 = UserFactory.create(display_name="User 2")
        prayer = PrayerFactory.create(author_id=user1.id)
        
        mark1 = PrayerMarkFactory.create(user_id=user1.id, prayer_id=prayer.id)
        mark2 = PrayerMarkFactory.create(user_id=user2.id, prayer_id=prayer.id)
        mark3 = PrayerMarkFactory.create(user_id=user1.id, prayer_id=prayer.id)  # Same user can mark multiple times
        
        test_session.add_all([user1, user2, prayer, mark1, mark2, mark3])
        test_session.commit()
        
        # Count total marks for prayer
        from sqlmodel import func
        stmt = select(func.count(PrayerMark.id)).where(PrayerMark.prayer_id == prayer.id)
        total_marks = test_session.exec(stmt).first()
        
        assert total_marks == 3
        
        # Count distinct users who marked
        stmt = select(func.count(func.distinct(PrayerMark.user_id))).where(PrayerMark.prayer_id == prayer.id)
        distinct_users = test_session.exec(stmt).first()
        
        assert distinct_users == 2
    
    def test_get_marks_by_user(self, test_session):
        """Test getting marks by user"""
        user = UserFactory.create()
        prayer1 = PrayerFactory.create(author_id=user.id, text="Prayer 1")
        prayer2 = PrayerFactory.create(author_id=user.id, text="Prayer 2")
        
        mark1 = PrayerMarkFactory.create(user_id=user.id, prayer_id=prayer1.id)
        mark2 = PrayerMarkFactory.create(user_id=user.id, prayer_id=prayer2.id)
        
        test_session.add_all([user, prayer1, prayer2, mark1, mark2])
        test_session.commit()
        
        # Get all marks by user
        stmt = select(PrayerMark).where(PrayerMark.user_id == user.id)
        user_marks = test_session.exec(stmt).all()
        
        assert len(user_marks) == 2
        marked_prayer_ids = [mark.prayer_id for mark in user_marks]
        assert prayer1.id in marked_prayer_ids
        assert prayer2.id in marked_prayer_ids