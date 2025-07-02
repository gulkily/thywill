# app_helpers/routes/prayer/feed_operations.py
"""
Prayer feed display and filtering operations.

Contains the main feed functionality with various filtering options.
Extracted from prayer_routes.py for better maintainability.
"""

from typing import Optional
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func

from models import (
    engine, User, Prayer, PrayerMark, PrayerAttribute
)

# Import helper functions
from app_helpers.services.auth_helpers import current_user
from app_helpers.services.prayer_helpers import get_feed_counts, todays_prompt
from app_helpers.services.auth.validation_helpers import is_admin
from app import PRAYER_MODE_ENABLED

# Initialize templates
templates = Jinja2Templates(directory="templates")

# Create router for feed operations
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
        
        
        if feed_type == "new_unprayed":
            # New prayers and prayers that have never been prayed (exclude archived)
            stmt = (
                select(Prayer, User.display_name)
                .outerjoin(User, Prayer.author_username == User.display_name)
                .outerjoin(PrayerMark, Prayer.id == PrayerMark.prayer_id)
                .where(Prayer.flagged == False)
                .where(exclude_archived())
                .group_by(Prayer.id)
                .having(func.count(PrayerMark.id) == 0)
                .order_by(Prayer.created_at.desc())
            )
        elif feed_type == "most_prayed":
            # Most prayed prayers (by total prayer count, exclude archived)
            stmt = (
                select(Prayer, User.display_name, func.count(PrayerMark.id).label('mark_count'))
                .outerjoin(User, Prayer.author_username == User.display_name)
                .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
                .where(Prayer.flagged == False)
                .where(exclude_archived())
                .group_by(Prayer.id)
                .order_by(func.count(PrayerMark.id).desc())
                .limit(50)
            )
        elif feed_type == "my_prayers":
            # Prayers the current user has marked as prayed (include all statuses)
            stmt = (
                select(Prayer, User.display_name)
                .outerjoin(User, Prayer.author_username == User.display_name)
                .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
                .where(Prayer.flagged == False)
                .where(PrayerMark.username == user.display_name)
                .group_by(Prayer.id)
                .order_by(func.max(PrayerMark.created_at).desc())
            )
        elif feed_type == "my_requests":
            # Prayer requests submitted by the current user (include all statuses)
            stmt = (
                select(Prayer, User.display_name)
                .outerjoin(User, Prayer.author_username == User.display_name)
                .where(Prayer.flagged == False)
                .where(Prayer.author_username == user.display_name)
                .order_by(Prayer.created_at.desc())
            )
        elif feed_type == "recent_activity":
            # Prayers with recent prayer marks (most recently prayed, exclude archived)
            stmt = (
                select(Prayer, User.display_name)
                .outerjoin(User, Prayer.author_username == User.display_name)
                .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
                .where(Prayer.flagged == False)
                .where(exclude_archived())
                .group_by(Prayer.id)
                .order_by(func.max(PrayerMark.created_at).desc())
                .limit(50)
            )
        elif feed_type == "answered":
            # Answered prayers (public celebration feed)
            stmt = (
                select(Prayer, User.display_name)
                .outerjoin(User, Prayer.author_username == User.display_name)
                .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
                .where(Prayer.flagged == False)
                .where(PrayerAttribute.attribute_name == 'answered')
                .order_by(Prayer.created_at.desc())
            )
        elif feed_type == "archived":
            # Archived prayers (personal feed for prayer authors only)
            stmt = (
                select(Prayer, User.display_name)
                .outerjoin(User, Prayer.author_username == User.display_name)
                .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
                .where(Prayer.flagged == False)
                .where(Prayer.author_username == user.display_name)  # Only user's own prayers
                .where(PrayerAttribute.attribute_name == 'archived')
                .order_by(Prayer.created_at.desc())
            )
        else:  # "all" or default
            # All prayers (exclude archived)
            stmt = (
                select(Prayer, User.display_name)
                .outerjoin(User, Prayer.author_username == User.display_name)
                .where(Prayer.flagged == False)
                .where(exclude_archived())
                .order_by(Prayer.created_at.desc())
            )
            
        results = s.exec(stmt).all()
        
        # Get all prayer marks for the current user
        user_marks_stmt = select(PrayerMark.prayer_id, func.count(PrayerMark.id)).where(PrayerMark.username == user.display_name).group_by(PrayerMark.prayer_id)
        user_marks_results = s.exec(user_marks_stmt).all()
        user_mark_counts = {prayer_id: count for prayer_id, count in user_marks_results}
        
        # Get mark counts for all prayers (total times prayed)
        mark_counts_stmt = select(PrayerMark.prayer_id, func.count(PrayerMark.id)).group_by(PrayerMark.prayer_id)
        mark_counts_results = s.exec(mark_counts_stmt).all()
        mark_counts = {prayer_id: count for prayer_id, count in mark_counts_results}
        
        # Get distinct user counts for all prayers (how many people prayed)
        distinct_user_counts_stmt = select(PrayerMark.prayer_id, func.count(func.distinct(PrayerMark.username))).group_by(PrayerMark.prayer_id)
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
                'author_id': prayer.author_username,
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
    feed_counts = get_feed_counts(user.display_name)
    
    return templates.TemplateResponse(
        "feed.html",
        {"request": request, "prayers": prayers_with_authors, "prompt": todays_prompt(), 
         "me": user, "session": session, "current_feed": feed_type, "feed_counts": feed_counts,
         "PRAYER_MODE_ENABLED": PRAYER_MODE_ENABLED, "is_admin": is_admin(user)}
    )