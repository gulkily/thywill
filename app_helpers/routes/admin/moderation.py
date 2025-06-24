"""
Admin Content Moderation Routes

Contains routes for managing content moderation including flagging and unflagging prayers.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session

# Import models
from models import engine, Prayer

# Import helper functions
from app_helpers.services.auth_helpers import current_user, is_admin

# Create router for this module
router = APIRouter()


@router.post("/admin/flag-prayer/{prayer_id}")
def flag_prayer(prayer_id: str, request: Request, user_session: tuple = Depends(current_user)):
    """
    Flag Prayer as Admin
    
    Flags a prayer for admin review. This action is used when a prayer
    contains inappropriate content or violates community guidelines.
    
    Requires admin privileges.
    
    Returns a redirect to the admin dashboard.
    """
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403)
    
    with Session(engine) as s:
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            raise HTTPException(404, "Prayer not found")
        
        prayer.flagged = True
        s.add(prayer)
        s.commit()
        
        # Note: Prayer flagging is logged through the flagged field change
        # For more detailed logging, consider using PrayerActivityLog instead
    
    return RedirectResponse("/admin", 303)


@router.post("/admin/unflag-prayer/{prayer_id}")
def unflag_prayer(prayer_id: str, request: Request, user_session: tuple = Depends(current_user)):
    """
    Unflag Prayer as Admin
    
    Removes the flag from a prayer, marking it as approved for the community.
    This action is used when a flagged prayer has been reviewed and found
    to be appropriate.
    
    Requires admin privileges.
    
    Returns a redirect to the admin dashboard.
    """
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403)
    
    with Session(engine) as s:
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            raise HTTPException(404, "Prayer not found")
        
        prayer.flagged = False
        s.add(prayer)
        s.commit()
        
        # Note: Prayer unflagging is logged through the flagged field change
        # For more detailed logging, consider using PrayerActivityLog instead
    
    return RedirectResponse("/admin", 303)