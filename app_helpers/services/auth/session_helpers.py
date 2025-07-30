# app_helpers/services/auth/session_helpers.py
"""
Session management functions.

Contains functionality for creating, validating, and managing user sessions.
Extracted from auth_helpers.py for better maintainability.

Enhanced with real-time system state archival for zero-downtime upgrades.
"""

import uuid
import logging
from datetime import datetime, timedelta
from fastapi import Request, HTTPException
from sqlmodel import Session

from models import (
    User, Session as SessionModel, engine
)

logger = logging.getLogger(__name__)

# Constants
SESSION_DAYS = 14


def create_session(user_id: str, auth_request_id: str = None, device_info: str = None, ip_address: str = None, is_fully_authenticated: bool = True) -> str:
    """Create a new user session with real-time system archival"""
    sid = uuid.uuid4().hex
    with Session(engine) as db:
        session_data = SessionModel(
            id=sid,
            username=user_id,
            expires_at=datetime.utcnow() + timedelta(days=SESSION_DAYS),
            auth_request_id=auth_request_id,
            device_info=device_info,
            ip_address=ip_address,
            is_fully_authenticated=is_fully_authenticated
        )
        db.add(session_data)
        db.commit()
        
        # Archive session creation in real-time
        try:
            from ..archive_writers import auth_archive_writer
            auth_archive_writer.log_security_event({
                'event_type': 'session_created',
                'user_id': user_id,
                'ip_address': ip_address or 'unknown',
                'user_agent': device_info or 'unknown',
                'created_at': datetime.utcnow(),
                'details': f'session_id={sid}, fully_authenticated={is_fully_authenticated}'
            })
        except Exception as e:
            logger.warning(f"Failed to archive session creation: {e}")
        
        # Archive full session data for export/import continuity
        try:
            from ..system_archive_service import SystemArchiveService
            system_archive = SystemArchiveService()
            archive_data = {
                'id': sid,
                'username': user_id,
                'created_at': session_data.created_at.isoformat(),
                'expires_at': session_data.expires_at.isoformat(),
                'ip_address': ip_address,
                'device_info': device_info,
                'is_fully_authenticated': is_fully_authenticated,
                'auth_request_id': auth_request_id
            }
            system_archive.log_session_event('created', archive_data, user_id)
        except Exception as e:
            logger.warning(f"Failed to archive full session data: {e}")
    
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
        
        user = db.get(User, sess.username)
        
        # Handle deleted user - invalidate session
        if not user:
            try:
                from ..archive_writers import auth_archive_writer
                auth_archive_writer.log_security_event({
                    'event_type': 'session_deleted',
                    'user_id': sess.username,
                    'ip_address': req.client.host if req.client else 'unknown',
                    'user_agent': req.headers.get("User-Agent", "unknown"),
                    'created_at': datetime.utcnow(),
                    'details': f'session_id={sess.id}, reason=user_deleted'
                })
            except Exception as e:
                logger.warning(f"Failed to archive session deletion: {e}")
            db.delete(sess)
            db.commit()
            raise HTTPException(401, detail="user_deleted")
        
        # Check if user is deactivated - block access if so
        if user.has_role("deactivated", db):
            # Invalidate session for deactivated users
            try:
                from ..archive_writers import auth_archive_writer
                auth_archive_writer.log_security_event({
                    'event_type': 'session_deleted',
                    'user_id': sess.username,
                    'ip_address': req.client.host if req.client else 'unknown',
                    'user_agent': req.headers.get("User-Agent", "unknown"),
                    'created_at': datetime.utcnow(),
                    'details': f'session_id={sess.id}, reason=account_deactivated'
                })
            except Exception as e:
                logger.warning(f"Failed to archive session deletion: {e}")
            db.delete(sess)
            db.commit()
            raise HTTPException(401, detail="account_deactivated")
        
        return user, sess


def require_full_auth(req: Request) -> tuple[User, SessionModel]:
    """Require full authentication for protected routes"""
    user, session = current_user(req)
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    return user, session


def validate_session_security(session: SessionModel, request: Request) -> bool:
    """Validate session security - check for suspicious activity"""
    from .validation_helpers import log_security_event
    
    current_ip = request.client.host if request.client else "unknown"
    current_ua = request.headers.get("User-Agent", "unknown")
    
    # Check for IP address changes (basic session hijacking detection)
    if session.ip_address and session.ip_address != current_ip:
        log_security_event(
            event_type="ip_change",
            user_id=session.username,
            ip_address=current_ip,
            user_agent=current_ua,
            details=f"IP changed from {session.ip_address} to {current_ip}"
        )
        # For now, just log it - could invalidate session in production
    
    return True


def _archive_session_event(event_type: str, session: SessionModel, user_id: int, reason: str = None):
    """Archive session lifecycle events for system state preservation"""
    try:
        from ..system_archive_service import SystemArchiveService
        
        system_archive = SystemArchiveService()
        session_data = {
            'id': session.id,
            'user_id': session.username,
            'created_at': session.created_at.isoformat() if session.created_at else None,
            'expires_at': session.expires_at.isoformat() if session.expires_at else None,
            'ip_address': session.ip_address,
            'device_info': session.device_info,
            'is_fully_authenticated': session.is_fully_authenticated,
            'auth_request_id': session.auth_request_id
        }
        
        if reason:
            session_data['reason'] = reason
        
        system_archive.log_session_event(event_type, session_data, user_id)
        
    except Exception as e:
        # Don't let archival failures break session operations
        logger.error(f"Session archival failed: {e}")


def invalidate_session(session_id: str, reason: str = "manual_logout"):
    """Invalidate a session with archival logging"""
    with Session(engine) as db:
        session = db.get(SessionModel, session_id)
        if session:
            try:
                from ..archive_writers import auth_archive_writer
                auth_archive_writer.log_security_event({
                    'event_type': 'session_deleted',
                    'user_id': session.username,
                    'ip_address': session.ip_address or 'unknown',
                    'user_agent': session.device_info or 'unknown',
                    'created_at': datetime.utcnow(),
                    'details': f'session_id={session_id}, reason={reason}'
                })
            except Exception as e:
                logger.warning(f"Failed to archive session deletion: {e}")
            db.delete(session)
            db.commit()
            return True
    return False