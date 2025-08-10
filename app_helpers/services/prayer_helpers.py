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
        
        # My unprayed (prayers user hasn't marked yet)
        counts['my_unprayed'] = s.exec(
            select(func.count(Prayer.id))
            .select_from(Prayer)
            .outerjoin(PrayerMark, 
                (Prayer.id == PrayerMark.prayer_id) & 
                (PrayerMark.username == user_id))
            .where(Prayer.flagged == False)
            .where(
                ~Prayer.id.in_(
                    select(PrayerAttribute.prayer_id)
                    .where(PrayerAttribute.attribute_name == 'archived')
                )
            )
            .where(PrayerMark.id.is_(None))
        ).first()
        
        # My requests - include all statuses  
        counts['my_requests'] = s.exec(
            select(func.count(Prayer.id))
            .where(Prayer.flagged == False)
            .where(Prayer.author_username == user_id)
        ).first()
        
        # Recent activity (prayers with any marks, ordered by most recent mark activity)
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
        ).first()
        
        # Daily prayer count (same as recent_activity - prayers with any marks)
        counts['daily_prayer'] = counts['recent_activity']
        
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
    quotes = [
        "Be still and know that I am God. - Psalm 46:10",
        "In everything give thanks, for this is God's will for you. - 1 Thessalonians 5:18",
        "Cast all your anxiety on Him because He cares for you. - 1 Peter 5:7",
        "The Lord is close to the brokenhearted. - Psalm 34:18",
        "Come to me, all you who are weary and burdened. - Matthew 11:28",
        "Trust in the Lord with all your heart. - Proverbs 3:5",
        "God is our refuge and strength, an ever-present help in trouble. - Psalm 46:1"
    ]
    # Rotate based on day of week
    import datetime
    day_index = datetime.datetime.now().weekday()
    return quotes[day_index % len(quotes)]


def generate_prayer(prompt: str) -> dict:
    """Generate a proper prayer from a user prompt using Anthropic API"""
    try:
        # Use dynamic prompt composition based on feature flags
        from app_helpers.services.prompt_composition_service import prompt_composition_service
        system_prompt = prompt_composition_service.build_prayer_generation_prompt()
        
        # Determine max tokens based on categorization features
        try:
            from app import PRAYER_CATEGORIZATION_ENABLED, AI_CATEGORIZATION_ENABLED
        except ImportError:
            import os
            PRAYER_CATEGORIZATION_ENABLED = os.getenv("PRAYER_CATEGORIZATION_ENABLED", "false").lower() == "true"
            AI_CATEGORIZATION_ENABLED = os.getenv("AI_CATEGORIZATION_ENABLED", "false").lower() == "true"
        
        # Increase max tokens if categorization analysis is enabled
        max_tokens = 400 if (PRAYER_CATEGORIZATION_ENABLED and AI_CATEGORIZATION_ENABLED) else 200

        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=max_tokens,
            temperature=0.7,
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        ai_response = response.content[0].text.strip()
        
        return {
            'prayer': ai_response,
            'full_response': ai_response,  # Include full response for categorization parsing
            'service_status': 'normal'
        }
    except Exception as e:
        print(f"Error generating prayer: {e}")
        fallback_prayer = f"Divine Creator, we lift up our friend who asks for help with: {prompt}. May your will be done in their life. Amen."
        return {
            'prayer': fallback_prayer,
            'full_response': fallback_prayer,  # Consistent structure for error handling
            'service_status': 'degraded'
        }


def set_daily_priority(prayer_id: str, admin_user: User, session: Session) -> bool:
    """Set a prayer as daily priority for today"""
    try:
        # Get the prayer
        prayer = session.exec(select(Prayer).where(Prayer.id == prayer_id)).first()
        if not prayer:
            return False
        
        # Set the daily priority attribute with today's date
        today_str = date.today().isoformat()
        prayer.set_attribute('daily_priority', today_str, admin_user.display_name, session)
        session.commit()
        return True
    except Exception:
        session.rollback()
        return False


def remove_daily_priority(prayer_id: str, session: Session) -> bool:
    """Remove daily priority status from a prayer"""
    try:
        # Get the prayer
        prayer = session.exec(select(Prayer).where(Prayer.id == prayer_id)).first()
        if not prayer:
            return False
        
        # Remove the daily priority attribute
        prayer.remove_attribute('daily_priority', session)
        session.commit()
        return True
    except Exception:
        session.rollback()
        return False


def expire_old_priorities(session: Session) -> int:
    """Remove expired daily priority attributes (older than today)"""
    try:
        today_str = date.today().isoformat()
        
        # Find all daily_priority attributes with dates before today
        old_priorities = session.exec(
            select(PrayerAttribute)
            .where(PrayerAttribute.attribute_name == 'daily_priority')
            .where(PrayerAttribute.attribute_value < today_str)
        ).all()
        
        count = len(old_priorities)
        
        # Delete expired priority attributes
        for priority_attr in old_priorities:
            session.delete(priority_attr)
        
        session.commit()
        return count
    except Exception:
        session.rollback()
        return 0


def is_daily_priority(prayer: Prayer, session: Session) -> bool:
    """Check if a prayer is marked as daily priority for today"""
    try:
        today_str = date.today().isoformat()
        
        priority_attr = session.exec(
            select(PrayerAttribute)
            .where(PrayerAttribute.prayer_id == prayer.id)
            .where(PrayerAttribute.attribute_name == 'daily_priority')
            .where(PrayerAttribute.attribute_value == today_str)
        ).first()
        
        return priority_attr is not None
    except Exception:
        return False