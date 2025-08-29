"""
Statistics service for calculating prayer and user metrics
"""

from sqlmodel import Session, select, func, text
from datetime import datetime, date, timedelta
from typing import Dict, List, Tuple
from models import Prayer, User, PrayerMark, PrayerAttribute


class StatisticsService:
    def __init__(self, session: Session):
        self.session = session
    
    def get_prayer_counts_by_period(self, period: str, start_date: date, end_date: date) -> Dict[str, int]:
        """Get prayer counts grouped by time period"""
        
        # Define the date format and grouping based on period
        if period == "daily":
            date_format = "%Y-%m-%d"
            date_trunc = "date(created_at)"
        elif period == "weekly":
            date_format = "%Y-W%W"  # Year-Week format
            date_trunc = "date(created_at, 'weekday 0', '-6 days')"  # Start of week (Monday)
        elif period == "monthly":
            date_format = "%Y-%m"
            date_trunc = "date(created_at, 'start of month')"
        elif period == "yearly":
            date_format = "%Y"
            date_trunc = "date(created_at, 'start of year')"
        else:
            raise ValueError(f"Unsupported period: {period}")
        
        # Build the SQL query
        query = text(f"""
            SELECT {date_trunc} as period_date, COUNT(*) as count
            FROM prayer 
            WHERE date(created_at) >= :start_date AND date(created_at) <= :end_date
            GROUP BY {date_trunc}
            ORDER BY period_date
        """)
        
        result = self.session.execute(query, {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
        })
        
        # Convert results to dictionary with formatted dates
        counts = {}
        for row in result:
            period_date = datetime.strptime(row[0], "%Y-%m-%d").date()
            formatted_date = period_date.strftime(date_format)
            counts[formatted_date] = row[1]
        
        return counts
    
    def get_total_prayers(self) -> int:
        """Get total count of all prayers"""
        return self.session.exec(select(func.count(Prayer.id))).first()
    
    def get_active_prayers_count(self) -> int:
        """Get count of prayers that are not archived"""
        # Count prayers that don't have an "archived" attribute
        archived_prayer_ids = select(PrayerAttribute.prayer_id).where(
            PrayerAttribute.attribute_name == "archived"
        )
        
        active_count = self.session.exec(
            select(func.count(Prayer.id)).where(
                Prayer.id.notin_(archived_prayer_ids)
            )
        ).first()
        
        return active_count or 0
    
    def get_answered_prayers_count(self) -> int:
        """Get count of prayers marked as answered"""
        answered_prayer_ids = select(PrayerAttribute.prayer_id).where(
            PrayerAttribute.attribute_name == "answered"
        )
        
        answered_count = self.session.exec(
            select(func.count()).select_from(
                select(PrayerAttribute.prayer_id).where(
                    PrayerAttribute.attribute_name == "answered"
                ).subquery()
            )
        ).first()
        
        return answered_count or 0
    
    def get_user_registration_counts_by_period(self, period: str, start_date: date, end_date: date) -> Dict[str, int]:
        """Get user registration counts grouped by time period"""
        
        if period == "daily":
            date_format = "%Y-%m-%d"
            date_trunc = "date(created_at)"
        elif period == "weekly":
            date_format = "%Y-W%W"
            date_trunc = "date(created_at, 'weekday 0', '-6 days')"
        elif period == "monthly":
            date_format = "%Y-%m"
            date_trunc = "date(created_at, 'start of month')"
        elif period == "yearly":
            date_format = "%Y"
            date_trunc = "date(created_at, 'start of year')"
        else:
            raise ValueError(f"Unsupported period: {period}")
        
        query = text(f"""
            SELECT {date_trunc} as period_date, COUNT(*) as count
            FROM user 
            WHERE date(created_at) >= :start_date AND date(created_at) <= :end_date
            GROUP BY {date_trunc}
            ORDER BY period_date
        """)
        
        result = self.session.execute(query, {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
        })
        
        counts = {}
        for row in result:
            period_date = datetime.strptime(row[0], "%Y-%m-%d").date()
            formatted_date = period_date.strftime(date_format)
            counts[formatted_date] = row[1]
        
        return counts
    
    def get_total_users(self) -> int:
        """Get total count of all users"""
        return self.session.exec(select(func.count(User.display_name))).first()
    
    def get_total_prayer_marks(self) -> int:
        """Get total count of all prayer marks"""
        return self.session.exec(select(func.count(PrayerMark.id))).first()
    
    def get_summary_statistics(self) -> Dict[str, int]:
        """Get summary statistics for dashboard overview"""
        return {
            "total_prayers": self.get_total_prayers(),
            "active_prayers": self.get_active_prayers_count(),
            "answered_prayers": self.get_answered_prayers_count(),
            "total_users": self.get_total_users(),
            "total_prayer_marks": self.get_total_prayer_marks()
        }