# app_helpers/routes/prayer/prayer_crud.py
"""
Prayer CRUD operations.

Contains Create, Read, Update, Delete operations for prayers.
Extracted from prayer_routes.py for better maintainability.
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func

from models import (
    engine, User, Prayer, PrayerMark, PrayerAttribute
)

# Import helper functions
from app_helpers.services.auth_helpers import current_user
from app_helpers.services.prayer_helpers import generate_prayer, find_compatible_prayer_partner
from app_helpers.services.archive_first_service import submit_prayer_archive_first

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Create router for CRUD operations
router = APIRouter()


@router.post("/prayers/preview")
def preview_prayer(text: str = Form(...),
                   tag: Optional[str] = Form(None),
                   user_session: tuple = Depends(current_user)):
    """
    Generate prayer preview without saving to database.
    
    Args:
        text: The prayer request text (max 500 chars)
        tag: Optional project tag for categorization
        user_session: Current authenticated user session
    
    Returns:
        JSON response with preview data
    """
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required to preview prayers")
    
    # Generate a proper prayer from the user's prompt
    prayer_result = generate_prayer(text)
    
    # Generate preview token for security
    import secrets
    preview_token = secrets.token_urlsafe(32)
    
    return {
        "original_text": text,
        "generated_prayer": prayer_result['prayer'],
        "service_status": prayer_result['service_status'],
        "tag": tag,
        "preview_token": preview_token
    }


@router.post("/prayers")
def submit_prayer(text: str = Form(...),
                  tag: Optional[str] = Form(None),
                  generated_prayer: Optional[str] = Form(None),
                  user_session: tuple = Depends(current_user)):
    """
    Submit a new prayer request.
    
    Args:
        text: The prayer request text (max 500 chars)
        tag: Optional project tag for categorization
        generated_prayer: Pre-generated prayer from preview (optional)
        user_session: Current authenticated user session
    
    Returns:
        Redirect to main feed after successful submission
    """
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required to submit prayers")
    
    # Use pre-generated prayer if provided, otherwise generate new one
    if generated_prayer:
        final_prayer = generated_prayer
    else:
        prayer_result = generate_prayer(text)
        final_prayer = prayer_result['prayer']
    
    # Use archive-first approach: write text file FIRST, then database
    prayer = submit_prayer_archive_first(
        text=text,
        author=user,
        tag=tag,
        generated_prayer=final_prayer
    )
    
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
            .outerjoin(User, PrayerMark.username == User.display_name)
            .where(PrayerMark.prayer_id == prayer_id)
            .order_by(PrayerMark.created_at.desc())
        )
        marks_results = s.exec(stmt).all()
        
        marks_with_users = []
        for mark, user_name in marks_results:
            marks_with_users.append({
                'user_name': user_name,
                'user_id': mark.username,
                'created_at': mark.created_at,
                'is_me': mark.username == user.display_name
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
            .outerjoin(User, Prayer.author_username == User.display_name)
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
        
        distinct_user_counts_stmt = select(PrayerMark.prayer_id, func.count(func.distinct(PrayerMark.username))).where(
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
            marker = s.get(User, mark.username)
            # Get author name
            author = s.get(User, prayer.author_username)
            
            activity_items.append({
                'mark': mark,
                'prayer': prayer,
                'marker_name': marker.display_name if marker else None,
                'author_name': author.display_name if author else None,
                'is_my_mark': mark.username == user.display_name,
                'is_my_prayer': prayer.author_username == user.display_name
            })
    
    return templates.TemplateResponse(
        "activity.html",
        {"request": request, "activity_items": activity_items, "me": user, "session": session}
    )