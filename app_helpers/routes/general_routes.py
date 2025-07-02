# general_routes.py - General application routes
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import io

from app_helpers.services.auth_helpers import current_user
from app_helpers.services.auth.validation_helpers import is_admin
from models import engine, Session as SessionModel
from sqlmodel import Session

# Configuration constants
MULTI_DEVICE_AUTH_ENABLED = os.getenv("MULTI_DEVICE_AUTH_ENABLED", "true").lower() == "true"


templates = Jinja2Templates(directory="templates")

router = APIRouter()

@router.get("/menu", response_class=HTMLResponse)
def menu(request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    return templates.TemplateResponse(
        "menu.html",
        {"request": request, "me": user, "session": session, "is_admin": is_admin(user)}
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