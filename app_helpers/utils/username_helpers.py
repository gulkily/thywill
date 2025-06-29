"""
Username normalization utilities for consistent username handling
"""

import re
from typing import Optional

def normalize_username(username: Optional[str]) -> Optional[str]:
    """
    Normalize username for consistent storage and lookup.
    
    Args:
        username: Raw username input
        
    Returns:
        Normalized username or None if invalid
        
    Rules:
    - Strip leading/trailing whitespace
    - Convert to lowercase for comparison (but preserve original case for display)
    - Remove extra internal whitespace (multiple spaces -> single space)
    - Remove non-printable characters
    - Ensure minimum length requirements
    """
    if not username:
        return None
        
    # Strip leading/trailing whitespace
    normalized = username.strip()
    
    if not normalized:
        return None
        
    # Remove non-printable characters except normal spaces
    normalized = ''.join(char for char in normalized if char.isprintable())
    
    # Collapse multiple whitespace characters into single spaces
    normalized = re.sub(r'\s+', ' ', normalized)
    
    # Final trim in case regex created leading/trailing spaces
    normalized = normalized.strip()
    
    # Ensure minimum length (at least 1 character after normalization)
    if len(normalized) < 1:
        return None
        
    # Ensure maximum length (reasonable limit)
    if len(normalized) > 100:
        return None
        
    return normalized

def normalize_username_for_lookup(username: Optional[str]) -> Optional[str]:
    """
    Normalize username for database lookups (case-insensitive).
    
    Args:
        username: Raw username input
        
    Returns:
        Lowercase normalized username for lookup, or None if invalid
    """
    normalized = normalize_username(username)
    if normalized is None:
        return None
    return normalized.lower()

def usernames_are_equivalent(username1: Optional[str], username2: Optional[str]) -> bool:
    """
    Check if two usernames are equivalent after normalization.
    
    Args:
        username1: First username
        username2: Second username
        
    Returns:
        True if usernames are equivalent, False otherwise
    """
    norm1 = normalize_username_for_lookup(username1)
    norm2 = normalize_username_for_lookup(username2)
    
    if norm1 is None or norm2 is None:
        return False
        
    return norm1 == norm2

def validate_username(username: Optional[str]) -> tuple[bool, Optional[str]]:
    """
    Validate and normalize a username for registration/storage.
    
    Args:
        username: Raw username input
        
    Returns:
        Tuple of (is_valid, normalized_username)
    """
    if not username:
        return False, None
        
    normalized = normalize_username(username)
    
    if normalized is None:
        return False, None
        
    # Additional validation rules
    if len(normalized) < 2:
        return False, None
        
    if len(normalized) > 50:  # More restrictive for registration
        return False, None
        
    # Check for reasonable character set (letters, numbers, spaces, basic punctuation)
    if not re.match(r'^[a-zA-Z0-9\s\.\-_\']+$', normalized):
        return False, None
        
    return True, normalized

# For backward compatibility and migration
def find_users_with_equivalent_usernames(session, target_username: str):
    """
    Find all users with usernames equivalent to the target username.
    Used for migration and duplicate detection.
    
    Args:
        session: Database session
        target_username: Username to find equivalents for
        
    Returns:
        List of User objects with equivalent usernames
    """
    from sqlmodel import select
    from models import User
    
    normalized_target = normalize_username_for_lookup(target_username)
    if not normalized_target:
        return []
    
    # Get all users and filter by normalized username
    # Note: This is not the most efficient approach for large datasets,
    # but it's reliable for finding all variations
    all_users = session.exec(select(User)).all()
    
    equivalent_users = []
    for user in all_users:
        if usernames_are_equivalent(user.display_name, target_username):
            equivalent_users.append(user)
    
    return equivalent_users