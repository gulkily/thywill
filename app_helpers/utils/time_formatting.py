# app_helpers/utils/time_formatting.py
"""
Time formatting utilities for user-friendly time display.
Converts hours to more intuitive units like days, weeks, or months.
"""

def format_hours_intelligently(hours: int) -> str:
    """
    Format hours into the most intuitive time unit for users.
    
    Args:
        hours: Number of hours to format
        
    Returns:
        str: Human-readable time string (e.g., "30 days", "2 weeks", "6 hours")
        
    Examples:
        format_hours_intelligently(1) -> "1 hour"
        format_hours_intelligently(24) -> "1 day" 
        format_hours_intelligently(48) -> "2 days"
        format_hours_intelligently(168) -> "1 week"
        format_hours_intelligently(720) -> "30 days"
        format_hours_intelligently(2160) -> "3 months"
    """
    if hours == 0:
        return "0 hours"
    
    # Calculate different time units
    days = hours / 24
    weeks = hours / (24 * 7)
    months = hours / (24 * 30)  # Approximate month as 30 days
    
    # Choose the most appropriate unit
    if hours < 24:
        # Less than a day: show hours
        unit = "hour" if hours == 1 else "hours"
        return f"{hours} {unit}"
    
    elif hours % 24 == 0 and days < 14:
        # Exact days and less than 2 weeks: show days
        days_int = int(days)
        unit = "day" if days_int == 1 else "days"
        return f"{days_int} {unit}"
    
    elif hours % (24 * 7) == 0 and weeks < 8:
        # Exact weeks and less than 2 months: show weeks
        weeks_int = int(weeks)
        unit = "week" if weeks_int == 1 else "weeks"
        return f"{weeks_int} {unit}"
    
    elif hours % (24 * 30) == 0 and months <= 12 and days != 30:
        # Exact months and less than a year (but not exactly 30 days): show months
        months_int = int(months)
        unit = "month" if months_int == 1 else "months"
        return f"{months_int} {unit}"
    
    elif days >= 1:
        # Default to days for other cases
        if days == int(days):
            days_int = int(days)
            unit = "day" if days_int == 1 else "days"
            return f"{days_int} {unit}"
        else:
            # Show decimal days if not exact
            unit = "day" if days < 2 else "days"
            return f"{days:.1f} {unit}"
    
    else:
        # Fallback to hours
        unit = "hour" if hours == 1 else "hours"
        return f"{hours} {unit}"

def format_hours_with_detail(hours: int) -> dict:
    """
    Format hours with detailed breakdown for debugging/admin interfaces.
    
    Args:
        hours: Number of hours to format
        
    Returns:
        dict: Detailed time breakdown with multiple representations
        
    Example:
        format_hours_with_detail(720) -> {
            'primary': '30 days',
            'detailed': '30 days (720 hours)',
            'hours': 720,
            'days': 30.0,
            'weeks': 4.29,
            'breakdown': '30 days = 4.3 weeks = 720 hours'
        }
    """
    primary = format_hours_intelligently(hours)
    
    days = hours / 24
    weeks = hours / (24 * 7)
    months = hours / (24 * 30)
    
    # Create detailed representation
    if hours >= 24:
        detailed = f"{primary} ({hours} hours)"
    else:
        detailed = primary
    
    # Create breakdown for admin interfaces
    breakdown_parts = []
    if months >= 1:
        breakdown_parts.append(f"{months:.1f} months")
    if weeks >= 1:
        breakdown_parts.append(f"{weeks:.1f} weeks")
    if days >= 1:
        breakdown_parts.append(f"{days:.1f} days")
    breakdown_parts.append(f"{hours} hours")
    
    breakdown = " = ".join(breakdown_parts)
    
    return {
        'primary': primary,
        'detailed': detailed,
        'hours': hours,
        'days': round(days, 1),
        'weeks': round(weeks, 2),
        'months': round(months, 2),
        'breakdown': breakdown
    }

def format_expiration_message(hours: int) -> str:
    """
    Format an expiration message for user interfaces.
    
    Args:
        hours: Number of hours until expiration
        
    Returns:
        str: User-friendly expiration message
        
    Examples:
        format_expiration_message(12) -> "Expires in 12 hours"
        format_expiration_message(720) -> "Expires in 30 days"
    """
    time_str = format_hours_intelligently(hours)
    return f"Expires in {time_str}"

def format_validity_message(hours: int) -> str:
    """
    Format a validity duration message for error messages and help text.
    
    Args:
        hours: Number of hours of validity
        
    Returns:
        str: User-friendly validity message
        
    Examples:
        format_validity_message(12) -> "valid for 12 hours"
        format_validity_message(720) -> "valid for 30 days"
    """
    time_str = format_hours_intelligently(hours)
    return f"valid for {time_str}"