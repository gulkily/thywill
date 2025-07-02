from datetime import datetime
from zoneinfo import ZoneInfo, available_timezones
from typing import Optional


def format_timestamp_for_timezone(dt: datetime, timezone_str: Optional[str] = None) -> str:
    """
    Format a datetime object for display in a specific timezone.
    
    Args:
        dt: UTC datetime object to format
        timezone_str: Target timezone string (e.g., 'America/New_York')
        
    Returns:
        Formatted timestamp string with timezone info
    """
    if not timezone_str:
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    try:
        user_tz = ZoneInfo(timezone_str)
        local_dt = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(user_tz)
        return local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def get_timezone_display_name(timezone_str: str) -> str:
    """
    Get a friendly display name for a timezone.
    
    Args:
        timezone_str: Timezone string (e.g., 'America/New_York')
        
    Returns:
        Friendly timezone name or the original string if conversion fails
    """
    try:
        tz = ZoneInfo(timezone_str)
        now = datetime.now(tz)
        return now.strftime("%Z")
    except Exception:
        return timezone_str


def validate_timezone(timezone_str: str) -> bool:
    """
    Validate that a timezone string is recognized by the system.
    
    Args:
        timezone_str: Timezone string to validate
        
    Returns:
        True if timezone is valid, False otherwise
    """
    if not timezone_str:
        return False
    
    try:
        return timezone_str in available_timezones()
    except Exception:
        return False


def get_user_timezone_from_request(request) -> Optional[str]:
    """
    Extract user timezone from request headers or cookies.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Timezone string if found and valid, None otherwise
    """
    # First try HTMX header (for dynamic requests)
    timezone_str = request.headers.get('X-User-Timezone')
    
    if timezone_str and validate_timezone(timezone_str):
        return timezone_str
    
    # Fallback to cookie (for initial page loads)
    timezone_str = request.cookies.get('user_timezone')
    
    if timezone_str and validate_timezone(timezone_str):
        return timezone_str
    
    return None