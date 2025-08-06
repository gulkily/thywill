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
    engine, User, InviteToken, InviteTokenUsage, Session as SessionModel,
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
from app_helpers.services.token_service import TOKEN_EXP_H
from app_helpers.utils.time_formatting import format_validity_message
from app_helpers.utils.user_management import is_user_deactivated
from app_helpers.services.archive_first_service import create_user_with_text_archive
from app_helpers.utils.username_helpers import (
    normalize_username, 
    normalize_username_for_lookup, 
    validate_username,
    find_users_with_equivalent_usernames
)

# Template and config setup
# Use shared templates instance with filters registered
from app_helpers.shared_templates import templates
router = APIRouter()

# Configuration
SESSION_DAYS = int(os.getenv("SESSION_DAYS", 90))
MULTI_DEVICE_AUTH_ENABLED = os.getenv("MULTI_DEVICE_AUTH_ENABLED", "True").lower() == "true"


def validate_goto_path(goto: str) -> str | None:
    """
    Validate goto parameter to prevent open redirect attacks.
    
    Args:
        goto: The goto parameter to validate
        
    Returns:
        str | None: Validated relative path starting with '/', or None if invalid
    """
    if not goto:
        return None
    
    # Must be a string
    if not isinstance(goto, str):
        return None
    
    # Must start with '/' (relative path)
    if not goto.startswith('/'):
        return None
    
    # Cannot contain protocol patterns (prevent external redirects)
    if '://' in goto or goto.startswith('//'):
        return None
    
    # Cannot contain dangerous characters
    if any(char in goto for char in ['<', '>', '"', "'"]):
        return None
    
    # Length limit for safety
    if len(goto) > 500:
        return None
    
    return goto


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
def claim_get(token: str, request: Request, goto: str = None):
    """
    Display the claim form for an invite token, with immediate validation.
    
    Args:
        token: The invite token to claim
        request: FastAPI request object
        goto: Optional redirect path after successful login (relative paths only)
        
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
        
        # Check if token has reached usage limit
        if inv.max_uses is not None and inv.usage_count >= inv.max_uses:
            return templates.TemplateResponse("claim.html", {
                "request": request, 
                "token": token,
                "error": f"This invite link has reached its usage limit ({inv.max_uses} uses). Please request a new invite."
            })
        
        if inv.expires_at < datetime.utcnow():
            return templates.TemplateResponse("claim.html", {
                "request": request, 
                "token": token,
                "error": f"This invite link has expired. Invite links are {format_validity_message(TOKEN_EXP_H)}. Please request a new invite link."
            })
        
        # Special handling for user_login tokens - auto-login without form
        if inv.token_type == "user_login":
            # For user_login tokens, the target user is pre-stored in used_by_user_id
            if not inv.used_by_user_id:
                return templates.TemplateResponse("claim.html", {
                    "request": request, 
                    "token": token,
                    "error": "This login link is invalid - no target user specified."
                })
            
            # Automatically log in the specified user
            return claim_post(token, inv.used_by_user_id, request, goto)
        
        # Special handling for email_verification tokens - auto-verify and redirect
        if inv.token_type == "email_verification":
            # Import here to avoid circular imports
            from app_helpers.services.email_management_service import EmailManagementService
            
            if not inv.used_by_user_id:
                return templates.TemplateResponse("claim.html", {
                    "request": request, 
                    "token": token,
                    "error": "This verification link is invalid - no target user specified."
                })
            
            # Verify the email
            email_service = EmailManagementService()
            success, message = email_service.verify_email_token(token)
            
            if success:
                # Mark token as used by incrementing usage count
                inv.usage_count += 1
                s.commit()
                
                return templates.TemplateResponse("claim.html", {
                    "request": request, 
                    "token": token,
                    "success": "Email verified successfully! You can now use email recovery to access your account.",
                    "is_email_verification": True
                })
            else:
                return templates.TemplateResponse("claim.html", {
                    "request": request, 
                    "token": token,
                    "error": f"Email verification failed: {message}",
                    "is_email_verification": True
                })
    
    # Token is valid, show the normal claim form with token type context
    return templates.TemplateResponse("claim.html", {
        "request": request, 
        "token": token, 
        "token_exp_hours": TOKEN_EXP_H,
        "token_type": inv.token_type,
        "is_device_token": inv.token_type == "multi_device"
    })


@router.post("/claim/{token}")
def claim_post(token: str, display_name: str = Form(...), request: Request = None, goto: str = None):
    """
    Process invite token claim - either create new user or initiate multi-device auth.
    
    Handles two scenarios:
    1. New user: Create account and log in directly
    2. Existing user: Create authentication request for multi-device auth (if enabled)
    
    Args:
        token: The invite token being claimed
        display_name: The username being claimed
        request: FastAPI request object for device/IP info
        goto: Optional redirect path after successful login (relative paths only)
        
    Returns:
        RedirectResponse: To main feed (new users) or auth status (existing users)
        
    Raises:
        HTTPException: 400 if invite expired, 429 if auth request already pending
    """
    # Validate goto parameter for security
    validated_goto = validate_goto_path(goto)
    
    with Session(engine) as s:
        inv = s.get(InviteToken, token)
        if not inv or inv.expires_at < datetime.utcnow():
            return templates.TemplateResponse("claim.html", {
                "request": request, 
                "token": token,
                "error": "This invite link has expired or is not valid. Please request a new invite link."
            })
        
        # Check if token has reached usage limit
        if inv.max_uses is not None and inv.usage_count >= inv.max_uses:
            return templates.TemplateResponse("claim.html", {
                "request": request, 
                "token": token,
                "error": f"This invite link has reached its usage limit ({inv.max_uses} uses). Please request a new invite."
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
        
        # TOKEN TYPE VALIDATION - This is the key change for preventing username conflicts
        if inv.token_type == "new_user":
            # NEW USER REGISTRATION: Reject if username exists
            if existing_user:
                return templates.TemplateResponse("claim.html", {
                    "request": request,
                    "token": token,
                    "error": f"Username '{display_name}' already exists. Please choose a different name like {display_name}_2024, {display_name}_Smith, etc."
                })
            # Continue to new user creation logic below
            
        elif inv.token_type == "multi_device":
            # MULTI-DEVICE LOGIN: Require existing username
            if not existing_user:
                return templates.TemplateResponse("claim.html", {
                    "request": request,
                    "token": token,
                    "error": f"This device link is for an existing account. Username '{display_name}' not found. Please enter the exact username for the account you want to access."
                })
            # Continue to existing user login logic below
            
        elif inv.token_type == "admin":
            # ADMIN TOKEN: Allow both existing and new users (will grant admin permissions)
            # No validation needed - admin tokens can create new users or login existing users
            pass
            
        elif inv.token_type == "user_login":
            # USER LOGIN TOKEN: Only for existing users, no privilege escalation
            if not existing_user:
                return templates.TemplateResponse("claim.html", {
                    "request": request,
                    "token": token,
                    "error": f"This login link is for an existing account. Username '{display_name}' not found. Please enter the exact username for the account you want to access."
                })
            # Continue to existing user login logic below
            
        else:
            # Invalid token type (shouldn't happen with default values, but defensive)
            return templates.TemplateResponse("claim.html", {
                "request": request,
                "token": token,
                "error": "Invalid invite link type. Please request a new invite."
            })
        
        # Check if this is an admin token for special role handling
        is_admin_token = (inv.created_by_user == "system")
            
        if existing_user:
            # SPECIAL CASE: Existing user with valid invite should login immediately
            # This is the key change - invite possession grants immediate access for existing users
            # while preserving verification requirement for users without invites
            
            # Allow immediate login for existing users with valid invites
            # Record usage and update usage count
            ip_address = request.client.host if request else None
            
            # Create usage record
            usage_record = InviteTokenUsage(
                invite_token_id=token,
                user_id=existing_user.display_name,
                claimed_at=datetime.utcnow(),
                ip_address=ip_address
            )
            s.add(usage_record)
            
            # Update token usage count and latest user
            inv.usage_count += 1
            inv.used_by_user_id = existing_user.display_name
            
            # Archive the invite token usage
            try:
                from app_helpers.services.archive_writers import system_archive_writer
                system_archive_writer.log_invite_usage(
                    token=token,
                    used_by=existing_user.display_name,
                    created_by=inv.created_by_user
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to archive invite token usage: {e}")
            
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
            
            # Extract device info for session creation
            device_info = request.headers.get("User-Agent", "Unknown") if request else "Unknown"
            ip_address = request.client.host if request else "Unknown"
            
            sid = create_session(
                user_id=user_id,
                device_info=device_info,
                ip_address=ip_address,
                is_fully_authenticated=True
            )
            # Use validated goto parameter or default to home
            redirect_url = validated_goto if validated_goto else "/"
            resp = RedirectResponse(redirect_url, 303)
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
            
            # Record usage and update usage count
            ip_address = request.client.host if request else None
            
            # Create usage record
            usage_record = InviteTokenUsage(
                invite_token_id=token,
                user_id=user.display_name,
                claimed_at=datetime.utcnow(),
                ip_address=ip_address
            )
            s.add(usage_record)
            
            # Update token usage count and latest user
            inv.usage_count += 1
            inv.used_by_user_id = user.display_name
            s.add(inv)
            
            # Archive the invite token usage
            try:
                from app_helpers.services.archive_writers import system_archive_writer
                system_archive_writer.log_invite_usage(
                    token=token,
                    used_by=user.display_name,
                    created_by=inv.created_by_user
                )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to archive invite token usage: {e}")
            
            # Grant admin role if this is a system-generated token
            grant_admin_role_for_system_token(user.display_name, token, s)
            
            s.commit()

            # Extract device info for session creation
            device_info = request.headers.get("User-Agent", "Unknown") if request else "Unknown"
            ip_address = request.client.host if request else "Unknown"

            sid = create_session(
                user_id=user.display_name,
                device_info=device_info,
                ip_address=ip_address,
                is_fully_authenticated=True
            )
            # Use validated goto parameter or default to home
            redirect_url = validated_goto if validated_goto else "/"
            resp = RedirectResponse(redirect_url, 303)
            resp.set_cookie("sid", sid, httponly=True, max_age=60*60*24*SESSION_DAYS)
            return resp


@router.get("/login", response_class=HTMLResponse)
def login_get(request: Request, recovery_sent: str = None):
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
        "MULTI_DEVICE_AUTH_ENABLED": MULTI_DEVICE_AUTH_ENABLED,
        "email_auth_enabled": os.getenv('EMAIL_AUTH_ENABLED', 'false').lower() == 'true',
        "recovery_sent": recovery_sent == 'true'
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