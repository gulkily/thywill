"""
Admin Authentication Management Routes

Contains routes for managing authentication requests and bulk operations.
"""

from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select

# Import models
from models import engine, AuthenticationRequest

# Import helper functions
from app_helpers.services.auth_helpers import (
    current_user, is_admin, log_auth_action
)

# Create router for this module
router = APIRouter()


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