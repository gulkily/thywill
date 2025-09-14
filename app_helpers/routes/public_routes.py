# app_helpers/routes/public_routes.py
"""
Public routes for non-authenticated users.
Provides API endpoints for public prayer access with rate limiting.
"""

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from datetime import datetime, timedelta
from sqlmodel import Session, select, func
from models import engine, SecurityLog, User, Session as SessionModel
from app_helpers.services.public_prayer_service import PublicPrayerService
from app_helpers.services.username_display_service import UsernameDisplayService

router = APIRouter()

# Templates
templates = Jinja2Templates(directory="templates")

# Rate limiting configuration
PUBLIC_RATE_LIMIT_PER_MINUTE = 100  # Increased for development
PUBLIC_RATE_LIMIT_PER_HOUR = 1000   # Increased for development


def check_public_rate_limit(request: Request) -> bool:
    """
    Check rate limiting for public endpoints.
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if request is allowed, False if rate limited
    """
    client_ip = request.client.host if request.client else "unknown"
    
    with Session(engine) as session:
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        
        # Count requests in last minute
        minute_count = session.exec(
            select(func.count(SecurityLog.id))
            .where(SecurityLog.ip_address == client_ip)
            .where(SecurityLog.event_type == "public_api_request")
            .where(SecurityLog.created_at > minute_ago)
        ).first() or 0
        
        # Count requests in last hour  
        hour_count = session.exec(
            select(func.count(SecurityLog.id))
            .where(SecurityLog.ip_address == client_ip)
            .where(SecurityLog.event_type == "public_api_request")
            .where(SecurityLog.created_at > hour_ago)
        ).first() or 0
        
        # Check limits
        if minute_count >= PUBLIC_RATE_LIMIT_PER_MINUTE:
            return False
        if hour_count >= PUBLIC_RATE_LIMIT_PER_HOUR:
            return False
            
        # Log this request for rate limiting
        log_entry = SecurityLog(
            user_id="public",
            ip_address=client_ip,
            event_type="public_api_request",
            details=f"Public API request to {request.url.path}"
        )
        session.add(log_entry)
        session.commit()
        
        return True


def is_user_authenticated(request: Request) -> bool:
    """
    Check if user is authenticated without raising exceptions.
    
    Returns:
        True if user has valid session, False otherwise
    """
    try:
        sid = request.cookies.get("sid")
        if not sid:
            return False
            
        with Session(engine) as session:
            sess = session.get(SessionModel, sid)
            if not sess:
                return False
            if sess.expires_at < datetime.utcnow():
                return False
            
            user = session.get(User, sess.username)
            if not user:
                return False
                
            return True
    except Exception:
        return False


@router.get("/", response_class=HTMLResponse)
async def public_homepage_or_redirect(request: Request):
    """
    Root route that serves public homepage for unauthenticated users
    and redirects authenticated users to their feed.
    """
    if is_user_authenticated(request):
        # User is authenticated, redirect to feed  
        return RedirectResponse("/feed", status_code=302)
    else:
        # User is not authenticated, serve public homepage
        return templates.TemplateResponse(
            "public_homepage.html",
            {"request": request}
        )


@router.get("/api/public/prayers")
async def get_public_prayers_api(
    request: Request,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=50, description="Number of prayers per page (max 50)")
):
    """
    Get paginated list of prayers eligible for public display.
    
    Rate limited: 10 requests per minute, 100 per hour per IP.
    """
    # Check rate limiting
    if not check_public_rate_limit(request):
        raise HTTPException(
            status_code=429, 
            detail="Rate limit exceeded. Please try again later."
        )
    
    try:
        # Get prayers from service
        result = PublicPrayerService.get_public_prayers(page=page, page_size=page_size)
        
        # Format prayers for JSON response with user display names
        formatted_prayers = []
        with Session(engine) as session:
            username_service = UsernameDisplayService()
            
            for prayer in result['prayers']:
                # Get formatted username with supporter badges
                display_name = username_service.render_username_with_badge(
                    prayer.author_username, session
                )
                
                # Get statistics for this prayer
                prayer_stats = result['statistics'].get(prayer.id, {})
                
                formatted_prayer = {
                    'id': prayer.id,
                    'text': prayer.text,
                    'generated_prayer': prayer.generated_prayer,
                    'author_username': prayer.author_username,
                    'author_display_name': display_name,
                    'created_at': prayer.created_at.isoformat(),
                    'project_tag': prayer.project_tag,
                    'total_prayers': prayer_stats.get('total_prayers', 0),
                    'unique_people': prayer_stats.get('unique_people', 0)
                }
                formatted_prayers.append(formatted_prayer)
        
        # Return formatted response
        return JSONResponse({
            'success': True,
            'prayers': formatted_prayers,
            'pagination': result['pagination']
        })
        
    except Exception as e:
        # Log error but don't expose details
        with Session(engine) as session:
            error_log = SecurityLog(
                user_id="public",
                ip_address=request.client.host if request.client else "unknown",
                event_type="public_api_error",
                details=f"Error in /api/public/prayers: {str(e)}"
            )
            session.add(error_log)
            session.commit()
        
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.get("/prayer/{prayer_id}", response_class=HTMLResponse)
async def public_prayer_page(
    prayer_id: str,
    request: Request
):
    """
    Serve individual prayer page template for public viewing.
    
    This route serves the HTML template that will fetch prayer data via JavaScript.
    The actual prayer data is loaded via the /api/public/prayer/{prayer_id} endpoint.
    """
    return templates.TemplateResponse(
        "public_prayer.html",
        {
            "request": request,
            "prayer_id": prayer_id
        }
    )


@router.get("/api/public/prayer/{prayer_id}")
async def get_public_prayer_api(
    prayer_id: str,
    request: Request
):
    """
    Get individual prayer by ID if eligible for public display.
    
    Rate limited: 10 requests per minute, 100 per hour per IP.
    """
    # Check rate limiting
    if not check_public_rate_limit(request):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    
    try:
        # Get prayer with user data
        result = PublicPrayerService.get_public_prayer_with_user(prayer_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Prayer not found or not available for public display"
            )
        
        prayer, user = result
        
        # Format prayer for JSON response
        with Session(engine) as session:
            username_service = UsernameDisplayService()
            display_name = username_service.render_username_with_badge(user.display_name, session)
        
        formatted_prayer = {
            'id': prayer.id,
            'text': prayer.text,
            'generated_prayer': prayer.generated_prayer,
            'author_username': prayer.author_username,
            'author_display_name': display_name,
            'created_at': prayer.created_at.isoformat(),
            'project_tag': prayer.project_tag
        }
        
        return JSONResponse({
            'success': True,
            'prayer': formatted_prayer
        })
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as e:
        # Log error but don't expose details
        with Session(engine) as session:
            error_log = SecurityLog(
                user_id="public",
                ip_address=request.client.host if request.client else "unknown",
                event_type="public_api_error", 
                details=f"Error in /api/public/prayer/{prayer_id}: {str(e)}"
            )
            session.add(error_log)
            session.commit()
        
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

# Duplicate route removed - already defined above at line 198

@router.get("/api/public/prayer/{prayer_id}/statistics")
async def get_public_prayer_statistics_api(
    prayer_id: str,
    request: Request
):
    """
    Get prayer statistics including who prayed and when.
    
    Rate limited: 10 requests per minute, 100 per hour per IP.
    """
    print(f"DEBUG: Starting statistics API for prayer {prayer_id}")
    
    # Check rate limiting
    if not check_public_rate_limit(request):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please try again later."
        )
    
    try:
        # First check if prayer is public-eligible
        prayer = PublicPrayerService.get_public_prayer_by_id(prayer_id)
        if not prayer:
            raise HTTPException(
                status_code=404,
                detail="Prayer not found or not available for public display"
            )
        
        # Get prayer statistics
        statistics = PublicPrayerService.get_prayer_statistics(prayer_id)
        
        # Format statistics with username display service for supporter badges
        with Session(engine) as session:
            username_service = UsernameDisplayService()
            
            # Add display names with supporter badges to prayer records
            for record in statistics['prayer_records']:
                record['display_name_html'] = username_service.render_username_with_badge(
                    record['username'], session
                )
        
        return JSONResponse({
            'success': True,
            'statistics': statistics
        })
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404, 429)
        raise
    except Exception as e:
        # Log error but don't expose details
        import traceback
        print(f"DEBUG: Error in /api/public/prayer/{prayer_id}/statistics: {str(e)}")
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        
        with Session(engine) as session:
            error_log = SecurityLog(
                user_id="public",
                ip_address=request.client.host if request.client else "unknown",
                event_type="public_api_error", 
                details=f"Error in /api/public/prayer/{prayer_id}/statistics: {str(e)}"
            )
            session.add(error_log)
            session.commit()
        
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
