# app_helpers/routes/prayer_routes.py
"""
Prayer-related route handlers extracted from app.py

This module contains all prayer-related FastAPI route handlers including:
- Feed display with filtering
- Prayer submission and management
- Prayer marking (praying for prayers)
- Prayer archiving and restoration
- Prayer answered marking
- Prayer statistics and activity feeds

All routes maintain exact backward compatibility with the original app.py implementation.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func

from models import (
    engine, User, Prayer, PrayerMark, PrayerAttribute, PrayerActivityLog,
    Session as SessionModel
)

# Import helper functions
from app_helpers.services.auth_helpers import current_user, require_full_auth, is_admin
from app_helpers.services.prayer_helpers import (
    get_feed_counts, generate_prayer, find_compatible_prayer_partner, todays_prompt
)

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Create router for prayer-related routes
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def feed(request: Request, feed_type: str = "all", user_session: tuple = Depends(current_user)):
    """
    Main feed displaying prayers with various filtering options.
    
    Feed types:
    - all: All non-archived prayers (default)
    - new_unprayed: Prayers that have never been prayed
    - most_prayed: Most prayed prayers by total count
    - my_prayers: Prayers the current user has marked as prayed
    - my_requests: Prayer requests submitted by current user
    - recent_activity: Prayers with recent prayer marks
    - answered: Answered prayers (celebration feed)
    - archived: Archived prayers (author's personal view only)
    """
    user, session = user_session
    # Ensure feed_type has a valid default
    if not feed_type:
        feed_type = "all"
        
    with Session(engine) as s:
        prayers_with_authors = []
        
        # Base filter to exclude archived prayers for public feeds
        def exclude_archived():
            return ~Prayer.id.in_(
                select(PrayerAttribute.prayer_id)
                .where(PrayerAttribute.attribute_name == 'archived')
            )
        
        # Religious preference filtering
        def apply_religious_filter():
            if user.religious_preference == "christian":
                # Christians see: all prayers + christian-only prayers
                return Prayer.target_audience.in_(["all", "christians_only"])
            else:
                # All faiths (unspecified) users see only "all" prayers
                return Prayer.target_audience == "all"
        
        if feed_type == "new_unprayed":
            # New prayers and prayers that have never been prayed (exclude archived)
            stmt = (
                select(Prayer, User.display_name)
                .join(User, Prayer.author_id == User.id)
                .outerjoin(PrayerMark, Prayer.id == PrayerMark.prayer_id)
                .where(Prayer.flagged == False)
                .where(exclude_archived())
                .where(apply_religious_filter())
                .group_by(Prayer.id)
                .having(func.count(PrayerMark.id) == 0)
                .order_by(Prayer.created_at.desc())
            )
        elif feed_type == "most_prayed":
            # Most prayed prayers (by total prayer count, exclude archived)
            stmt = (
                select(Prayer, User.display_name, func.count(PrayerMark.id).label('mark_count'))
                .join(User, Prayer.author_id == User.id)
                .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
                .where(Prayer.flagged == False)
                .where(exclude_archived())
                .where(apply_religious_filter())
                .group_by(Prayer.id)
                .order_by(func.count(PrayerMark.id).desc())
                .limit(50)
            )
        elif feed_type == "my_prayers":
            # Prayers the current user has marked as prayed (include all statuses)
            stmt = (
                select(Prayer, User.display_name)
                .join(User, Prayer.author_id == User.id)
                .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
                .where(Prayer.flagged == False)
                .where(PrayerMark.user_id == user.id)
                .group_by(Prayer.id)
                .order_by(func.max(PrayerMark.created_at).desc())
            )
        elif feed_type == "my_requests":
            # Prayer requests submitted by the current user (include all statuses)
            stmt = (
                select(Prayer, User.display_name)
                .join(User, Prayer.author_id == User.id)
                .where(Prayer.flagged == False)
                .where(Prayer.author_id == user.id)
                .order_by(Prayer.created_at.desc())
            )
        elif feed_type == "recent_activity":
            # Prayers with recent prayer marks (most recently prayed, exclude archived)
            stmt = (
                select(Prayer, User.display_name)
                .join(User, Prayer.author_id == User.id)
                .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
                .where(Prayer.flagged == False)
                .where(exclude_archived())
                .where(apply_religious_filter())
                .group_by(Prayer.id)
                .order_by(func.max(PrayerMark.created_at).desc())
                .limit(50)
            )
        elif feed_type == "answered":
            # Answered prayers (public celebration feed)
            stmt = (
                select(Prayer, User.display_name)
                .join(User, Prayer.author_id == User.id)
                .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
                .where(Prayer.flagged == False)
                .where(PrayerAttribute.attribute_name == 'answered')
                .where(apply_religious_filter())
                .order_by(Prayer.created_at.desc())
            )
        elif feed_type == "archived":
            # Archived prayers (personal feed for prayer authors only)
            stmt = (
                select(Prayer, User.display_name)
                .join(User, Prayer.author_id == User.id)
                .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
                .where(Prayer.flagged == False)
                .where(Prayer.author_id == user.id)  # Only user's own prayers
                .where(PrayerAttribute.attribute_name == 'archived')
                .order_by(Prayer.created_at.desc())
            )
        else:  # "all" or default
            # All prayers (exclude archived)
            stmt = (
                select(Prayer, User.display_name)
                .join(User, Prayer.author_id == User.id)
                .where(Prayer.flagged == False)
                .where(exclude_archived())
                .where(apply_religious_filter())
                .order_by(Prayer.created_at.desc())
            )
            
        results = s.exec(stmt).all()
        
        # Get all prayer marks for the current user
        user_marks_stmt = select(PrayerMark.prayer_id, func.count(PrayerMark.id)).where(PrayerMark.user_id == user.id).group_by(PrayerMark.prayer_id)
        user_marks_results = s.exec(user_marks_stmt).all()
        user_mark_counts = {prayer_id: count for prayer_id, count in user_marks_results}
        
        # Get mark counts for all prayers (total times prayed)
        mark_counts_stmt = select(PrayerMark.prayer_id, func.count(PrayerMark.id)).group_by(PrayerMark.prayer_id)
        mark_counts_results = s.exec(mark_counts_stmt).all()
        mark_counts = {prayer_id: count for prayer_id, count in mark_counts_results}
        
        # Get distinct user counts for all prayers (how many people prayed)
        distinct_user_counts_stmt = select(PrayerMark.prayer_id, func.count(func.distinct(PrayerMark.user_id))).group_by(PrayerMark.prayer_id)
        distinct_user_counts_results = s.exec(distinct_user_counts_stmt).all()
        distinct_user_counts = {prayer_id: count for prayer_id, count in distinct_user_counts_results}
        
        # Create a list of prayers with author names and mark data
        for result in results:
            if len(result) == 3:  # most_prayed query includes mark_count
                prayer, author_name, _ = result
            else:
                prayer, author_name = result
                
            prayer_dict = {
                'id': prayer.id,
                'author_id': prayer.author_id,
                'text': prayer.text,
                'generated_prayer': prayer.generated_prayer,
                'project_tag': prayer.project_tag,
                'created_at': prayer.created_at,
                'flagged': prayer.flagged,
                'target_audience': prayer.target_audience,
                'author_name': author_name,
                'marked_by_user': user_mark_counts.get(prayer.id, 0),
                'mark_count': mark_counts.get(prayer.id, 0),
                'distinct_user_count': distinct_user_counts.get(prayer.id, 0),
                'is_archived': prayer.is_archived(s),
                'is_answered': prayer.is_answered(s),
                'answer_date': prayer.answer_date(s),
                'answer_testimony': prayer.answer_testimony(s)
            }
            prayers_with_authors.append(prayer_dict)
    
    # Get feed counts
    feed_counts = get_feed_counts(user.id)
    
    return templates.TemplateResponse(
        "feed.html",
        {"request": request, "prayers": prayers_with_authors, "prompt": todays_prompt(), 
         "me": user, "session": session, "current_feed": feed_type, "feed_counts": feed_counts}
    )


@router.post("/prayers")
def submit_prayer(text: str = Form(...),
                  tag: Optional[str] = Form(None),
                  target_audience: str = Form("all"),
                  user_session: tuple = Depends(current_user)):
    """
    Submit a new prayer request.
    
    Args:
        text: The prayer request text (max 500 chars)
        tag: Optional project tag for categorization
        target_audience: Target audience ("all" or "christians_only")
        user_session: Current authenticated user session
    
    Returns:
        Redirect to main feed after successful submission
    """
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required to submit prayers")
    
    # Validate target audience
    valid_audiences = ["all", "christians_only"]
    if target_audience not in valid_audiences:
        target_audience = "all"
    
    # Generate a proper prayer from the user's prompt
    generated_prayer = generate_prayer(text)
    
    with Session(engine) as s:
        prayer = Prayer(
            author_id=user.id, 
            text=text[:500], 
            generated_prayer=generated_prayer,
            project_tag=tag,
            target_audience=target_audience,
        )
        s.add(prayer)
        s.commit()
        
        # Try to find a compatible prayer partner immediately
        compatible_user = find_compatible_prayer_partner(prayer, s)
        if compatible_user:
            # Assign prayer to compatible user
            mark = PrayerMark(user_id=compatible_user.id, prayer_id=prayer.id)
            s.add(mark)
            s.commit()
            print(f"Prayer {prayer.id} assigned to compatible user {compatible_user.id}")
    
    return RedirectResponse("/", 303)


@router.post("/flag/{pid}")
def flag_prayer(pid: str, request: Request, user_session: tuple = Depends(current_user)):
    """
    Flag or unflag a prayer for moderation.
    
    Only admins can unflag content. Regular users can only flag content.
    Supports HTMX requests for dynamic UI updates.
    
    Args:
        pid: Prayer ID to flag/unflag
        request: FastAPI request object
        user_session: Current authenticated user session
    
    Returns:
        For HTMX: HTML response with updated prayer view
        For regular: Redirect to appropriate page
    """
    user, session = user_session
    with Session(engine) as s:
        p = s.get(Prayer, pid)
        if not p:
            raise HTTPException(404)
        
        # Only allow unflagging if user is admin
        if p.flagged and not is_admin(user):
            raise HTTPException(403, "Only admins can unflag content")
            
        p.flagged = not p.flagged
        s.add(p); s.commit()
        
        # If this is an HTMX request, return appropriate content
        if request.headers.get("HX-Request"):
            # Check if this is coming from admin panel by looking at the referer
            referer = request.headers.get("referer", "")
            is_admin_panel = "/admin" in referer
            
            if p.flagged:
                # Return shielded version when flagging
                return HTMLResponse(templates.get_template("flagged_prayer.html").render(
                    prayer=p, is_admin=is_admin(user)
                ))
            else:
                # When unflagging (admin only)
                if is_admin_panel:
                    # If unflagging from admin panel, just remove the item
                    return HTMLResponse("")
                else:
                    # If unflagging from main feed, restore the full prayer view
                    # Get author name and prayer marks
                    author = s.get(User, p.author_id)
                    author_name = author.display_name if author else "Unknown"
                    
                    # Get mark counts
                    mark_count_stmt = select(func.count(PrayerMark.id)).where(PrayerMark.prayer_id == p.id)
                    total_mark_count = s.exec(mark_count_stmt).first() or 0
                    
                    distinct_user_count_stmt = select(func.count(func.distinct(PrayerMark.user_id))).where(PrayerMark.prayer_id == p.id)
                    distinct_user_count = s.exec(distinct_user_count_stmt).first() or 0
                    
                    user_mark_count_stmt = select(func.count(PrayerMark.id)).where(
                        PrayerMark.prayer_id == p.id,
                        PrayerMark.user_id == user.id
                    )
                    user_mark_count = s.exec(user_mark_count_stmt).first() or 0
                    
                    # Build prayer stats display
                    prayer_stats = ""
                    if total_mark_count > 0:
                        if distinct_user_count == 1:
                            if total_mark_count == 1:
                                prayer_stats = f'<a href="/prayer/{p.id}/marks" class="text-purple-600 dark:text-purple-300 hover:text-purple-800 dark:hover:text-purple-200 hover:underline">🙏 1 person prayed this once</a>'
                            else:
                                prayer_stats = f'<a href="/prayer/{p.id}/marks" class="text-purple-600 dark:text-purple-300 hover:text-purple-800 dark:hover:text-purple-200 hover:underline">🙏 1 person prayed this {total_mark_count} times</a>'
                        else:
                            prayer_stats = f'<a href="/prayer/{p.id}/marks" class="text-purple-600 dark:text-purple-300 hover:text-purple-800 dark:hover:text-purple-200 hover:underline">🙏 {distinct_user_count} people prayed this {total_mark_count} times</a>'
                    
                    user_mark_text = ""
                    if user_mark_count > 0:
                        if user_mark_count == 1:
                            user_mark_text = f'<span class="text-green-600 dark:text-green-400 text-xs bg-green-100 dark:bg-green-900 px-2 py-1 rounded border border-green-300 dark:border-green-600">✓ You prayed this</span>'
                        else:
                            user_mark_text = f'<span class="text-green-600 dark:text-green-400 text-xs bg-green-100 dark:bg-green-900 px-2 py-1 rounded border border-green-300 dark:border-green-600">✓ You prayed this {user_mark_count} times</span>'
                    
                    return HTMLResponse(templates.get_template("unflagged_prayer.html").render(
                        prayer=p, user=user, author_name=author_name, 
                        prayer_stats=prayer_stats, user_mark_text=user_mark_text
                    ))
            
    # For non-HTMX requests, redirect appropriately
    if p.flagged:
        return RedirectResponse("/", 303)  # Back to main feed when flagging
    else:
        return RedirectResponse("/admin", 303)  # Back to admin when unflagging


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
        
        # Add a new prayer mark
        mark = PrayerMark(user_id=user.id, prayer_id=prayer_id)
        s.add(mark)
        s.commit()
        
        # If this is an HTMX request, return just the updated prayer mark section
        if request.headers.get("HX-Request"):
            # Get updated mark count for all users (total times)
            mark_count_stmt = select(func.count(PrayerMark.id)).where(PrayerMark.prayer_id == prayer_id)
            total_mark_count = s.exec(mark_count_stmt).first()
            
            # Get updated distinct user count (how many people)
            distinct_user_count_stmt = select(func.count(func.distinct(PrayerMark.user_id))).where(PrayerMark.prayer_id == prayer_id)
            distinct_user_count = s.exec(distinct_user_count_stmt).first()
            
            # Get updated mark count for current user
            user_mark_count_stmt = select(func.count(PrayerMark.id)).where(
                PrayerMark.prayer_id == prayer_id,
                PrayerMark.user_id == user.id
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
                prayer_id=prayer_id, prayer_stats=prayer_stats, user_mark_count=user_mark_count
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
        if prayer.author_id != user.id and not is_admin(user):
            raise HTTPException(403, "Only prayer author or admin can archive this prayer")
        
        # Set archived attribute
        prayer.set_attribute('archived', 'true', user.id, s)
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
        if prayer.author_id != user.id and not is_admin(user):
            raise HTTPException(403, "Only prayer author or admin can restore this prayer")
        
        # Remove archived attribute
        prayer.remove_attribute('archived', s, user.id)
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
        if prayer.author_id != user.id and not is_admin(user):
            raise HTTPException(403, "Only prayer author or admin can mark this prayer as answered")
        
        # Set answered attribute with current date
        from datetime import datetime
        answer_date = datetime.utcnow().isoformat()
        prayer.set_attribute('answered', 'true', user.id, s)
        prayer.set_attribute('answer_date', answer_date, user.id, s)
        
        # Add testimony if provided
        if testimony and testimony.strip():
            prayer.set_attribute('answer_testimony', testimony.strip(), user.id, s)
        
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


@router.get("/prayer/{prayer_id}/marks", response_class=HTMLResponse)
def prayer_marks(prayer_id: str, request: Request, user_session: tuple = Depends(current_user)):
    """
    Display all prayer marks (who prayed) for a specific prayer.
    
    Shows chronological list of all users who prayed for this prayer
    with timestamps and user identification.
    
    Args:
        prayer_id: ID of prayer to show marks for
        request: FastAPI request object
        user_session: Current authenticated user session
    
    Returns:
        HTML page showing prayer marks with statistics
    """
    user, session = user_session
    with Session(engine) as s:
        # Get the prayer
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            raise HTTPException(404, "Prayer not found")
        
        # Get all marks for this prayer with user info
        stmt = (
            select(PrayerMark, User.display_name)
            .join(User, PrayerMark.user_id == User.id)
            .where(PrayerMark.prayer_id == prayer_id)
            .order_by(PrayerMark.created_at.desc())
        )
        marks_results = s.exec(stmt).all()
        
        marks_with_users = []
        for mark, user_name in marks_results:
            marks_with_users.append({
                'user_name': user_name,
                'user_id': mark.user_id,
                'created_at': mark.created_at,
                'is_me': mark.user_id == user.id
            })
        
        # Calculate statistics
        total_marks = len(marks_with_users)
        distinct_users = len(set(mark['user_name'] for mark in marks_with_users))
    
    return templates.TemplateResponse(
        "prayer_marks.html",
        {"request": request, "prayer": prayer, "marks": marks_with_users, "me": user, 
         "session": session, "total_marks": total_marks, "distinct_users": distinct_users}
    )


@router.get("/answered", response_class=HTMLResponse)
def answered_celebration(request: Request, user_session: tuple = Depends(current_user)):
    """
    Display celebration feed showing recently answered prayers.
    
    Shows statistics about answered prayers and testimonies to celebrate
    God's faithfulness and encourage the community.
    
    Args:
        request: FastAPI request object
        user_session: Current authenticated user session
    
    Returns:
        HTML page showing answered prayers celebration feed with statistics
    """
    user, session = user_session
    
    with Session(engine) as s:
        # Get recent answered prayers (last 10)
        recent_stmt = (
            select(Prayer, User.display_name)
            .join(User, Prayer.author_id == User.id)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerAttribute.attribute_name == 'answered')
            .order_by(Prayer.created_at.desc())
            .limit(10)
        )
        recent_results = s.exec(recent_stmt).all()
        
        # Get prayer marks for answered prayers
        answered_prayer_ids = [prayer.id for prayer, _ in recent_results]
        mark_counts_stmt = select(PrayerMark.prayer_id, func.count(PrayerMark.id)).where(
            PrayerMark.prayer_id.in_(answered_prayer_ids)
        ).group_by(PrayerMark.prayer_id)
        mark_counts_results = s.exec(mark_counts_stmt).all()
        mark_counts = {prayer_id: count for prayer_id, count in mark_counts_results}
        
        distinct_user_counts_stmt = select(PrayerMark.prayer_id, func.count(func.distinct(PrayerMark.user_id))).where(
            PrayerMark.prayer_id.in_(answered_prayer_ids)
        ).group_by(PrayerMark.prayer_id)
        distinct_user_counts_results = s.exec(distinct_user_counts_stmt).all()
        distinct_user_counts = {prayer_id: count for prayer_id, count in distinct_user_counts_results}
        
        # Build recent answered prayers list
        recent_answered = []
        for prayer, author_name in recent_results:
            prayer_dict = {
                'id': prayer.id,
                'text': prayer.text,
                'generated_prayer': prayer.generated_prayer,
                'created_at': prayer.created_at,
                'author_name': author_name,
                'mark_count': mark_counts.get(prayer.id, 0),
                'distinct_user_count': distinct_user_counts.get(prayer.id, 0),
                'answer_date': prayer.answer_date(s),
                'answer_testimony': prayer.answer_testimony(s)
            }
            recent_answered.append(prayer_dict)
        
        # Calculate statistics
        total_answered = s.exec(
            select(func.count(func.distinct(Prayer.id)))
            .select_from(Prayer)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerAttribute.attribute_name == 'answered')
        ).first()
        
        total_testimonies = s.exec(
            select(func.count(func.distinct(Prayer.id)))
            .select_from(Prayer)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerAttribute.attribute_name == 'answer_testimony')
        ).first()
        
        # Recent answered this month
        from datetime import datetime, timedelta
        month_ago = datetime.utcnow() - timedelta(days=30)
        recent_count = s.exec(
            select(func.count(func.distinct(Prayer.id)))
            .select_from(Prayer)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerAttribute.attribute_name == 'answered')
            .where(PrayerAttribute.created_at >= month_ago)
        ).first()
        
        # Community prayer statistics
        community_prayers = s.exec(select(func.count(PrayerMark.id))).first()
        total_prayers = s.exec(select(func.count(Prayer.id)).where(Prayer.flagged == False)).first()
        answered_percentage = round((total_answered / total_prayers * 100)) if total_prayers > 0 else 0
        
        avg_prayer_marks = round(community_prayers / total_prayers) if total_prayers > 0 else 0
    
    return templates.TemplateResponse(
        "answered_celebration.html",
        {
            "request": request, 
            "me": user, 
            "session": session,
            "recent_answered": recent_answered,
            "total_answered": total_answered,
            "total_testimonies": total_testimonies,
            "recent_count": recent_count,
            "community_prayers": community_prayers,
            "answered_percentage": answered_percentage,
            "avg_prayer_marks": avg_prayer_marks
        }
    )


@router.get("/activity", response_class=HTMLResponse)
def recent_activity(request: Request, user_session: tuple = Depends(current_user)):
    """
    Display recent prayer activity feed.
    
    Shows chronological list of recent prayer marks across the community
    to encourage prayer participation and show community engagement.
    
    Args:
        request: FastAPI request object
        user_session: Current authenticated user session
    
    Returns:
        HTML page showing recent prayer activity feed
    """
    user, session = user_session
    with Session(engine) as s:
        # Get recent prayer marks with prayer and user info
        recent_marks_stmt = (
            select(PrayerMark)
            .join(Prayer, PrayerMark.prayer_id == Prayer.id)
            .where(Prayer.flagged == False)
            .order_by(PrayerMark.created_at.desc())
            .limit(100)
        )
        recent_marks = s.exec(recent_marks_stmt).all()
        
        activity_items = []
        for mark in recent_marks:
            # Get prayer info
            prayer = s.get(Prayer, mark.prayer_id)
            # Get marker name
            marker = s.get(User, mark.user_id)
            # Get author name
            author = s.get(User, prayer.author_id)
            
            activity_items.append({
                'mark': mark,
                'prayer': prayer,
                'marker_name': marker.display_name,
                'author_name': author.display_name,
                'is_my_mark': mark.user_id == user.id,
                'is_my_prayer': prayer.author_id == user.id
            })
    
    return templates.TemplateResponse(
        "activity.html",
        {"request": request, "activity_items": activity_items, "me": user, "session": session}
    )