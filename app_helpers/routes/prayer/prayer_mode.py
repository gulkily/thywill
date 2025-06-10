# app_helpers/routes/prayer/prayer_mode.py
"""
Prayer mode operations for full-screen, distraction-free prayer experience.

Provides endpoints for:
- Prayer mode initialization and session management
- Next prayer navigation
- Quick prayer mode variants
- Session state persistence
"""

import json
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func, desc

from models import (
    engine, User, Prayer, PrayerMark, PrayerSkip, PrayerAttribute
)

# Import helper functions
from app_helpers.services.auth_helpers import current_user
from app_helpers.services.prayer_helpers import get_filtered_prayers_for_user

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Create router for prayer mode operations
router = APIRouter()


def get_prayer_age_text(prayer_created_at: datetime) -> str:
    """Generate human-readable prayer age text."""
    now = datetime.utcnow()
    diff = now - prayer_created_at
    
    if diff.days == 0:
        if diff.seconds < 3600:  # Less than 1 hour
            minutes = diff.seconds // 60
            if minutes < 1:
                return "Just now"
            elif minutes == 1:
                return "1 minute ago"
            else:
                return f"{minutes} minutes ago"
        else:  # Less than 24 hours
            hours = diff.seconds // 3600
            if hours == 1:
                return "1 hour ago"
            else:
                return f"{hours} hours ago"
    elif diff.days == 1:
        return "1 day ago"
    elif diff.days < 30:
        return f"{diff.days} days ago"
    elif diff.days < 365:
        months = diff.days // 30
        if months == 1:
            return "1 month ago"
        else:
            return f"{months} months ago"
    else:
        years = diff.days // 365
        if years == 1:
            return "1 year ago"
        else:
            return f"{years} years ago"


def initialize_prayer_queue(session: Session, user: User, feed_type: str = "new_unprayed") -> List[str]:
    """Initialize prayer queue with smart sorting based on user's prayer and skip history."""
    
    # Base filter to exclude archived prayers for public feeds
    def exclude_archived():
        return ~Prayer.id.in_(
            select(PrayerAttribute.prayer_id)
            .where(PrayerAttribute.attribute_name == 'archived')
        )
    
    # Religious preference filtering
    def apply_religious_filter():
        if user.religious_preference == "christian":
            return Prayer.target_audience.in_(["all", "christians_only"])
        else:
            return Prayer.target_audience == "all"
    
    # Get all eligible prayers
    base_stmt = (
        select(Prayer)
        .where(Prayer.flagged == False)
        .where(exclude_archived())
        .where(apply_religious_filter())
    )
    
    prayers = session.exec(base_stmt).all()
    
    # Calculate sorting scores for each prayer
    prayer_scores = []
    
    for prayer in prayers:
        score = 0
        
        # Base score: newer prayers get higher score
        days_old = (datetime.utcnow() - prayer.created_at).days
        score += max(0, 30 - days_old)  # Up to 30 points for newness
        
        # Global prayer count: less prayed prayers get higher score
        global_prayer_count = session.exec(
            select(func.count(PrayerMark.id)).where(PrayerMark.prayer_id == prayer.id)
        ).one()
        score += max(0, 20 - global_prayer_count)  # Up to 20 points for being less prayed
        
        # User's prayer history: recently prayed prayers get lower score
        user_prayer_marks = session.exec(
            select(PrayerMark).where(
                PrayerMark.prayer_id == prayer.id,
                PrayerMark.user_id == user.id
            ).order_by(PrayerMark.created_at.desc())
        ).all()
        
        if user_prayer_marks:
            # Most recent prayer mark
            latest_mark = user_prayer_marks[0]
            days_since_prayed = (datetime.utcnow() - latest_mark.created_at).days
            
            # Penalty for recently prayed prayers
            if days_since_prayed < 1:
                score -= 50  # Heavy penalty for same day
            elif days_since_prayed < 3:
                score -= 30  # Medium penalty for recent
            elif days_since_prayed < 7:
                score -= 15  # Light penalty for this week
            
            # Additional penalty for multiple prayer marks
            score -= min(10, len(user_prayer_marks) * 2)
        
        # User's skip history: recently skipped prayers get lower score
        user_skips = session.exec(
            select(PrayerSkip).where(
                PrayerSkip.prayer_id == prayer.id,
                PrayerSkip.user_id == user.id
            ).order_by(PrayerSkip.created_at.desc())
        ).all()
        
        if user_skips:
            latest_skip = user_skips[0]
            days_since_skipped = (datetime.utcnow() - latest_skip.created_at).days
            
            # Penalty for recently skipped prayers
            if days_since_skipped < 1:
                score -= 25  # Penalty for same day skip
            elif days_since_skipped < 3:
                score -= 15  # Medium penalty for recent skip
            elif days_since_skipped < 7:
                score -= 8   # Light penalty for this week
            
            # Additional penalty for multiple skips
            score -= min(8, len(user_skips) * 1)
        
        prayer_scores.append((prayer.id, score))
    
    # Sort by score (highest first) and take top 10 for quick mode
    prayer_scores.sort(key=lambda x: x[1], reverse=True)
    return [prayer_id for prayer_id, score in prayer_scores[:10]]


@router.get("/prayer-mode", response_class=HTMLResponse)
def prayer_mode(
    request: Request, 
    position: int = 0,
    user_session: tuple = Depends(current_user)
):
    """
    Initialize prayer mode session with smart sorting.
    
    Args:
        position: Current position in prayer queue (for navigation)
    """
    user, _ = user_session
    
    with Session(engine) as s:
        # Initialize prayer queue with smart sorting
        prayer_queue = initialize_prayer_queue(s, user)
        
        if not prayer_queue:
            # No prayers available, redirect to feed
            return templates.TemplateResponse("error.html", {
                "request": request,
                "error_message": "No prayers available for prayer mode",
                "user": user
            })
        
        # Validate position
        if position < 0 or position >= len(prayer_queue):
            position = 0
        
        # Get current prayer
        current_prayer = s.get(Prayer, prayer_queue[position])
        if not current_prayer:
            raise HTTPException(status_code=404, detail="Prayer not found")
        
        # Check if user has already prayed this prayer
        user_has_prayed = False
        if user:
            existing_mark = s.exec(
                select(PrayerMark).where(
                    PrayerMark.user_id == user.id,
                    PrayerMark.prayer_id == current_prayer.id
                )
            ).first()
            user_has_prayed = existing_mark is not None
        
        # Get prayer stats
        prayer_count = s.exec(
            select(func.count(PrayerMark.id)).where(PrayerMark.prayer_id == current_prayer.id)
        ).one()
        
        distinct_users = s.exec(
            select(func.count(func.distinct(PrayerMark.user_id))).where(PrayerMark.prayer_id == current_prayer.id)
        ).one()
        
        # Generate prayer age text
        prayer_age = get_prayer_age_text(current_prayer.created_at)
        
        return templates.TemplateResponse("prayer_mode.html", {
            "request": request,
            "user": user,
            "prayer": current_prayer,
            "prayer_age": prayer_age,
            "current_position": position + 1,
            "total_prayers": len(prayer_queue),
            "user_has_prayed": user_has_prayed,
            "prayer_count": prayer_count,
            "distinct_users": distinct_users,
            "prayer_queue": prayer_queue,
            "position": position
        })




@router.post("/api/prayer-mode/skip/{prayer_id}")
def skip_prayer(prayer_id: str, user_session: tuple = Depends(current_user)):
    """Record that user skipped a prayer."""
    user, _ = user_session
    
    with Session(engine) as s:
        # Check if skip already exists for this user and prayer
        existing_skip = s.exec(
            select(PrayerSkip).where(
                PrayerSkip.user_id == user.id,
                PrayerSkip.prayer_id == prayer_id
            )
        ).first()
        
        # Add skip record (allow multiple skips)
        if not existing_skip:
            skip_record = PrayerSkip(
                user_id=user.id,
                prayer_id=prayer_id
            )
            s.add(skip_record)
            s.commit()
        
        return JSONResponse({"status": "skipped"})