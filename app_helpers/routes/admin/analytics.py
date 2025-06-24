"""
Admin Analytics Routes

Contains routes for statistical analysis and reporting.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlmodel import Session

# Import models
from models import engine

# Import helper functions
from app_helpers.services.auth_helpers import current_user, is_admin
from app_helpers.services.prayer_helpers import get_religious_preference_stats

# Create router for this module
router = APIRouter()


@router.get("/api/religious-stats")
async def get_religious_stats(request: Request, user_session: tuple = Depends(current_user)):
    """
    Religious Preference Statistics API
    
    Returns statistical data about religious preferences across the user base.
    This API endpoint provides insights for administrators about the community's
    religious diversity and preferences.
    
    Returns JSON data with:
    - Distribution of religious preferences
    - Prayer style preferences among Christians
    - User counts and percentages
    
    Requires admin privileges.
    """
    user, session = user_session
    
    if not is_admin(user):
        raise HTTPException(403, "Admin access required")
    
    with Session(engine) as db:
        stats = get_religious_preference_stats(db)
        return stats


@router.get("/api/religious-preference-stats")
async def get_religious_preference_stats_api(request: Request, user_session: tuple = Depends(current_user)):
    """
    Religious Preference Statistics API (alternative endpoint)
    
    Returns statistical data about religious preferences across the user base.
    This API endpoint provides insights for administrators about the community's
    religious diversity and preferences.
    
    Returns JSON data with:
    - Distribution of religious preferences
    - Prayer style preferences among Christians
    - User counts and percentages
    
    Requires admin privileges.
    """
    user, session = user_session
    
    if not is_admin(user):
        raise HTTPException(403, "Admin access required")
    
    with Session(engine) as db:
        stats = get_religious_preference_stats(db)
        return stats