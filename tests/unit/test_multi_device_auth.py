"""Unit tests for multi-device authentication workflows"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlmodel import Session, select, func

from models import User, AuthenticationRequest, AuthApproval, AuthAuditLog, Session as SessionModel
from tests.factories import UserFactory, AuthenticationRequestFactory, AuthApprovalFactory, SessionFactory
from app import (
    approve_auth_request, get_pending_requests_for_approval, 
    cleanup_expired_requests, log_auth_action
)


@pytest.mark.unit
class TestMultiDeviceAuthWorkflows:
    """Test complete multi-device authentication workflows"""
    
    def test_create_auth_request_workflow(self, test_session):
        """Test creating authentication request workflow"""
        user = UserFactory.create()
        test_session.add(user)
        test_session.commit()
        
        # Create auth request
        auth_req = AuthenticationRequestFactory.create(
            user_id=user.id,
            device_info="iPhone Safari",
            ip_address="192.168.1.100",
            status="pending"
        )
        test_session.add(auth_req)
        test_session.commit()
        
        # Verify request was created correctly
        assert auth_req.user_id == user.id
        assert auth_req.status == "pending"
        assert auth_req.device_info == "iPhone Safari"
        assert auth_req.ip_address == "192.168.1.100"
        assert auth_req.expires_at > datetime.utcnow()
        
        # Check expiration (7 days default)
        time_diff = auth_req.expires_at - auth_req.created_at
        assert time_diff.days == 7
    
    def test_auth_request_with_existing_pending_request(self, test_session):
        """Test rate limiting prevents duplicate pending requests"""
        user = UserFactory.create()
        
        # Create existing pending request from same IP
        existing_req = AuthenticationRequestFactory.create(
            user_id=user.id,
            ip_address="192.168.1.100",
            status="pending",
            created_at=datetime.utcnow() - timedelta(minutes=30)
        )
        
        test_session.add_all([user, existing_req])
        test_session.commit()
        
        # Check for existing pending request (simulating app logic)
        recent_request = test_session.exec(
            select(AuthenticationRequest)
            .where(AuthenticationRequest.user_id == user.id)
            .where(AuthenticationRequest.ip_address == "192.168.1.100")
            .where(AuthenticationRequest.status == "pending")
            .where(AuthenticationRequest.created_at > datetime.utcnow() - timedelta(hours=1))
        ).first()
        
        # Should find the existing request
        assert recent_request is not None
        assert recent_request.id == existing_req.id
    
    def test_auth_request_cleanup_expired(self, test_session):
        """Test cleanup of expired authentication requests"""
        user = UserFactory.create()
        
        # Create expired request
        expired_req = AuthenticationRequestFactory.create(
            user_id=user.id,
            status="pending",
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        
        # Create valid request
        valid_req = AuthenticationRequestFactory.create(
            user_id=user.id,
            status="pending",
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        
        test_session.add_all([user, expired_req, valid_req])
        test_session.commit()
        
        # Run cleanup
        with patch('app.Session') as mock_session_class, \
             patch('app.log_auth_action') as mock_log:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            cleanup_expired_requests()
        
        # Check that expired request was marked as expired
        updated_expired = test_session.get(AuthenticationRequest, expired_req.id)
        updated_valid = test_session.get(AuthenticationRequest, valid_req.id)
        
        assert updated_expired.status == "expired"
        assert updated_valid.status == "pending"
        
        # Verify audit log was called
        mock_log.assert_called()


@pytest.mark.unit
class TestAuthApprovalProcesses:
    """Test authentication approval processes"""
    
    def test_admin_approval_instant(self, test_session):
        """Test admin approval provides instant approval"""
        user = UserFactory.create()
        admin = UserFactory.create(id="admin")
        
        auth_req = AuthenticationRequestFactory.create(
            user_id=user.id,
            status="pending"
        )
        
        test_session.add_all([user, admin, auth_req])
        test_session.commit()
        
        # Admin approves request
        with patch('app.Session') as mock_session_class, \
             patch('app.log_auth_action') as mock_log:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            result = approve_auth_request(auth_req.id, admin.id)
        
        assert result is True
        
        # Check request was approved
        updated_req = test_session.get(AuthenticationRequest, auth_req.id)
        assert updated_req.status == "approved"
        assert updated_req.approved_by_user_id == admin.id
        assert updated_req.approved_at is not None
        
        # Verify audit logging
        mock_log.assert_called()
        call_args = mock_log.call_args[1]
        assert call_args['action'] == 'approved'
        assert call_args['actor_type'] == 'admin'
    
    def test_self_approval_with_full_session(self, test_session):
        """Test self approval when user has full authenticated session"""
        user = UserFactory.create()
        
        # Create full authenticated session for user
        full_session = SessionFactory.create(
            user_id=user.id,
            is_fully_authenticated=True,
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        
        auth_req = AuthenticationRequestFactory.create(
            user_id=user.id,
            status="pending"
        )
        
        test_session.add_all([user, full_session, auth_req])
        test_session.commit()
        
        # User approves their own request
        with patch('app.Session') as mock_session_class, \
             patch('app.log_auth_action') as mock_log:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            result = approve_auth_request(auth_req.id, user.id)
        
        assert result is True
        
        # Check request was approved
        updated_req = test_session.get(AuthenticationRequest, auth_req.id)
        assert updated_req.status == "approved"
        assert updated_req.approved_by_user_id == user.id
        
        # Verify audit logging shows self approval
        mock_log.assert_called()
        call_args = mock_log.call_args[1]
        assert call_args['action'] == 'approved'
        assert call_args['actor_type'] == 'self'
    
    def test_self_approval_without_full_session(self, test_session):
        """Test self approval fails without full authenticated session"""
        user = UserFactory.create()
        
        # Create half authenticated session
        half_session = SessionFactory.create(
            user_id=user.id,
            is_fully_authenticated=False,
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        
        auth_req = AuthenticationRequestFactory.create(
            user_id=user.id,
            status="pending"
        )
        
        test_session.add_all([user, half_session, auth_req])
        test_session.commit()
        
        # User tries to approve their own request
        with patch('app.Session') as mock_session_class, \
             patch('app.log_auth_action') as mock_log:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            result = approve_auth_request(auth_req.id, user.id)
        
        # Should not be approved (no full session found)
        assert result is True  # Function returns True but doesn't approve
        
        # Check request is still pending
        updated_req = test_session.get(AuthenticationRequest, auth_req.id)
        assert updated_req.status == "pending"  # Still pending
        
        # Should log approval vote, not final approval
        mock_log.assert_called()
        call_args = mock_log.call_args[1]
        assert call_args['action'] == 'approval_vote'
    
    def test_peer_approval_progression(self, test_session):
        """Test peer approval requires multiple approvals"""
        # Setup users
        requester = UserFactory.create(id="requester")
        peer1 = UserFactory.create(id="peer1")
        peer2 = UserFactory.create(id="peer2")
        
        auth_req = AuthenticationRequestFactory.create(
            user_id=requester.id,
            status="pending"
        )
        
        test_session.add_all([requester, peer1, peer2, auth_req])
        test_session.commit()
        
        # First peer approval (should not approve yet)
        with patch('app.Session') as mock_session_class, \
             patch('app.log_auth_action') as mock_log, \
             patch('app.PEER_APPROVAL_COUNT', 2):  # Require 2 peer approvals
            mock_session_class.return_value.__enter__.return_value = test_session
            
            result1 = approve_auth_request(auth_req.id, peer1.id)
        
        assert result1 is True
        
        # Check still pending after first approval
        updated_req = test_session.get(AuthenticationRequest, auth_req.id)
        assert updated_req.status == "pending"
        
        # Check approval was recorded
        approval1 = test_session.exec(
            select(AuthApproval)
            .where(AuthApproval.auth_request_id == auth_req.id)
            .where(AuthApproval.approver_user_id == peer1.id)
        ).first()
        assert approval1 is not None
        
        # Second peer approval (should approve now)
        with patch('app.Session') as mock_session_class, \
             patch('app.log_auth_action') as mock_log, \
             patch('app.PEER_APPROVAL_COUNT', 2):
            mock_session_class.return_value.__enter__.return_value = test_session
            
            result2 = approve_auth_request(auth_req.id, peer2.id)
        
        assert result2 is True
        
        # Check request is now approved
        final_req = test_session.get(AuthenticationRequest, auth_req.id)
        assert final_req.status == "approved"
        assert final_req.approved_by_user_id == peer2.id  # Last approver
    
    def test_duplicate_approval_prevented(self, test_session):
        """Test user cannot approve same request twice"""
        user = UserFactory.create()
        approver = UserFactory.create()
        
        auth_req = AuthenticationRequestFactory.create(
            user_id=user.id,
            status="pending"
        )
        
        # Create existing approval
        existing_approval = AuthApprovalFactory.create(
            auth_request_id=auth_req.id,
            approver_user_id=approver.id
        )
        
        test_session.add_all([user, approver, auth_req, existing_approval])
        test_session.commit()
        
        # Try to approve again
        with patch('app.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            result = approve_auth_request(auth_req.id, approver.id)
        
        # Should return False (already approved)
        assert result is False
    
    def test_get_pending_requests_for_approval(self, test_session):
        """Test getting pending requests that user can approve"""
        user1 = UserFactory.create(id="user1")
        user2 = UserFactory.create(id="user2")
        approver = UserFactory.create(id="approver")
        
        # Request user1 can approve
        req1 = AuthenticationRequestFactory.create(
            user_id=user1.id,
            status="pending",
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        
        # Request user2 can approve  
        req2 = AuthenticationRequestFactory.create(
            user_id=user2.id,
            status="pending",
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        
        # Request already approved by approver
        req3 = AuthenticationRequestFactory.create(
            user_id=user1.id,
            status="pending",
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        existing_approval = AuthApprovalFactory.create(
            auth_request_id=req3.id,
            approver_user_id=approver.id
        )
        
        # Expired request
        req4 = AuthenticationRequestFactory.create(
            user_id=user2.id,
            status="pending",
            expires_at=datetime.utcnow() - timedelta(hours=1)
        )
        
        test_session.add_all([
            user1, user2, approver, req1, req2, req3, req4, existing_approval
        ])
        test_session.commit()
        
        # Get requests approver can approve
        with patch('app.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            pending_requests = get_pending_requests_for_approval(approver.id)
        
        # Should return req1 and req2 (not req3 - already approved, not req4 - expired)
        assert len(pending_requests) == 2
        
        request_ids = [req['request'].id for req in pending_requests]
        assert req1.id in request_ids
        assert req2.id in request_ids
        assert req3.id not in request_ids  # Already approved
        assert req4.id not in request_ids  # Expired


@pytest.mark.unit
class TestAuditLogging:
    """Test authentication audit logging and security monitoring"""
    
    def test_log_auth_action_with_session(self, test_session):
        """Test logging auth action with existing session"""
        auth_req_id = "test_auth_req"
        
        # Call the actual function we're testing (without mocking)
        from app import log_auth_action
        
        # Test with existing session
        log_auth_action(
            auth_request_id=auth_req_id,
            action="approved",
            actor_user_id="admin",
            actor_type="admin",
            details="Request approved by admin",
            ip_address="127.0.0.1",
            user_agent="Test Browser",
            db_session=test_session
        )
        
        test_session.commit()  # Ensure changes are committed
        
        # Verify log entry was added to session
        from sqlmodel import select
        log_entry = test_session.exec(
            select(AuthAuditLog)
            .where(AuthAuditLog.auth_request_id == auth_req_id)
        ).first()
        
        assert log_entry is not None
        assert log_entry.action == "approved"
        assert log_entry.actor_user_id == "admin"
        assert log_entry.actor_type == "admin"
        assert log_entry.details == "Request approved by admin"
        assert log_entry.ip_address == "127.0.0.1"
        assert log_entry.user_agent == "Test Browser"
    
    def test_log_auth_action_without_session(self, test_session):
        """Test logging auth action without existing session"""
        with patch('app.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            from app import log_auth_action
            
            log_auth_action(
                auth_request_id="test_req_2",
                action="created",
                actor_user_id="user123",
                actor_type="user",
                details="Authentication request created"
            )
        
        # Verify log entry was created
        from sqlmodel import select
        log_entry = test_session.exec(
            select(AuthAuditLog)
            .where(AuthAuditLog.auth_request_id == "test_req_2")
        ).first()
        
        assert log_entry is not None
        assert log_entry.action == "created"
        assert log_entry.actor_user_id == "user123"
        assert log_entry.actor_type == "user"
    
    def test_audit_log_progression_workflow(self, test_session):
        """Test audit logging throughout approval workflow"""
        user = UserFactory.create()
        admin = UserFactory.create(id="admin")
        
        auth_req = AuthenticationRequestFactory.create(
            user_id=user.id,
            status="pending"
        )
        
        test_session.add_all([user, admin, auth_req])
        test_session.commit()
        
        # Log creation
        from app import log_auth_action
        log_auth_action(
            auth_request_id=auth_req.id,
            action="created",
            actor_user_id=user.id,
            actor_type="user",
            details="Authentication request created",
            db_session=test_session
        )
        
        # Log approval
        log_auth_action(
            auth_request_id=auth_req.id,
            action="approved",
            actor_user_id=admin.id,
            actor_type="admin",
            details="Request approved by admin",
            db_session=test_session
        )
        
        test_session.commit()
        
        # Verify both log entries exist
        from sqlmodel import select
        log_entries = test_session.exec(
            select(AuthAuditLog)
            .where(AuthAuditLog.auth_request_id == auth_req.id)
            .order_by(AuthAuditLog.created_at)
        ).all()
        
        assert len(log_entries) == 2
        
        # Check creation log
        creation_log = log_entries[0]
        assert creation_log.action == "created"
        assert creation_log.actor_user_id == user.id
        assert creation_log.actor_type == "user"
        
        # Check approval log
        approval_log = log_entries[1]
        assert approval_log.action == "approved"
        assert approval_log.actor_user_id == admin.id
        assert approval_log.actor_type == "admin"
    
    def test_security_event_logging(self, test_session):
        """Test security event logging functionality"""
        from app import log_security_event
        
        with patch('app.Session') as mock_session_class:
            mock_session_class.return_value.__enter__.return_value = test_session
            
            log_security_event(
                event_type="failed_login",
                user_id="test_user",
                ip_address="192.168.1.100",
                user_agent="Chrome Browser",
                details="Multiple failed login attempts detected"
            )
        
        # Verify security log entry
        from sqlmodel import select
        from models import SecurityLog
        
        security_entry = test_session.exec(
            select(SecurityLog)
            .where(SecurityLog.event_type == "failed_login")
        ).first()
        
        assert security_entry is not None
        assert security_entry.user_id == "test_user"
        assert security_entry.ip_address == "192.168.1.100"
        assert security_entry.user_agent == "Chrome Browser"
        assert security_entry.details == "Multiple failed login attempts detected"