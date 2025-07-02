"""
Prayer-related helper functions extracted from app.py
This module contains prayer management, filtering, and generation functions.
"""

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
            .where(PrayerMark.username == user_id)
        ).first()
        
        # My requests - include all statuses  
        counts['my_requests'] = s.exec(
            select(func.count(Prayer.id))
            .where(Prayer.flagged == False)
            .where(Prayer.author_username == user_id)
        ).first()
        
        # Recent activity (prayers with marks in last 7 days)
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
            .where(Prayer.author_username == user_id)
            .where(PrayerAttribute.attribute_name == 'archived')
        ).first()
        
        return counts




def find_compatible_prayer_partner(prayer: Prayer, db: Session, exclude_user_ids: list[str] = None) -> User | None:
    """Find a user to assign to pray for this prayer"""
    
    # Build user query
    user_query = select(User)
    
    # Exclude users who have already been assigned this prayer
    assigned_user_ids = db.exec(
        select(PrayerMark.username).where(PrayerMark.prayer_id == prayer.id)
    ).all()
    
    # Add additional exclusions if provided
    if exclude_user_ids:
        assigned_user_ids.extend(exclude_user_ids)
    
    if assigned_user_ids:
        user_query = user_query.where(~User.display_name.in_(assigned_user_ids))
    
    # Exclude the prayer author
    user_query = user_query.where(User.display_name != prayer.author_username)
    
    return db.exec(user_query).first()




def todays_prompt() -> str:
    """Get today's prayer prompt"""
    return "Let us pray 🙏"


def generate_prayer(prompt: str) -> dict:
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

IMPORTANT: Do NOT use first person ("me", "my", "I"). Instead, write the prayer so that community members can pray it FOR the person who made the request. Use third person references like "them", "they", "this person", or terms like "our friend" or "our brother/sister".

CRITICAL: Return ONLY the prayer text itself. Do NOT include any introductory phrases, explanations, or preambles like "Here's a prayer..." or "Here's a transformed...". Start directly with the prayer."""

        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            temperature=0.7,
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return {
            'prayer': response.content[0].text.strip(),
            'service_status': 'normal'
        }
    except Exception as e:
        print(f"Error generating prayer: {e}")
        return {
            'prayer': f"Divine Creator, we lift up our friend who asks for help with: {prompt}. May your will be done in their life. Amen.",
            'service_status': 'degraded'
        }