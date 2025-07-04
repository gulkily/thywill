# app_helpers/services/token_service.py
"""
Centralized token service for invite token creation and management.
Consolidates all token generation logic to eliminate duplication.
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlmodel import Session

from models import InviteToken, engine

# Single source of truth for token expiration configuration
TOKEN_EXP_H = int(os.getenv("INVITE_TOKEN_EXPIRATION_HOURS", "12"))
# Default max uses for invite tokens
DEFAULT_INVITE_MAX_USES = int(os.getenv("DEFAULT_INVITE_MAX_USES", "1"))

def generate_invite_token() -> str:
    """
    Generate a secure invite token.
    
    Uses 8 random bytes converted to hexadecimal, resulting in a 16-character
    token using only 0-9a-f characters. This provides 64 bits of entropy
    which is cryptographically secure while being shorter than UUIDs.
    
    Returns:
        str: A 16-character hexadecimal token
    """
    return secrets.token_hex(8)

def calculate_expiration_time(hours: Optional[int] = None) -> datetime:
    """
    Calculate expiration time for invite tokens.
    
    Args:
        hours: Number of hours until expiration. If None, uses TOKEN_EXP_H
        
    Returns:
        datetime: UTC datetime when token should expire
    """
    expiration_hours = hours if hours is not None else TOKEN_EXP_H
    return datetime.utcnow() + timedelta(hours=expiration_hours)

def create_invite_token(
    created_by_user: str,
    custom_token: Optional[str] = None,
    custom_expiration_hours: Optional[int] = None,
    max_uses: Optional[int] = None,
    db_session: Optional[Session] = None
) -> dict:
    """
    Create and save an invite token to the database.
    
    Args:
        created_by_user: Username of the user creating the token
        custom_token: Optional custom token string (if None, generates one)
        custom_expiration_hours: Optional custom expiration time in hours
        max_uses: Optional maximum number of uses (if None, uses DEFAULT_INVITE_MAX_USES)
        db_session: Optional existing database session to use
        
    Returns:
        dict: Token information (token, expires_at, created_by_user, usage_count, max_uses)
    """
    token_str = custom_token or generate_invite_token()
    expires_at = calculate_expiration_time(custom_expiration_hours)
    token_max_uses = max_uses if max_uses is not None else DEFAULT_INVITE_MAX_USES
    
    invite_token = InviteToken(
        token=token_str,
        created_by_user=created_by_user,
        expires_at=expires_at,
        usage_count=0,
        max_uses=token_max_uses,
        used_by_user_id=None
    )
    
    # Use provided session or create a new one
    if db_session:
        db_session.add(invite_token)
        db_session.flush()  # Don't commit, let caller handle it
        # Capture values while session is active
        result = {
            'token': invite_token.token,
            'expires_at': invite_token.expires_at,
            'created_by_user': invite_token.created_by_user,
            'usage_count': invite_token.usage_count,
            'max_uses': invite_token.max_uses,
            'used': invite_token.used  # Backward compatibility property
        }
    else:
        with Session(engine) as session:
            session.add(invite_token)
            session.commit()
            # Capture values while session is still active
            result = {
                'token': invite_token.token,
                'expires_at': invite_token.expires_at,
                'created_by_user': invite_token.created_by_user,
                'usage_count': invite_token.usage_count,
                'max_uses': invite_token.max_uses,
                'used': invite_token.used  # Backward compatibility property
            }
    
    return result

def create_system_token(custom_expiration_hours: Optional[int] = None, max_uses: Optional[int] = None) -> dict:
    """
    Create a system-generated invite token (for admin use).
    
    Args:
        custom_expiration_hours: Optional custom expiration time in hours
        max_uses: Optional maximum number of uses
        
    Returns:
        dict: Token information (token, expires_at, created_by_user, usage_count, max_uses)
    """
    return create_invite_token(
        created_by_user="system",
        custom_expiration_hours=custom_expiration_hours,
        max_uses=max_uses
    )

def get_token_expiration_config() -> dict:
    """
    Get current token expiration configuration info.
    
    Returns:
        dict: Configuration information for debugging/display
    """
    return {
        'environment_variable': os.getenv("INVITE_TOKEN_EXPIRATION_HOURS"),
        'calculated_hours': TOKEN_EXP_H,
        'calculated_days': TOKEN_EXP_H / 24,
        'default_expiration_time': calculate_expiration_time()
    }