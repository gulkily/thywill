# app_helpers/services/auth/validation_helpers.py
"""
Validation and security functions.

Contains functionality for user validation, security logging, and rate limiting.
Extracted from auth_helpers.py for better maintainability.
"""

from datetime import datetime, timedelta
from sqlmodel import Session, select, func

from models import (
    User, AuthenticationRequest, AuthAuditLog, SecurityLog, engine
)

# Constants
MAX_AUTH_REQUESTS_PER_HOUR = 10


def is_admin(user: User) -> bool:
    """Check if user has admin privileges using role-based system"""
    from sqlmodel import Session
    from models import engine
    
    # For backward compatibility during migration, check both systems
    if user.id == "admin":
        return True
    
    # Check role-based system
    try:
        with Session(engine) as session:
            return user.has_role("admin", session)
    except Exception:
        # Fallback to old system if role tables don't exist yet
        return user.id == "admin"


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