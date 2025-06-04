"""
Prayer-related helper functions extracted from app.py
This module contains prayer management, filtering, and generation functions.
"""

import yaml
import anthropic
import os
from datetime import datetime, timedelta, date
from sqlmodel import Session, select, func, text
from models import (
    User, Prayer, PrayerMark, PrayerAttribute, engine
)

# Initialize Anthropic client
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


def get_feed_counts(user_id: str) -> dict:
    """Get counts for different feed types"""
    with Session(engine) as s:
        counts = {}
        
        # Helper to exclude archived and flagged prayers
        def active_prayer_filter():
            return (
                Prayer.flagged == False
            ).where(
                ~Prayer.id.in_(
                    select(PrayerAttribute.prayer_id)
                    .where(PrayerAttribute.attribute_name.in_(['archived', 'flagged']))
                )
            )
        
        # All prayers (active only)
        counts['all'] = s.exec(
            select(func.count(Prayer.id))
            .where(Prayer.flagged == False)
            .where(
                ~Prayer.id.in_(
                    select(PrayerAttribute.prayer_id)
                    .where(PrayerAttribute.attribute_name == 'archived')
                )
            )
        ).first()
        
        # New & unprayed
        stmt = (
            select(func.count(Prayer.id))
            .select_from(Prayer)
            .outerjoin(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.flagged == False)
            .where(
                ~Prayer.id.in_(
                    select(PrayerAttribute.prayer_id)
                    .where(PrayerAttribute.attribute_name == 'archived')
                )
            )
            .group_by(Prayer.id)
            .having(func.count(PrayerMark.id) == 0)
        )
        unprayed_prayers = s.exec(stmt).all()
        counts['new_unprayed'] = len(unprayed_prayers)
        
        # Most prayed (prayers with at least 1 mark)
        counts['most_prayed'] = s.exec(
            select(func.count(func.distinct(Prayer.id)))
            .select_from(Prayer)
            .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.flagged == False)
            .where(
                ~Prayer.id.in_(
                    select(PrayerAttribute.prayer_id)
                    .where(PrayerAttribute.attribute_name == 'archived')
                )
            )
        ).first()
        
        # My prayers (prayers user has marked) - include all statuses
        counts['my_prayers'] = s.exec(
            select(func.count(func.distinct(Prayer.id)))
            .select_from(Prayer)
            .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerMark.user_id == user_id)
        ).first()
        
        # My requests - include all statuses  
        counts['my_requests'] = s.exec(
            select(func.count(Prayer.id))
            .where(Prayer.flagged == False)
            .where(Prayer.author_id == user_id)
        ).first()
        
        # Recent activity (prayers with marks in last 7 days) - active only
        week_ago = datetime.utcnow() - timedelta(days=7)
        counts['recent_activity'] = s.exec(
            select(func.count(func.distinct(Prayer.id)))
            .select_from(Prayer)
            .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(Prayer.flagged == False)
            .where(
                ~Prayer.id.in_(
                    select(PrayerAttribute.prayer_id)
                    .where(PrayerAttribute.attribute_name == 'archived')
                )
            )
            .where(PrayerMark.created_at >= week_ago)
        ).first()
        
        # Answered prayers count
        counts['answered'] = s.exec(
            select(func.count(func.distinct(Prayer.id)))
            .select_from(Prayer)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(PrayerAttribute.attribute_name == 'answered')
        ).first()
        
        # Archived prayers count (user's own only)
        counts['archived'] = s.exec(
            select(func.count(func.distinct(Prayer.id)))
            .select_from(Prayer)
            .join(PrayerAttribute, Prayer.id == PrayerAttribute.prayer_id)
            .where(Prayer.flagged == False)
            .where(Prayer.author_id == user_id)
            .where(PrayerAttribute.attribute_name == 'archived')
        ).first()
        
        return counts


def get_filtered_prayers_for_user(user: User, db: Session, include_archived: bool = False, include_answered: bool = False) -> list[Prayer]:
    """Get prayers filtered based on user's religious preferences and attributes"""
    
    # Base query for non-flagged prayers
    base_query = select(Prayer).where(Prayer.flagged == False)
    
    # Apply attribute filtering
    excluded_attributes = []
    if not include_archived:
        excluded_attributes.append('archived')
    if not include_answered:
        excluded_attributes.append('answered')
    
    if excluded_attributes:
        excluded_prayer_ids = db.exec(
            select(PrayerAttribute.prayer_id).where(
                PrayerAttribute.attribute_name.in_(excluded_attributes)
            )
        ).all()
        
        if excluded_prayer_ids:
            base_query = base_query.where(~Prayer.id.in_(excluded_prayer_ids))
    
    # Apply religious preference filtering
    if user.religious_preference == "christian":
        # Christians see: all prayers + christian-only prayers
        base_query = base_query.where(
            Prayer.target_audience.in_(["all", "christians_only"])
        )
    else:
        # All faiths (unspecified) users see only "all" prayers
        base_query = base_query.where(Prayer.target_audience == "all")
    
    return db.exec(base_query.order_by(Prayer.created_at.desc())).all()


def find_compatible_prayer_partner(prayer: Prayer, db: Session, exclude_user_ids: list[str] = None) -> User | None:
    """Find a user compatible with the prayer's religious targeting requirements"""
    
    # Build user query based on prayer target audience
    user_query = select(User)
    
    # Apply religious compatibility filtering
    if prayer.target_audience == "christians_only":
        user_query = user_query.where(User.religious_preference == "christian")
    # For "all", no additional religious filtering needed
    
    # Exclude users who have already been assigned this prayer
    assigned_user_ids = db.exec(
        select(PrayerMark.user_id).where(PrayerMark.prayer_id == prayer.id)
    ).all()
    
    # Add additional exclusions if provided
    if exclude_user_ids:
        assigned_user_ids.extend(exclude_user_ids)
    
    if assigned_user_ids:
        user_query = user_query.where(~User.id.in_(assigned_user_ids))
    
    # Exclude the prayer author
    user_query = user_query.where(User.id != prayer.author_id)
    
    return db.exec(user_query).first()


def get_religious_preference_stats(db: Session) -> dict:
    """Get statistics about religious preference distribution"""
    stats = {}
    
    # User preference distribution
    user_prefs = db.exec(
        text("SELECT religious_preference, COUNT(*) FROM user GROUP BY religious_preference")
    ).fetchall()
    stats['user_preferences'] = {pref: count for pref, count in user_prefs}
    
    # Prayer target audience distribution
    prayer_targets = db.exec(
        text("SELECT target_audience, COUNT(*) FROM prayer GROUP BY target_audience")
    ).fetchall()
    stats['prayer_targets'] = {target: count for target, count in prayer_targets}
    
    return stats


def todays_prompt() -> str:
    """Get today's prayer prompt from YAML file"""
    try:
        data = yaml.safe_load(open("prompts.yaml"))
        return data.get(str(date.today()), "Let us pray 🙏")
    except FileNotFoundError:
        return "Let us pray 🙏"


def generate_prayer(prompt: str) -> str:
    """Generate a proper prayer from a user prompt using Anthropic API"""
    try:
        system_prompt = """You are a wise and compassionate spiritual guide. Your task is to transform user requests into beautiful, proper prayers that a COMMUNITY can pray FOR the person making the request.

Create prayers that are:
- Written for others to pray FOR the requester (use "them", "they", "this person", or "our friend/brother/sister")
- Properly formed with appropriate address to the Divine
- Concise yet meaningful (2-4 sentences)
- Godly and reverent in tone
- Well-intentioned and positive
- Easy for a community to pray together
- Agreeable to people of various faith backgrounds

IMPORTANT: Do NOT use first person ("me", "my", "I"). Instead, write the prayer so that community members can pray it FOR the person who made the request. Use third person references like "them", "they", "this person", or terms like "our friend" or "our brother/sister"."""

        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            temperature=0.7,
            system=system_prompt,
            messages=[
                {"role": "user", "content": f"Please transform this prayer request into a community prayer that others can pray for the person: {prompt}"}
            ]
        )
        
        return response.content[0].text.strip()
    except Exception as e:
        print(f"Error generating prayer: {e}")
        return f"Divine Creator, we lift up our friend who asks for help with: {prompt}. May your will be done in their life. Amen."