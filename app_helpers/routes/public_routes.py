# app_helpers/routes/public_routes.py
"""
Public routes for non-authenticated users.
Provides API endpoints for public prayer access with rate limiting.
"""

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from sqlmodel import Session, select, func
from models import engine, SecurityLog, User, Session as SessionModel
from app_helpers.services.public_prayer_service import PublicPrayerService
from app_helpers.services.username_display_service import UsernameDisplayService
from app_helpers.services.membership_application_service import MembershipApplicationService
import os

router = APIRouter()

# Templates
templates = Jinja2Templates(directory="templates")

# Rate limiting configuration
PUBLIC_RATE_LIMIT_PER_MINUTE = 100  # Increased for development
PUBLIC_RATE_LIMIT_PER_HOUR = 1000   # Increased for development

# Application rate limiting (more restrictive)
APPLICATION_RATE_LIMIT_PER_HOUR = 5  # 5 applications per hour per IP
APPLICATION_RATE_LIMIT_PER_DAY = 10  # 10 applications per day per IP


# Pydantic models for request validation
class MembershipApplicationRequest(BaseModel):
    username: str
    essay: str
    contact: Optional[str] = None


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


def check_application_rate_limit(request: Request) -> bool:
    """
    Check rate limiting for membership applications (more restrictive).

    Args:
        request: FastAPI request object

    Returns:
        True if request is allowed, False if rate limited
    """
    client_ip = request.client.host if request.client else "unknown"

    with Session(engine) as session:
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        # Count applications in last hour
        hour_count = session.exec(
            select(func.count(SecurityLog.id))
            .where(SecurityLog.ip_address == client_ip)
            .where(SecurityLog.event_type == "membership_application")
            .where(SecurityLog.created_at > hour_ago)
        ).first() or 0

        # Count applications in last day
        day_count = session.exec(
            select(func.count(SecurityLog.id))
            .where(SecurityLog.ip_address == client_ip)
            .where(SecurityLog.event_type == "membership_application")
            .where(SecurityLog.created_at > day_ago)
        ).first() or 0

        # Check limits
        if hour_count >= APPLICATION_RATE_LIMIT_PER_HOUR:
            return False
        if day_count >= APPLICATION_RATE_LIMIT_PER_DAY:
            return False

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
async def public_homepage_or_redirect(request: Request, show: str = None):
    """
    Root route that serves public homepage for unauthenticated users
    and redirects authenticated users to their feed.
    """
    if is_user_authenticated(request):
        # User is authenticated, redirect to feed  
        return RedirectResponse("/feed", status_code=302)
    else:
        # User is not authenticated, serve public homepage
        membership_applications_enabled = os.getenv('MEMBERSHIP_APPLICATIONS_ENABLED', 'true').lower() == 'true'
        return templates.TemplateResponse(
            "public_homepage.html",
            {
                "request": request,
                "membership_applications_enabled": membership_applications_enabled,
                "show_application_form": show == "apply"
            }
        )


@router.get("/apply", response_class=HTMLResponse)
async def membership_application_page(request: Request):
    """
    Direct link to membership application form.
    Redirects authenticated users to feed.
    """
    if is_user_authenticated(request):
        # User is authenticated, redirect to feed
        return RedirectResponse("/feed", status_code=302)
    else:
        # User is not authenticated, serve homepage with application form shown
        membership_applications_enabled = os.getenv('MEMBERSHIP_APPLICATIONS_ENABLED', 'true').lower() == 'true'

        if not membership_applications_enabled:
            # Feature disabled, redirect to homepage
            return RedirectResponse("/", status_code=302)

        return templates.TemplateResponse(
            "membership_application.html",
            {
                "request": request
            }
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



@router.post("/api/membership/apply")
async def submit_membership_application(
    application_request: MembershipApplicationRequest,
    request: Request
):
    """
    Submit a membership application.

    Rate limited: 5 applications per hour, 10 per day per IP.
    """
    # Check if feature is enabled
    membership_applications_enabled = os.getenv('MEMBERSHIP_APPLICATIONS_ENABLED', 'true').lower() == 'true'
    if not membership_applications_enabled:
        raise HTTPException(
            status_code=404,
            detail="Membership applications are currently disabled"
        )

    # Check application rate limiting
    if not check_application_rate_limit(request):
        raise HTTPException(
            status_code=429,
            detail="Application rate limit exceeded. Please try again later."
        )

    try:
        client_ip = request.client.host if request.client else "unknown"

        # Validate input
        username = application_request.username.strip()
        essay = application_request.essay.strip()
        contact = application_request.contact.strip() if application_request.contact else None

        # Basic validation
        if not username or len(username) < 2:
            raise HTTPException(
                status_code=400,
                detail="Username must be at least 2 characters long"
            )

        if not essay or len(essay) < 20:
            raise HTTPException(
                status_code=400,
                detail="Essay must be at least 20 characters long"
            )

        if not contact or len(contact.strip()) < 3:
            raise HTTPException(
                status_code=400,
                detail="Contact information is required and must be at least 3 characters long"
            )

        if len(username) > 50:
            raise HTTPException(
                status_code=400,
                detail="Username must be 50 characters or less"
            )

        if len(essay) > 1000:
            raise HTTPException(
                status_code=400,
                detail="Essay must be 1000 characters or less"
            )

        # Check if username already exists
        with Session(engine) as session:
            existing_user = session.get(User, username)
            if existing_user:
                raise HTTPException(
                    status_code=400,
                    detail="Username already taken. Please choose a different username."
                )

        # Create application using service
        application = MembershipApplicationService.create_application(
            username=username,
            essay=essay,
            contact_info=contact,
            ip_address=client_ip
        )

        # Log the application for rate limiting
        with Session(engine) as session:
            log_entry = SecurityLog(
                user_id="public",
                ip_address=client_ip,
                event_type="membership_application",
                details=f"Membership application submitted for username: {username}"
            )
            session.add(log_entry)
            session.commit()

        return JSONResponse({
            "success": True,
            "message": "Application submitted successfully",
            "application_id": application.id
        })

    except HTTPException:
        # Re-raise validation errors
        raise
    except Exception as e:
        # Log error but dont expose details
        with Session(engine) as session:
            error_log = SecurityLog(
                user_id="public",
                ip_address=request.client.host if request.client else "unknown",
                event_type="membership_application_error",
                details=f"Error in /api/membership/apply: {str(e)}"
            )
            session.add(error_log)
            session.commit()

        raise HTTPException(
            status_code=500,
            detail="Internal server error while processing application"
        )


@router.get("/apply/status", response_class=HTMLResponse)
def membership_application_status_page(request: Request):
    """
    Display application status lookup page
    """
    # Check if feature is enabled
    membership_applications_enabled = os.getenv('MEMBERSHIP_APPLICATIONS_ENABLED', 'true').lower() == 'true'
    if not membership_applications_enabled:
        raise HTTPException(404)

    return templates.TemplateResponse("membership_application_status.html", {
        "request": request
    })


@router.post("/api/membership/status")
async def get_membership_application_status(
    status_request: dict,
    request: Request
):
    """
    Get status of a membership application by ID
    """
    # Check if feature is enabled
    membership_applications_enabled = os.getenv('MEMBERSHIP_APPLICATIONS_ENABLED', 'true').lower() == 'true'
    if not membership_applications_enabled:
        raise HTTPException(404)

    # Basic rate limiting (use public rate limit)
    if not check_public_rate_limit(request):
        raise HTTPException(429)

    try:
        application_id = status_request.get('application_id', '').strip()

        if not application_id:
            raise HTTPException(
                status_code=400,
                detail="Application ID is required"
            )

        # Look up application
        with Session(engine) as session:
            stmt = select(MembershipApplication).where(MembershipApplication.id == application_id)
            application = session.exec(stmt).first()

            if not application:
                return JSONResponse({
                    "success": False,
                    "error": "Application not found. Please check your Application ID."
                })

            # Return status information
            status_info = {
                "username": application.username,
                "status": application.status,
                "created_at": application.created_at.isoformat(),
                "processed_at": application.processed_at.isoformat() if application.processed_at else None
            }

            # Add status-specific information
            if application.status == "approved":
                status_info["message"] = "Your application has been approved! You should have received an invite link at your contact information."
            elif application.status == "rejected":
                status_info["message"] = "Your application was not approved at this time."
            else:
                status_info["message"] = "Your application is pending review by our administrators."

            return JSONResponse({
                "success": True,
                "application": status_info
            })

    except HTTPException:
        raise
    except Exception as e:
        # Log error
        with Session(engine) as session:
            error_log = SecurityLog(
                user_id="public",
                ip_address=request.client.host if request.client else "unknown",
                event_type="membership_status_error",
                details=f"Error in /api/membership/status: {str(e)}"
            )
            session.add(error_log)
            session.commit()

        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

