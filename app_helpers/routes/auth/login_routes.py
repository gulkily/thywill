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
    AuthenticationRequest
)

# Import helper functions
from app_helpers.services.auth_helpers import (
    create_session, check_rate_limit, cleanup_expired_requests,
    create_auth_request
)

# Template and config setup
templates = Jinja2Templates(directory="templates")
router = APIRouter()

# Configuration
SESSION_DAYS = int(os.getenv("SESSION_DAYS", 90))
MULTI_DEVICE_AUTH_ENABLED = os.getenv("MULTI_DEVICE_AUTH_ENABLED", "True").lower() == "true"


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
            return templates.TemplateResponse("claim.html", {
                "request": request, 
                "token": token,
                "error": "This invite link has expired or has already been used. Please request a new invite link."
            })

        # Check if username already exists
        existing_user = s.exec(
            select(User).where(User.display_name == display_name)
        ).first()
        
        if existing_user:
            # SPECIAL CASE: Existing user with valid invite should login immediately
            # This is the key change - invite possession grants immediate access for existing users
            # while preserving verification requirement for users without invites
            
            # Allow immediate login for existing users with valid invites
            # Mark invite as used and create full session
            inv.used = True
            inv.used_by_user_id = existing_user.id
            s.add(inv)
            s.commit()
            
            sid = create_session(existing_user.id)
            resp = RedirectResponse("/", 303)
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