# user_routes.py - User profile and community routes
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func

from models import engine, User, Prayer, PrayerMark, Session as SessionModel
from app_helpers.services.auth_helpers import current_user
from app_helpers.utils.user_management import is_user_deactivated

templates = Jinja2Templates(directory="templates")

router = APIRouter()

@router.get("/profile", response_class=HTMLResponse)
def my_profile(request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    return user_profile(request, user.id, user_session)

@router.get("/user/{user_id}", response_class=HTMLResponse)
def user_profile(request: Request, user_id: str, user_session: tuple = Depends(current_user)):
    user, session = user_session
    with Session(engine) as s:
        # Get the profile user
        profile_user = s.get(User, user_id)
        if not profile_user:
            raise HTTPException(404, "User not found")
        
        is_own_profile = user_id == user.id
        
        # Get inviter information
        inviter = None
        if profile_user.invited_by_user_id:
            inviter = s.get(User, profile_user.invited_by_user_id)
        
        # Get prayer statistics
        stats = {}
        
        # Total prayers authored
        stats['prayers_authored'] = s.exec(
            select(func.count(Prayer.id))
            .where(Prayer.author_id == user_id)
            .where(Prayer.flagged == False)
        ).first() or 0
        
        # Total prayers marked (how many times they've prayed)
        stats['prayers_marked'] = s.exec(
            select(func.count(PrayerMark.id))
            .where(PrayerMark.user_id == user_id)
        ).first() or 0
        
        # Distinct prayers marked (unique prayers they've prayed)
        stats['distinct_prayers_marked'] = s.exec(
            select(func.count(func.distinct(PrayerMark.prayer_id)))
            .where(PrayerMark.user_id == user_id)
        ).first() or 0
        
        # Recent prayer requests (last 5)
        recent_requests_stmt = (
            select(Prayer)
            .where(Prayer.author_id == user_id)
            .where(Prayer.flagged == False)
            .order_by(Prayer.created_at.desc())
            .limit(5)
        )
        recent_requests = s.exec(recent_requests_stmt).all()
        
        # Recent prayers marked (last 5 unique prayers)
        recent_marks_stmt = (
            select(Prayer, func.max(PrayerMark.created_at).label('last_marked'))
            .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .join(User, Prayer.author_id == User.id)
            .where(PrayerMark.user_id == user_id)
            .where(Prayer.flagged == False)
            .group_by(Prayer.id)
            .order_by(func.max(PrayerMark.created_at).desc())
            .limit(5)
        )
        recent_marks_results = s.exec(recent_marks_stmt).all()
        recent_marked_prayers = []
        for prayer, last_marked in recent_marks_results:
            # Get author name
            author = s.get(User, prayer.author_id)
            recent_marked_prayers.append({
                'prayer': prayer,
                'author_name': author.display_name if author else "Unknown",
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
            if profile_user.id == 'admin':
                role_names = ['admin (legacy)']
        
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
                "role_names": role_names
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
                .where(Prayer.author_id == profile_user.id)
                .where(Prayer.flagged == False)
            ).first() or 0
            
            prayers_marked = s.exec(
                select(func.count(PrayerMark.id))
                .where(PrayerMark.user_id == profile_user.id)
            ).first() or 0
            
            distinct_prayers_marked = s.exec(
                select(func.count(func.distinct(PrayerMark.prayer_id)))
                .where(PrayerMark.user_id == profile_user.id)
            ).first() or 0
            
            # Get last activity
            last_activity = None
            last_prayer_mark = s.exec(
                select(PrayerMark.created_at)
                .where(PrayerMark.user_id == profile_user.id)
                .order_by(PrayerMark.created_at.desc())
                .limit(1)
            ).first()
            
            last_prayer_request = s.exec(
                select(Prayer.created_at)
                .where(Prayer.author_id == profile_user.id)
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
            is_deactivated = is_user_deactivated(profile_user.id, s)
            
            # For regular users, filter out deactivated users (except themselves)
            if is_deactivated and profile_user.id != user.id:
                continue
            
            users_with_stats.append({
                'user': profile_user,
                'prayers_authored': prayers_authored,
                'prayers_marked': prayers_marked,
                'distinct_prayers_marked': distinct_prayers_marked,
                'last_activity': last_activity,
                'is_me': profile_user.id == user.id,
                'is_deactivated': is_deactivated,
                'is_admin': profile_user.has_role("admin", s)
            })
        
        return templates.TemplateResponse(
            "users.html",
            {"request": request, "users": users_with_stats, "me": user, "session": session}
        )

@router.get("/preferences", response_class=HTMLResponse)
async def get_user_preferences(request: Request, user_session: tuple = Depends(current_user)):
    """Display user religious preference settings"""
    user, session = user_session
    
    with Session(engine) as db:
        db_user = db.get(User, user.id)
        return templates.TemplateResponse("preferences.html", {
            "request": request,
            "user": db_user,
            "me": user,
            "session": session
        })

@router.post("/preferences")
async def update_user_preferences(
    request: Request,
    religious_preference: str = Form(...),
    prayer_style: str = Form(None),
    user_session: tuple = Depends(current_user)
):
    """Update user's religious preferences"""
    user, session = user_session
    
    # Validate religious preference
    valid_preferences = ["christian", "unspecified"]
    if religious_preference not in valid_preferences:
        raise HTTPException(400, "Invalid religious preference")
    
    # Validate prayer style for Christians
    valid_prayer_styles = ["in_jesus_name", "interfaith", None, ""]
    if prayer_style and prayer_style not in valid_prayer_styles:
        raise HTTPException(400, "Invalid prayer style")
    
    with Session(engine) as db:
        db_user = db.get(User, user.id)
        old_preference = db_user.religious_preference
        old_style = db_user.prayer_style
        
        db_user.religious_preference = religious_preference
        
        # Only set prayer style for Christian users
        if religious_preference == "christian":
            db_user.prayer_style = prayer_style if prayer_style else None
        else:
            db_user.prayer_style = None
        
        db.add(db_user)
        db.commit()
        
        # Log the preference change for analytics
        print(f"User {user.id} changed preference: {old_preference} -> {religious_preference}, style: {old_style} -> {db_user.prayer_style}")
    
    return RedirectResponse("/profile", status_code=303)

@router.get("/profile/preferences")
async def get_user_preferences_alt(request: Request, user_session: tuple = Depends(current_user)):
    """Display user religious preference settings (alternative endpoint)"""
    user, session = user_session
    
    with Session(engine) as db:
        db_user = db.get(User, user.id)
        return templates.TemplateResponse("preferences.html", {
            "request": request,
            "user": db_user,
            "me": user,
            "session": session
        })

@router.post("/profile/preferences")
async def update_religious_preferences(
    request: Request,
    religious_preference: str = Form(...),
    prayer_style: str = Form(None),
    user_session: tuple = Depends(current_user)
):
    """Update user's religious preferences (alternative endpoint)"""
    user, session = user_session
    
    # Validate religious preference
    valid_preferences = ["christian", "unspecified"]
    if religious_preference not in valid_preferences:
        raise HTTPException(400, "Invalid religious preference")
    
    # Validate prayer style for Christians
    valid_prayer_styles = ["in_jesus_name", "interfaith", None, ""]
    if prayer_style and prayer_style not in valid_prayer_styles:
        raise HTTPException(400, "Invalid prayer style")
    
    with Session(engine) as db:
        db_user = db.get(User, user.id)
        old_preference = db_user.religious_preference
        old_style = db_user.prayer_style
        
        db_user.religious_preference = religious_preference
        
        # Only set prayer style for Christian users
        if religious_preference == "christian":
            db_user.prayer_style = prayer_style if prayer_style else None
        else:
            db_user.prayer_style = None
        
        db.add(db_user)
        db.commit()
        
        # Log the preference change for analytics
        print(f"User {user.id} changed preference: {old_preference} -> {religious_preference}, style: {old_style} -> {db_user.prayer_style}")
    
    return RedirectResponse("/profile", status_code=303)

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
        user_id=user.id,
        ip_address=client_ip,
        user_agent=user_agent,
        details=f"User {user.display_name} logged out"
    )
    
    # Clear the session cookie and redirect to logged-out confirmation page
    response = RedirectResponse("/logged-out", status_code=303)
    response.delete_cookie("sid", path="/", domain=None)
    return response