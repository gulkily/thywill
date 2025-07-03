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

def register_filters(templates):
    """
    Register all custom filters with the Jinja2 templates environment.
    
    Args:
        templates: Jinja2Templates instance
    """
    templates.env.filters['timezone_format'] = timezone_format_filter
    templates.env.filters['format_hours'] = format_hours_filter
    templates.env.filters['format_expiration'] = format_expiration_filter