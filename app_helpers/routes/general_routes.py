# general_routes.py - General application routes
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import io

from app_helpers.services.auth_helpers import current_user
from app_helpers.services.auth.validation_helpers import is_admin
from app_helpers.timezone_utils import get_user_timezone_from_request
from models import engine, Session as SessionModel
from sqlmodel import Session

# Configuration constants
MULTI_DEVICE_AUTH_ENABLED = os.getenv("MULTI_DEVICE_AUTH_ENABLED", "true").lower() == "true"


# Use shared templates instance with filters registered
from app_helpers.shared_templates import templates

router = APIRouter()

@router.get("/menu", response_class=HTMLResponse)
def menu(request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    user_timezone = get_user_timezone_from_request(request)
    return templates.TemplateResponse(
        "menu.html",
        {"request": request, "me": user, "session": session, "is_admin": is_admin(user), "user_timezone": user_timezone}
    )

@router.get("/logged-out", response_class=HTMLResponse)
async def logged_out_page(request: Request):
    """Show logged-out confirmation page - no authentication required"""
    # Explicitly ensure no user data is passed to template
    return templates.TemplateResponse("logged_out.html", {
        "request": request,
        "me": None,  # Explicitly set user to None
        "MULTI_DEVICE_AUTH_ENABLED": MULTI_DEVICE_AUTH_ENABLED
    })

@router.get("/donate", response_class=HTMLResponse)
def donate(request: Request, user_session: tuple = Depends(current_user)):
    """Donation page with PayPal and Venmo options"""
    user, session = user_session
    
    # Get payment configuration from environment
    paypal_username = os.getenv("PAYPAL_USERNAME", "")
    venmo_handle = os.getenv("VENMO_HANDLE", "")
    
    return templates.TemplateResponse(
        "donate.html",
        {
            "request": request, 
            "me": user, 
            "session": session,
            "paypal_username": paypal_username,
            "venmo_handle": venmo_handle
        }
    )

@router.post("/dismiss-welcome")
async def dismiss_welcome(user_session: tuple = Depends(current_user)):
    """Dismiss the welcome message for the current user"""
    user, session = user_session
    
    with Session(engine) as db_session:
        # Update user's welcome message dismissal status
        user.welcome_message_dismissed = True
        db_session.add(user)
        db_session.commit()
    
    return JSONResponse({"success": True})

@router.get("/how-it-works", response_class=HTMLResponse)
def how_it_works(request: Request, user_session: tuple = Depends(current_user)):
    """How ThyWill Works - Technical explanation and architecture details"""
    user, session = user_session
    
    return templates.TemplateResponse(
        "how_it_works.html",
        {
            "request": request, 
            "me": user, 
            "session": session
        }
    )

@router.get("/export", response_class=HTMLResponse)
def export_page(request: Request, user_session: tuple = Depends(current_user)):
    """Community export information and download page - Text Archives."""
    user, session = user_session
    
    return templates.TemplateResponse(
        "export.html",
        {
            "request": request, 
            "me": user, 
            "session": session
        }
    )


@router.get("/export/text-archive")
async def export_text_archive(user_session: tuple = Depends(current_user)):
    """
    Export complete community text archive as ZIP file.
    Available to any authenticated user for community transparency.
    Contains human-readable text files organized by date and type.
    """
    user, session = user_session
    
    try:
        # Import the archive download service
        from app_helpers.services.archive_download_service import ArchiveDownloadService
        from app import TEXT_ARCHIVE_BASE_DIR
        from fastapi.responses import FileResponse
        
        # Create the service and generate the full community archive
        download_service = ArchiveDownloadService(TEXT_ARCHIVE_BASE_DIR)
        zip_path = download_service.create_full_community_zip()
        
        # Return the file for download
        filename = os.path.basename(zip_path)
        return FileResponse(
            path=zip_path,
            filename=filename,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Text archive export failed: {str(e)}"
        )


@router.post("/create-device-token")
def create_device_token_route(request: Request, user_session: tuple = Depends(current_user)):
    """Create a device token for current user."""
    from app_helpers.services.auth_helpers import require_full_auth
    from app_helpers.services.invite_helpers import create_device_token
    from app_helpers.services.token_service import TOKEN_EXP_H
    
    user, session = user_session
    
    # Check if user is fully authenticated
    if not session.is_fully_authenticated:
        raise HTTPException(401, "Full authentication required to create device tokens")
    
    try:
        # Create device token with shorter expiry (24 hours vs regular invite expiry)
        token = create_device_token(user.display_name, expiry_hours=24)
        device_url = f"{request.base_url}claim/{token}"
        
        return templates.TemplateResponse("device_token_modal.html", {
            "request": request,
            "token": token,
            "device_url": device_url,
            "expires_hours": 24,  # Device tokens expire faster
            "user": user
        })
    except Exception as e:
        raise HTTPException(500, f"Failed to create device token: {str(e)}")