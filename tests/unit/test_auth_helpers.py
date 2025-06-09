"""Unit tests for authentication helper functions"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from fastapi import HTTPException
from sqlmodel import Session

from models import User, Session as SessionModel, InviteToken, AuthenticationRequest, SecurityLog
from tests.factories import UserFactory, SessionFactory, InviteTokenFactory, AuthenticationRequestFactory
from app import (
    create_session, current_user, require_full_auth, is_admin,
    create_auth_request, check_rate_limit, validate_session_security,
    log_security_event
)


@pytest.mark.unit
class TestSessionHelpers:
    """Test session management helper functions"""
    
    def test_create_session_basic(self, test_session):
        """Test creating a basic session"""
        user = UserFactory.create()
        test_session.add(user)
        test_session.commit()
        
        with patch('app_helpers.services.auth_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            session_id = create_session(user.id)
            
            assert session_id is not None
            assert len(session_id) == 32  # UUID hex length
            
            # Verify session was created in database
            created_session = test_session.get(SessionModel, session_id)
            assert created_session is not None
            assert created_session.user_id == user.id
            assert created_session.is_fully_authenticated is True
    
    def test_create_session_with_auth_request(self, test_session):
        """Test creating session with multi-device auth fields"""
        user = UserFactory.create()
        test_session.add(user)
        test_session.commit()
        
        with patch('app_helpers.services.auth_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            session_id = create_session(
                user_id=user.id,
                auth_request_id="auth_req_123",
                device_info="Test Browser",
                ip_address="192.168.1.100",
                is_fully_authenticated=False
            )
            
            created_session = test_session.get(SessionModel, session_id)
            assert created_session.auth_request_id == "auth_req_123"
            assert created_session.device_info == "Test Browser"
            assert created_session.ip_address == "192.168.1.100"
            assert created_session.is_fully_authenticated is False
    
    def test_current_user_valid_session(self, test_session):
        """Test current_user with valid session"""
        user = UserFactory.create()
        session = SessionFactory.create(
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        test_session.add_all([user, session])
        test_session.commit()
        
        # Mock request with session cookie
        mock_request = Mock()
        mock_request.cookies.get.return_value = session.id
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "Test Browser"
        
        with patch('app_helpers.services.auth_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            returned_user, returned_session = current_user(mock_request)
            
            assert returned_user.id == user.id
            assert returned_session.id == session.id
    
    def test_current_user_no_session_cookie(self, test_session):
        """Test current_user with no session cookie raises 401"""
        mock_request = Mock()
        mock_request.cookies.get.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            current_user(mock_request)
        
        assert exc_info.value.status_code == 401
    
    def test_current_user_expired_session(self, test_session):
        """Test current_user with expired session raises 401"""
        user = UserFactory.create()
        session = SessionFactory.create(
            user_id=user.id,
            expires_at=datetime.utcnow() - timedelta(days=1)  # Expired
        )
        test_session.add_all([user, session])
        test_session.commit()
        
        mock_request = Mock()
        mock_request.cookies.get.return_value = session.id
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "Test Browser"
        
        with patch('app_helpers.services.auth_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            with pytest.raises(HTTPException) as exc_info:
                current_user(mock_request)
            
            assert exc_info.value.status_code == 401
    
    def test_current_user_invalid_session_id(self, test_session):
        """Test current_user with invalid session ID raises 401"""
        mock_request = Mock()
        mock_request.cookies.get.return_value = "invalid_session_id"
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "Test Browser"
        
        with patch('app_helpers.services.auth_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            with pytest.raises(HTTPException) as exc_info:
                current_user(mock_request)
            
            assert exc_info.value.status_code == 401
    
    def test_require_full_auth_with_full_session(self, test_session):
        """Test require_full_auth with fully authenticated session"""
        user = UserFactory.create()
        session = SessionFactory.create(
            user_id=user.id,
            is_fully_authenticated=True
        )
        test_session.add_all([user, session])
        test_session.commit()
        
        mock_request = Mock()
        mock_request.cookies.get.return_value = session.id
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "Test Browser"
        
        with patch('app_helpers.services.auth_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            returned_user = require_full_auth(mock_request)
            assert returned_user.id == user.id
    
    def test_require_full_auth_with_half_session(self, test_session):
        """Test require_full_auth with half-authenticated session raises 403"""
        user = UserFactory.create()
        session = SessionFactory.create(
            user_id=user.id,
            is_fully_authenticated=False
        )
        test_session.add_all([user, session])
        test_session.commit()
        
        mock_request = Mock()
        mock_request.cookies.get.return_value = session.id
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "Test Browser"
        
        with patch('app_helpers.services.auth_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            with pytest.raises(HTTPException) as exc_info:
                require_full_auth(mock_request)
            
            assert exc_info.value.status_code == 403
            assert "Full authentication required" in str(exc_info.value.detail)


@pytest.mark.unit
class TestAdminHelpers:
    """Test admin role checking functions"""
    
    def test_is_admin_with_admin_user(self):
        """Test is_admin returns True for admin user"""
        admin_user = UserFactory.create(id="admin")
        assert is_admin(admin_user) is True
    
    def test_is_admin_with_regular_user(self):
        """Test is_admin returns False for regular user"""
        regular_user = UserFactory.create(id="regular_user_123")
        assert is_admin(regular_user) is False
    
    def test_is_admin_with_user_named_admin(self):
        """Test is_admin only checks ID, not display name"""
        user_named_admin = UserFactory.create(
            id="not_admin", 
            display_name="admin"
        )
        assert is_admin(user_named_admin) is False


@pytest.mark.unit
class TestAuthRequestHelpers:
    """Test authentication request helper functions"""
    
    def test_create_auth_request_basic(self, test_session):
        """Test creating basic authentication request"""
        user = UserFactory.create()
        test_session.add(user)
        test_session.commit()
        
        with patch('app_helpers.services.auth_helpers.Session') as mock_session_class, \
             patch('app_helpers.services.auth_helpers.log_auth_action') as mock_log:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            request_id = create_auth_request(
                user_id=user.id,
                device_info="Test Browser",
                ip_address="127.0.0.1"
            )
            
            assert request_id is not None
            assert len(request_id) == 32
            
            # Verify request was created in database
            auth_req = test_session.get(AuthenticationRequest, request_id)
            assert auth_req is not None
            assert auth_req.user_id == user.id
            assert auth_req.device_info == "Test Browser"
            assert auth_req.ip_address == "127.0.0.1"
            assert auth_req.status == "pending"
            
            # Verify logging was called
            mock_log.assert_called_once()
    
    def test_check_rate_limit_within_limit(self, test_session):
        """Test rate limiting when within limits"""
        user = UserFactory.create()
        test_session.add(user)
        test_session.commit()
        
        with patch('app_helpers.services.auth_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            # No existing requests, should be allowed
            result = check_rate_limit(user.id, "127.0.0.1")
            assert result is True
    
    def test_check_rate_limit_exceeded_by_user(self, test_session):
        """Test rate limiting when user exceeds limit"""
        user = UserFactory.create()
        
        # Create multiple recent auth requests (exceeding limit)
        recent_time = datetime.utcnow() - timedelta(minutes=30)
        auth_requests = []
        for i in range(11):  # Exceeds MAX_AUTH_REQUESTS_PER_HOUR (10)
            req = AuthenticationRequestFactory.create(
                user_id=user.id,
                created_at=recent_time + timedelta(minutes=i),
                ip_address="127.0.0.1"
            )
            auth_requests.append(req)
        
        test_session.add_all([user] + auth_requests)
        test_session.commit()
        
        with patch('app_helpers.services.auth_helpers.Session') as mock_session_class, \
             patch('app_helpers.services.auth_helpers.log_security_event') as mock_log:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            result = check_rate_limit(user.id, "127.0.0.1")
            assert result is False
            
            # Verify security event was logged
            mock_log.assert_called_once()
    
    def test_check_rate_limit_old_requests_ignored(self, test_session):
        """Test that old requests don't count toward rate limit"""
        user = UserFactory.create()
        
        # Create old auth requests (more than 1 hour ago)
        old_time = datetime.utcnow() - timedelta(hours=2)
        old_requests = []
        for i in range(5):  # Many old requests
            req = AuthenticationRequestFactory.create(
                user_id=user.id,
                created_at=old_time,
                ip_address="127.0.0.1"
            )
            old_requests.append(req)
        
        test_session.add_all([user] + old_requests)
        test_session.commit()
        
        with patch('app_helpers.services.auth_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            # Should be allowed since old requests don't count
            result = check_rate_limit(user.id, "127.0.0.1")
            assert result is True


@pytest.mark.unit
class TestSecurityHelpers:
    """Test security validation and logging functions"""
    
    def test_validate_session_security_same_ip(self, test_session):
        """Test session security validation with same IP"""
        session = SessionFactory.create(ip_address="127.0.0.1")
        test_session.add(session)
        test_session.commit()
        
        mock_request = Mock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "Test Browser"
        
        with patch('app_helpers.services.auth_helpers.log_security_event') as mock_log:
            result = validate_session_security(session, mock_request)
            assert result is True
            
            # No security event should be logged for same IP
            mock_log.assert_not_called()
    
    def test_validate_session_security_different_ip(self, test_session):
        """Test session security validation with different IP"""
        session = SessionFactory.create(ip_address="192.168.1.100")
        test_session.add(session)
        test_session.commit()
        
        mock_request = Mock()
        mock_request.client.host = "10.0.0.50"  # Different IP
        mock_request.headers.get.return_value = "Test Browser"
        
        with patch('app_helpers.services.auth_helpers.log_security_event') as mock_log:
            result = validate_session_security(session, mock_request)
            assert result is True  # Still returns True, just logs
            
            # Security event should be logged for IP change
            mock_log.assert_called_once()
            args = mock_log.call_args[1]
            assert args['event_type'] == 'ip_change'
            assert args['user_id'] == session.user_id
    
    def test_validate_session_security_no_original_ip(self, test_session):
        """Test session security validation with no original IP stored"""
        session = SessionFactory.create(ip_address=None)
        test_session.add(session)
        test_session.commit()
        
        mock_request = Mock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "Test Browser"
        
        with patch('app_helpers.services.auth_helpers.log_security_event') as mock_log:
            result = validate_session_security(session, mock_request)
            assert result is True
            
            # No security event should be logged when no original IP
            mock_log.assert_not_called()
    
    def test_log_security_event(self, test_session):
        """Test security event logging"""
        with patch('app_helpers.services.auth_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            log_security_event(
                event_type="failed_login",
                user_id="test_user",
                ip_address="127.0.0.1",
                user_agent="Test Browser",
                details="Multiple failed attempts"
            )
            
            # Verify log entry was created
            from sqlmodel import select
            stmt = select(SecurityLog).where(SecurityLog.event_type == "failed_login")
            log_entry = test_session.exec(stmt).first()
            
            assert log_entry is not None
            assert log_entry.event_type == "failed_login"
            assert log_entry.user_id == "test_user"
            assert log_entry.ip_address == "127.0.0.1"
            assert log_entry.user_agent == "Test Browser"
            assert log_entry.details == "Multiple failed attempts"


@pytest.mark.unit
class TestInviteTokenValidation:
    """Test invite token creation and validation"""
    
    def test_invite_token_validation_valid(self, test_session):
        """Test validation of valid invite token"""
        token = InviteTokenFactory.create(
            used=False,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        test_session.add(token)
        test_session.commit()
        
        # Simulate validation logic
        retrieved_token = test_session.get(InviteToken, token.token)
        is_valid = (
            retrieved_token is not None and
            not retrieved_token.used and
            retrieved_token.expires_at > datetime.utcnow()
        )
        
        assert is_valid is True
    
    def test_invite_token_validation_used(self, test_session):
        """Test validation of used invite token"""
        token = InviteTokenFactory.create(
            used=True,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        test_session.add(token)
        test_session.commit()
        
        retrieved_token = test_session.get(InviteToken, token.token)
        is_valid = (
            retrieved_token is not None and
            not retrieved_token.used and
            retrieved_token.expires_at > datetime.utcnow()
        )
        
        assert is_valid is False
    
    def test_invite_token_validation_expired(self, test_session):
        """Test validation of expired invite token"""
        token = InviteTokenFactory.create(
            used=False,
            expires_at=datetime.utcnow() - timedelta(hours=1)  # Expired
        )
        test_session.add(token)
        test_session.commit()
        
        retrieved_token = test_session.get(InviteToken, token.token)
        is_valid = (
            retrieved_token is not None and
            not retrieved_token.used and
            retrieved_token.expires_at > datetime.utcnow()
        )
        
        assert is_valid is False
    
    def test_invite_token_validation_nonexistent(self, test_session):
        """Test validation of non-existent invite token"""
        retrieved_token = test_session.get(InviteToken, "nonexistent_token")
        is_valid = (
            retrieved_token is not None and
            not retrieved_token.used and
            retrieved_token.expires_at > datetime.utcnow()
        )
        
        assert is_valid is False