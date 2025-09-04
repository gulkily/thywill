# app_helpers/services/profile_data_service.py
"""
Profile data service for handling user prayer statistics and detailed views.
Provides reusable database query functions for profile-related data.
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlmodel import Session, select, func
from models import User, Prayer, PrayerMark


class ProfileDataService:
    """Service for retrieving user profile data and prayer statistics"""
    
    @staticmethod
    def get_user_prayer_requests(
        user_id: str, 
        session: Session,
        page: int = 1, 
        per_page: int = 20
    ) -> Tuple[List[Prayer], int]:
        """
        Get paginated list of prayer requests by a user.
        
        Returns:
            Tuple of (prayers_list, total_count)
        """
        offset = (page - 1) * per_page
        
        # Get total count
        count_stmt = (
            select(func.count(Prayer.id))
            .where(Prayer.author_username == user_id)
            .where(Prayer.flagged == False)
        )
        total_count = session.exec(count_stmt).first() or 0
        
        # Get paginated results
        prayers_stmt = (
            select(Prayer)
            .where(Prayer.author_username == user_id)
            .where(Prayer.flagged == False)
            .order_by(Prayer.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        prayers = session.exec(prayers_stmt).all()
        
        # Pre-compute prayer attributes for template use
        enriched_prayers = []
        for prayer in prayers:
            # Create a copy with computed attributes
            prayer_dict = prayer.model_dump()
            prayer_dict['is_answered'] = prayer.is_answered(session)
            prayer_dict['is_archived'] = prayer.is_archived(session)
            enriched_prayers.append(prayer_dict)
        
        return enriched_prayers, total_count
    
    @staticmethod
    def get_user_prayers_marked(
        user_id: str, 
        session: Session,
        page: int = 1, 
        per_page: int = 20
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get paginated list of prayers the user has marked/prayed for.
        
        Returns:
            Tuple of (prayer_data_list, total_count)
        """
        offset = (page - 1) * per_page
        
        # Get total count of distinct prayers marked
        count_stmt = (
            select(func.count(func.distinct(PrayerMark.prayer_id)))
            .where(PrayerMark.username == user_id)
        )
        total_count = session.exec(count_stmt).first() or 0
        
        # Get paginated results with prayer details and last marked time
        prayers_stmt = (
            select(Prayer, func.max(PrayerMark.created_at).label('last_marked'))
            .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(PrayerMark.username == user_id)
            .where(Prayer.flagged == False)
            .group_by(Prayer.id)
            .order_by(func.max(PrayerMark.created_at).desc())
            .offset(offset)
            .limit(per_page)
        )
        
        results = session.exec(prayers_stmt).all()
        prayer_data = []
        
        for prayer, last_marked in results:
            # Get author information
            author = session.get(User, prayer.author_username)
            # Pre-compute prayer attributes for template use
            prayer_dict = prayer.model_dump()
            prayer_dict['is_answered'] = prayer.is_answered(session)
            prayer_dict['is_archived'] = prayer.is_archived(session)
            
            prayer_data.append({
                'prayer': prayer_dict,
                'author': author,
                'author_name': author.display_name if author else "Unknown",
                'last_marked': last_marked
            })
        
        return prayer_data, total_count
    
    @staticmethod
    def get_user_unique_prayers_info(
        user_id: str, 
        session: Session,
        page: int = 1, 
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Get information about unique prayers the user has prayed for.
        
        Returns:
            Dict with unique count, total marks, and optional sample prayers
        """
        # Get unique prayers count
        unique_count = session.exec(
            select(func.count(func.distinct(PrayerMark.prayer_id)))
            .where(PrayerMark.username == user_id)
        ).first() or 0
        
        # Get total prayer marks count
        total_marks = session.exec(
            select(func.count(PrayerMark.id))
            .where(PrayerMark.username == user_id)
        ).first() or 0
        
        # Calculate average prayers per unique request
        avg_prayers_per_request = 0
        if unique_count > 0:
            avg_prayers_per_request = round(total_marks / unique_count, 1)
        
        # Get sample prayers for display (most recently prayed)
        offset = (page - 1) * per_page
        sample_prayers_stmt = (
            select(Prayer, func.max(PrayerMark.created_at).label('last_marked'))
            .join(PrayerMark, Prayer.id == PrayerMark.prayer_id)
            .where(PrayerMark.username == user_id)
            .where(Prayer.flagged == False)
            .group_by(Prayer.id)
            .order_by(func.max(PrayerMark.created_at).desc())
            .offset(offset)
            .limit(per_page)
        )
        
        sample_results = session.exec(sample_prayers_stmt).all()
        sample_prayers = []
        
        for prayer, last_marked in sample_results:
            # Get author and mark count for this prayer
            author = session.get(User, prayer.author_username)
            mark_count = session.exec(
                select(func.count(PrayerMark.id))
                .where(PrayerMark.prayer_id == prayer.id)
                .where(PrayerMark.username == user_id)
            ).first() or 0
            
            # Pre-compute prayer attributes for template use
            prayer_dict = prayer.model_dump()
            prayer_dict['is_answered'] = prayer.is_answered(session)
            prayer_dict['is_archived'] = prayer.is_archived(session)
            
            sample_prayers.append({
                'prayer': prayer_dict,
                'author': author,
                'author_name': author.display_name if author else "Unknown",
                'last_marked': last_marked,
                'mark_count': mark_count
            })
        
        return {
            'unique_count': unique_count,
            'total_marks': total_marks,
            'avg_prayers_per_request': avg_prayers_per_request,
            'sample_prayers': sample_prayers,
            'has_more': len(sample_results) == per_page
        }
    
    @staticmethod
    def get_pagination_info(total_count: int, page: int, per_page: int) -> Dict[str, Any]:
        """
        Calculate pagination information.
        
        Returns:
            Dict with pagination details (total_pages, has_prev, has_next, etc.)
        """
        total_pages = (total_count + per_page - 1) // per_page  # Ceiling division
        
        return {
            'total_count': total_count,
            'total_pages': total_pages,
            'current_page': page,
            'per_page': per_page,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'prev_page': page - 1 if page > 1 else None,
            'next_page': page + 1 if page < total_pages else None,
            'start_item': (page - 1) * per_page + 1 if total_count > 0 else 0,
            'end_item': min(page * per_page, total_count)
        }