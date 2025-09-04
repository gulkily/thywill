# user_routes.py - User profile and community routes
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Request, Form, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func

from models import engine, User, Prayer, PrayerMark, Session as SessionModel
from app_helpers.services.auth_helpers import current_user
from app_helpers.services.auth.validation_helpers import log_security_event, is_admin
from app_helpers.services.profile_data_service import ProfileDataService
from app_helpers.utils.user_management import is_user_deactivated
from app_helpers.timezone_utils import get_user_timezone_from_request

# Use shared templates instance with filters registered
from app_helpers.shared_templates import templates

router = APIRouter()

@router.get("/profile", response_class=HTMLResponse)
def my_profile(request: Request, user_session: tuple = Depends(current_user), email_success: str = None, email_error: str = None):
    user, session = user_session
    return user_profile(request, user.display_name, user_session, email_success, email_error)

@router.get("/user/{user_id}", response_class=HTMLResponse)
def user_profile(request: Request, user_id: str, user_session: tuple = Depends(current_user), email_success: str = None, email_error: str = None):
    user, session = user_session
    with Session(engine) as s:
        # Get the profile user
        profile_user = s.get(User, user_id)
        if not profile_user:
            raise HTTPException(404, "User not found")
        
        is_own_profile = user_id == user.display_name
        
        # Get inviter information
        inviter = None
        if profile_user.invited_by_username:
            inviter = s.get(User, profile_user.invited_by_username)
        
        # Get prayer statistics
        stats = {}
        
        # Total prayers authored
        stats['prayers_authored'] = s.exec(
            select(func.count(Prayer.id))
            .where(Prayer.author_username == user_id)
            .where(Prayer.flagged == False)
        ).first() or 0
        
        # Total prayers marked (how many times they've prayed)
        stats['prayers_marked'] = s.exec(
            select(func.count(PrayerMark.id))
            .where(PrayerMark.username == user_id)
        ).first() or 0
        
        # Distinct prayers marked (unique prayers they've prayed)
        stats['distinct_prayers_marked'] = s.exec(
            select(func.count(func.distinct(PrayerMark.prayer_id)))
            .where(PrayerMark.username == user_id)
        ).first() or 0
        
        # Recent prayer requests (last 5)
        recent_requests_stmt = (
            select(Prayer)
            .where(Prayer.author_username == user_id)
            .where(Prayer.flagged == False)
            .order_by(Prayer.created_at.desc())
            .limit(5)
        )
        recent_requests = s.exec(recent_requests_stmt).all()
        
        # Recent prayers marked (last 5 unique prayers)
        recent_marks_stmt = (
            select(Prayer, func.max(PrayerMark.created_at).label('last_marked'))
            .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .outerjoin(User, Prayer.author_username == User.display_name)
            .where(PrayerMark.username == user_id)
            .where(Prayer.flagged == False)
            .group_by(Prayer.id)
            .order_by(func.max(PrayerMark.created_at).desc())
            .limit(5)
        )
        recent_marks_results = s.exec(recent_marks_stmt).all()
        recent_marked_prayers = []
        for prayer, last_marked in recent_marks_results:
            # Get author name
            author = s.get(User, prayer.author_username)
            recent_marked_prayers.append({
                'prayer': prayer,
                'author_name': author.display_name if author else "Unknown",
                'author': author,  # Add user object for supporter badge
                'last_marked': last_marked
            })
        
        # Get user roles for profile display
        try:
            user_roles = profile_user.get_roles(s)
            role_names = [role.name for role in user_roles]
        except Exception:
            # Fallback for users without role system or if tables don't exist
            user_roles = []
            role_names = []
            # Check old admin system for backward compatibility
            if profile_user.display_name == 'admin':
                role_names = ['admin (legacy)']
        
        user_timezone = get_user_timezone_from_request(request)
        
        # Get email information for own profile
        user_email = None
        email_status = None
        email_auth_enabled = os.getenv('EMAIL_AUTH_ENABLED', 'false').lower() == 'true'
        if is_own_profile and email_auth_enabled:
            try:
                from app_helpers.services.email_management_service import EmailManagementService
                email_service = EmailManagementService()
                email_status = email_service.get_user_email_status(profile_user.display_name)
                if email_status and email_status['verified']:
                    user_email = email_status['email']
            except Exception:
                pass  # Email service not available or error
        
        return templates.TemplateResponse(
            "profile.html",
            {
                "request": request, 
                "profile_user": profile_user, 
                "me": user,
                "session": session, 
                "is_own_profile": is_own_profile,
                "stats": stats,
                "recent_requests": recent_requests,
                "recent_marked_prayers": recent_marked_prayers,
                "inviter": inviter,
                "user_roles": user_roles,
                "role_names": role_names,
                "is_admin": is_admin(user),
                "user_timezone": user_timezone,
                "user_email": user_email,
                "email_status": email_status,
                "email_auth_enabled": email_auth_enabled,
                "email_success": email_success,
                "email_error": email_error
            }
        )

@router.get("/users", response_class=HTMLResponse)
def users_list(request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    with Session(engine) as s:
        # Get all users with their statistics
        users_stmt = select(User).order_by(User.created_at.desc())
        all_users = s.exec(users_stmt).all()
        
        users_with_stats = []
        for profile_user in all_users:
            # Get statistics for each user
            prayers_authored = s.exec(
                select(func.count(Prayer.id))
                .where(Prayer.author_username == profile_user.display_name)
                .where(Prayer.flagged == False)
            ).first() or 0
            
            prayers_marked = s.exec(
                select(func.count(PrayerMark.id))
                .where(PrayerMark.username == profile_user.display_name)
            ).first() or 0
            
            distinct_prayers_marked = s.exec(
                select(func.count(func.distinct(PrayerMark.prayer_id)))
                .where(PrayerMark.username == profile_user.display_name)
            ).first() or 0
            
            # Get last activity
            last_activity = None
            last_prayer_mark = s.exec(
                select(PrayerMark.created_at)
                .where(PrayerMark.username == profile_user.display_name)
                .order_by(PrayerMark.created_at.desc())
                .limit(1)
            ).first()
            
            last_prayer_request = s.exec(
                select(Prayer.created_at)
                .where(Prayer.author_username == profile_user.display_name)
                .where(Prayer.flagged == False)
                .order_by(Prayer.created_at.desc())
                .limit(1)
            ).first()
            
            if last_prayer_mark and last_prayer_request:
                last_activity = max(last_prayer_mark, last_prayer_request)
            elif last_prayer_mark:
                last_activity = last_prayer_mark
            elif last_prayer_request:
                last_activity = last_prayer_request
            
            # Check if user is deactivated
            is_deactivated = is_user_deactivated(profile_user.display_name, s)
            
            # For regular users, filter out deactivated users (except themselves)
            if is_deactivated and profile_user.display_name != user.display_name:
                continue
            
            users_with_stats.append({
                'user': profile_user,
                'prayers_authored': prayers_authored,
                'prayers_marked': prayers_marked,
                'distinct_prayers_marked': distinct_prayers_marked,
                'last_activity': last_activity,
                'is_me': profile_user.display_name == user.display_name,
                'is_deactivated': is_deactivated,
                'is_admin': profile_user.has_role("admin", s)
            })
        
        user_timezone = get_user_timezone_from_request(request)
        
        return templates.TemplateResponse(
            "users.html",
            {"request": request, "users": users_with_stats, "me": user, "session": session, "is_admin": is_admin(user), "user_timezone": user_timezone}
        )


@router.post("/logout")
async def logout(request: Request, user_session: tuple = Depends(current_user)):
    """Log out the current user by clearing their session"""
    user, session = user_session
    
    # Get client info for logging
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
    # Delete the session from database
    with Session(engine) as db:
        db.delete(session)
        db.commit()
    
    # Log the logout event
    log_security_event(
        event_type="logout",
        user_id=user.display_name,
        ip_address=client_ip,
        user_agent=user_agent,
        details=f"User {user.display_name} logged out"
    )
    
    # Clear the session cookie and redirect to logged-out confirmation page
    response = RedirectResponse("/logged-out", status_code=303)
    response.delete_cookie("sid", path="/", domain=None)
    return response


@router.get("/profile/{user_id}/prayers", response_class=HTMLResponse)
def user_profile_prayers(
    request: Request, 
    user_id: str, 
    page: int = Query(1, ge=1),
    user_session: tuple = Depends(current_user)
):
    """Display paginated list of prayer requests by a specific user"""
    user, session = user_session
    
    with Session(engine) as s:
        # Get the profile user
        profile_user = s.get(User, user_id)
        if not profile_user:
            raise HTTPException(404, "User not found")
        
        is_own_profile = user_id == user.display_name
        
        # Get prayer requests with pagination
        prayers, total_count = ProfileDataService.get_user_prayer_requests(
            user_id, s, page, 20
        )
        
        # Get pagination info
        pagination = ProfileDataService.get_pagination_info(total_count, page, 20)
        
        user_timezone = get_user_timezone_from_request(request)
        
        return templates.TemplateResponse(
            "profile_prayers.html",
            {
                "request": request,
                "profile_user": profile_user,
                "me": user,
                "session": session,
                "is_own_profile": is_own_profile,
                "prayers": prayers,
                "pagination": pagination,
                "user_timezone": user_timezone,
                "is_admin": is_admin(user)
            }
        )


@router.get("/profile/{user_id}/prayed", response_class=HTMLResponse)
def user_profile_prayed(
    request: Request, 
    user_id: str, 
    page: int = Query(1, ge=1),
    user_session: tuple = Depends(current_user)
):
    """Display paginated list of prayers the user has marked/prayed for"""
    user, session = user_session
    
    with Session(engine) as s:
        # Get the profile user
        profile_user = s.get(User, user_id)
        if not profile_user:
            raise HTTPException(404, "User not found")
        
        is_own_profile = user_id == user.display_name
        
        # Get prayers marked with pagination
        prayer_data, total_count = ProfileDataService.get_user_prayers_marked(
            user_id, s, page, 20
        )
        
        # Get pagination info
        pagination = ProfileDataService.get_pagination_info(total_count, page, 20)
        
        user_timezone = get_user_timezone_from_request(request)
        
        return templates.TemplateResponse(
            "profile_prayed.html",
            {
                "request": request,
                "profile_user": profile_user,
                "me": user,
                "session": session,
                "is_own_profile": is_own_profile,
                "prayer_data": prayer_data,
                "pagination": pagination,
                "user_timezone": user_timezone,
                "is_admin": is_admin(user)
            }
        )


@router.get("/profile/{user_id}/unique", response_class=HTMLResponse)
def user_profile_unique(
    request: Request, 
    user_id: str, 
    page: int = Query(1, ge=1),
    user_session: tuple = Depends(current_user)
):
    """Display unique prayers information and breakdown for the user"""
    user, session = user_session
    
    with Session(engine) as s:
        # Get the profile user
        profile_user = s.get(User, user_id)
        if not profile_user:
            raise HTTPException(404, "User not found")
        
        is_own_profile = user_id == user.display_name
        
        # Get unique prayers information
        unique_data = ProfileDataService.get_user_unique_prayers_info(
            user_id, s, page, 20
        )
        
        # Get pagination info for sample prayers
        pagination = ProfileDataService.get_pagination_info(
            unique_data['unique_count'], page, 20
        )
        
        user_timezone = get_user_timezone_from_request(request)
        
        return templates.TemplateResponse(
            "profile_unique.html",
            {
                "request": request,
                "profile_user": profile_user,
                "me": user,
                "session": session,
                "is_own_profile": is_own_profile,
                "unique_data": unique_data,
                "pagination": pagination,
                "user_timezone": user_timezone,
                "is_admin": is_admin(user)
            }
        )