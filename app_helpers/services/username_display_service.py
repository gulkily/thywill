"""
Username Display Service for ThyWill

Provides centralized functionality for displaying usernames with supporter badges
consistently across all templates and routes.
"""

from typing import Dict, List, Optional
from sqlmodel import Session, select
from models import User, engine


class UsernameDisplayService:
    """Service for centralized username display with supporter badges."""
    
    def __init__(self):
        self._user_cache = {}  # Simple in-memory cache for performance
    
    def get_user_display_data(self, username: str, session: Session) -> Dict:
        """
        Get complete user display data including supporter status.
        
        Args:
            username: The username to look up
            session: Database session
            
        Returns:
            Dict with user data including supporter status
        """
        if not username:
            return {'username': '', 'is_supporter': False, 'supporter_since': None}
        
        # Check cache first
        if username in self._user_cache:
            return self._user_cache[username]
        
        # Query database
        user = session.exec(select(User).where(User.display_name == username)).first()
        
        if user:
            user_data = {
                'username': user.display_name,
                'is_supporter': user.is_supporter,
                'supporter_since': user.supporter_since,
                'user_object': user
            }
        else:
            user_data = {
                'username': username,
                'is_supporter': False,
                'supporter_since': None,
                'user_object': None
            }
        
        # Cache the result
        self._user_cache[username] = user_data
        return user_data
    
    def render_username_with_badge(self, username: str, session: Session) -> str:
        """
        Render username with supporter badge HTML.
        
        Args:
            username: The username to render
            session: Database session
            
        Returns:
            HTML string with username and supporter badge if applicable
        """
        user_data = self.get_user_display_data(username, session)
        
        if user_data['is_supporter'] and user_data['user_object']:
            from app_helpers.services.supporter_badge_service import supporter_badge_service
            badge_html = supporter_badge_service.generate_user_badge_html(user_data['user_object'])
            return f'{username}{badge_html}'
        
        return username
    
    def add_user_objects_to_prayers(self, prayers: List[Dict], session: Session) -> List[Dict]:
        """
        Add user objects to prayer dictionaries for badge support.
        
        Args:
            prayers: List of prayer dictionaries
            session: Database session
            
        Returns:
            Updated prayer dictionaries with user objects and display HTML
        """
        for prayer in prayers:
            if 'author_name' in prayer:
                user_data = self.get_user_display_data(prayer['author_name'], session)
                prayer['author'] = user_data['user_object']
                prayer['author_display_html'] = self.render_username_with_badge(
                    prayer['author_name'], session
                )
        
        return prayers
    
    def clear_cache(self):
        """Clear the user cache - useful for testing or when user data changes."""
        self._user_cache.clear()


# Global instance for use throughout the application
username_display_service = UsernameDisplayService()