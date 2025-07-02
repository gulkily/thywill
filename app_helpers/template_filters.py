"""
Template filters for timezone and formatting functionality.
"""

from datetime import datetime
from app_helpers.timezone_utils import format_timestamp_for_timezone


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


def register_filters(templates):
    """
    Register all custom filters with the Jinja2 templates environment.
    
    Args:
        templates: Jinja2Templates instance
    """
    templates.env.filters['timezone_format'] = timezone_format_filter