# invite_routes.py - Invite system routes
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from models import engine, InviteToken
from app_helpers.services.auth_helpers import current_user
from app_helpers.services.invite_helpers import get_invite_tree, get_invite_stats, get_user_invite_path

# Configuration from app.py
TOKEN_EXP_H = 12  # invite links valid 12 h

templates = Jinja2Templates(directory="templates")

router = APIRouter()

@router.post("/invites", response_class=HTMLResponse)
def new_invite(request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required to create invites")
    token = uuid.uuid4().hex
    with Session(engine) as db:
        db.add(InviteToken(
            token=token,
            created_by_user=user.id,
            expires_at=datetime.utcnow() + timedelta(hours=TOKEN_EXP_H)
        ))
        db.commit()

    url = request.url_for("claim_get", token=token)  # absolute link
    # Return a modal-style overlay that doesn't shift layout
    return HTMLResponse(templates.get_template("invite_modal.html").render(url=url))

@router.get("/invite-tree", response_class=HTMLResponse)
def invite_tree(request: Request, user_session: tuple = Depends(current_user)):
    """Display the complete invite tree for all users to see"""
    user, session = user_session
    
    # Get the complete tree data
    tree_data = get_invite_tree()
    
    # Get invite statistics
    stats = get_invite_stats()
    
    # Get current user's invite path
    user_path = get_user_invite_path(user.id)
    
    return templates.TemplateResponse(
        "invite_tree.html",
        {
            "request": request, 
            "me": user, 
            "session": session,
            "tree_data": tree_data,
            "stats": stats,
            "user_path": user_path
        }
    )