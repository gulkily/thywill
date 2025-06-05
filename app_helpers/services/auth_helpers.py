"""
Authentication helper functions extracted from app.py
This module contains authentication, authorization, and security-related functions.
"""

import uuid
from datetime import datetime, timedelta
from fastapi import Request, HTTPException
from sqlmodel import Session, select, func
from models import (
    User, Session as SessionModel, AuthenticationRequest, AuthApproval, 
    AuthAuditLog, SecurityLog, engine
)

# Constants (these should match app.py)
SESSION_DAYS = 14
PEER_APPROVAL_COUNT = 2
MAX_AUTH_REQUESTS_PER_HOUR = 3


def create_session(user_id: str, auth_request_id: str = None, device_info: str = None, ip_address: str = None, is_fully_authenticated: bool = True) -> str:
    """Create a new user session"""
    sid = uuid.uuid4().hex
    with Session(engine) as db:
        db.add(SessionModel(
            id=sid,
            user_id=user_id,
            expires_at=datetime.utcnow() + timedelta(days=SESSION_DAYS),
            auth_request_id=auth_request_id,
            device_info=device_info,
            ip_address=ip_address,
            is_fully_authenticated=is_fully_authenticated
        ))
        db.commit()
    return sid


def current_user(req: Request) -> tuple[User, SessionModel]:
    """Get current authenticated user and session from request"""
    sid = req.cookies.get("sid")
    if not sid:
        raise HTTPException(401, detail="no_session")
    with Session(engine) as db:
        sess = db.get(SessionModel, sid)
        if not sess:
            raise HTTPException(401, detail="invalid_session")
        if sess.expires_at < datetime.utcnow():
            raise HTTPException(401, detail="expired_session")
        
        # Security: Validate session
        validate_session_security(sess, req)
        
        user = db.get(User, sess.user_id)
        return user, sess


def require_full_auth(req: Request) -> User:
    """Require full authentication for protected routes"""
    user, session = current_user(req)
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    return user


def is_admin(user: User) -> bool:
    """Check if user has admin privileges"""
    return user.id == "admin"   # first user gets id 'admin' (see startup)


def create_auth_request(user_id: str, device_info: str = None, ip_address: str = None) -> str:
    """Create a new authentication request for an existing user"""
    import random
    request_id = uuid.uuid4().hex
    verification_code = f"{random.randint(100000, 999999):06d}"  # 6-digit code
    
    with Session(engine) as db:
        db.add(AuthenticationRequest(
            id=request_id,
            user_id=user_id,
            device_info=device_info,
            ip_address=ip_address,
            verification_code=verification_code,
            expires_at=datetime.utcnow() + timedelta(days=7)
        ))
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
        # Get all pending requests
        stmt = (
            select(AuthenticationRequest, User.display_name)
            .join(User, AuthenticationRequest.user_id == User.id)
            .where(AuthenticationRequest.status == "pending")
            .where(AuthenticationRequest.expires_at > datetime.utcnow())
            .order_by(AuthenticationRequest.created_at.desc())
        )
        
        results = db.exec(stmt).all()
        requests_with_info = []
        
        for auth_req, requester_name in results:
            # Check if user has already approved this request
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
                
                requests_with_info.append({
                    'request': auth_req,
                    'requester_name': requester_name,
                    'approval_count': approval_count,
                    'can_approve': True
                })
        
        return requests_with_info


def log_auth_action(auth_request_id: str, action: str, actor_user_id: str = None, 
                   actor_type: str = None, details: str = None, ip_address: str = None, 
                   user_agent: str = None, db_session: Session = None) -> None:
    """Log authentication-related actions for audit purposes"""
    log_entry = AuthAuditLog(
        auth_request_id=auth_request_id,
        action=action,
        actor_user_id=actor_user_id,
        actor_type=actor_type,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent
    )
    
    if db_session:
        # Use existing session
        db_session.add(log_entry)
    else:
        # Create new session
        with Session(engine) as db:
            db.add(log_entry)
            db.commit()


def log_security_event(event_type: str, user_id: str = None, ip_address: str = None, 
                      user_agent: str = None, details: str = None) -> None:
    """Log security-related events"""
    with Session(engine) as db:
        log_entry = SecurityLog(
            event_type=event_type,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=details
        )
        db.add(log_entry)
        db.commit()


def check_rate_limit(user_id: str, ip_address: str) -> bool:
    """Check if user/IP is rate limited for auth requests"""
    with Session(engine) as db:
        # Check requests in last hour
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        # Count auth requests from this user or IP in last hour
        user_requests = db.exec(
            select(func.count(AuthenticationRequest.id))
            .where(AuthenticationRequest.user_id == user_id)
            .where(AuthenticationRequest.created_at > hour_ago)
        ).first() or 0
        
        ip_requests = db.exec(
            select(func.count(AuthenticationRequest.id))
            .where(AuthenticationRequest.ip_address == ip_address)
            .where(AuthenticationRequest.created_at > hour_ago)
        ).first() or 0
        
        if user_requests >= MAX_AUTH_REQUESTS_PER_HOUR or ip_requests >= MAX_AUTH_REQUESTS_PER_HOUR:
            log_security_event(
                event_type="rate_limit",
                user_id=user_id,
                ip_address=ip_address,
                details=f"Rate limit exceeded: {user_requests} user requests, {ip_requests} IP requests in last hour"
            )
            return False
        
        return True


def validate_session_security(session: SessionModel, request: Request) -> bool:
    """Validate session security - check for suspicious activity"""
    current_ip = request.client.host if request.client else "unknown"
    current_ua = request.headers.get("User-Agent", "unknown")
    
    # Check for IP address changes (basic session hijacking detection)
    if session.ip_address and session.ip_address != current_ip:
        log_security_event(
            event_type="ip_change",
            user_id=session.user_id,
            ip_address=current_ip,
            user_agent=current_ua,
            details=f"IP changed from {session.ip_address} to {current_ip}"
        )
        # For now, just log it - could invalidate session in production
    
    return True


def cleanup_expired_requests() -> None:
    """Mark expired authentication requests as expired"""
    with Session(engine) as db:
        expired_requests = db.exec(
            select(AuthenticationRequest)
            .where(AuthenticationRequest.status == "pending")
            .where(AuthenticationRequest.expires_at < datetime.utcnow())
        ).all()
        
        for req in expired_requests:
            req.status = "expired"
            # Log the expiration
            log_auth_action(
                auth_request_id=req.id,
                action="expired",
                actor_type="system",
                details="Request expired after 7 days"
            )
        
        db.commit()