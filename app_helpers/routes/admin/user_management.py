"""
Admin User Management Routes

Contains routes for managing users including deactivation, reactivation, and status checking.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func

# Import models
from models import engine, User, Prayer, PrayerMark

# Import helper functions
from app_helpers.services.auth_helpers import current_user, is_admin
from app_helpers.utils.user_management import (
    deactivate_user, reactivate_user, is_user_deactivated, 
    get_user_deactivation_info, UserManagementError
)

# Initialize templates
templates = Jinja2Templates(directory="templates")

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
                .where(Prayer.author_id == profile_user.id)
                .where(Prayer.flagged == False)
            ).first() or 0
            
            prayers_marked = s.exec(
                select(func.count(PrayerMark.id))
                .where(PrayerMark.user_id == profile_user.id)
            ).first() or 0
            
            # Check deactivation status
            is_deactivated = is_user_deactivated(profile_user.id, s)
            deactivation_info = None
            if is_deactivated:
                deactivation_info = get_user_deactivation_info(profile_user.id, s)
            
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
            target_user = db.exec(select(User).where(User.id == user_id)).first()
            if not target_user:
                raise HTTPException(404, "User not found")
            
            # Prevent self-deactivation
            if user_id == user.id:
                raise HTTPException(400, "Cannot deactivate your own account")
            
            # Deactivate the user
            success = deactivate_user(
                user_id=user_id,
                admin_id=user.id,
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
            target_user = db.exec(select(User).where(User.id == user_id)).first()
            if not target_user:
                raise HTTPException(404, "User not found")
            
            # Reactivate the user
            success = reactivate_user(
                user_id=user_id,
                admin_id=user.id,
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
            target_user = db.exec(select(User).where(User.id == user_id)).first()
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