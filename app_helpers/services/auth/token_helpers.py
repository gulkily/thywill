# app_helpers/services/auth/token_helpers.py
"""
Token and authentication request management functions.

Contains functionality for creating, approving, and managing authentication requests,
plus the notification system. Extracted from auth_helpers.py for better maintainability.
"""

import uuid
from datetime import datetime, timedelta
from sqlmodel import Session, select, func

from models import (
    User, Session as SessionModel, AuthenticationRequest, AuthApproval, 
    NotificationState, engine
)

# Constants
PEER_APPROVAL_COUNT = 2


def create_auth_request(user_id: str, device_info: str = None, ip_address: str = None) -> str:
    """Create a new authentication request for an existing user"""
    import random
    from .validation_helpers import log_auth_action
    
    request_id = uuid.uuid4().hex
    verification_code = f"{random.randint(100000, 999999):06d}"  # 6-digit code
    
    with Session(engine) as db:
        # Create the authentication request
        auth_request = AuthenticationRequest(
            id=request_id,
            user_id=user_id,
            device_info=device_info,
            ip_address=ip_address,
            verification_code=verification_code,
            expires_at=datetime.utcnow() + timedelta(days=7)
        )
        db.add(auth_request)
        
        # Create notifications for all potential approvers
        # 1. Self-notification (for other authenticated devices of same user)
        self_notification = NotificationState(
            id=uuid.uuid4().hex,
            user_id=user_id,
            auth_request_id=request_id,
            notification_type="auth_request"
        )
        db.add(self_notification)
        
        # 2. Notifications for all other users (for peer approval)
        other_users = db.exec(
            select(User.id)
            .where(User.id != user_id)
        ).all()
        
        for other_user_id in other_users:
            other_notification = NotificationState(
                id=uuid.uuid4().hex,
                user_id=other_user_id,
                auth_request_id=request_id,
                notification_type="auth_request"
            )
            db.add(other_notification)
        
        db.commit()
        
        # Log the creation
        log_auth_action(
            auth_request_id=request_id,
            action="created",
            actor_user_id=user_id,
            actor_type="user",
            details=f"Authentication request created from {device_info}",
            ip_address=ip_address,
            user_agent=device_info,
            db_session=db
        )
    return request_id


def approve_auth_request(request_id: str, approver_id: str) -> bool:
    """Approve an authentication request. Returns True if approved, False if already processed"""
    from .validation_helpers import is_admin, log_auth_action
    
    with Session(engine) as db:
        auth_req = db.get(AuthenticationRequest, request_id)
        if not auth_req or auth_req.status != "pending" or auth_req.expires_at < datetime.utcnow():
            return False
        
        approver = db.get(User, approver_id)
        if not approver:
            return False
        
        # Check if already approved by this user
        existing_approval = db.exec(
            select(AuthApproval)
            .where(AuthApproval.auth_request_id == request_id)
            .where(AuthApproval.approver_user_id == approver_id)
        ).first()
        
        if existing_approval:
            return False
        
        # Add approval
        db.add(AuthApproval(
            auth_request_id=request_id,
            approver_user_id=approver_id
        ))
        
        # Get current approval count AFTER adding this approval
        db.flush()  # Ensure the approval is written to get accurate count
        approval_count = db.exec(
            select(func.count(AuthApproval.id))
            .where(AuthApproval.auth_request_id == request_id)
        ).first() or 0
        
        # Check approval conditions
        should_approve = False
        
        # Admin approval - instant
        if is_admin(approver):
            should_approve = True
        
        # Same user approval - check if approver has a full session
        elif approver_id == auth_req.user_id:
            full_session = db.exec(
                select(SessionModel)
                .where(SessionModel.user_id == approver_id)
                .where(SessionModel.is_fully_authenticated == True)
                .where(SessionModel.expires_at > datetime.utcnow())
            ).first()
            if full_session:
                should_approve = True
        
        # Peer approval - check if we have enough approvals
        else:
            if approval_count >= PEER_APPROVAL_COUNT:
                should_approve = True
        
        if should_approve:
            auth_req.status = "approved"
            auth_req.approved_by_user_id = approver_id
            auth_req.approved_at = datetime.utcnow()
            
            # Log the final approval
            approval_type = "admin" if is_admin(approver) else ("self" if approver_id == auth_req.user_id else "peer")
            log_auth_action(
                auth_request_id=request_id,
                action="approved",
                actor_user_id=approver_id,
                actor_type=approval_type,
                details=f"Request approved by {approval_type} after {approval_count} approvals",
                db_session=db
            )
        else:
            # Log the individual approval vote
            approval_type = "admin" if is_admin(approver) else ("self" if approver_id == auth_req.user_id else "peer")
            log_auth_action(
                auth_request_id=request_id,
                action="approval_vote",
                actor_user_id=approver_id,
                actor_type=approval_type,
                details=f"Approval vote cast by {approval_type} ({approval_count}/{PEER_APPROVAL_COUNT} approvals)",
                db_session=db
            )
        
        db.commit()
        return True


def get_pending_requests_for_approval(user_id: str) -> list:
    """Get authentication requests that the user can approve"""
    with Session(engine) as db:
        stmt = (
            select(AuthenticationRequest, User.display_name)
            .join(User, AuthenticationRequest.user_id == User.id)
            .where(AuthenticationRequest.status == "pending")
            .where(AuthenticationRequest.expires_at > datetime.utcnow())
            .order_by(AuthenticationRequest.created_at.desc())
        )
        
        results = db.exec(stmt).all()
        requests = []
        
        for auth_req, requester_name in results:
            # Check if current user has already approved this request
            existing_approval = db.exec(
                select(AuthApproval)
                .where(AuthApproval.auth_request_id == auth_req.id)
                .where(AuthApproval.approver_user_id == user_id)
            ).first()
            
            if not existing_approval:
                # Get current approval count
                approval_count = db.exec(
                    select(func.count(AuthApproval.id))
                    .where(AuthApproval.auth_request_id == auth_req.id)
                ).first() or 0
                
                requests.append({
                    'request': auth_req,
                    'requester_name': requester_name,
                    'approval_count': approval_count,
                    'approvals_needed': PEER_APPROVAL_COUNT
                })
        
        return requests


def cleanup_expired_requests() -> None:
    """Mark expired authentication requests as expired"""
    from .validation_helpers import log_auth_action
    
    with Session(engine) as db:
        expired_requests = db.exec(
            select(AuthenticationRequest)
            .where(AuthenticationRequest.status == "pending")
            .where(AuthenticationRequest.expires_at < datetime.utcnow())
        ).all()
        
        for auth_req in expired_requests:
            auth_req.status = "expired"
            log_auth_action(
                auth_request_id=auth_req.id,
                action="expired",
                actor_type="system",
                details="Request expired after 7 days"
            )
        
        db.commit()


# ═══════════════════════════════════════════════════════════════
# NOTIFICATION SYSTEM FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def create_auth_notification(user_id: str, auth_request_id: str) -> str:
    """Create notification when auth request is created for user"""
    notification_id = uuid.uuid4().hex
    with Session(engine) as db:
        notification = NotificationState(
            id=notification_id,
            user_id=user_id,
            auth_request_id=auth_request_id,
            notification_type="auth_request"
        )
        db.add(notification)
        db.commit()
    return notification_id


def get_unread_auth_notifications(user_id: str) -> list:
    """Get unread authentication notifications for user with auth request details"""
    with Session(engine) as db:
        stmt = (
            select(NotificationState, AuthenticationRequest, User.display_name)
            .join(AuthenticationRequest, NotificationState.auth_request_id == AuthenticationRequest.id)
            .join(User, AuthenticationRequest.user_id == User.id)
            .where(NotificationState.user_id == user_id)
            .where(NotificationState.is_read == False)
            .where(AuthenticationRequest.status == "pending")
            .where(AuthenticationRequest.expires_at > datetime.utcnow())
            .order_by(NotificationState.created_at.desc())
        )
        
        results = db.exec(stmt).all()
        notifications = []
        
        for notification, auth_req, requester_name in results:
            notifications.append({
                'id': notification.id,
                'created_at': notification.created_at,
                'auth_request': auth_req,
                'requester_name': requester_name,
                'notification_type': notification.notification_type
            })
        
        return notifications


def mark_notification_read(notification_id: str, user_id: str) -> bool:
    """Mark notification as read"""
    with Session(engine) as db:
        notification = db.get(NotificationState, notification_id)
        if not notification or notification.user_id != user_id:
            return False
        
        notification.is_read = True
        notification.read_at = datetime.utcnow()
        db.commit()
        return True


def get_notification_count(user_id: str) -> int:
    """Get count of unread notifications for user"""
    with Session(engine) as db:
        count = db.exec(
            select(func.count(NotificationState.id))
            .where(NotificationState.user_id == user_id)
            .where(NotificationState.is_read == False)
            .join(AuthenticationRequest, NotificationState.auth_request_id == AuthenticationRequest.id)
            .where(AuthenticationRequest.status == "pending")
            .where(AuthenticationRequest.expires_at > datetime.utcnow())
        ).first() or 0
        return count


def cleanup_expired_notifications() -> int:
    """Remove notifications for expired/completed auth requests"""
    with Session(engine) as db:
        # Get expired or completed auth requests
        completed_requests = db.exec(
            select(AuthenticationRequest.id)
            .where(
                (AuthenticationRequest.expires_at < datetime.utcnow()) |
                (AuthenticationRequest.status.in_(["approved", "rejected", "expired"]))
            )
        ).all()
        
        if not completed_requests:
            return 0
        
        # Delete associated notifications
        deleted_notifications = db.exec(
            select(NotificationState)
            .where(NotificationState.auth_request_id.in_(completed_requests))
        ).all()
        
        for notification in deleted_notifications:
            db.delete(notification)
        
        db.commit()
        return len(deleted_notifications)