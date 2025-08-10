# app_helpers/routes/prayer/feed_operations.py
"""
Prayer feed display and filtering operations.

Contains the main feed functionality with various filtering options.
Extracted from prayer_routes.py for better maintainability.
"""

import os
from datetime import date, datetime
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
from app_helpers.services.prayer_helpers import get_feed_counts, todays_prompt, is_daily_priority
from app_helpers.services.auth.validation_helpers import is_admin
from app_helpers.timezone_utils import get_user_timezone_from_request
# Note: Avoiding imports from app.py to prevent circular imports
# Using os.getenv directly for feature flags

# Use shared templates instance with filters registered
from app_helpers.shared_templates import templates

# Create router for feed operations
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def feed(request: Request, feed_type: str = "all", category: Optional[str] = None, 
         min_safety: Optional[float] = None, user_session: tuple = Depends(current_user)):
    """
    Main feed displaying prayers with various filtering options.
    
    Feed types:
    - all: All non-archived prayers (default)
    - new_unprayed: Prayers that have never been prayed
    - most_prayed: Most prayed prayers by total count
    - my_prayers: Prayers the current user has marked as prayed
    - my_unprayed: Prayers the current user has not prayed yet
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
        
        # Categorization filters
        def apply_category_filters(stmt):
            """Apply category and safety filters to a statement"""
            # Only apply filters if categorization is enabled
            if not os.getenv('PRAYER_CATEGORIZATION_ENABLED', 'false').lower() == 'true':
                return stmt
                
            if category and category != 'all' and os.getenv('PRAYER_CATEGORY_FILTERING_ENABLED', 'false').lower() == 'true':
                stmt = stmt.where(Prayer.subject_category == category)
            
            if min_safety is not None and os.getenv('SAFETY_SCORING_ENABLED', 'false').lower() == 'true':
                stmt = stmt.where(Prayer.safety_score >= min_safety)
            
            return stmt
        
        
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
            stmt = apply_category_filters(stmt)
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
            stmt = apply_category_filters(stmt)
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
            stmt = apply_category_filters(stmt)
        elif feed_type == "my_unprayed":
            # Prayers the current user has NOT prayed yet
            stmt = (
                select(Prayer, User.display_name)
                .outerjoin(User, Prayer.author_username == User.display_name)
                .outerjoin(PrayerMark, 
                    (Prayer.id == PrayerMark.prayer_id) & 
                    (PrayerMark.username == user.display_name))
                .where(Prayer.flagged == False)
                .where(exclude_archived())
                .where(PrayerMark.id.is_(None))  # User hasn't prayed this
                .order_by(Prayer.created_at.desc())
            )
            stmt = apply_category_filters(stmt)
        elif feed_type == "my_requests":
            # Prayer requests submitted by the current user (include all statuses)
            stmt = (
                select(Prayer, User.display_name)
                .outerjoin(User, Prayer.author_username == User.display_name)
                .where(Prayer.flagged == False)
                .where(Prayer.author_username == user.display_name)
                .order_by(Prayer.created_at.desc())
            )
            stmt = apply_category_filters(stmt)
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
            stmt = apply_category_filters(stmt)
        elif feed_type == "daily_prayer":
            # Daily priority first, then by least recent prayer mark (oldest last prayer at top)
            # This shows prayers that need prayer attention most
            # Note: We don't use ORDER BY with LIMIT here because it would exclude priority prayers
            # Instead we fetch all prayers and sort in Python
            stmt = (
                select(Prayer, User.display_name)
                .outerjoin(User, Prayer.author_username == User.display_name)
                .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
                .where(Prayer.flagged == False)
                .where(exclude_archived())
                .group_by(Prayer.id)
            )
            stmt = apply_category_filters(stmt)
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
            stmt = apply_category_filters(stmt)
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
            stmt = apply_category_filters(stmt)
        else:  # "all" or default
            # All prayers (exclude archived)
            stmt = (
                select(Prayer, User.display_name)
                .outerjoin(User, Prayer.author_username == User.display_name)
                .where(Prayer.flagged == False)
                .where(exclude_archived())
                .order_by(Prayer.created_at.desc())
            )
            stmt = apply_category_filters(stmt)
            
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
                
            # Get author user object for supporter badge
            author_user = s.exec(select(User).where(User.display_name == author_name)).first()
            
            prayer_dict = {
                'id': prayer.id,
                'author_id': prayer.author_username,
                'text': prayer.text,
                'generated_prayer': prayer.generated_prayer,
                'project_tag': prayer.project_tag,
                'created_at': prayer.created_at,
                'flagged': prayer.flagged,
                'author_name': author_name,
                'author': author_user,  # Add user object for supporter badge
                'marked_by_user': user_mark_counts.get(prayer.id, 0),
                'mark_count': mark_counts.get(prayer.id, 0),
                'distinct_user_count': distinct_user_counts.get(prayer.id, 0),
                'is_archived': prayer.is_archived(s),
                'is_answered': prayer.is_answered(s),
                'answer_date': prayer.answer_date(s),
                'answer_testimony': prayer.answer_testimony(s),
                'is_daily_priority': is_daily_priority(prayer, s) if os.getenv('DAILY_PRIORITY_ENABLED', 'false').lower() == 'true' else False
            }
            prayers_with_authors.append(prayer_dict)
    
    # Special sorting for daily_prayer feed: priority first, then by oldest prayer activity
    if feed_type == "daily_prayer":
        daily_priority_enabled = os.getenv('DAILY_PRIORITY_ENABLED', 'false').lower() == 'true'
        
        # Get the most recent prayer mark timestamp for each prayer (for sorting)
        with Session(engine) as sort_session:
            prayer_timestamps = {}
            for prayer_dict in prayers_with_authors:
                latest_mark = sort_session.exec(
                    select(func.max(PrayerMark.created_at))
                    .where(PrayerMark.prayer_id == prayer_dict['id'])
                ).first()
                prayer_timestamps[prayer_dict['id']] = latest_mark or datetime.min
        
        if daily_priority_enabled:
            # Sort with daily priority first, then by oldest prayer mark (longest since last prayer)
            priority_prayers = [p for p in prayers_with_authors if p['is_daily_priority']]
            non_priority_prayers = [p for p in prayers_with_authors if not p['is_daily_priority']]
            
            # Sort non-priority prayers by oldest prayer mark first (ASC order)
            non_priority_prayers.sort(key=lambda p: prayer_timestamps.get(p['id'], datetime.min))
            
            
            prayers_with_authors = priority_prayers + non_priority_prayers
        else:
            # If priority disabled, just sort by oldest prayer mark
            prayers_with_authors.sort(key=lambda p: prayer_timestamps.get(p['id'], datetime.min))
        
        # Apply limit after sorting
        prayers_with_authors = prayers_with_authors[:50]
    
    # Get feed counts
    feed_counts = get_feed_counts(user.display_name)
    
    # Get user timezone
    user_timezone = get_user_timezone_from_request(request)
    
    return templates.TemplateResponse(
        "feed.html",
        {"request": request, "prayers": prayers_with_authors, "prompt": todays_prompt(), 
         "me": user, "session": session, "current_feed": feed_type, "feed_counts": feed_counts,
         "PRAYER_MODE_ENABLED": os.getenv('PRAYER_MODE_ENABLED', 'true').lower() == 'true', 
         "is_admin": is_admin(user),
         "DAILY_PRIORITY_ENABLED": os.getenv('DAILY_PRIORITY_ENABLED', 'false').lower() == 'true',
         "user_timezone": user_timezone,
         # Prayer Categorization Feature Flags
         "PRAYER_CATEGORIZATION_ENABLED": os.getenv('PRAYER_CATEGORIZATION_ENABLED', 'false').lower() == 'true',
         "PRAYER_CATEGORY_BADGES_ENABLED": os.getenv('PRAYER_CATEGORY_BADGES_ENABLED', 'false').lower() == 'true',
         "PRAYER_CATEGORY_FILTERING_ENABLED": os.getenv('PRAYER_CATEGORY_FILTERING_ENABLED', 'false').lower() == 'true',
         "SPECIFICITY_BADGES_ENABLED": os.getenv('SPECIFICITY_BADGES_ENABLED', 'false').lower() == 'true',
         "SAFETY_SCORING_ENABLED": os.getenv('SAFETY_SCORING_ENABLED', 'false').lower() == 'true',
         "HIGH_SAFETY_FILTER_ENABLED": os.getenv('HIGH_SAFETY_FILTER_ENABLED', 'false').lower() == 'true',
         "SAFETY_BADGES_VISIBLE": os.getenv('SAFETY_BADGES_VISIBLE', 'false').lower() == 'true',
         "CATEGORY_FILTER_DROPDOWN_ENABLED": os.getenv('CATEGORY_FILTER_DROPDOWN_ENABLED', 'false').lower() == 'true',
         "FILTER_PERSISTENCE_ENABLED": os.getenv('FILTER_PERSISTENCE_ENABLED', 'false').lower() == 'true'}
    )