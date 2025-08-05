"""
Admin User Management Routes

Contains routes for managing users including deactivation, reactivation, and status checking.
"""

from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func

# Import models
from models import engine, User, Prayer, PrayerMark, InviteToken

# Import helper functions
from app_helpers.services.auth_helpers import current_user, is_admin
from app_helpers.utils.user_management import (
    deactivate_user, reactivate_user, is_user_deactivated, 
    get_user_deactivation_info, UserManagementError
)
from app_helpers.services.token_service import create_user_login_token
from app_helpers.utils.username_helpers import find_users_with_equivalent_usernames

# Initialize templates
# Use shared templates instance with filters registered
from app_helpers.shared_templates import templates

# Create router for this module
router = APIRouter()


@router.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request, user_session: tuple = Depends(current_user)):
    """
    Admin User Management
    
    Displays user management interface for administrators including:
    - List of all users with their statistics
    - User activity and engagement metrics
    - Admin controls for user management
    
    Requires admin privileges.
    """
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403)
    
    with Session(engine) as s:
        # Get all users with basic stats
        users_stmt = select(User).order_by(User.created_at.desc())
        all_users = s.exec(users_stmt).all()
        
        users_with_stats = []
        for profile_user in all_users:
            # Get prayer counts
            prayers_authored = s.exec(
                select(func.count(Prayer.id))
                .where(Prayer.author_username == profile_user.display_name)
                .where(Prayer.flagged == False)
            ).first() or 0
            
            prayers_marked = s.exec(
                select(func.count(PrayerMark.id))
                .where(PrayerMark.username == profile_user.display_name)
            ).first() or 0
            
            # Check deactivation status
            is_deactivated = is_user_deactivated(profile_user.display_name, s)
            deactivation_info = None
            if is_deactivated:
                deactivation_info = get_user_deactivation_info(profile_user.display_name, s)
            
            users_with_stats.append({
                'user': profile_user,
                'prayers_authored': prayers_authored,
                'prayers_marked': prayers_marked,
                'is_admin': profile_user.has_role("admin", s),
                'is_deactivated': is_deactivated,
                'deactivation_info': deactivation_info
            })
    
    return templates.TemplateResponse(
        "users.html", {
            "request": request,
            "users": users_with_stats,
            "me": user,
            "session": session,
            "is_admin_view": True  # Flag to show admin controls
        }
    )


@router.post("/admin/users/{user_id}/deactivate")
def deactivate_user_route(user_id: str, request: Request, user_session: tuple = Depends(current_user)):
    """
    Deactivate User (Soft Delete)
    
    Deactivates a user by removing all their roles and assigning the 'deactivated' role.
    This prevents login while preserving all data for audit purposes.
    
    Requires admin privileges.
    """
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403, "Admin privileges required")
    
    try:
        with Session(engine) as db:
            # Check if target user exists
            target_user = db.exec(select(User).where(User.display_name == user_id)).first()
            if not target_user:
                raise HTTPException(404, "User not found")
            
            # Prevent self-deactivation
            if user_id == user.display_name:
                raise HTTPException(400, "Cannot deactivate your own account")
            
            # Deactivate the user
            success = deactivate_user(
                user_id=user_id,
                admin_id=user.display_name,
                reason=f"Deactivated by admin {user.display_name}",
                session=db
            )
            
            if success:
                return {"status": "success", "message": f"User {target_user.display_name} has been deactivated"}
            else:
                raise HTTPException(500, "Deactivation failed")
                
    except UserManagementError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Internal error: {str(e)}")


@router.post("/admin/users/{user_id}/reactivate") 
def reactivate_user_route(user_id: str, request: Request, user_session: tuple = Depends(current_user)):
    """
    Reactivate User
    
    Reactivates a previously deactivated user by removing the 'deactivated' role
    and restoring the default 'user' role.
    
    Requires admin privileges.
    """
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403, "Admin privileges required")
    
    try:
        with Session(engine) as db:
            # Check if target user exists
            target_user = db.exec(select(User).where(User.display_name == user_id)).first()
            if not target_user:
                raise HTTPException(404, "User not found")
            
            # Reactivate the user
            success = reactivate_user(
                user_id=user_id,
                admin_id=user.display_name,
                session=db
            )
            
            if success:
                return {"status": "success", "message": f"User {target_user.display_name} has been reactivated"}
            else:
                raise HTTPException(500, "Reactivation failed")
                
    except UserManagementError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Internal error: {str(e)}")


@router.get("/admin/users/{user_id}/status")
def get_user_status(user_id: str, request: Request, user_session: tuple = Depends(current_user)):
    """
    Get User Status
    
    Returns the current activation status of a user, including deactivation
    information if applicable.
    
    Requires admin privileges.
    """
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403, "Admin privileges required")
    
    try:
        with Session(engine) as db:
            # Check if user exists
            target_user = db.exec(select(User).where(User.display_name == user_id)).first()
            if not target_user:
                raise HTTPException(404, "User not found")
            
            is_deactivated = is_user_deactivated(user_id, db)
            
            status = {
                "user_id": user_id,
                "display_name": target_user.display_name,
                "is_deactivated": is_deactivated,
                "is_active": not is_deactivated
            }
            
            if is_deactivated:
                deactivation_info = get_user_deactivation_info(user_id, db)
                if deactivation_info:
                    status.update(deactivation_info)
            
            return status
            
    except Exception as e:
        raise HTTPException(500, f"Internal error: {str(e)}")


@router.post("/admin/create-login-link")
def create_login_link(
    request: Request, 
    username: str = Form(...),
    goto_url: str = Form(""),
    hours: int = Form(12),
    user_session: tuple = Depends(current_user)
):
    """
    Create User-Specific Login Link
    
    Creates a user_login token for an existing user with optional redirect URL.
    This allows admins to generate direct login links for users.
    
    Args:
        username: The username to create a login link for
        goto_url: Optional redirect path after login (must be relative)
        hours: Token expiration time in hours (default: 12)
        
    Returns:
        RedirectResponse: Back to admin panel with success message or error
        
    Requires admin privileges.
    """
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403, "Admin privileges required")
    
    try:
        with Session(engine) as db:
            # Validate username exists
            existing_users = find_users_with_equivalent_usernames(db, username.strip())
            if not existing_users:
                return RedirectResponse(
                    f"/admin?error=Username '{username}' not found. Please check the username and try again.",
                    status_code=303
                )
            
            target_user = existing_users[0]
            
            # Validate hours
            if hours <= 0 or hours > 168:  # 1 week max
                return RedirectResponse(
                    "/admin?error=Hours must be between 1 and 168 (1 week max).",
                    status_code=303
                )
            
            # Create the user login token
            token_info = create_user_login_token(
                created_by_user=user.display_name,
                custom_expiration_hours=hours,
                max_uses=1,  # Single use for security
                db_session=db
            )
            
            # Store the target user in the token for user_login tokens
            token_record = db.get(InviteToken, token_info['token'])
            token_record.used_by_user_id = target_user.display_name  # Pre-populate target user
            db.add(token_record)
            
            db.commit()
            
            # Build the claim URL
            base_url = str(request.url_for("claim_get", token=token_info['token']))
            
            # Add goto parameter if provided
            if goto_url.strip() and goto_url.startswith('/'):
                from urllib.parse import urlencode
                params = urlencode({'goto': goto_url.strip()})
                claim_url = f"{base_url}?{params}"
            else:
                claim_url = base_url
            
            # Success message with the generated URL
            success_msg = f"✅ Login link created for {target_user.display_name} (valid for {hours} hours)"
            
            # Store the URL in a way that makes it easy to copy
            from urllib.parse import quote
            return RedirectResponse(
                f"/admin?success={quote(success_msg)}&login_url={quote(claim_url)}&username={quote(target_user.display_name)}",
                status_code=303
            )
            
    except Exception as e:
        return RedirectResponse(
            f"/admin?error=Failed to create login link: {str(e)}",
            status_code=303
        )