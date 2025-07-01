# app_helpers/routes/auth/notification_routes.py - Simplified notification handlers
"""
Simplified notification system route handlers for authentication.

This module contains:
- Read-only notification display for authentication requests
- HTMX notification content delivery
- Redirect users to /auth/pending for all management actions
"""

import time
from datetime import datetime

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

# Import helper functions
from app_helpers.services.auth_helpers import (
    current_user, get_unread_auth_notifications, mark_notification_read
)

# Template and config setup
templates = Jinja2Templates(directory="templates")
router = APIRouter()


@router.get("/auth/notifications", response_class=HTMLResponse)
def get_notifications(request: Request, user_session: tuple = Depends(current_user)):
    """Get pending auth requests for notification display (read-only)"""
    user, session = user_session
    
    # Check if user is fully authenticated
    if not session.is_fully_authenticated:
        return HTMLResponse(content='<div class="p-4 text-center text-gray-500">Please complete authentication</div>')
    
    try:
        notifications = get_unread_auth_notifications(user.display_name)
        
        context = {
            "request": request,
            "notifications": notifications,
            "user": user
        }
        
        return templates.TemplateResponse("components/notification_content.html", context)
    
    except Exception as e:
        print(f"Error in get_notifications: {e}")
        # Return error content with link to auth pending page
        error_html = """
        <div class="p-4 text-center">
            <div class="text-red-500 mb-2">Error loading notifications</div>
            <div class="text-xs text-gray-500 mb-3">Please try refreshing the page</div>
            <a href="/auth/pending" class="text-blue-600 hover:text-blue-700 text-sm">
                Go to Authentication Requests →
            </a>
        </div>
        """
        return HTMLResponse(content=error_html)


@router.post("/auth/notifications/{notification_id}/read")
def mark_notification_as_read(
    notification_id: str, 
    user_session: tuple = Depends(current_user)
):
    """Mark notification as read and redirect to auth pending page"""
    user, session = user_session
    
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Authentication required")
    
    success = mark_notification_read(notification_id, user.display_name)
    if not success:
        raise HTTPException(404, "Notification not found")
    
    # Redirect to auth pending page for management
    return RedirectResponse("/auth/pending", 303)