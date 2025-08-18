# app_helpers/routes/prayer/prayer_status.py
"""
Prayer status management operations.

Contains functionality for marking prayers, archiving, and answering prayers.
Extracted from prayer_routes.py for better maintainability.
"""

import os
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
from app_helpers.services.prayer_helpers import set_daily_priority, remove_daily_priority, get_daily_priority_date

# Initialize templates
# Use shared templates instance with filters registered
from app_helpers.shared_templates import templates

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
            
            # Refresh prayer object to get current state after any updates
            s.refresh(prayer)
            
            # Pre-compute prayer status for template (methods require session parameter)
            is_prayer_archived = prayer.is_archived(s)
            is_prayer_answered = prayer.is_answered(s)
            
            # Import is_daily_priority function and check feature flag
            from app_helpers.services.prayer_helpers import is_daily_priority
            is_prayer_daily_priority = is_daily_priority(prayer, s) if os.getenv('DAILY_PRIORITY_ENABLED', 'false').lower() == 'true' else False
            
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
                prayer_session=session,
                is_admin=is_admin(user),
                is_prayer_archived=is_prayer_archived,
                is_prayer_answered=is_prayer_answered,
                is_daily_priority=is_prayer_daily_priority,
                DAILY_PRIORITY_ENABLED=os.getenv('DAILY_PRIORITY_ENABLED', 'false').lower() == 'true'
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


@router.post("/prayer/{prayer_id}/set-priority")
def set_prayer_priority(prayer_id: str, request: Request, user_session: tuple = Depends(current_user)):
    """
    Mark a prayer as daily priority (admin only).
    
    Only admins can set daily priorities.
    
    Args:
        prayer_id: ID of prayer to set as daily priority
        request: FastAPI request object
        user_session: Current authenticated user session
    
    Returns:
        For HTMX: HTML response with success message
        For regular: Redirect to main feed
    """
    # Check if daily priority feature is enabled
    if not os.getenv('DAILY_PRIORITY_ENABLED', 'false').lower() == 'true':
        raise HTTPException(404, "Feature not available")
    
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    
    # Only admins can set daily priorities
    if not is_admin(user):
        raise HTTPException(403, "Only admins can set daily priorities")
    
    with Session(engine) as s:
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            raise HTTPException(404, "Prayer not found")
        
        # Set daily priority
        success = set_daily_priority(prayer_id, user, s)
        if not success:
            raise HTTPException(500, "Failed to set daily priority")
        
        if request.headers.get("HX-Request"):
            # Get the priority date that was just set
            priority_date = get_daily_priority_date(prayer_id, s)
            priority_date_tooltip = f" (set on {priority_date})" if priority_date else ""
            
            # Return priority badge with out-of-band menu update
            priority_badge_html = f'''
                <div id="priority-badge-{prayer_id}">
                  <div class="absolute top-2 right-2">
                    <span class="text-yellow-500 dark:text-yellow-400 text-sm opacity-75" title="Daily Priority Prayer{priority_date_tooltip}">⭐</span>
                  </div>
                </div>
            '''
            
            # Update dropdown menu out-of-band with priority date
            priority_date_display = f'''
                      <div class="text-xs text-gray-500 dark:text-gray-400 mt-1">Set on {priority_date}</div>''' if priority_date else ""
            
            menu_html = f'''
                <form method="post" action="/prayer/{prayer_id}/remove-priority" class="block" hx-swap-oob="outerHTML:form[action='/prayer/{prayer_id}/set-priority']">
                  <button type="submit" 
                          hx-post="/prayer/{prayer_id}/remove-priority"
                          hx-target="#priority-badge-{prayer_id}"
                          hx-swap="outerHTML"
                          onclick="hideDropdown('{prayer_id}')"
                          class="block w-full text-left px-4 py-3 text-sm text-orange-600 dark:text-orange-400 hover:bg-orange-50 dark:hover:bg-orange-900/20 hover:text-orange-800 dark:hover:text-orange-300 transition-colors duration-150 font-medium">
                    <div>⭐ Remove Daily Priority</div>{priority_date_display}
                  </button>
                </form>
            '''
            
            return HTMLResponse(priority_badge_html + menu_html)
    
    return RedirectResponse("/", 303)


@router.post("/prayer/{prayer_id}/remove-priority")
def remove_prayer_priority(prayer_id: str, request: Request, user_session: tuple = Depends(current_user)):
    """
    Remove daily priority status from a prayer (admin only).
    
    Only admins can remove daily priorities.
    
    Args:
        prayer_id: ID of prayer to remove priority from
        request: FastAPI request object
        user_session: Current authenticated user session
    
    Returns:
        For HTMX: HTML response with success message
        For regular: Redirect to main feed
    """
    # Check if daily priority feature is enabled
    if not os.getenv('DAILY_PRIORITY_ENABLED', 'false').lower() == 'true':
        raise HTTPException(404, "Feature not available")
    
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    
    # Only admins can remove daily priorities
    if not is_admin(user):
        raise HTTPException(403, "Only admins can remove daily priorities")
    
    with Session(engine) as s:
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            raise HTTPException(404, "Prayer not found")
        
        # Remove daily priority
        success = remove_daily_priority(prayer_id, s)
        if not success:
            raise HTTPException(500, "Failed to remove daily priority")
        
        if request.headers.get("HX-Request"):
            # Return empty priority badge with out-of-band menu update
            priority_badge_html = f'''
                <div id="priority-badge-{prayer_id}">
                </div>
            '''
            
            # Update dropdown menu out-of-band
            menu_html = f'''
                <form method="post" action="/prayer/{prayer_id}/set-priority" class="block" hx-swap-oob="outerHTML:form[action='/prayer/{prayer_id}/remove-priority']">
                  <button type="submit" 
                          hx-post="/prayer/{prayer_id}/set-priority"
                          hx-target="#priority-badge-{prayer_id}"
                          hx-swap="outerHTML"
                          onclick="hideDropdown('{prayer_id}')"
                          class="block w-full text-left px-4 py-3 text-sm text-yellow-600 dark:text-yellow-400 hover:bg-yellow-50 dark:hover:bg-yellow-900/20 hover:text-yellow-800 dark:hover:text-yellow-300 transition-colors duration-150 font-medium whitespace-nowrap">
                    ⭐ Mark as Daily Priority
                  </button>
                </form>
            '''
            
            return HTMLResponse(priority_badge_html + menu_html)
    
    return RedirectResponse("/", 303)