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
    engine, User, Prayer, PrayerMark, PrayerAttribute
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


def initialize_prayer_queue(session: Session, user: User, feed_type: str, mode: str = "standard") -> List[int]:
    """Initialize prayer queue based on feed type and mode."""
    
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
    
    # Build query based on feed type - but include all prayers regardless of user's prayer history
    if feed_type == "new_unprayed":
        # In prayer mode, show all prayers but prioritize truly unprayed ones first
        stmt = (
            select(Prayer)
            .outerjoin(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.flagged == False)
            .where(exclude_archived())
            .where(apply_religious_filter())
            .group_by(Prayer.id)
            .order_by(func.count(PrayerMark.id).asc(), Prayer.created_at.desc())
        )
    elif feed_type == "most_prayed":
        # Show all prayers ordered by prayer count (most prayed first)
        stmt = (
            select(Prayer)
            .outerjoin(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.flagged == False)
            .where(exclude_archived())
            .where(apply_religious_filter())
            .group_by(Prayer.id)
            .order_by(func.count(PrayerMark.id).desc(), Prayer.created_at.desc())
        )
    else:
        # Default to new_unprayed approach
        stmt = (
            select(Prayer)
            .outerjoin(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.flagged == False)
            .where(exclude_archived())
            .where(apply_religious_filter())
            .group_by(Prayer.id)
            .order_by(func.count(PrayerMark.id).asc(), Prayer.created_at.desc())
        )
    
    # Apply mode-specific limits
    if mode == "quick":
        stmt = stmt.limit(10)
    else:
        stmt = stmt.limit(25)
    
    # Execute query and extract prayer IDs
    prayer_results = session.exec(stmt).all()
    return [prayer.id for prayer in prayer_results]


@router.get("/prayer-mode", response_class=HTMLResponse)
@router.get("/prayer-mode/{feed_type}", response_class=HTMLResponse)
def prayer_mode(
    request: Request, 
    feed_type: str = "new_unprayed",
    mode: str = "standard",
    position: int = 0,
    user_session: tuple = Depends(current_user)
):
    """
    Initialize prayer mode session.
    
    Args:
        feed_type: Type of prayers to include (new_unprayed, most_prayed, etc.)
        mode: Prayer mode variant (standard, quick)
        position: Current position in prayer queue (for navigation)
    """
    user, _ = user_session
    
    with Session(engine) as s:
        # Initialize prayer queue
        prayer_queue = initialize_prayer_queue(s, user, feed_type, mode)
        
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
            "mode": mode,
            "feed_type": feed_type,
            "prayer_queue": prayer_queue,
            "position": position
        })


@router.get("/api/prayer-mode/next")
def next_prayer(
    feed_type: str = "new_unprayed",
    mode: str = "standard", 
    position: int = 0,
    user_session: tuple = Depends(current_user)
):
    """Get next prayer in prayer mode queue."""
    user, _ = user_session
    
    with Session(engine) as s:
        # Get prayer queue
        prayer_queue = initialize_prayer_queue(s, user, feed_type, mode)
        
        if not prayer_queue:
            return JSONResponse({
                "status": "error",
                "message": "No prayers available"
            })
        
        # Calculate next position
        next_position = position + 1
        
        if next_position >= len(prayer_queue):
            # End of queue
            return JSONResponse({
                "status": "completed",
                "message": "Prayer session completed!",
                "prayers_completed": len(prayer_queue)
            })
        
        # Get next prayer
        next_prayer_id = prayer_queue[next_position]
        prayer = s.get(Prayer, next_prayer_id)
        
        if not prayer:
            raise HTTPException(status_code=404, detail="Prayer not found")
        
        # Check if user has already prayed this prayer
        user_has_prayed = False
        if user:
            existing_mark = s.exec(
                select(PrayerMark).where(
                    PrayerMark.user_id == user.id,
                    PrayerMark.prayer_id == prayer.id
                )
            ).first()
            user_has_prayed = existing_mark is not None
        
        # Get prayer stats
        prayer_count = s.exec(
            select(func.count(PrayerMark.id)).where(PrayerMark.prayer_id == prayer.id)
        ).one()
        
        distinct_users = s.exec(
            select(func.count(func.distinct(PrayerMark.user_id))).where(PrayerMark.prayer_id == prayer.id)
        ).one()
        
        # Generate prayer age text
        prayer_age = get_prayer_age_text(prayer.created_at)
        
        return JSONResponse({
            "status": "success",
            "prayer": {
                "id": prayer.id,
                "text": prayer.text,
                "generated_prayer": prayer.generated_prayer,
                "author_first_name": prayer.author.first_name if prayer.author else "Anonymous",
                "prayer_age": prayer_age,
                "prayer_count": prayer_count,
                "distinct_users": distinct_users,
                "user_has_prayed": user_has_prayed
            },
            "position": {
                "current": next_position + 1,
                "total": len(prayer_queue)
            },
            "navigation": {
                "next_url": f"/prayer-mode/{feed_type}?mode={mode}&position={next_position}"
            }
        })