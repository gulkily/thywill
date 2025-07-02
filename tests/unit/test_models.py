"""Unit tests for SQLModel models"""
import pytest
import uuid
from datetime import datetime, timedelta
from sqlmodel import Session

from models import User, Prayer, Session as SessionModel, InviteToken, PrayerMark, AuthenticationRequest, AuthApproval, AuthAuditLog, SecurityLog
from tests.factories import UserFactory, PrayerFactory, SessionFactory, InviteTokenFactory, PrayerMarkFactory, AuthenticationRequestFactory, AuthApprovalFactory


@pytest.mark.unit
class TestUserModel:
    """Test User model validation and creation"""
    
    def test_user_creation_with_defaults(self, test_session):
        """Test creating user with default values"""
        user = UserFactory.create()
        test_session.add(user)
        test_session.commit()
        
        assert user.display_name is not None
        assert len(user.display_name) > 0
        assert user.display_name.startswith("TestUser")
        assert isinstance(user.created_at, datetime)
    
    def test_user_creation_with_custom_values(self, test_session):
        """Test creating user with custom values"""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        user = UserFactory.create(
            display_name="custom_user", 
            created_at=custom_time
        )
        test_session.add(user)
        test_session.commit()
        
        assert user.display_name == "custom_user"
        assert user.created_at == custom_time
    
    def test_admin_user_creation(self, test_session):
        """Test creating admin user"""
        admin = UserFactory.create_admin()
        test_session.add(admin)
        test_session.commit()
        
        assert admin.display_name == "admin"
    
    def test_user_display_name_length_validation(self, test_session):
        """Test display name length constraints"""
        # Test very long display name (should be truncated in app logic, not model)
        long_name = "x" * 100
        user = UserFactory.create(display_name=long_name)
        test_session.add(user)
        test_session.commit()
        
        # Model itself doesn't enforce length, app logic does
        assert user.display_name == long_name


@pytest.mark.unit
class TestPrayerModel:
    """Test Prayer model validation and creation"""
    
    def test_prayer_creation_with_defaults(self, test_session):
        """Test creating prayer with default values"""
        prayer = PrayerFactory.create()
        test_session.add(prayer)
        test_session.commit()
        
        assert prayer.id is not None
        assert len(prayer.id) == 32
        assert prayer.author_username == "testuser"
        assert prayer.text == "Please pray for my test"
        assert prayer.generated_prayer == "Divine Creator, we lift up our friend. Amen."
        assert prayer.project_tag is None
        assert isinstance(prayer.created_at, datetime)
        assert prayer.flagged is False
    
    def test_prayer_creation_with_custom_values(self, test_session):
        """Test creating prayer with custom values"""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        prayer = PrayerFactory.create(
            id="custom_prayer_id",
            author_username="custom_author",
            text="Custom prayer text",
            generated_prayer="Custom generated prayer",
            project_tag="test_project",
            created_at=custom_time,
            flagged=True
        )
        test_session.add(prayer)
        test_session.commit()
        
        assert prayer.id == "custom_prayer_id"
        assert prayer.author_username == "custom_author"
        assert prayer.text == "Custom prayer text"
        assert prayer.generated_prayer == "Custom generated prayer"
        assert prayer.project_tag == "test_project"
        assert prayer.created_at == custom_time
        assert prayer.flagged is True
    
    def test_prayer_without_generated_prayer(self, test_session):
        """Test prayer creation without generated prayer"""
        prayer = PrayerFactory.create(generated_prayer=None)
        test_session.add(prayer)
        test_session.commit()
        
        assert prayer.generated_prayer is None


@pytest.mark.unit
class TestSessionModel:
    """Test Session model validation and creation"""
    
    def test_session_creation_with_defaults(self, test_session):
        """Test creating session with default values"""
        session = SessionFactory.create()
        test_session.add(session)
        test_session.commit()
        
        assert session.id is not None
        assert len(session.id) == 32
        assert session.username == "testuser"
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.expires_at, datetime)
        assert session.expires_at > session.created_at
        assert session.auth_request_id is None
        assert session.device_info is None
        assert session.ip_address is None
        assert session.is_fully_authenticated is True
    
    def test_session_with_multi_device_auth_fields(self, test_session):
        """Test session with multi-device authentication fields"""
        session = SessionFactory.create(
            auth_request_id="auth_req_123",
            device_info="Mozilla/5.0 Test Browser",
            ip_address="192.168.1.100",
            is_fully_authenticated=False
        )
        test_session.add(session)
        test_session.commit()
        
        assert session.auth_request_id == "auth_req_123"
        assert session.device_info == "Mozilla/5.0 Test Browser"
        assert session.ip_address == "192.168.1.100"
        assert session.is_fully_authenticated is False
    
    def test_session_expiration_calculation(self, test_session):
        """Test session expiration date calculation"""
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        expected_expiry = start_time + timedelta(days=14)
        
        session = SessionFactory.create(
            created_at=start_time,
            expires_at=expected_expiry
        )
        test_session.add(session)
        test_session.commit()
        
        assert session.expires_at == expected_expiry
        assert (session.expires_at - session.created_at).days == 14


@pytest.mark.unit
class TestInviteTokenModel:
    """Test InviteToken model validation and creation"""
    
    def test_invite_token_creation_with_defaults(self, test_session):
        """Test creating invite token with default values"""
        token = InviteTokenFactory.create()
        test_session.add(token)
        test_session.commit()
        
        assert token.token is not None
        assert len(token.token) == 32
        assert token.created_by_user == "admin"
        assert token.used is False
        assert isinstance(token.expires_at, datetime)
        assert token.expires_at > datetime.utcnow()
    
    def test_invite_token_creation_with_custom_values(self, test_session):
        """Test creating invite token with custom values"""
        custom_expiry = datetime(2024, 12, 31, 23, 59, 59)
        token = InviteTokenFactory.create(
            token="custom_token_123",
            created_by_user="user123",
            used=True,
            expires_at=custom_expiry
        )
        test_session.add(token)
        test_session.commit()
        
        assert token.token == "custom_token_123"
        assert token.created_by_user == "user123"
        assert token.used is True
        assert token.expires_at == custom_expiry
    
    def test_invite_token_expiration_default(self, test_session):
        """Test invite token default expiration (12 hours)"""
        now = datetime.utcnow()
        token = InviteTokenFactory.create()
        test_session.add(token)
        test_session.commit()
        
        # Should expire approximately 12 hours from now
        time_diff = token.expires_at - now
        assert 11.5 <= time_diff.total_seconds() / 3600 <= 12.5  # Within 30 minutes of 12 hours


@pytest.mark.unit
class TestPrayerMarkModel:
    """Test PrayerMark model validation and creation"""
    
    def test_prayer_mark_creation_with_defaults(self, test_session):
        """Test creating prayer mark with default values"""
        mark = PrayerMarkFactory.create()
        test_session.add(mark)
        test_session.commit()
        
        assert mark.id is not None
        assert len(mark.id) == 32
        assert mark.username == "testuser"
        assert mark.prayer_id == "test_prayer_id"
        assert isinstance(mark.created_at, datetime)
    
    def test_prayer_mark_creation_with_custom_values(self, test_session):
        """Test creating prayer mark with custom values"""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        mark = PrayerMarkFactory.create(
            id="custom_mark_id",
            username="custom_user",
            prayer_id="custom_prayer",
            created_at=custom_time
        )
        test_session.add(mark)
        test_session.commit()
        
        assert mark.id == "custom_mark_id"
        assert mark.username == "custom_user"
        assert mark.prayer_id == "custom_prayer"
        assert mark.created_at == custom_time


@pytest.mark.unit
class TestAuthenticationRequestModel:
    """Test AuthenticationRequest model validation and creation"""
    
    def test_auth_request_creation_with_defaults(self, test_session):
        """Test creating authentication request with default values"""
        auth_req = AuthenticationRequestFactory.create()
        test_session.add(auth_req)
        test_session.commit()
        
        assert auth_req.id is not None
        assert len(auth_req.id) == 32
        assert auth_req.user_id == "testuser"
        assert auth_req.device_info == "Test Browser"
        assert auth_req.ip_address == "127.0.0.1"
        assert isinstance(auth_req.created_at, datetime)
        assert isinstance(auth_req.expires_at, datetime)
        assert auth_req.status == "pending"
        assert auth_req.approved_by_user_id is None
        assert auth_req.approved_at is None
    
    def test_auth_request_expiration_default(self, test_session):
        """Test authentication request default expiration (7 days)"""
        auth_req = AuthenticationRequestFactory.create()
        test_session.add(auth_req)
        test_session.commit()
        
        time_diff = auth_req.expires_at - auth_req.created_at
        assert time_diff.days == 7
    
    def test_auth_request_approval_workflow(self, test_session):
        """Test authentication request approval fields"""
        approved_time = datetime.utcnow()
        auth_req = AuthenticationRequestFactory.create(
            status="approved",
            approved_by_user_id="admin",
            approved_at=approved_time
        )
        test_session.add(auth_req)
        test_session.commit()
        
        assert auth_req.status == "approved"
        assert auth_req.approved_by_user_id == "admin"
        assert auth_req.approved_at == approved_time


@pytest.mark.unit
class TestAuthApprovalModel:
    """Test AuthApproval model validation and creation"""
    
    def test_auth_approval_creation_with_defaults(self, test_session):
        """Test creating auth approval with default values"""
        approval = AuthApprovalFactory.create()
        test_session.add(approval)
        test_session.commit()
        
        assert approval.id is not None
        assert len(approval.id) == 32
        assert approval.auth_request_id == "test_auth_request_id"
        assert approval.approver_user_id == "testuser"
        assert isinstance(approval.created_at, datetime)
    
    def test_auth_approval_creation_with_custom_values(self, test_session):
        """Test creating auth approval with custom values"""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        approval = AuthApprovalFactory.create(
            id="custom_approval_id",
            auth_request_id="custom_auth_req",
            approver_user_id="custom_approver",
            created_at=custom_time
        )
        test_session.add(approval)
        test_session.commit()
        
        assert approval.id == "custom_approval_id"
        assert approval.auth_request_id == "custom_auth_req"
        assert approval.approver_user_id == "custom_approver"
        assert approval.created_at == custom_time


@pytest.mark.unit
class TestAuditLogModels:
    """Test audit and security log models"""
    
    def test_auth_audit_log_creation(self, test_session):
        """Test creating auth audit log entry"""
        log_entry = AuthAuditLog(
            auth_request_id="test_auth_req",
            action="approved",
            actor_user_id="admin",
            actor_type="admin",
            details="Request approved by admin",
            ip_address="127.0.0.1",
            user_agent="Test Browser"
        )
        test_session.add(log_entry)
        test_session.commit()
        
        assert log_entry.id is not None
        assert log_entry.auth_request_id == "test_auth_req"
        assert log_entry.action == "approved"
        assert log_entry.actor_user_id == "admin"
        assert log_entry.actor_type == "admin"
        assert log_entry.details == "Request approved by admin"
        assert isinstance(log_entry.created_at, datetime)
    
    def test_security_log_creation(self, test_session):
        """Test creating security log entry"""
        log_entry = SecurityLog(
            event_type="failed_login",
            user_id="test_user",
            ip_address="192.168.1.100",
            user_agent="Test Browser",
            details="Multiple failed login attempts"
        )
        test_session.add(log_entry)
        test_session.commit()
        
        assert log_entry.id is not None
        assert log_entry.event_type == "failed_login"
        assert log_entry.user_id == "test_user"
        assert log_entry.ip_address == "192.168.1.100"
        assert log_entry.user_agent == "Test Browser"
        assert log_entry.details == "Multiple failed login attempts"
        assert isinstance(log_entry.created_at, datetime)