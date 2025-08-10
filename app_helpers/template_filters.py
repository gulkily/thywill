"""
Template filters for timezone and formatting functionality.
"""

from datetime import datetime
from app_helpers.timezone_utils import format_timestamp_for_timezone
from app_helpers.utils.time_formatting import (
    format_hours_intelligently, 
    format_expiration_message,
    format_validity_message
)
from pathlib import Path
import re
from typing import Optional


def timezone_format_filter(dt: datetime, timezone_str: str = None) -> str:
    """
    Jinja2 template filter for formatting timestamps in user's timezone.
    
    Usage in templates:
    {{ prayer.created_at|timezone_format(user_timezone) }}
    
    Args:
        dt: datetime object to format
        timezone_str: Target timezone string
        
    Returns:
        Formatted timestamp string
    """
    return format_timestamp_for_timezone(dt, timezone_str)


def format_hours_filter(hours: int) -> str:
    """
    Jinja2 template filter for formatting hours into intuitive time units.
    
    Usage in templates:
    {{ token_exp_hours|format_hours }}
    
    Args:
        hours: Number of hours to format
        
    Returns:
        str: Human-readable time string (e.g., "30 days", "2 weeks")
    """
    return format_hours_intelligently(hours)

def format_expiration_filter(hours: int) -> str:
    """
    Jinja2 template filter for formatting expiration messages.
    
    Usage in templates:
    {{ token_exp_hours|format_expiration }}
    
    Args:
        hours: Number of hours until expiration
        
    Returns:
        str: User-friendly expiration message (e.g., "Expires in 30 days")
    """
    return format_expiration_message(hours)


def supporter_badge_filter(user) -> str:
    """
    Jinja2 template filter for displaying supporter badges.
    
    Usage in templates:
    {{ user|supporter_badge }}
    
    Args:
        user: User object with is_supporter attribute
        
    Returns:
        str: HTML for supporter badge or empty string
    """
    if not user or not getattr(user, 'is_supporter', False):
        return ''
    
    # Import here to avoid circular imports
    from app_helpers.services.supporter_badge_service import supporter_badge_service
    return supporter_badge_service.generate_user_badge_html(user)


def username_display_filter(username: str) -> str:
    """
    Jinja2 template filter for displaying usernames with supporter badges.
    
    Usage in templates:
    {{ username|username_display|safe }}
    
    Args:
        username: Username string to display
        
    Returns:
        str: HTML for username with supporter badge if applicable
    """
    if not username:
        return ''
    
    # Import here to avoid circular imports
    from app_helpers.services.username_display_service import username_display_service
    from models import engine
    from sqlmodel import Session
    
    with Session(engine) as session:
        return username_display_service.render_username_with_badge(username, session)


def prayer_file_url_filter(prayer) -> Optional[str]:
    """
    Jinja2 template filter for generating file system URLs for prayer archive files.
    
    Usage in templates:
    {{ prayer|prayer_file_url }}
    
    Args:
        prayer: Prayer object with text_file_path attribute
        
    Returns:
        str: File system URL like /files/prayers/2025/08/filename.txt or None if no archive
    """
    if not prayer or not getattr(prayer, 'text_file_path', None):
        return None
    
    file_path = prayer.text_file_path
    
    # Extract year, month, and filename from path like:
    # "text_archives/prayers.123456/2025/08/2025_08_10_prayer_at_1234.txt"
    match = re.search(r'/(\d{4})/(\d{2})/([^/]+\.txt)$', file_path)
    if not match:
        return None
    
    year, month, filename = match.groups()
    return f"/files/prayers/{year}/{month}/{filename}"

def register_filters(templates):
    """
    Register all custom filters with the Jinja2 templates environment.
    
    Args:
        templates: Jinja2Templates instance
    """
    templates.env.filters['timezone_format'] = timezone_format_filter
    templates.env.filters['format_hours'] = format_hours_filter
    templates.env.filters['format_expiration'] = format_expiration_filter
    templates.env.filters['supporter_badge'] = supporter_badge_filter
    templates.env.filters['username_display'] = username_display_filter
    templates.env.filters['prayer_file_url'] = prayer_file_url_filter