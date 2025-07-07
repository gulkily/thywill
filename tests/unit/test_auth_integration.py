"""Integration tests for authentication workflows (unit level)"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from fastapi import HTTPException
from sqlmodel import Session, select

from models import User, Session as SessionModel, InviteToken, AuthenticationRequest, SecurityLog
from tests.factories import UserFactory, SessionFactory, InviteTokenFactory, AuthenticationRequestFactory
from app_helpers.services.auth_helpers import create_session, current_user, create_auth_request, check_rate_limit


@pytest.mark.unit
class TestUserRegistrationWorkflow:
    """Test user registration workflow components"""
    
    def test_invite_token_workflow_new_user(self, test_session):
        """Test complete invite token workflow for new user"""
        # Step 1: Create invite token
        token = InviteTokenFactory.create(
            token="valid_token",
            used=False,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        test_session.add(token)
        test_session.commit()
        
        # Step 2: Validate token (simulating claim_post logic)
        retrieved_token = test_session.get(InviteToken, "valid_token")
        is_valid = (
            retrieved_token is not None and
            not retrieved_token.used and
            retrieved_token.expires_at > datetime.utcnow()
        )
        assert is_valid is True
        
        # Step 3: Create new user
        new_user = UserFactory.create(display_name="New User")
        test_session.add(new_user)
        
        # Step 4: Mark token as used
        retrieved_token.usage_count = retrieved_token.max_uses or 1
        test_session.add(retrieved_token)
        test_session.commit()
        
        # Step 5: Create session for new user
        with patch('app_helpers.services.auth.session_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            session_id = create_session(new_user.display_name)
        
        # Verify complete workflow
        assert session_id is not None
        created_session = test_session.get(SessionModel, session_id)
        assert created_session.username == new_user.display_name
        assert created_session.is_fully_authenticated is True
        
        # Verify token is marked as used
        final_token = test_session.get(InviteToken, "valid_token")
        assert final_token.used is True
    
    def test_invite_token_workflow_expired_token(self, test_session):
        """Test workflow with expired token"""
        token = InviteTokenFactory.create(
            token="expired_token",
            used=False,
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        test_session.add(token)
        test_session.commit()
        
        # Validate token - should fail
        retrieved_token = test_session.get(InviteToken, "expired_token")
        is_valid = (
            retrieved_token is not None and
            not retrieved_token.used and
            retrieved_token.expires_at > datetime.utcnow()
        )
        assert is_valid is False
    
    def test_existing_user_multi_device_workflow(self, test_session):
        """Test multi-device auth workflow for existing user"""
        # Step 1: Create existing user
        existing_user = UserFactory.create(display_name="Existing User")
        test_session.add(existing_user)
        test_session.commit()
        
        # Step 2: Create authentication request
        with patch('app_helpers.services.auth.token_helpers.Session') as mock_session_class, \
             patch('app_helpers.services.auth.validation_helpers.log_auth_action') as mock_log:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            auth_req_id = create_auth_request(
                username=existing_user.display_name,
                device_info="New Device",
                ip_address="192.168.1.100"
            )
        
        # Verify auth request was created
        auth_req = test_session.get(AuthenticationRequest, auth_req_id)
        assert auth_req is not None
        assert auth_req.user_id == existing_user.display_name
        assert auth_req.status == "pending"
        
        # Step 3: Create half-authenticated session
        with patch('app_helpers.services.auth.session_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            session_id = create_session(
                username=existing_user.display_name,
                auth_request_id=auth_req_id,
                device_info="New Device",
                ip_address="192.168.1.100",
                is_fully_authenticated=False
            )
        
        # Verify half-authenticated session
        session = test_session.get(SessionModel, session_id)
        assert session.username == existing_user.display_name
        assert session.auth_request_id == auth_req_id
        assert session.is_fully_authenticated is False


@pytest.mark.unit
class TestSessionAuthenticationWorkflow:
    """Test session-based authentication workflow"""
    
    def test_full_authentication_workflow(self, test_session):
        """Test complete authentication workflow"""
        # Step 1: Create user and full session
        user = UserFactory.create()
        session = SessionFactory.create(
            username=user.display_name,
            is_fully_authenticated=True,
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        test_session.add_all([user, session])
        test_session.commit()
        
        # Step 2: Simulate request with session cookie
        mock_request = Mock()
        mock_request.cookies.get.return_value = session.id
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "Test Browser"
        
        # Step 3: Authenticate user
        with patch('app_helpers.services.auth.session_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            authenticated_user, authenticated_session = current_user(mock_request)
        
        # Verify authentication
        assert authenticated_user.display_name == user.display_name
        assert authenticated_session.id == session.id
        assert authenticated_session.is_fully_authenticated is True
    
    def test_half_authentication_workflow(self, test_session):
        """Test half-authenticated session workflow"""
        user = UserFactory.create()
        session = SessionFactory.create(
            username=user.display_name,
            is_fully_authenticated=False,
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        test_session.add_all([user, session])
        test_session.commit()
        
        # Step 1: User can still be identified
        mock_request = Mock()
        mock_request.cookies.get.return_value = session.id
        mock_request.client.host = "127.0.0.1"
        mock_request.headers.get.return_value = "Test Browser"
        
        with patch('app_helpers.services.auth.session_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            authenticated_user, authenticated_session = current_user(mock_request)
        
        assert authenticated_user.display_name == user.display_name
        assert authenticated_session.is_fully_authenticated is False
        
        # Step 2: But cannot access full-auth-required features
        from app import require_full_auth
        
        with patch('app_helpers.services.auth.session_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            with pytest.raises(HTTPException) as exc_info:
                require_full_auth(mock_request)
            
            assert exc_info.value.status_code == 403


@pytest.mark.unit
class TestRateLimitingWorkflow:
    """Test rate limiting workflows"""
    
    def test_rate_limiting_progression(self, test_session):
        """Test rate limiting progression from allowed to blocked"""
        user = UserFactory.create()
        test_session.add(user)
        test_session.commit()
        
        # Step 1: First request - should be allowed
        with patch('app_helpers.services.auth.validation_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            result1 = check_rate_limit(user.display_name, "127.0.0.1")
            assert result1 is True
        
        # Step 2: Create multiple recent requests (exceed limit)
        recent_time = datetime.utcnow() - timedelta(minutes=30)
        auth_requests = []
        for i in range(10):  # Reaches MAX_AUTH_REQUESTS_PER_HOUR (10)
            req = AuthenticationRequestFactory.create(
                username=user.display_name,
                created_at=recent_time + timedelta(minutes=i*5),
                ip_address="127.0.0.1"
            )
            auth_requests.append(req)
        
        test_session.add_all(auth_requests)
        test_session.commit()
        
        # Step 3: Next request should be blocked
        with patch('app_helpers.services.auth.validation_helpers.Session') as mock_session_class, \
             patch('app_helpers.services.auth.validation_helpers.log_security_event') as mock_log:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            result2 = check_rate_limit(user.display_name, "127.0.0.1")
            assert result2 is False
            
            # Verify security event was logged
            mock_log.assert_called_once()
            args = mock_log.call_args[1]
            assert args['event_type'] == 'rate_limit'
    
    def test_rate_limiting_time_window(self, test_session):
        """Test rate limiting respects time window"""
        user = UserFactory.create()
        test_session.add(user)
        test_session.commit()
        
        # Step 1: Create old requests (outside time window)
        old_time = datetime.utcnow() - timedelta(hours=2)
        old_requests = []
        for i in range(5):  # Many old requests
            req = AuthenticationRequestFactory.create(
                username=user.display_name,
                created_at=old_time,
                ip_address="127.0.0.1"
            )
            old_requests.append(req)
        
        test_session.add_all(old_requests)
        test_session.commit()
        
        # Step 2: New request should be allowed (old ones don't count)
        with patch('app_helpers.services.auth.validation_helpers.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            result = check_rate_limit(user.display_name, "127.0.0.1")
            assert result is True


@pytest.mark.unit
class TestSecurityWorkflow:
    """Test security validation workflows"""
    
    def test_session_security_ip_tracking(self, test_session):
        """Test session security with IP address tracking"""
        from app import validate_session_security
        
        # Step 1: Session with original IP
        session = SessionFactory.create(ip_address="192.168.1.100")
        test_session.add(session)
        test_session.commit()
        
        # Step 2: Request from same IP - no security concern
        mock_request1 = Mock()
        mock_request1.client.host = "192.168.1.100"
        mock_request1.headers.get.return_value = "Test Browser"
        
        with patch('app_helpers.services.auth.validation_helpers.log_security_event') as mock_log:
            result1 = validate_session_security(session, mock_request1)
            assert result1 is True
            mock_log.assert_not_called()
        
        # Step 3: Request from different IP - security event logged
        mock_request2 = Mock()
        mock_request2.client.host = "10.0.0.50"
        mock_request2.headers.get.return_value = "Test Browser"
        
        with patch('app_helpers.services.auth.validation_helpers.log_security_event') as mock_log:
            result2 = validate_session_security(session, mock_request2)
            assert result2 is True  # Still allowed, just logged
            
            mock_log.assert_called_once()
            args = mock_log.call_args[1]
            assert args['event_type'] == 'ip_change'
            assert args['user_id'] == session.username
    
    def test_admin_privilege_workflow(self, test_session):
        """Test admin privilege checking workflow"""
        from app import is_admin
        
        # Step 1: Create admin user
        admin_user = UserFactory.create(display_name="admin")
        test_session.add(admin_user)
        test_session.commit()
        
        # Step 2: Verify admin privileges
        assert is_admin(admin_user) is True
        
        # Step 3: Create regular user
        regular_user = UserFactory.create(display_name="Regular User")
        test_session.add(regular_user)
        test_session.commit()
        
        # Step 4: Verify no admin privileges
        assert is_admin(regular_user) is False
        
        # Step 5: User with admin name but different display_name
        fake_admin = UserFactory.create(
            display_name="fake_admin"  # Different name than admin
        )
        test_session.add(fake_admin)
        test_session.commit()
        
        assert is_admin(fake_admin) is False