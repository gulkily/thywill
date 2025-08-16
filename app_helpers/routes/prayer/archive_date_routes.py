# app_helpers/routes/prayer/archive_date_routes.py
"""
Archive date management routes for auto-archive functionality.
"""

from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from sqlmodel import Session

from models import engine, Prayer
from app_helpers.services.auth_helpers import current_user
from app_helpers.services.prayer_helpers import dismiss_archive_suggestion, postpone_archive_suggestion

# Create router
router = APIRouter()


@router.post("/prayer/{prayer_id}/dismiss-archive-suggestion")
def dismiss_archive_suggestion_route(prayer_id: str, 
                                   user_session: tuple = Depends(current_user)):
    """Dismiss archive suggestion for a prayer"""
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    
    with Session(engine) as s:
        # Verify prayer exists and user is author
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            raise HTTPException(404, "Prayer not found")
        
        if prayer.author_username != user.display_name:
            raise HTTPException(403, "Only prayer author can dismiss archive suggestions")
        
        success = dismiss_archive_suggestion(prayer_id, user.display_name, s)
        if not success:
            raise HTTPException(400, "Failed to dismiss archive suggestion")
    
    return JSONResponse({"success": True, "message": "Archive suggestion dismissed"})


@router.post("/prayer/{prayer_id}/postpone-archive-suggestion")
def postpone_archive_suggestion_route(prayer_id: str,
                                    days: int = Form(...),
                                    user_session: tuple = Depends(current_user)):
    """Postpone archive suggestion by specified days"""
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    
    if days < 1 or days > 365:
        raise HTTPException(400, "Days must be between 1 and 365")
    
    with Session(engine) as s:
        # Verify prayer exists and user is author
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            raise HTTPException(404, "Prayer not found")
        
        if prayer.author_username != user.display_name:
            raise HTTPException(403, "Only prayer author can postpone archive suggestions")
        
        success = postpone_archive_suggestion(prayer_id, days, s)
        if not success:
            raise HTTPException(400, "Failed to postpone archive suggestion")
    
    return JSONResponse({"success": True, "message": f"Archive suggestion postponed by {days} days"})