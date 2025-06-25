# app_helpers/services/auth/session_helpers.py
"""
Session management functions.

Contains functionality for creating, validating, and managing user sessions.
Extracted from auth_helpers.py for better maintainability.
"""

import uuid
from datetime import datetime, timedelta
from fastapi import Request, HTTPException
from sqlmodel import Session

from models import (
    User, Session as SessionModel, engine
)

# Constants
SESSION_DAYS = 14


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
        
        # Handle deleted user - invalidate session
        if not user:
            db.delete(sess)
            db.commit()
            raise HTTPException(401, detail="user_deleted")
        
        # Check if user is deactivated - block access if so
        if user.has_role("deactivated", db):
            # Invalidate session for deactivated users
            db.delete(sess)
            db.commit()
            raise HTTPException(401, detail="account_deactivated")
        
        return user, sess


def require_full_auth(req: Request) -> User:
    """Require full authentication for protected routes"""
    user, session = current_user(req)
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    return user


def validate_session_security(session: SessionModel, request: Request) -> bool:
    """Validate session security - check for suspicious activity"""
    from .validation_helpers import log_security_event
    
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