"""
Admin Routes Module

This module contains all admin-related route handlers extracted from app.py.
These routes handle administrative functions including:
- Admin dashboard with flagged prayers and authentication requests
- Authentication audit log viewing
- Bulk approval of authentication requests
- Religious preference statistics API

All routes require admin privileges and maintain the same signatures and logic
as the original implementations for 100% backward compatibility.
"""

from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select, func

# Import models
from models import (
    engine, User, Prayer, AuthenticationRequest, AuthApproval, 
    AuthAuditLog, PrayerMark
)

# Import helper functions
from app_helpers.services.auth_helpers import (
    current_user, is_admin, cleanup_expired_requests, log_auth_action
)
from app_helpers.utils.user_management import (
    deactivate_user, reactivate_user, is_user_deactivated, 
    get_user_deactivation_info, UserManagementError, get_active_users,
    get_deactivated_users
)
from app_helpers.services.prayer_helpers import get_religious_preference_stats

# Initialize router and templates
router = APIRouter()
# Use shared templates instance with filters registered
from app_helpers.shared_templates import templates


@router.get("/admin", response_class=HTMLResponse)
def admin(request: Request, user_session: tuple = Depends(current_user)):
    """
    Admin Dashboard
    
    Displays the main admin dashboard with:
    - Flagged prayers that need review
    - Pending authentication requests with approval status
    - Admin controls for managing the community
    
    Requires admin privileges.
    """
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403)
    
    cleanup_expired_requests()  # Clean up old requests
    
    with Session(engine) as s:
        # Join Prayer and User tables to get author display names for flagged prayers
        stmt = (
            select(Prayer, User.display_name)
            .outerjoin(User, Prayer.author_username == User.display_name)
            .where(Prayer.flagged == True)
        )
        results = s.exec(stmt).all()
        
        # Create a list of flagged prayers with author names
        flagged_with_authors = []
        for prayer, author_name in results:
            prayer_dict = {
                'id': prayer.id,
                'author_id': prayer.author_username,
                'text': prayer.text,
                'generated_prayer': prayer.generated_prayer,
                'project_tag': prayer.project_tag,
                'created_at': prayer.created_at,
                'flagged': prayer.flagged,
                'author_name': author_name
            }
            flagged_with_authors.append(prayer_dict)
        
        # Get authentication requests for admin review
        auth_requests_stmt = (
            select(AuthenticationRequest, User.display_name)
            .outerjoin(User, AuthenticationRequest.user_id == User.display_name)
            .where(AuthenticationRequest.status == "pending")
            .where(AuthenticationRequest.expires_at > datetime.utcnow())
            .order_by(AuthenticationRequest.created_at.desc())
        )
        
        auth_results = s.exec(auth_requests_stmt).all()
        auth_requests_with_info = []
        
        for auth_req, requester_name in auth_results:
            # Get current approval count
            approval_count = s.exec(
                select(func.count(AuthApproval.id))
                .where(AuthApproval.auth_request_id == auth_req.id)
            ).first() or 0
            
            # Get approvers
            approvers = s.exec(
                select(AuthApproval, User.display_name)
                .outerjoin(User, AuthApproval.approver_user_id == User.display_name)
                .where(AuthApproval.auth_request_id == auth_req.id)
            ).all()
            
            approver_info = []
            for approval, approver_name in approvers:
                approver_info.append({
                    'name': approver_name,
                    'is_admin': approval.approver_user_id == "admin",
                    'approved_at': approval.created_at
                })
            
            auth_requests_with_info.append({
                'request': auth_req,
                'requester_name': requester_name,
                'approval_count': approval_count,
                'approvers': approver_info
            })
    
    return templates.TemplateResponse(
        "admin.html", {
            "request": request, 
            "flagged": flagged_with_authors, 
            "auth_requests": auth_requests_with_info,
            "me": user,
            "session": session
        }
    )


@router.get("/admin/auth-audit", response_class=HTMLResponse)
def auth_audit_log(request: Request, user_session: tuple = Depends(current_user)):
    """
    Authentication Audit Log
    
    Displays a detailed audit log of authentication-related activities including:
    - Authentication request approvals and denials
    - Admin actions on authentication requests
    - System-generated authentication events
    
    Shows the last 100 entries with actor and requester information.
    Requires admin privileges.
    """
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403)
    
    with Session(engine) as db:
        # Get audit log entries (last 100)
        audit_entries = db.exec(
            select(AuthAuditLog)
            .order_by(AuthAuditLog.created_at.desc())
            .limit(100)
        ).all()
        
        audit_with_info = []
        for entry in audit_entries:
            # Get actor info
            actor_name = "System"
            if entry.actor_user_id:
                actor = db.get(User, entry.actor_user_id)
                actor_name = actor.display_name if actor else "Unknown"
            
            # Get requester info
            auth_req = db.get(AuthenticationRequest, entry.auth_request_id)
            requester_name = "Unknown"
            if auth_req:
                requester = db.get(User, auth_req.user_id)
                requester_name = requester.display_name if requester else "Unknown"
            
            audit_with_info.append({
                'entry': entry,
                'actor_name': actor_name,
                'requester_name': requester_name,
                'auth_request': auth_req
            })
    
    return templates.TemplateResponse(
        "auth_audit.html",
        {"request": request, "audit_entries": audit_with_info, "me": user, "session": session}
    )


@router.post("/admin/bulk-approve")
def bulk_approve_requests(request: Request, user_session: tuple = Depends(current_user)):
    """
    Bulk Approve Authentication Requests
    
    Approves all pending authentication requests in a single operation.
    This is useful for administrators to quickly process a backlog of requests.
    
    Each approval is logged individually in the audit trail.
    Requires admin privileges.
    
    Returns a redirect to the admin dashboard with a success message.
    """
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403)
    
    # Approve all pending requests
    approved_count = 0
    with Session(engine) as db:
        pending_requests = db.exec(
            select(AuthenticationRequest)
            .where(AuthenticationRequest.status == "pending")
            .where(AuthenticationRequest.expires_at > datetime.utcnow())
        ).all()
        
        # Process each request and store the data we need before modifying
        requests_to_process = []
        for auth_req in pending_requests:
            requests_to_process.append({
                'id': auth_req.id,
                'object': auth_req
            })
        
        for req_data in requests_to_process:
            auth_req = req_data['object']
            auth_req_id = req_data['id']
            
            # Approve each request
            auth_req.status = "approved"
            auth_req.approved_by_user_id = user.display_name
            auth_req.approved_at = datetime.utcnow()
            approved_count += 1
            
            # Add to current session to ensure it's attached
            db.add(auth_req)
            
            # Log the bulk approval using the stored ID
            log_auth_action(
                auth_request_id=auth_req_id,
                action="approved",
                actor_user_id=user.display_name,
                actor_type="admin",
                details="Request approved via bulk admin action"
            )
        
        db.commit()
    
    return RedirectResponse(f"/admin?message=Approved {approved_count} requests", 303)


@router.get("/api/religious-stats")
async def get_religious_stats(request: Request, user_session: tuple = Depends(current_user)):
    """
    Religious Preference Statistics API
    
    Returns statistical data about religious preferences across the user base.
    This API endpoint provides insights for administrators about the community's
    religious diversity and preferences.
    
    Returns JSON data with:
    - Distribution of religious preferences
    - Prayer style preferences among Christians
    - User counts and percentages
    
    Requires admin privileges.
    """
    user, session = user_session
    
    if not is_admin(user):
        raise HTTPException(403, "Admin access required")
    
    with Session(engine) as db:
        stats = get_religious_preference_stats(db)
        return stats


@router.get("/api/religious-preference-stats")
async def get_religious_preference_stats_api(request: Request, user_session: tuple = Depends(current_user)):
    """
    Religious Preference Statistics API (alternative endpoint)
    
    Returns statistical data about religious preferences across the user base.
    This API endpoint provides insights for administrators about the community's
    religious diversity and preferences.
    
    Returns JSON data with:
    - Distribution of religious preferences
    - Prayer style preferences among Christians
    - User counts and percentages
    
    Requires admin privileges.
    """
    user, session = user_session
    
    if not is_admin(user):
        raise HTTPException(403, "Admin access required")
    
    with Session(engine) as db:
        stats = get_religious_preference_stats(db)
        return stats


@router.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request, user_session: tuple = Depends(current_user)):
    """
    Admin User Management
    
    Displays user management interface for administrators including:
    - List of all users with their statistics
    - User activity and engagement metrics
    - Admin controls for user management
    
    Requires admin privileges.
    """
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403)
    
    with Session(engine) as s:
        # Get all users with basic stats
        users_stmt = select(User).order_by(User.created_at.desc())
        all_users = s.exec(users_stmt).all()
        
        users_with_stats = []
        for profile_user in all_users:
            # Get prayer counts
            prayers_authored = s.exec(
                select(func.count(Prayer.id))
                .where(Prayer.author_username == profile_user.display_name)
                .where(Prayer.flagged == False)
            ).first() or 0
            
            prayers_marked = s.exec(
                select(func.count(PrayerMark.id))
                .where(PrayerMark.username == profile_user.display_name)
            ).first() or 0
            
            # Check deactivation status
            is_deactivated = is_user_deactivated(profile_user.display_name, s)
            deactivation_info = None
            if is_deactivated:
                deactivation_info = get_user_deactivation_info(profile_user.display_name, s)
            
            users_with_stats.append({
                'user': profile_user,
                'prayers_authored': prayers_authored,
                'prayers_marked': prayers_marked,
                'is_admin': profile_user.has_role("admin", s),
                'is_deactivated': is_deactivated,
                'deactivation_info': deactivation_info
            })
    
    return templates.TemplateResponse(
        "users.html", {
            "request": request,
            "users": users_with_stats,
            "me": user,
            "session": session,
            "is_admin_view": True  # Flag to show admin controls
        }
    )


@router.post("/admin/flag-prayer/{prayer_id}")
def flag_prayer(prayer_id: str, request: Request, user_session: tuple = Depends(current_user)):
    """
    Flag Prayer as Admin
    
    Flags a prayer for admin review. This action is used when a prayer
    contains inappropriate content or violates community guidelines.
    
    Requires admin privileges.
    
    Returns a redirect to the admin dashboard.
    """
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403)
    
    with Session(engine) as s:
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            raise HTTPException(404, "Prayer not found")
        
        prayer.flagged = True
        s.add(prayer)
        s.commit()
        
        # Note: Prayer flagging is logged through the flagged field change
        # For more detailed logging, consider using PrayerActivityLog instead
    
    return RedirectResponse("/admin", 303)


@router.post("/admin/unflag-prayer/{prayer_id}")
def unflag_prayer(prayer_id: str, request: Request, user_session: tuple = Depends(current_user)):
    """
    Unflag Prayer as Admin
    
    Removes the flag from a prayer, marking it as approved for the community.
    This action is used when a flagged prayer has been reviewed and found
    to be appropriate.
    
    Requires admin privileges.
    
    Returns a redirect to the admin dashboard.
    """
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403)
    
    with Session(engine) as s:
        prayer = s.get(Prayer, prayer_id)
        if not prayer:
            raise HTTPException(404, "Prayer not found")
        
        prayer.flagged = False
        s.add(prayer)
        s.commit()
        
        # Note: Prayer unflagging is logged through the flagged field change
        # For more detailed logging, consider using PrayerActivityLog instead
    
    return RedirectResponse("/admin", 303)


@router.post("/admin/users/{user_id}/deactivate")
def deactivate_user_route(user_id: str, request: Request, user_session: tuple = Depends(current_user)):
    """
    Deactivate User (Soft Delete)
    
    Deactivates a user by removing all their roles and assigning the 'deactivated' role.
    This prevents login while preserving all data for audit purposes.
    
    Requires admin privileges.
    """
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403, "Admin privileges required")
    
    try:
        with Session(engine) as db:
            # Check if target user exists
            target_user = db.exec(select(User).where(User.display_name == user_id)).first()
            if not target_user:
                raise HTTPException(404, "User not found")
            
            # Prevent self-deactivation
            if user_id == user.display_name:
                raise HTTPException(400, "Cannot deactivate your own account")
            
            # Deactivate the user
            success = deactivate_user(
                user_id=user_id,
                admin_id=user.display_name,
                reason=f"Deactivated by admin {user.display_name}",
                session=db
            )
            
            if success:
                return {"status": "success", "message": f"User {target_user.display_name} has been deactivated"}
            else:
                raise HTTPException(500, "Deactivation failed")
                
    except UserManagementError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Internal error: {str(e)}")


@router.post("/admin/users/{user_id}/reactivate") 
def reactivate_user_route(user_id: str, request: Request, user_session: tuple = Depends(current_user)):
    """
    Reactivate User
    
    Reactivates a previously deactivated user by removing the 'deactivated' role
    and restoring the default 'user' role.
    
    Requires admin privileges.
    """
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403, "Admin privileges required")
    
    try:
        with Session(engine) as db:
            # Check if target user exists
            target_user = db.exec(select(User).where(User.display_name == user_id)).first()
            if not target_user:
                raise HTTPException(404, "User not found")
            
            # Reactivate the user
            success = reactivate_user(
                user_id=user_id,
                admin_id=user.display_name,
                session=db
            )
            
            if success:
                return {"status": "success", "message": f"User {target_user.display_name} has been reactivated"}
            else:
                raise HTTPException(500, "Reactivation failed")
                
    except UserManagementError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Internal error: {str(e)}")


@router.get("/admin/users/{user_id}/status")
def get_user_status(user_id: str, request: Request, user_session: tuple = Depends(current_user)):
    """
    Get User Status
    
    Returns the current activation status of a user, including deactivation
    information if applicable.
    
    Requires admin privileges.
    """
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403, "Admin privileges required")
    
    try:
        with Session(engine) as db:
            # Check if user exists
            target_user = db.exec(select(User).where(User.display_name == user_id)).first()
            if not target_user:
                raise HTTPException(404, "User not found")
            
            is_deactivated = is_user_deactivated(user_id, db)
            
            status = {
                "user_id": user_id,
                "display_name": target_user.display_name,
                "is_deactivated": is_deactivated,
                "is_active": not is_deactivated
            }
            
            if is_deactivated:
                deactivation_info = get_user_deactivation_info(user_id, db)
                if deactivation_info:
                    status.update(deactivation_info)
            
            return status
            
    except Exception as e:
        raise HTTPException(500, f"Internal error: {str(e)}")