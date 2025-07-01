# app_helpers/routes/auth/login_routes.py - Login and registration route handlers
"""
Login and registration route handlers for authentication.

This module contains:
- Invite claim flow (GET/POST /claim/{token})
- User login flow (GET/POST /login)
"""

import os
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from models import (
    engine, User, InviteToken, Session as SessionModel,
    AuthenticationRequest, Role, UserRole
)

# Import helper functions
from app_helpers.services.auth_helpers import (
    create_session, check_rate_limit, cleanup_expired_requests,
    create_auth_request
)
from app_helpers.utils.invite_tree_validation import (
    validate_new_user_invite_relationship, 
    validate_existing_user_invite_update,
    validate_user_operation
)
from app_helpers.utils.user_management import is_user_deactivated
from app_helpers.services.archive_first_service import create_user_with_text_archive
from app_helpers.utils.username_helpers import (
    normalize_username, 
    normalize_username_for_lookup, 
    validate_username,
    find_users_with_equivalent_usernames
)

# Template and config setup
templates = Jinja2Templates(directory="templates")
router = APIRouter()

# Configuration
SESSION_DAYS = int(os.getenv("SESSION_DAYS", 90))
MULTI_DEVICE_AUTH_ENABLED = os.getenv("MULTI_DEVICE_AUTH_ENABLED", "True").lower() == "true"


def grant_admin_role_for_system_token(user_id: str, token: str, session: Session) -> None:
    """
    Grant admin role to user if they claimed a system-generated admin token.
    
    Args:
        user_id: ID of the user to potentially grant admin role to
        token: The invite token that was claimed
        session: Database session
    """
    # Get the invite token details
    inv = session.get(InviteToken, token)
    if not inv or inv.created_by_user != "system":
        return  # Not a system-generated token
    
    # Check if user already has admin role
    admin_role_stmt = select(Role).where(Role.name == "admin")
    admin_role = session.exec(admin_role_stmt).first()
    
    if not admin_role:
        # Admin role doesn't exist, skip
        return
    
    # Check if user already has admin role
    existing_role_stmt = select(UserRole).where(
        UserRole.user_id == user_id,
        UserRole.role_id == admin_role.id
    )
    existing_role = session.exec(existing_role_stmt).first()
    
    if existing_role:
        return  # User already has admin role
    
    # Grant admin role
    user_role = UserRole(
        user_id=user_id,
        role_id=admin_role.id,
        granted_by=None,  # System granted
        granted_at=datetime.utcnow()
    )
    session.add(user_role)


@router.get("/claim/{token}", response_class=HTMLResponse)
def claim_get(token: str, request: Request):
    """
    Display the claim form for an invite token, with immediate validation.
    
    Args:
        token: The invite token to claim
        request: FastAPI request object
        
    Returns:
        HTMLResponse: The claim.html template with token context, or error if invalid
    """
    # Validate token immediately on GET request
    with Session(engine) as s:
        inv = s.get(InviteToken, token)
        
        # Check if token exists, is not used, and hasn't expired
        if not inv:
            return templates.TemplateResponse("claim.html", {
                "request": request, 
                "token": token,
                "error": "This invite link is not valid. Please check the link or request a new invite."
            })
        
        if inv.used:
            return templates.TemplateResponse("claim.html", {
                "request": request, 
                "token": token,
                "error": "This invite link has already been used. Each invite link can only be used once."
            })
        
        if inv.expires_at < datetime.utcnow():
            return templates.TemplateResponse("claim.html", {
                "request": request, 
                "token": token,
                "error": "This invite link has expired. Invite links are valid for 12 hours. Please request a new invite link."
            })
    
    # Token is valid, show the normal claim form
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
            return templates.TemplateResponse("claim.html", {
                "request": request, 
                "token": token,
                "error": "This invite link has expired or has already been used. Please request a new invite link."
            })

        # Validate and normalize the display name
        is_valid, normalized_display_name = validate_username(display_name)
        if not is_valid:
            return templates.TemplateResponse("claim.html", {
                "request": request, 
                "token": token,
                "error": "Please enter a valid username (2-50 characters, letters, numbers, spaces, and basic punctuation only)."
            })
        
        # Check for existing users with equivalent usernames (case-insensitive, normalized)
        existing_users = find_users_with_equivalent_usernames(s, normalized_display_name)
        existing_user = existing_users[0] if existing_users else None
        
        # Check if this is an admin token for special role handling
        is_admin_token = (inv.created_by_user == "system")
            
        if existing_user:
            # SPECIAL CASE: Existing user with valid invite should login immediately
            # This is the key change - invite possession grants immediate access for existing users
            # while preserving verification requirement for users without invites
            
            # Allow immediate login for existing users with valid invites
            # Mark invite as used and create full session
            inv.used = True
            inv.used_by_user_id = existing_user.display_name
            
            # Check if user is deactivated before allowing login
            if is_user_deactivated(existing_user.display_name, s):
                return templates.TemplateResponse("error.html", {
                    "request": request,
                    "error_title": "Account Deactivated",
                    "error_message": "This account has been deactivated and cannot be accessed. Please contact an administrator if you believe this is an error.",
                    "show_back_button": True,
                    "back_url": "/login"
                })
            
            # CRITICAL FIX: Update existing user's invite relationship if not already set
            # This ensures existing users get properly connected to the invite tree
            if validate_existing_user_invite_update(existing_user, token, s):
                existing_user.invited_by_username = inv.created_by_user if inv.created_by_user != "system" else None
                existing_user.invite_token_used = token
                s.add(existing_user)
            
            # Store user ID before any commits to avoid ObjectDeletedError
            user_id = existing_user.display_name
            
            # Grant admin role if this is a system-generated token
            grant_admin_role_for_system_token(user_id, token, s)
            
            s.add(inv)
            s.commit()
            sid = create_session(user_id)
            resp = RedirectResponse("/", 303)
            resp.set_cookie("sid", sid, httponly=True, max_age=60*60*24*SESSION_DAYS)
            return resp
        
        else:
            # New user - create account normally
            uid = "admin" if s.exec(select(User)).first() is None else uuid.uuid4().hex
            
            # Validate and ensure proper invite relationship
            user_data = {
                'id': uid,
                'display_name': normalized_display_name
            }
            user_data = validate_new_user_invite_relationship(user_data, token, s)
            
            # Get inviter's display name for archive
            inviter_display_name = ""
            if inv.created_by_user and inv.created_by_user != "system":
                inviter = s.get(User, inv.created_by_user)
                if inviter:
                    inviter_display_name = inviter.display_name
            
            # Create user with archive-first approach
            archive_user_data = {
                'display_name': user_data['display_name'],
                'invited_by_display_name': inviter_display_name,
                'religious_preference': user_data.get('religious_preference', 'unspecified'),
                'prayer_style': user_data.get('prayer_style'),
                'invited_by_username': user_data.get('invited_by_username'),
                'invite_token_used': user_data.get('invite_token_used', token)
            }
            
            # Use archive-first approach: text archive FIRST, then database
            user, _ = create_user_with_text_archive(archive_user_data, uid)
            
            inv.used = True
            inv.used_by_user_id = uid
            s.add(inv)
            
            # Grant admin role if this is a system-generated token
            grant_admin_role_for_system_token(uid, token, s)
            
            s.commit()

            sid = create_session(uid)
            resp = RedirectResponse("/", 303)
            resp.set_cookie("sid", sid, httponly=True, max_age=60*60*24*SESSION_DAYS)
            return resp


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
        # Normalize username for lookup
        normalized_username = normalize_username_for_lookup(username)
        if not normalized_username:
            return templates.TemplateResponse(
                "login.html", 
                {
                    "request": request, 
                    "error": "Please enter a valid username.",
                    "username": username.strip()
                }
            )
        
        # Check if user exists using normalized lookup
        existing_users = find_users_with_equivalent_usernames(db, normalized_username)
        existing_user = existing_users[0] if existing_users else None
        
        if not existing_user:
            return templates.TemplateResponse(
                "login.html", 
                {
                    "request": request, 
                    "error": "Username not found. Please check your username or request an invite link to create a new account.",
                    "username": username.strip()
                }
            )
        
        # Check if user is deactivated
        if is_user_deactivated(existing_user.display_name, db):
            return templates.TemplateResponse(
                "login.html", 
                {
                    "request": request, 
                    "error": "This account has been deactivated and cannot be accessed. Please contact an administrator if you believe this is an error.",
                    "username": username.strip()
                }
            )
        
        # Security: Check rate limits
        if not check_rate_limit(existing_user.display_name, ip_address):
            return templates.TemplateResponse(
                "login.html", 
                {
                    "request": request, 
                    "error": "Too many login attempts. Please try again later.",
                    "username": username.strip()
                }
            )
        
        # Check for existing pending request from same IP/device combination in last hour
        # Modified to allow separate requests per device by checking both IP and device_info
        recent_request = db.exec(
            select(AuthenticationRequest)
            .where(AuthenticationRequest.user_id == existing_user.display_name)
            .where(AuthenticationRequest.ip_address == ip_address)
            .where(AuthenticationRequest.device_info == device_info)
            .where(AuthenticationRequest.status == "pending")
            .where(AuthenticationRequest.created_at > datetime.utcnow() - timedelta(hours=1))
        ).first()
        
        if recent_request:
            # Redirect to existing auth status with the pending request
            sid = create_session(
                user_id=existing_user.display_name,
                auth_request_id=recent_request.id,
                device_info=device_info,
                ip_address=ip_address,
                is_fully_authenticated=False
            )
            resp = RedirectResponse("/auth/status", 303)
            resp.set_cookie("sid", sid, httponly=True, max_age=60*60*24*SESSION_DAYS)
            return resp
        
        # Create the authentication request (reusing existing helper)
        request_id = create_auth_request(existing_user.display_name, device_info, ip_address)
        
        # Create a half-authenticated session (reusing existing logic)
        sid = create_session(
            user_id=existing_user.display_name,
            auth_request_id=request_id,
            device_info=device_info,
            ip_address=ip_address,
            is_fully_authenticated=False
        )
        
        # Redirect to existing lobby page
        resp = RedirectResponse("/auth/status", 303)
        resp.set_cookie("sid", sid, httponly=True, max_age=60*60*24*SESSION_DAYS)
        return resp