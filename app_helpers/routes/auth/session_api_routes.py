# app_helpers/routes/auth/session_api_routes.py - Session persistence API endpoints
"""
Session persistence API endpoints for LocalStorage backup/restore functionality.

Provides minimal endpoints to support frontend session persistence:
- POST /api/session/backup - Backup current session data for authenticated users
- POST /api/session/restore - Restore session from LocalStorage backup
- GET /api/session/info - Get current session info for backup purposes
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlmodel import Session

from models import engine, User, Session as SessionModel
from app_helpers.services.auth.session_helpers import current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Request/Response models
class SessionBackupRequest(BaseModel):
    userData: Optional[Dict[str, Any]] = None

class SessionRestoreRequest(BaseModel):
    sessionId: str
    userData: Optional[Dict[str, Any]] = None

class SessionInfoResponse(BaseModel):
    sessionId: str
    userId: str
    displayName: str
    expiresAt: str
    isFullyAuthenticated: bool


@router.get("/api/session/info", response_model=SessionInfoResponse)
async def get_session_info(request: Request):
    """
    Get current session information for backup purposes.
    
    Since session cookies are httpOnly, frontend needs this endpoint 
    to get session data for LocalStorage backup.
    """
    try:
        user, session = current_user(request)
        
        return SessionInfoResponse(
            sessionId=session.id,
            userId=user.display_name,  # display_name is the primary key
            displayName=user.display_name,
            expiresAt=session.expires_at.isoformat(),
            isFullyAuthenticated=session.is_fully_authenticated
        )
        
    except HTTPException as e:
        # Re-raise authentication errors
        raise e
    except Exception as e:
        logger.error(f"Error getting session info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/session/backup")
async def backup_session_data(
    backup_request: SessionBackupRequest,
    request: Request
):
    """
    Acknowledge session backup request.
    
    This endpoint mainly serves to validate the current session
    and log backup events. The actual backup is handled by frontend.
    """
    try:
        user, session = current_user(request)
        
        # Log backup event for audit trail
        logger.info(f"Session backup initiated for user {user.display_name} (session {session.id})")
        
        return JSONResponse(content={
            "status": "success",
            "message": "Session backup acknowledged",
            "sessionId": session.id,
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except HTTPException as e:
        # Re-raise authentication errors  
        raise e
    except Exception as e:
        logger.error(f"Error handling session backup: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/api/session/restore") 
async def restore_session_cookie(
    restore_request: SessionRestoreRequest,
    request: Request
):
    """
    Restore session cookie from LocalStorage backup.
    
    Validates the session ID against the database and sets the session cookie
    if the session is still valid.
    """
    try:
        session_id = restore_request.sessionId
        
        if not session_id:
            raise HTTPException(status_code=400, detail="Session ID required")
        
        # Validate session against database
        with Session(engine) as db:
            session = db.get(SessionModel, session_id)
            
            if not session:
                logger.warning(f"Session restore failed: Invalid session ID {session_id}")
                raise HTTPException(status_code=401, detail="Invalid session")
                
            if session.expires_at < datetime.utcnow():
                logger.warning(f"Session restore failed: Expired session {session_id}")
                raise HTTPException(status_code=401, detail="Expired session")
            
            # Validate user still exists
            user = db.get(User, session.username)
            if not user:
                logger.warning(f"Session restore failed: User not found for session {session_id}")
                raise HTTPException(status_code=401, detail="User not found")
            
            # Check if user is deactivated
            from app_helpers.utils.user_management import is_user_deactivated
            if is_user_deactivated(user.display_name):
                logger.warning(f"Session restore failed: User {user.display_name} is deactivated")
                raise HTTPException(status_code=401, detail="User account deactivated")
        
        # Log successful restore
        logger.info(f"Session restored successfully for user {user.display_name} (session {session_id})")
        
        # Create response with session cookie
        from fastapi.responses import JSONResponse
        response = JSONResponse(content={
            "status": "success",
            "message": "Session restored successfully",
            "sessionId": session_id,
            "userId": user.display_name,
            "displayName": user.display_name,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Set the session cookie (matching existing cookie settings)
        from app_helpers.services.auth.session_helpers import SESSION_DAYS
        response.set_cookie(
            "sid", 
            session_id, 
            httponly=True, 
            max_age=60*60*24*SESSION_DAYS,
            secure=request.url.scheme == "https",
            samesite="lax"
        )
        
        return response
        
    except HTTPException as e:
        # Re-raise HTTP exceptions (validation errors, auth errors)
        raise e
    except Exception as e:
        logger.error(f"Error restoring session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/api/session/clear")
async def clear_session_data(request: Request):
    """
    Clear session data (logout).
    
    This endpoint provides an API way to clear session data,
    useful for frontend session persistence cleanup.
    """
    try:
        # Try to get current session, but don't fail if none exists
        try:
            user, session = current_user(request)
            logger.info(f"Session cleared via API for user {user.display_name} (session {session.id})")
        except HTTPException:
            # No active session, that's fine
            logger.info("Session clear requested but no active session found")
        
        # Create response that clears the session cookie
        response = JSONResponse(content={
            "status": "success",
            "message": "Session cleared",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Clear the session cookie
        response.delete_cookie("sid")
        
        return response
        
    except Exception as e:
        logger.error(f"Error clearing session: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")