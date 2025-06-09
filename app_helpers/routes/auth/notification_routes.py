# app_helpers/routes/auth/notification_routes.py - Notification system handlers
"""
Notification system route handlers for authentication.

This module contains:
- Notification endpoints for authentication requests
- Notification verification and approval workflows
- HTMX notification content delivery
"""

import os
import time
from datetime import datetime

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

# Import helper functions
from app_helpers.services.auth_helpers import (
    current_user, get_unread_auth_notifications, mark_notification_read,
    validate_verification_code, approve_auth_request
)

# Template and config setup
templates = Jinja2Templates(directory="templates")
router = APIRouter()

# Configuration
REQUIRE_VERIFICATION_CODE = os.getenv("REQUIRE_VERIFICATION_CODE", "False").lower() == "true"


@router.get("/auth/notifications-test", response_class=HTMLResponse)
def get_notifications_test(request: Request, user_session: tuple = Depends(current_user)):
    """Simple test endpoint for notifications"""
    user, session = user_session
    return HTMLResponse(content=f'<div class="p-4">Test response for {user.display_name} at {datetime.utcnow()}</div>')


@router.get("/auth/notifications", response_class=HTMLResponse)
def get_notifications(request: Request, user_session: tuple = Depends(current_user)):
    """Get unread notifications for current user (HTMX endpoint)"""
    start_time = time.time()
    
    user, session = user_session
    
    # Check if user is fully authenticated
    if not session.is_fully_authenticated:
        return HTMLResponse(content='<div class="p-4 text-center text-gray-500">Full authentication required</div>')
    
    try:
        # Get notifications (always use template for consistency)
        db_start = time.time()
        notifications = get_unread_auth_notifications(user.id)
        notification_count = len(notifications)
        db_time = time.time() - db_start
        
        context = {
            "request": request,
            "notifications": notifications,
            "notification_count": notification_count,
            "user": user,
            "require_verification_code": REQUIRE_VERIFICATION_CODE
        }
        
        template_start = time.time()
        response = templates.TemplateResponse("components/notification_content.html", context)
        template_time = time.time() - template_start
        
        total_time = time.time() - start_time
        print(f"Notification endpoint timing: DB={db_time:.3f}s, Template={template_time:.3f}s, Total={total_time:.3f}s ({notification_count} notifications)")
        
        return response
    
    except Exception as e:
        print(f"Error in get_notifications: {e}")
        # Return error content
        error_html = f"""
        <div class="p-4 text-center">
            <div class="text-red-500 mb-2">Error loading notifications</div>
            <div class="text-xs text-gray-500">Please try refreshing the page</div>
        </div>
        """
        return HTMLResponse(content=error_html)


@router.post("/auth/notifications/{notification_id}/read")
def mark_notification_as_read(
    notification_id: str, 
    request: Request,
    user_session: tuple = Depends(current_user)
):
    """Mark notification as read"""
    user, session = user_session
    
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    
    success = mark_notification_read(notification_id, user.id)
    if not success:
        raise HTTPException(404, "Notification not found")
    
    # Return updated notifications
    return get_notifications(request, user_session)


@router.post("/auth/notifications/{notification_id}/verify")
def verify_notification_code(
    notification_id: str,
    verification_code: str = Form(...),
    user_session: tuple = Depends(current_user)
):
    """Validate verification code before approval"""
    user, session = user_session
    
    if not session.is_fully_authenticated:
        return {"success": False, "error_type": "auth_required", "message": "Full authentication required"}
    
    result = validate_verification_code(notification_id, user.id, verification_code)
    return result


@router.post("/auth/notifications/{notification_id}/approve")
def approve_from_notification(
    notification_id: str,
    verification_code: str = Form(...),
    request: Request = None,
    user_session: tuple = Depends(current_user)
):
    """Approve auth request with mandatory verification code validation"""
    user, session = user_session
    
    # Check if user is fully authenticated
    if not session.is_fully_authenticated:
        return {
            "success": False,
            "error_type": "auth_required",
            "message": "Full authentication required"
        }
    
    # First validate the verification code
    validation_result = validate_verification_code(notification_id, user.id, verification_code)
    
    if not validation_result["success"]:
        return {
            "success": False,
            "error_type": validation_result["error_type"],
            "message": validation_result["message"],
            "similar_codes": validation_result.get("similar_codes", [])
        }
    
    # If validation passed, approve the request
    auth_req = validation_result["auth_request"]
    approval_success = approve_auth_request(auth_req.id, user.id)
    
    if approval_success:
        # Mark notification as read
        mark_notification_read(notification_id, user.id)
        
        return {
            "success": True,
            "message": "Authentication request approved successfully"
        }
    else:
        return {
            "success": False,
            "error_type": "approval_failed",
            "message": "Failed to approve authentication request"
        }