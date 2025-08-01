"""
Admin Dashboard Routes

Contains routes for the main admin dashboard and audit logging.
"""

from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func
# Remove direct SQLAlchemy import - use SQLModel functionality

# Import models
from models import (
    engine, User, Prayer, AuthenticationRequest, AuthApproval, 
    AuthAuditLog, PrayerMark
)
from app_helpers.timezone_utils import get_user_timezone_from_request

# Import helper functions
from app_helpers.services.auth_helpers import (
    current_user, is_admin, cleanup_expired_requests, log_auth_action
)

# Initialize templates
# Use shared templates instance with filters registered
from app_helpers.shared_templates import templates

# Create router for this module
router = APIRouter()


@router.get("/admin", response_class=HTMLResponse)
def admin(request: Request, user_session: tuple = Depends(current_user)):
    """
    Admin Dashboard
    
    Displays the main admin dashboard with:
    - Flagged prayers that need review
    - Pending authentication requests with approval status
    - Admin controls for managing the community
    
    Requires admin privileges.
    """
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403)
    
    cleanup_expired_requests()  # Clean up old requests
    
    with Session(engine) as s:
        # Join Prayer and User tables to get author display names for flagged prayers
        stmt = (
            select(Prayer, User.display_name)
            .outerjoin(User, Prayer.author_username == User.display_name)
            .where(Prayer.flagged == True)
        )
        results = s.exec(stmt).all()
        
        flagged_prayers = []
        for prayer, author_name in results:
            flagged_prayers.append({
                'prayer': prayer,
                'author_name': author_name or 'Unknown'
            })
        
        # Get pending authentication requests with approval counts
        auth_requests_query = (
            select(
                AuthenticationRequest.id,
                AuthenticationRequest.user_id,
                AuthenticationRequest.created_at,
                AuthenticationRequest.device_info,
                User.display_name,
                func.count(AuthApproval.id).label("approval_count")
            )
            .join(User, AuthenticationRequest.user_id == User.display_name)
            .outerjoin(AuthApproval, AuthenticationRequest.id == AuthApproval.auth_request_id)
            .where(AuthenticationRequest.status == "pending")
            .group_by(
                AuthenticationRequest.id,
                AuthenticationRequest.user_id,
                AuthenticationRequest.created_at, 
                AuthenticationRequest.device_info,
                User.display_name
            )
        )
        
        auth_requests_results = s.exec(auth_requests_query).all()
        
        auth_requests = []
        for req_id, user_id, created_at, device_info, display_name, approval_count in auth_requests_results:
            auth_requests.append({
                'id': req_id,
                'user_id': user_id,
                'display_name': display_name,
                'created_at': created_at,
                'device_info': device_info,
                'approval_count': approval_count
            })
    
    user_timezone = get_user_timezone_from_request(request)
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "user": user,
        "flagged_prayers": flagged_prayers,
        "auth_requests": auth_requests,
        "user_timezone": user_timezone
    })


@router.get("/admin/auth-audit", response_class=HTMLResponse)
def auth_audit_log(request: Request, user_session: tuple = Depends(current_user)):
    """
    Authentication Audit Log
    
    Displays comprehensive audit trail of authentication events including:
    - All authentication request events
    - Approval/rejection actions
    - Admin actions
    - Security events
    
    Requires admin privileges.
    """
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403)
    
    with Session(engine) as s:
        # Simplified query without SQLAlchemy aliases - get audit logs and resolve users separately
        audit_query = (
            select(
                AuthAuditLog.created_at,
                AuthAuditLog.action,
                AuthAuditLog.actor_type,
                AuthAuditLog.details,
                User.display_name.label("actor_name"),
                AuthenticationRequest.user_id
            )
            .outerjoin(User, AuthAuditLog.actor_user_id == User.display_name)
            .outerjoin(AuthenticationRequest, AuthAuditLog.auth_request_id == AuthenticationRequest.id)
            .group_by(
                AuthAuditLog.created_at,
                AuthAuditLog.action,
                AuthAuditLog.actor_type,
                AuthAuditLog.details,
                User.display_name,
                AuthenticationRequest.user_id
            )
            .order_by(AuthAuditLog.created_at.desc())
            .limit(200)  # Limit to recent 200 events
        )
        
        audit_results = s.exec(audit_query).all()
        
        audit_events = []
        for created_at, action, actor_type, details, actor_name, requesting_user_id in audit_results:
            # Resolve requesting user name separately
            requesting_user_name = "Unknown"
            if requesting_user_id:
                requesting_user = s.get(User, requesting_user_id)
                if requesting_user:
                    requesting_user_name = requesting_user.display_name
            
            audit_events.append({
                'created_at': created_at,
                'action': action,
                'actor_type': actor_type,
                'actor_name': actor_name or "System",
                'requesting_user_name': requesting_user_name,
                'details': details
            })
    
    user_timezone = get_user_timezone_from_request(request)
    return templates.TemplateResponse("auth_audit.html", {
        "request": request,
        "user": user,
        "audit_events": audit_events,
        "user_timezone": user_timezone
    })