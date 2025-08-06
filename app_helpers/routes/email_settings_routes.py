"""
Email Settings Routes - User email management endpoints
"""
import os
from fastapi import APIRouter, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from app_helpers.services.auth_helpers import current_user
from app_helpers.services.email_management_service import EmailManagementService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/settings/email/add")
def add_email(
    request: Request,
    email: str = Form(...),
    user_session: tuple = Depends(current_user)
):
    """Add and verify email address for user account"""
    if not _is_email_auth_enabled():
        raise HTTPException(status_code=404, detail="Email authentication is not enabled")
    
    user, session = user_session
    email_service = EmailManagementService()
    
    try:
        success, message = email_service.add_user_email(user.display_name, email)
        
        if success:
            return RedirectResponse(
                url="/profile?email_success=" + message.replace(' ', '+'),
                status_code=303
            )
        else:
            return RedirectResponse(
                url="/profile?email_error=" + message.replace(' ', '+'),
                status_code=303
            )
    
    except Exception as e:
        logger.error(f"Error adding email for user {user.display_name}: {e}")
        return RedirectResponse(
            url="/profile?email_error=An+error+occurred.+Please+try+again.",
            status_code=303
        )

@router.post("/settings/email/change")
def change_email(
    request: Request,
    new_email: str = Form(...),
    user_session: tuple = Depends(current_user)
):
    """Change user's email address (requires new verification)"""
    if not _is_email_auth_enabled():
        raise HTTPException(status_code=404, detail="Email authentication is not enabled")
    
    user, session = user_session
    email_service = EmailManagementService()
    
    try:
        # Add new email without removing current one (allow_pending=True)
        success, message = email_service.add_user_email(user.display_name, new_email, allow_pending=True)
        
        if success:
            return RedirectResponse(
                url="/profile?email_success=" + message.replace(' ', '+'),
                status_code=303
            )
        else:
            return RedirectResponse(
                url="/profile?email_error=" + message.replace(' ', '+'),
                status_code=303
            )
    
    except Exception as e:
        logger.error(f"Error changing email for user {user.display_name}: {e}")
        return RedirectResponse(
            url="/profile?email_error=An+error+occurred.+Please+try+again.",
            status_code=303
        )

@router.post("/settings/email/remove")
def remove_email(
    request: Request,
    user_session: tuple = Depends(current_user)
):
    """Remove email association from user account"""
    if not _is_email_auth_enabled():
        raise HTTPException(status_code=404, detail="Email authentication is not enabled")
    
    user, session = user_session
    email_service = EmailManagementService()
    
    try:
        success = email_service.remove_user_email(user.display_name)
        
        if success:
            return RedirectResponse(
                url="/profile?email_success=Email+address+removed+successfully.",
                status_code=303
            )
        else:
            return RedirectResponse(
                url="/profile?email_error=No+email+address+found+to+remove.",
                status_code=303
            )
    
    except Exception as e:
        logger.error(f"Error removing email for user {user.display_name}: {e}")
        return RedirectResponse(
            url="/profile?email_error=An+error+occurred.+Please+try+again.",
            status_code=303
        )

@router.post("/auth/email-recovery")
def email_recovery(
    request: Request,
    email: str = Form(...)
):
    """Handle email recovery request"""
    if not _is_email_auth_enabled():
        raise HTTPException(status_code=404, detail="Email authentication is not enabled")
    
    email_service = EmailManagementService()
    
    try:
        # Always return success to prevent email enumeration
        email_service.send_recovery_email(email)
        return RedirectResponse(
            url="/login?recovery_sent=true",
            status_code=303
        )
    
    except Exception as e:
        logger.error(f"Error in email recovery: {e}")
        # Still return success to prevent email enumeration
        return RedirectResponse(
            url="/login?recovery_sent=true",
            status_code=303
        )

def _is_email_auth_enabled() -> bool:
    """Check if email authentication is enabled via feature flag"""
    return os.getenv('EMAIL_AUTH_ENABLED', 'false').lower() == 'true'