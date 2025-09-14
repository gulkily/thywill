# app_helpers/services/public_prayer_service.py
"""
Public prayer service for handling prayers accessible to non-authenticated users.
Provides filtering, pagination, and data retrieval for public prayer display.
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlmodel import Session, select, func
from models import Prayer, PrayerAttribute, User, PrayerMark, engine


class PublicPrayerService:
    """Service for retrieving prayers suitable for public display"""
    
    @staticmethod
    def get_public_prayers(
        page: int = 1, 
        page_size: int = 20,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Get paginated list of prayers eligible for public display.
        
        Filtering rules:
        - Exclude flagged prayers (Prayer.flagged == True)  
        - Exclude archived prayers UNLESS they have praise reports
        - Include all other non-flagged prayers
        
        Args:
            page: Page number (1-based)
            page_size: Number of prayers per page
            session: Optional database session
            
        Returns:
            Dict with prayers, pagination info, and metadata
        """
        should_close_session = session is None
        if session is None:
            session = Session(engine)
            
        try:
            offset = (page - 1) * page_size
            
            # Base query for public-eligible prayers
            base_query = (
                select(Prayer)
                .where(Prayer.flagged == False)
            )
            
            # Get archived prayer IDs (those with 'archived' attribute)
            archived_prayer_ids_subquery = (
                select(PrayerAttribute.prayer_id)
                .where(PrayerAttribute.attribute_name == 'archived')
            )
            
            # Get archived prayers that have praise reports (answered attribute)
            praise_report_prayer_ids_subquery = (
                select(PrayerAttribute.prayer_id)
                .where(PrayerAttribute.attribute_name == 'answered')
            )
            
            # Final filtering: exclude archived prayers EXCEPT those with praise reports
            filtered_query = base_query.where(
                ~Prayer.id.in_(
                    archived_prayer_ids_subquery.except_(praise_report_prayer_ids_subquery)
                )
            )
            
            # Get total count for pagination
            count_query = select(func.count()).select_from(filtered_query.subquery())
            total_count = session.exec(count_query).first() or 0
            
            # Get paginated results
            prayers_query = (
                filtered_query
                .order_by(Prayer.created_at.desc())
                .offset(offset)
                .limit(page_size)
            )
            prayers = list(session.exec(prayers_query).all())
            
            # Get basic statistics for all prayers in one query
            prayer_ids = [prayer.id for prayer in prayers]
            statistics = {}
            
            if prayer_ids:
                # Get total prayer counts for all prayers
                total_counts = session.exec(
                    select(PrayerMark.prayer_id, func.count(PrayerMark.id))
                    .where(PrayerMark.prayer_id.in_(prayer_ids))
                    .group_by(PrayerMark.prayer_id)
                ).all()
                
                # Get unique people counts for all prayers
                unique_counts = session.exec(
                    select(PrayerMark.prayer_id, func.count(func.distinct(PrayerMark.username)))
                    .where(PrayerMark.prayer_id.in_(prayer_ids))
                    .group_by(PrayerMark.prayer_id)
                ).all()
                
                # Build statistics dictionary
                for prayer_id, count in total_counts:
                    if prayer_id not in statistics:
                        statistics[prayer_id] = {}
                    statistics[prayer_id]['total_prayers'] = count
                    
                for prayer_id, count in unique_counts:
                    if prayer_id not in statistics:
                        statistics[prayer_id] = {}
                    statistics[prayer_id]['unique_people'] = count
            
            # Calculate pagination metadata
            total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
            has_next = page < total_pages
            has_prev = page > 1
            
            return {
                'prayers': prayers,
                'statistics': statistics,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': has_next,
                    'has_prev': has_prev,
                    'next_page': page + 1 if has_next else None,
                    'prev_page': page - 1 if has_prev else None
                }
            }
            
        finally:
            if should_close_session:
                session.close()
    
    @staticmethod
    def get_public_prayer_by_id(
        prayer_id: str, 
        session: Optional[Session] = None
    ) -> Optional[Prayer]:
        """
        Get a single prayer by ID if it's eligible for public display.
        
        Args:
            prayer_id: Prayer ID to retrieve
            session: Optional database session
            
        Returns:
            Prayer object if found and public-eligible, None otherwise
        """
        should_close_session = session is None
        if session is None:
            session = Session(engine)
            
        try:
            # Get the prayer
            prayer = session.get(Prayer, prayer_id)
            
            if not prayer or not PublicPrayerService._is_prayer_public_eligible(prayer, session):
                return None
                
            return prayer
            
        finally:
            if should_close_session:
                session.close()
    
    @staticmethod
    def _is_prayer_public_eligible(prayer: Prayer, session: Session) -> bool:
        """
        Check if a prayer is eligible for public display.
        
        Rules:
        - Must not be flagged
        - If archived, must have praise reports (answered attribute)
        
        Args:
            prayer: Prayer to check
            session: Database session
            
        Returns:
            True if prayer can be displayed publicly, False otherwise
        """
        # Check if flagged
        if prayer.flagged:
            return False
        
        # Check if archived
        archived_stmt = select(PrayerAttribute).where(
            PrayerAttribute.prayer_id == prayer.id,
            PrayerAttribute.attribute_name == 'archived'
        )
        is_archived = session.exec(archived_stmt).first() is not None
        
        # If archived, must have praise reports to be public
        if is_archived:
            answered_stmt = select(PrayerAttribute).where(
                PrayerAttribute.prayer_id == prayer.id,
                PrayerAttribute.attribute_name == 'answered'
            )
            has_praise_report = session.exec(answered_stmt).first() is not None
            return has_praise_report
        
        # Non-archived, non-flagged prayers are public-eligible
        return True
    
    @staticmethod
    def get_public_prayer_with_user(
        prayer_id: str, 
        session: Optional[Session] = None
    ) -> Optional[Tuple[Prayer, User]]:
        """
        Get a prayer with its author user data for public display.
        
        Args:
            prayer_id: Prayer ID to retrieve
            session: Optional database session
            
        Returns:
            Tuple of (Prayer, User) if found and eligible, None otherwise
        """
        should_close_session = session is None
        if session is None:
            session = Session(engine)
            
        try:
            prayer = PublicPrayerService.get_public_prayer_by_id(prayer_id, session)
            if not prayer:
                return None
            
            # Get the user
            user = session.exec(
                select(User).where(User.display_name == prayer.author_username)
            ).first()
            
            if not user:
                return None
                
            return (prayer, user)
            
        finally:
            if should_close_session:
                session.close()
    
    @staticmethod
    def get_prayer_statistics(
        prayer_id: str,
        session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Get prayer statistics including who prayed and how many times.
        
        Args:
            prayer_id: Prayer ID to get statistics for
            session: Optional database session
            
        Returns:
            Dict with prayer statistics and records
        """
        should_close_session = session is None
        if session is None:
            session = Session(engine)
            
        try:
            # Get all prayer marks for this prayer
            prayer_marks = session.exec(
                select(PrayerMark, User.display_name)
                .join(User, PrayerMark.username == User.display_name)
                .where(PrayerMark.prayer_id == prayer_id)
                .order_by(PrayerMark.created_at.desc())
            ).all()
            
            # Calculate statistics
            total_prayers = len(prayer_marks)
            unique_people = len(set(mark.username for mark, _ in prayer_marks))
            
            # Format prayer records with user display names
            prayer_records = []
            for mark, display_name in prayer_marks:
                prayer_records.append({
                    'id': mark.id,
                    'username': mark.username,
                    'display_name': display_name,
                    'prayed_at': mark.created_at.isoformat(),  # Convert to ISO format for JSON serialization
                    'formatted_date': mark.created_at.strftime('%B %d, %Y at %I:%M %p')
                })
            
            return {
                'total_prayers': total_prayers,
                'unique_people': unique_people,
                'prayer_records': prayer_records
            }
            
        finally:
            if should_close_session:
                session.close()