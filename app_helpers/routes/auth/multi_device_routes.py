# app_helpers/routes/auth/multi_device_routes.py - Multi-device authentication handlers
"""
Multi-device authentication route handlers.

This module contains:
- Authentication request creation and processing
- Request approval/rejection workflows
- Authentication status monitoring
"""

import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from models import (
    engine, User, AuthenticationRequest, AuthApproval, Session as SessionModel
)

# Import helper functions
from app_helpers.services.auth_helpers import (
    create_session, current_user, is_admin, cleanup_expired_requests,
    create_auth_request, approve_auth_request, get_pending_requests_for_approval,
    log_auth_action, check_rate_limit
)

# Template and config setup
templates = Jinja2Templates(directory="templates")
router = APIRouter()

# Configuration
SESSION_DAYS = int(os.getenv("SESSION_DAYS", 90))
MULTI_DEVICE_AUTH_ENABLED = os.getenv("MULTI_DEVICE_AUTH_ENABLED", "True").lower() == "true"
PEER_APPROVAL_COUNT = int(os.getenv("PEER_APPROVAL_COUNT", 2))
REQUIRE_VERIFICATION_CODE = os.getenv("REQUIRE_VERIFICATION_CODE", "False").lower() == "true"


@router.post("/auth/request")
def create_authentication_request(display_name: str = Form(...), request: Request = None):
    """
    Create an authentication request for an existing username.
    
    This is used when someone wants to log in as an existing user on a new device.
    Creates a pending authentication request that requires approval from other users.
    
    Args:
        display_name: The existing username to authenticate as
        request: FastAPI request object for device/IP tracking
        
    Returns:
        RedirectResponse: To auth status page with half-authenticated session
        
    Raises:
        HTTPException: 404 if multi-device auth disabled, 400 if user not found,
                      429 if rate limited or request already pending
    """
    if not MULTI_DEVICE_AUTH_ENABLED:
        raise HTTPException(404, "Multi-device authentication is disabled")
    
    cleanup_expired_requests()  # Clean up old requests
    
    device_info = request.headers.get("User-Agent", "Unknown") if request else "Unknown"
    ip_address = request.client.host if request else "Unknown"
    
    with Session(engine) as db:
        # Check if user exists
        existing_user = db.exec(
            select(User).where(User.display_name == display_name)
        ).first()
        
        if not existing_user:
            raise HTTPException(400, "Username not found. Please use an invite link to create a new account.")
        
        # Security: Check rate limits
        if not check_rate_limit(existing_user.id, ip_address):
            raise HTTPException(429, "Too many authentication requests. Please try again later.")
        
        # Check for existing pending request from same IP/device in last hour
        recent_request = db.exec(
            select(AuthenticationRequest)
            .where(AuthenticationRequest.user_id == existing_user.id)
            .where(AuthenticationRequest.ip_address == ip_address)
            .where(AuthenticationRequest.status == "pending")
            .where(AuthenticationRequest.created_at > datetime.utcnow() - timedelta(hours=1))
        ).first()
        
        if recent_request:
            # Redirect to existing auth status with the pending request
            sid = create_session(
                user_id=existing_user.id,
                auth_request_id=recent_request.id,
                device_info=device_info,
                ip_address=ip_address,
                is_fully_authenticated=False
            )
            resp = RedirectResponse("/auth/status", 303)
            resp.set_cookie("sid", sid, httponly=True, max_age=60*60*24*SESSION_DAYS)
            return resp
        
        # Create the authentication request
        request_id = create_auth_request(existing_user.id, device_info, ip_address)
        
        # Create a half-authenticated session
        sid = create_session(
            user_id=existing_user.id,
            auth_request_id=request_id,
            device_info=device_info,
            ip_address=ip_address,
            is_fully_authenticated=False
        )
        
        resp = RedirectResponse("/auth/status", 303)
        resp.set_cookie("sid", sid, httponly=True, max_age=60*60*24*SESSION_DAYS)
        return resp


@router.get("/auth/pending", response_class=HTMLResponse)
def pending_requests(request: Request, user_session: tuple = Depends(current_user)):
    """
    Show pending authentication requests for approval.
    
    Displays all pending authentication requests that the current user can approve.
    Only fully authenticated users can access this page.
    
    Args:
        request: FastAPI request object
        user_session: Current user and session from dependency
        
    Returns:
        HTMLResponse: auth_requests.html template with pending requests
        
    Raises:
        HTTPException: 403 if not fully authenticated
    """
    user, session = user_session
    cleanup_expired_requests()
    
    # Only fully authenticated users can approve
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    
    pending_requests = get_pending_requests_for_approval(user.id)
    
    return templates.TemplateResponse(
        "auth_requests.html",
        {
            "request": request, 
            "pending_requests": pending_requests, 
            "me": user, 
            "session": session,
            "peer_approval_count": PEER_APPROVAL_COUNT
        }
    )


@router.post("/auth/approve/{request_id}")
def approve_request(request_id: str, user_session: tuple = Depends(current_user)):
    """
    Approve an authentication request.
    
    Allows fully authenticated users to approve pending authentication requests
    from other users. Creates an approval record and may complete the auth process.
    
    Args:
        request_id: ID of the authentication request to approve
        user_session: Current user and session from dependency
        
    Returns:
        RedirectResponse: Back to pending requests page
        
    Raises:
        HTTPException: 403 if not fully authenticated, 400 if unable to approve
    """
    user, session = user_session
    
    # Only fully authenticated users can approve
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    
    success = approve_auth_request(request_id, user.id)
    if not success:
        raise HTTPException(400, "Unable to approve request")
    
    return RedirectResponse("/auth/pending", 303)


@router.post("/auth/reject/{request_id}")
def reject_request(request_id: str, user_session: tuple = Depends(current_user)):
    """
    Reject an authentication request.
    
    Allows admins to reject pending authentication requests.
    Currently restricted to admin users only for security.
    
    Args:
        request_id: ID of the authentication request to reject
        user_session: Current user and session from dependency
        
    Returns:
        RedirectResponse: Back to pending requests page
        
    Raises:
        HTTPException: 403 if not admin, 400 if request not found or already processed
    """
    user, session = user_session
    
    # Only fully authenticated users can reject, and only admins for now
    if not session.is_fully_authenticated or not is_admin(user):
        raise HTTPException(403, "Admin authentication required")
    
    with Session(engine) as db:
        auth_req = db.get(AuthenticationRequest, request_id)
        if not auth_req or auth_req.status != "pending":
            raise HTTPException(400, "Request not found or already processed")
        
        auth_req.status = "rejected"
        auth_req.approved_by_user_id = user.id
        auth_req.approved_at = datetime.utcnow()
        
        # Log the rejection
        log_auth_action(
            auth_request_id=request_id,
            action="rejected",
            actor_user_id=user.id,
            actor_type="admin",
            details="Request rejected by admin"
        )
        
        db.commit()
    
    return RedirectResponse("/auth/pending", 303)


@router.get("/auth/my-requests", response_class=HTMLResponse)
def my_auth_requests(request: Request, user_session: tuple = Depends(current_user)):
    """
    Show user's own authentication requests for self-approval.
    
    Displays the user's own authentication requests, allowing them to see
    pending requests and optionally self-approve if the feature is enabled.
    
    Args:
        request: FastAPI request object
        user_session: Current user and session from dependency
        
    Returns:
        HTMLResponse: my_auth_requests.html template with user's requests
        
    Raises:
        HTTPException: 403 if not fully authenticated
    """
    user, session = user_session
    cleanup_expired_requests()
    
    # Only fully authenticated users can view
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    
    with Session(engine) as db:
        # Get user's authentication requests
        user_requests = db.exec(
            select(AuthenticationRequest)
            .where(AuthenticationRequest.user_id == user.id)
            .order_by(AuthenticationRequest.created_at.desc())
        ).all()
        
        # Get approval info for each request
        requests_with_approvals = []
        for auth_req in user_requests:
            approvals = db.exec(
                select(AuthApproval, User.display_name)
                .join(User, AuthApproval.approver_user_id == User.id)
                .where(AuthApproval.auth_request_id == auth_req.id)
            ).all()
            
            approval_info = []
            for approval, approver_name in approvals:
                approval_info.append({
                    'approver_name': approver_name,
                    'approved_at': approval.created_at,
                    'is_admin': approval.approver_user_id == "admin",
                    'is_self': approval.approver_user_id == user.id
                })
            
            requests_with_approvals.append({
                'request': auth_req,
                'approvals': approval_info,
                'approval_count': len(approval_info)
            })
    
    return templates.TemplateResponse(
        "my_auth_requests.html",
        {
            "request": request,
            "user": user,
            "session": session,
            "requests": requests_with_approvals,
            "peer_approval_count": PEER_APPROVAL_COUNT
        }
    )