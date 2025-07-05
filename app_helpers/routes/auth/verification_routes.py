# app_helpers/routes/auth/verification_routes.py - Authentication status and verification handlers
"""
Authentication status and verification route handlers.

This module contains:
- Authentication status monitoring
- HTMX status check endpoints
- Status display and verification logic
"""

import os
from datetime import datetime

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from models import (
    engine, User, AuthenticationRequest, AuthApproval, Session as SessionModel
)

# Import helper functions
from app_helpers.services.auth_helpers import current_user

# Template and config setup
# Use shared templates instance with filters registered
from app_helpers.shared_templates import templates
router = APIRouter()

# Configuration
PEER_APPROVAL_COUNT = int(os.getenv("PEER_APPROVAL_COUNT", 2))
REQUIRE_VERIFICATION_CODE = os.getenv("REQUIRE_VERIFICATION_CODE", "False").lower() == "true"


@router.get("/auth/status", response_class=HTMLResponse)
def auth_status(request: Request, user_session: tuple = Depends(current_user)):
    """
    Show authentication status for half-authenticated users.
    
    Displays pending authentication request status, approval progress,
    and automatically upgrades to full authentication if request is approved.
    
    Args:
        request: FastAPI request object
        user_session: Current user and session from dependency
        
    Returns:
        HTMLResponse: auth_pending.html template with status info, or
        RedirectResponse: To main feed if already fully authenticated
        
    Raises:
        HTTPException: 404 if authentication request not found
    """
    user, session = user_session
    
    if session.is_fully_authenticated:
        return RedirectResponse("/", 303)
    
    with Session(engine) as db:
        auth_req = db.get(AuthenticationRequest, session.auth_request_id)
        if not auth_req:
            raise HTTPException(404, "Authentication request not found")
        
        # Get approval count and approvers
        approvals = db.exec(
            select(AuthApproval)
            .where(AuthApproval.auth_request_id == auth_req.id)
        ).all()
        
        approval_info = []
        for approval in approvals:
            # Get the approver's display name
            approver = db.get(User, approval.approver_user_id)
            approver_name = approver.display_name if approver else approval.approver_user_id
            
            approval_info.append({
                'approver_name': approver_name,
                'approved_at': approval.created_at,
                'is_admin': approval.approver_user_id == "admin",
                'is_self': approval.approver_user_id == user.display_name
            })
        
        # Check if approved
        if auth_req.status == "approved":
            # Upgrade session to full authentication
            session.is_fully_authenticated = True
            db.add(session)
            db.commit()
            return RedirectResponse("/", 303)
        
        context = {
            "request": request,
            "user": user,
            "auth_request": auth_req,
            "approvals": approval_info,
            "approval_count": len(approval_info),
            "needs_approvals": PEER_APPROVAL_COUNT - len(approval_info) if len(approval_info) < PEER_APPROVAL_COUNT else 0,
            "peer_approval_count": PEER_APPROVAL_COUNT,
            "require_verification_code": REQUIRE_VERIFICATION_CODE
        }
        
        return templates.TemplateResponse("auth_pending.html", context)


@router.get("/auth/status-check", response_class=HTMLResponse)
def auth_status_check(request: Request, user_session: tuple = Depends(current_user)):
    """
    HTMX endpoint for checking authentication status updates.
    
    Returns just the approval status section for live updates without full page refresh.
    If user is approved, returns a redirect trigger to main page.
    
    Args:
        request: FastAPI request object
        user_session: Current user and session from dependency
        
    Returns:
        HTMLResponse: Status section HTML or redirect trigger
    """
    user, session = user_session
    
    # If already fully authenticated, trigger redirect
    if session.is_fully_authenticated:
        return HTMLResponse("""
            <div hx-trigger="load" hx-get="/" hx-target="body" hx-swap="outerHTML">
                <div class="text-center text-green-600 dark:text-green-400 font-medium">
                    ✅ Approved! Redirecting to main page...
                </div>
            </div>
        """)
    
    with Session(engine) as db:
        auth_req = db.get(AuthenticationRequest, session.auth_request_id)
        if not auth_req:
            return HTMLResponse('''
            <div class="border border-red-200 dark:border-red-700 rounded-lg p-4 bg-red-50 dark:bg-red-900/50">
                <div class="flex items-start">
                    <div class="flex-shrink-0">
                        <svg class="w-5 h-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-sm font-medium text-red-800 dark:text-red-200">Request Not Found</h3>
                        <div class="mt-2 text-sm text-red-700 dark:text-red-300">
                            <p>Your authentication request has expired or doesn't exist.</p>
                            <div class="mt-3">
                                <a href="/login" class="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-red-700 dark:text-red-200 bg-red-100 dark:bg-red-800 hover:bg-red-200 dark:hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500">
                                    Start New Request
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            ''')
        
        # Check if approved (same logic as main auth_status route)
        if auth_req.status == "approved":
            # Upgrade session to full authentication
            session.is_fully_authenticated = True
            db.add(session)
            db.commit()
            
            # Return redirect trigger
            return HTMLResponse("""
                <div hx-trigger="load" hx-get="/" hx-target="body" hx-swap="outerHTML">
                    <div class="text-center text-green-600 dark:text-green-400 font-medium">
                        ✅ Approved! Redirecting to main page...
                    </div>
                </div>
            """)
        
        # Get approval info (same as main route)
        approvals = db.exec(
            select(AuthApproval)
            .where(AuthApproval.auth_request_id == auth_req.id)
        ).all()
        
        approval_info = []
        for approval in approvals:
            # Get the approver's display name
            approver = db.get(User, approval.approver_user_id)
            approver_name = approver.display_name if approver else approval.approver_user_id
            
            approval_info.append({
                'approver_name': approver_name,
                'approved_at': approval.created_at,
                'is_admin': approval.approver_user_id == "admin",
                'is_self': approval.approver_user_id == user.display_name
            })
        
        context = {
            "request": request,
            "user": user,
            "auth_request": auth_req,
            "approvals": approval_info,
            "approval_count": len(approval_info),
            "needs_approvals": PEER_APPROVAL_COUNT - len(approval_info) if len(approval_info) < PEER_APPROVAL_COUNT else 0,
            "peer_approval_count": PEER_APPROVAL_COUNT,
            "require_verification_code": REQUIRE_VERIFICATION_CODE
        }
        
        # Return just the status section HTML
        return HTMLResponse(f"""
            <div id="approval-status" 
                 class="border border-gray-200 dark:border-gray-700 rounded-lg p-4"
                 hx-get="/auth/status-check" 
                 hx-trigger="every 5s" 
                 hx-target="#approval-status" 
                 hx-swap="outerHTML">
              <h3 class="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">Approval Status</h3>
              
              <div class="space-y-3">
                <div class="flex items-center justify-between">
                  <span class="text-sm text-gray-600 dark:text-gray-400">Request created:</span>
                  <span class="text-sm font-medium text-gray-900 dark:text-gray-100">{auth_req.created_at.strftime('%b %d, %Y at %I:%M %p')}</span>
                </div>
                
                <div class="flex items-center justify-between">
                  <span class="text-sm text-gray-600 dark:text-gray-400">Expires:</span>
                  <span class="text-sm font-medium text-gray-900 dark:text-gray-100">{auth_req.expires_at.strftime('%b %d, %Y at %I:%M %p')}</span>
                </div>
                
                <div class="flex items-center justify-between">
                  <span class="text-sm text-gray-600 dark:text-gray-400">Current approvals:</span>
                  <span class="text-sm font-medium text-gray-900 dark:text-gray-100">{len(approval_info)}</span>
                </div>
                
                {f'''<div class="flex items-center justify-between">
                  <span class="text-sm text-gray-600 dark:text-gray-400">Still needed:</span>
                  <span class="text-sm font-medium text-yellow-600 dark:text-yellow-400">{PEER_APPROVAL_COUNT - len(approval_info)} more approval{'s' if PEER_APPROVAL_COUNT - len(approval_info) != 1 else ''}</span>
                </div>''' if len(approval_info) < PEER_APPROVAL_COUNT else ''}
                
                <!-- Live status indicator -->
                <div class="flex items-center justify-between pt-2 border-t border-gray-100 dark:border-gray-600">
                  <span class="text-xs text-gray-500 dark:text-gray-400">Status updates:</span>
                  <span class="text-xs text-green-600 dark:text-green-400">Live (checking every 5s)</span>
                </div>
              </div>
            </div>
        """)