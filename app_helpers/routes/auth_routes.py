# app_helpers/routes/auth_routes.py - Authentication route handlers
"""
Authentication route handlers extracted from main app.py for better code organization.

This module contains all authentication-related route handlers including:
- Invite claim flow (GET/POST /claim/{token})
- Multi-device authentication request flow
- Authentication approval/rejection flows
- Authentication status and audit

All routes maintain exact same signatures and logic as original app.py implementation
for 100% backward compatibility.

Extracted Routes:
- GET /claim/{token} - claim_get() - Display claim form for invite token
- POST /claim/{token} - claim_post() - Process invite token claim
- POST /auth/request - create_authentication_request() - Create auth request for existing user
- GET /auth/status - auth_status() - Show authentication status for half-authenticated users
- GET /auth/pending - pending_requests() - Show pending auth requests for approval
- POST /auth/approve/{request_id} - approve_request() - Approve an authentication request
- POST /auth/reject/{request_id} - reject_request() - Reject an authentication request
- GET /auth/my-requests - my_auth_requests() - Show user's own auth requests

Usage:
This router is included in the main FastAPI app via:
    from app_helpers.routes.auth_routes import router as auth_router
    app.include_router(auth_router)
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func

from models import (
    engine, User, InviteToken, Session as SessionModel,
    AuthenticationRequest, AuthApproval, AuthAuditLog
)

# Import helper functions
from app_helpers.services.auth_helpers import (
    create_session, current_user, is_admin,
    create_auth_request, approve_auth_request, get_pending_requests_for_approval,
    log_auth_action, log_security_event, check_rate_limit,
    cleanup_expired_requests
)

# Configuration constants - these should match app.py values
SESSION_DAYS = 14
MULTI_DEVICE_AUTH_ENABLED = os.getenv("MULTI_DEVICE_AUTH_ENABLED", "true").lower() == "true"
REQUIRE_APPROVAL_FOR_EXISTING_USERS = os.getenv("REQUIRE_APPROVAL_FOR_EXISTING_USERS", "true").lower() == "true"
PEER_APPROVAL_COUNT = int(os.getenv("PEER_APPROVAL_COUNT", "2"))

# Initialize templates - this should point to the same template directory as main app
templates = Jinja2Templates(directory="templates")

# Create router instance
router = APIRouter()

# ───────── Invite-claim flow ─────────
@router.get("/claim/{token}", response_class=HTMLResponse)
def claim_get(token: str, request: Request):
    """
    Display the claim form for an invite token.
    
    Args:
        token: The invite token to claim
        request: FastAPI request object
        
    Returns:
        HTMLResponse: The claim.html template with token context
    """
    return templates.TemplateResponse("claim.html", {"request": request, "token": token})


@router.post("/claim/{token}")
def claim_post(token: str, display_name: str = Form(...), request: Request = None):
    """
    Process invite token claim - either create new user or initiate multi-device auth.
    
    Handles two scenarios:
    1. New user: Create account and log in directly
    2. Existing user: Create authentication request for multi-device auth (if enabled)
    
    Args:
        token: The invite token being claimed
        display_name: The username being claimed
        request: FastAPI request object for device/IP info
        
    Returns:
        RedirectResponse: To main feed (new users) or auth status (existing users)
        
    Raises:
        HTTPException: 400 if invite expired, 429 if auth request already pending
    """
    with Session(engine) as s:
        inv = s.get(InviteToken, token)
        if not inv or inv.used or inv.expires_at < datetime.utcnow():
            raise HTTPException(400, "Invite expired")

        # Check if username already exists
        existing_user = s.exec(
            select(User).where(User.display_name == display_name)
        ).first()
        
        if existing_user:
            # Username exists - check if multi-device auth is enabled and required
            if not MULTI_DEVICE_AUTH_ENABLED or not REQUIRE_APPROVAL_FOR_EXISTING_USERS:
                # Allow direct login without approval
                sid = create_session(existing_user.id)
                resp = RedirectResponse("/", 303)
                resp.set_cookie("sid", sid, httponly=True, max_age=60*60*24*SESSION_DAYS)
                return resp
            
            # Multi-device auth required - create authentication request
            device_info = request.headers.get("User-Agent", "Unknown") if request else "Unknown"
            ip_address = request.client.host if request else "Unknown"
            
            # Check for recent requests
            recent_request = s.exec(
                select(AuthenticationRequest)
                .where(AuthenticationRequest.user_id == existing_user.id)
                .where(AuthenticationRequest.ip_address == ip_address)
                .where(AuthenticationRequest.status == "pending")
                .where(AuthenticationRequest.created_at > datetime.utcnow() - timedelta(hours=1))
            ).first()
            
            if recent_request:
                raise HTTPException(429, "Authentication request already pending. Please wait.")
            
            # Create auth request
            request_id = create_auth_request(existing_user.id, device_info, ip_address)
            
            # Create half-authenticated session
            sid = create_session(
                user_id=existing_user.id,
                auth_request_id=request_id,
                device_info=device_info,
                ip_address=ip_address,
                is_fully_authenticated=False
            )
            
            # Don't mark invite as used for existing users
            resp = RedirectResponse("/auth/status", 303)
            resp.set_cookie("sid", sid, httponly=True, max_age=60*60*24*SESSION_DAYS)
            return resp
        
        else:
            # New user - create account normally
            uid = "admin" if s.exec(select(User)).first() is None else uuid.uuid4().hex
            user = User(
                id=uid, 
                display_name=display_name[:40],
                invited_by_user_id=inv.created_by_user if inv.created_by_user != "system" else None,
                invite_token_used=token
            )
            inv.used = True
            inv.used_by_user_id = uid
            s.add_all([user, inv]); s.commit()

            sid = create_session(uid)
            resp = RedirectResponse("/", 303)
            resp.set_cookie("sid", sid, httponly=True, max_age=60*60*24*SESSION_DAYS)
            return resp


# ───────── Authentication request routes ─────────
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
            raise HTTPException(429, "Authentication request already pending for this device.")
        
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


@router.get("/auth/status", response_class=HTMLResponse)
def auth_status(request: Request, user_session: tuple = Depends(current_user)):
    """
    Show authentication status for half-authenticated users.
    
    Displays pending authentication request status, approval progress,
    and automatically upgrades to full authentication if request is approved.
    
    Args:
        request: FastAPI request object
        user_session: Current user and session from dependency
        
    Returns:
        HTMLResponse: auth_pending.html template with status info, or
        RedirectResponse: To main feed if already fully authenticated
        
    Raises:
        HTTPException: 404 if authentication request not found
    """
    user, session = user_session
    
    if session.is_fully_authenticated:
        return RedirectResponse("/", 303)
    
    with Session(engine) as db:
        auth_req = db.get(AuthenticationRequest, session.auth_request_id)
        if not auth_req:
            raise HTTPException(404, "Authentication request not found")
        
        # Get approval count and approvers
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
        
        # Check if approved
        if auth_req.status == "approved":
            # Upgrade session to full authentication
            session.is_fully_authenticated = True
            db.add(session)
            db.commit()
            return RedirectResponse("/", 303)
        
        context = {
            "request": request,
            "user": user,
            "auth_request": auth_req,
            "approvals": approval_info,
            "approval_count": len(approval_info),
            "needs_approvals": PEER_APPROVAL_COUNT - len(approval_info) if len(approval_info) < PEER_APPROVAL_COUNT else 0,
            "peer_approval_count": PEER_APPROVAL_COUNT
        }
        
        return templates.TemplateResponse("auth_pending.html", context)


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
    
    Displays all authentication requests created by the current user,
    including their approval status and the ability to self-approve
    if they have a fully authenticated session.
    
    Args:
        request: FastAPI request object
        user_session: Current user and session from dependency
        
    Returns:
        HTMLResponse: my_auth_requests.html template with user's requests
    """
    user, session = user_session
    cleanup_expired_requests()
    
    with Session(engine) as db:
        # Get all authentication requests for this user
        my_requests_stmt = (
            select(AuthenticationRequest)
            .where(AuthenticationRequest.user_id == user.id)
            .order_by(AuthenticationRequest.created_at.desc())
        )
        
        my_requests = db.exec(my_requests_stmt).all()
        requests_with_info = []
        
        for auth_req in my_requests:
            # Get approvals for this request
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
            
            can_self_approve = (
                auth_req.status == "pending" and 
                session.is_fully_authenticated and
                not any(a['is_self'] for a in approval_info)
            )
            
            requests_with_info.append({
                'request': auth_req,
                'approvals': approval_info,
                'approval_count': len(approval_info),
                'can_self_approve': can_self_approve,
                'is_current_session': auth_req.id == session.auth_request_id
            })
    
    return templates.TemplateResponse(
        "my_auth_requests.html",
        {"request": request, "my_requests": requests_with_info, "me": user, "session": session, "peer_approval_count": PEER_APPROVAL_COUNT}
    )


# ───────── Direct login routes ─────────
@router.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    """
    Display the login form for existing users.
    
    Shows a simple username form that allows existing users to request
    access without needing an invite link. Redirects authenticated users.
    
    Args:
        request: FastAPI request object
        
    Returns:
        HTMLResponse: login.html template, or redirect if already authenticated
        HTTPException: 404 if login feature is disabled
    """
    # Check if login feature is enabled
    if not MULTI_DEVICE_AUTH_ENABLED:
        raise HTTPException(404, "Login feature is disabled")
    
    # Check if user is already authenticated
    try:
        # Try to get current user - if successful, redirect to main page
        sid = request.cookies.get("sid")
        if sid:
            with Session(engine) as db:
                session = db.exec(
                    select(SessionModel).where(SessionModel.id == sid)
                ).first()
                if session and session.expires_at > datetime.utcnow():
                    if session.is_fully_authenticated:
                        return RedirectResponse("/", 303)
                    else:
                        # Half-authenticated, send to status page
                        return RedirectResponse("/auth/status", 303)
    except:
        # Not authenticated, continue to show login form
        pass
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "MULTI_DEVICE_AUTH_ENABLED": MULTI_DEVICE_AUTH_ENABLED
    })


@router.post("/login")
def login_post(username: str = Form(...), request: Request = None):
    """
    Process login form submission for existing users.
    
    Validates the username exists, creates an authentication request,
    and redirects to the lobby system for approval. This leverages
    the existing multi-device authentication flow.
    
    Args:
        username: The username to log in as
        request: FastAPI request object for device/IP tracking
        
    Returns:
        RedirectResponse: To auth status page with half-authenticated session,
                         or back to login form with error
    """
    if not MULTI_DEVICE_AUTH_ENABLED:
        return templates.TemplateResponse(
            "login.html", 
            {
                "request": request, 
                "error": "Login is currently disabled. Please use an invite link.",
                "username": username.strip() if username else ""
            }
        )
    
    cleanup_expired_requests()  # Clean up old requests
    
    device_info = request.headers.get("User-Agent", "Unknown") if request else "Unknown"
    ip_address = request.client.host if request else "Unknown"
    
    with Session(engine) as db:
        # Check if user exists
        existing_user = db.exec(
            select(User).where(User.display_name == username.strip())
        ).first()
        
        if not existing_user:
            return templates.TemplateResponse(
                "login.html", 
                {
                    "request": request, 
                    "error": "Username not found. Please check your username or request an invite link to create a new account.",
                    "username": username.strip()
                }
            )
        
        # Security: Check rate limits
        if not check_rate_limit(existing_user.id, ip_address):
            return templates.TemplateResponse(
                "login.html", 
                {
                    "request": request, 
                    "error": "Too many login attempts. Please try again later.",
                    "username": username.strip()
                }
            )
        
        # Check for existing pending request from same IP/device in last hour
        recent_request = db.exec(
            select(AuthenticationRequest)
            .where(AuthenticationRequest.user_id == existing_user.id)
            .where(AuthenticationRequest.ip_address == ip_address)
            .where(AuthenticationRequest.status == "pending")
            .where(AuthenticationRequest.created_at > datetime.utcnow() - timedelta(hours=1))
        ).first()
        
        if recent_request:
            return templates.TemplateResponse(
                "login.html", 
                {
                    "request": request, 
                    "error": "You already have a pending login request from this device. Please wait for approval.",
                    "username": username.strip()
                }
            )
        
        # Create the authentication request (reusing existing helper)
        request_id = create_auth_request(existing_user.id, device_info, ip_address)
        
        # Create a half-authenticated session (reusing existing logic)
        sid = create_session(
            user_id=existing_user.id,
            auth_request_id=request_id,
            device_info=device_info,
            ip_address=ip_address,
            is_fully_authenticated=False
        )
        
        # Redirect to existing lobby page
        resp = RedirectResponse("/auth/status", 303)
        resp.set_cookie("sid", sid, httponly=True, max_age=60*60*24*SESSION_DAYS)
        return resp