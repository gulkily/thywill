# app_helpers/routes/prayer/prayer_status.py
"""
Prayer status management operations.

Contains functionality for marking prayers, archiving, and answering prayers.
Extracted from prayer_routes.py for better maintainability.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func

from models import engine, Prayer, PrayerMark

# Import helper functions
from app_helpers.services.auth_helpers import current_user, is_admin
from app_helpers.services.archive_first_service import append_prayer_activity_with_archive

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Create router for status operations
router = APIRouter()


@router.post("/mark/{prayer_id}")
def mark_prayer(prayer_id: str, request: Request, user_session: tuple = Depends(current_user)):
    """
    Mark a prayer as prayed (add a prayer mark).
    
    Users can mark the same prayer multiple times. Supports HTMX for dynamic updates.
    
    Args:
        prayer_id: ID of prayer to mark as prayed
        request: FastAPI request object
        user_session: Current authenticated user session
    
    Returns:
        For HTMX: HTML response with updated prayer mark section
        For regular: Redirect to prayer anchor
    """
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required to mark prayers")
    with Session(engine) as s:
        # Check if prayer exists
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            raise HTTPException(404, "Prayer not found")
        
        # Use archive-first approach: write to text archive FIRST, then database
        append_prayer_activity_with_archive(prayer_id, "prayed", user)
        
        # If this is an HTMX request, return just the updated prayer mark section
        if request.headers.get("HX-Request"):
            # Get updated mark count for all users (total times)
            mark_count_stmt = select(func.count(PrayerMark.id)).where(PrayerMark.prayer_id == prayer_id)
            total_mark_count = s.exec(mark_count_stmt).first()
            
            # Get updated distinct user count (how many people)
            distinct_user_count_stmt = select(func.count(func.distinct(PrayerMark.username))).where(PrayerMark.prayer_id == prayer_id)
            distinct_user_count = s.exec(distinct_user_count_stmt).first()
            
            # Get updated mark count for current user
            user_mark_count_stmt = select(func.count(PrayerMark.id)).where(
                PrayerMark.prayer_id == prayer_id,
                PrayerMark.username == user.display_name
            )
            user_mark_count = s.exec(user_mark_count_stmt).first()
            
            # Build the prayer stats display
            prayer_stats = ""
            if total_mark_count > 0:
                if distinct_user_count == 1:
                    if total_mark_count == 1:
                        prayer_stats = f'<a href="/prayer/{prayer_id}/marks" class="text-purple-600 dark:text-purple-300 hover:text-purple-800 dark:hover:text-purple-200 hover:underline">🙏 1 person prayed this once</a>'
                    else:
                        prayer_stats = f'<a href="/prayer/{prayer_id}/marks" class="text-purple-600 dark:text-purple-300 hover:text-purple-800 dark:hover:text-purple-200 hover:underline">🙏 1 person prayed this {total_mark_count} times</a>'
                else:
                    prayer_stats = f'<a href="/prayer/{prayer_id}/marks" class="text-purple-600 dark:text-purple-300 hover:text-purple-800 dark:hover:text-purple-200 hover:underline">🙏 {distinct_user_count} people prayed this {total_mark_count} times</a>'
            
            # Return the updated prayer mark section HTML
            return HTMLResponse(templates.get_template("prayer_marks_section.html").render(
                prayer_id=prayer_id, 
                prayer_stats=prayer_stats, 
                user_mark_count=user_mark_count,
                prayer=prayer,
                me=user,
                prayer_session=session
            ))
    
    # For non-HTMX requests, redirect back to the specific prayer
    return RedirectResponse(f"/#prayer-{prayer_id}", 303)


@router.post("/prayer/{prayer_id}/archive")
def archive_prayer(prayer_id: str, request: Request, user_session: tuple = Depends(current_user)):
    """
    Archive a prayer (hide from public feeds, accessible only to author).
    
    Only the prayer author or admin can archive prayers.
    
    Args:
        prayer_id: ID of prayer to archive
        request: FastAPI request object  
        user_session: Current authenticated user session
    
    Returns:
        For HTMX: HTML response with archive confirmation
        For regular: Redirect to main feed
    """
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    
    with Session(engine) as s:
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            raise HTTPException(404, "Prayer not found")
        
        # Only prayer author or admin can archive prayers
        if prayer.author_username != user.display_name and not is_admin(user):
            raise HTTPException(403, "Only prayer author or admin can archive this prayer")
        
        # Use archive-first approach: write to text archive FIRST, then database
        append_prayer_activity_with_archive(prayer_id, "archived", user)
        s.commit()
        
        if request.headers.get("HX-Request"):
            # Return success message with gentle transition
            return HTMLResponse(f'''
                <div class="prayer-archived bg-amber-50 dark:bg-amber-900/20 p-3 rounded border border-amber-200 dark:border-amber-700 text-center">
                    <span class="text-amber-700 dark:text-amber-300 text-sm font-medium">
                        📁 Prayer archived successfully
                    </span>
                </div>
            ''')
    
    return RedirectResponse("/", 303)


@router.post("/prayer/{prayer_id}/restore")
def restore_prayer(prayer_id: str, request: Request, user_session: tuple = Depends(current_user)):
    """
    Restore an archived prayer (make visible in public feeds again).
    
    Only the prayer author or admin can restore prayers.
    
    Args:
        prayer_id: ID of prayer to restore
        request: FastAPI request object
        user_session: Current authenticated user session
    
    Returns:
        For HTMX: HTML response with restore confirmation
        For regular: Redirect to main feed
    """
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    
    with Session(engine) as s:
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            raise HTTPException(404, "Prayer not found")
        
        # Only prayer author or admin can restore prayers
        if prayer.author_username != user.display_name and not is_admin(user):
            raise HTTPException(403, "Only prayer author or admin can restore this prayer")
        
        # Use archive-first approach: write to text archive FIRST, then database
        append_prayer_activity_with_archive(prayer_id, "restored", user)
        s.commit()
        
        if request.headers.get("HX-Request"):
            # Return success message
            return HTMLResponse(f'''
                <div class="prayer-restored bg-green-50 dark:bg-green-900/20 p-3 rounded border border-green-200 dark:border-green-700 text-center">
                    <span class="text-green-700 dark:text-green-300 text-sm font-medium">
                        ✅ Prayer restored successfully
                    </span>
                </div>
            ''')
    
    return RedirectResponse("/", 303)


@router.post("/prayer/{prayer_id}/answered")
def mark_prayer_answered(prayer_id: str, request: Request, 
                        testimony: Optional[str] = Form(None),
                        user_session: tuple = Depends(current_user)):
    """
    Mark a prayer as answered with optional testimony.
    
    Only the prayer author or admin can mark prayers as answered.
    Answered prayers appear in the celebration feed.
    
    Args:
        prayer_id: ID of prayer to mark as answered
        request: FastAPI request object
        testimony: Optional testimony about how prayer was answered
        user_session: Current authenticated user session
    
    Returns:
        For HTMX: HTML response with celebration message
        For regular: Redirect to main feed
    """
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    
    with Session(engine) as s:
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            raise HTTPException(404, "Prayer not found")
        
        # Only prayer author or admin can mark prayers as answered
        if prayer.author_username != user.display_name and not is_admin(user):
            raise HTTPException(403, "Only prayer author or admin can mark this prayer as answered")
        
        # Use archive-first approach: write to text archive FIRST, then database
        # Pass testimony as extra data for the answered action
        testimony_text = testimony.strip() if testimony and testimony.strip() else ""
        append_prayer_activity_with_archive(prayer_id, "answered", user, testimony_text)
        
        s.commit()
        
        if request.headers.get("HX-Request"):
            # Return celebration message
            return HTMLResponse(f'''
                <div class="prayer-answered bg-green-100 dark:bg-green-900/30 p-4 rounded-lg border border-green-300 dark:border-green-600 text-center">
                    <div class="flex items-center justify-center gap-2 mb-2">
                        <span class="text-2xl">🎉</span>
                        <span class="text-green-800 dark:text-green-200 font-semibold">Prayer Answered!</span>
                    </div>
                    <p class="text-green-700 dark:text-green-300 text-sm">
                        Praise the Lord! This prayer has been moved to the celebration feed.
                    </p>
                </div>
            ''')
    
    return RedirectResponse("/", 303)