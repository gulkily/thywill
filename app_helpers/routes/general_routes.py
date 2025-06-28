# general_routes.py - General application routes
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import io

from app_helpers.services.auth_helpers import current_user
from app_helpers.services.export_service import CommunityExportService
from models import engine, Session as SessionModel
from sqlmodel import Session

# Configuration constants
MULTI_DEVICE_AUTH_ENABLED = os.getenv("MULTI_DEVICE_AUTH_ENABLED", "true").lower() == "true"

# Rate limiting for exports - store last export time per user
_user_last_export = {}

templates = Jinja2Templates(directory="templates")

router = APIRouter()

@router.get("/menu", response_class=HTMLResponse)
def menu(request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    return templates.TemplateResponse(
        "menu.html",
        {"request": request, "me": user, "session": session}
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
    paypal_username = os.getenv("PAYPAL_USERNAME", "YourPayPalUsername")
    venmo_handle = os.getenv("VENMO_HANDLE", "YourVenmoHandle")
    
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
    """Community export information and download page."""
    user, session = user_session
    
    # Get export statistics for server-side rendering
    from app_helpers.services.export_service import CommunityExportService
    export_service = CommunityExportService()
    export_info = export_service.get_export_info()
    
    return templates.TemplateResponse(
        "export.html",
        {
            "request": request, 
            "me": user, 
            "session": session,
            "export_info": export_info
        }
    )

@router.get("/export/info")
async def export_info(user_session: tuple = Depends(current_user)):
    """Get export information and statistics."""
    user, session = user_session
    
    # Initialize export service
    export_service = CommunityExportService()
    
    # Get export info
    info = export_service.get_export_info()
    
    return JSONResponse(info)

@router.get("/export/database")
async def export_database(user_session: tuple = Depends(current_user)):
    """
    Export complete community database as ZIP file.
    Available to any authenticated user for community maintenance.
    Includes intelligent caching and rate limiting.
    """
    user, session = user_session
    
    # Rate limiting: prevent too frequent exports
    rate_limit_minutes = int(os.getenv("EXPORT_RATE_LIMIT_MINUTES", "2"))  # Default 2 minutes
    current_time = datetime.utcnow()
    
    if user.id in _user_last_export:
        time_since_last = current_time - _user_last_export[user.id]
        if time_since_last < timedelta(minutes=rate_limit_minutes):
            remaining_seconds = int((timedelta(minutes=rate_limit_minutes) - time_since_last).total_seconds())
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Please wait {remaining_seconds} seconds before requesting another export."
            )
    
    # Initialize export service
    export_service = CommunityExportService()
    
    # Generate filename with current date
    current_date = datetime.utcnow().strftime("%Y-%m-%d")
    filename = f"community_export_{current_date}.zip"
    
    # Get export data as ZIP (with caching)
    zip_data, from_cache = export_service.export_to_zip()
    
    # Update rate limiting tracker only for fresh exports
    if not from_cache:
        _user_last_export[user.id] = current_time
    
    # Create streaming response
    def generate():
        # Stream the ZIP data in chunks for memory efficiency
        chunk_size = 8192
        
        for i in range(0, len(zip_data), chunk_size):
            yield zip_data[i:i + chunk_size]
    
    # Add cache headers
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Content-Type": "application/zip"
    }
    
    if from_cache:
        headers["X-Cache-Status"] = "HIT"
    else:
        headers["X-Cache-Status"] = "MISS"
    
    return StreamingResponse(
        generate(),
        media_type="application/zip",
        headers=headers
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