# invite_routes.py - Invite system routes
import uuid
import secrets
import base64
import io
from datetime import datetime, timedelta
import qrcode
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from models import engine, InviteToken
from app_helpers.services.auth_helpers import current_user
from app_helpers.services.invite_helpers import get_invite_tree, get_invite_stats, get_user_invite_path

# Configuration from app.py
TOKEN_EXP_H = 12  # invite links valid 12 h

# Use shared templates instance with filters registered
from app_helpers.shared_templates import templates

router = APIRouter()

def generate_short_token() -> str:
    """Generate a shorter hex token with 16 characters (64 bits of entropy).
    
    Uses 8 random bytes converted to hexadecimal, resulting in a 16-character
    token using only 0-9a-f characters. This provides good security while
    being significantly shorter than UUIDs.
    """
    return secrets.token_hex(8)

def generate_qr_code_data_url(text: str) -> str:
    """Generate a QR code as a base64-encoded data URL.
    
    Args:
        text: The text to encode in the QR code
        
    Returns:
        str: A data URL containing the QR code as a PNG image
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=2,
    )
    qr.add_data(text)
    qr.make(fit=True)
    
    # Create image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 data URL
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_base64}"

@router.post("/invites", response_class=HTMLResponse)
def new_invite(request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required to create invites")
    token = generate_short_token()
    with Session(engine) as db:
        invite_token = InviteToken(
            token=token,
            created_by_user=user.display_name,
            expires_at=datetime.utcnow() + timedelta(hours=TOKEN_EXP_H)
        )
        db.add(invite_token)
        db.commit()
        
        # Archive the invite token creation
        try:
            from app_helpers.services.archive_writers import system_archive_writer
            system_archive_writer.log_invite_usage(
                token=token,
                used_by='',  # Not used yet
                created_by=user.display_name
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to archive invite token creation: {e}")

    url = request.url_for("claim_get", token=token)  # absolute link
    qr_code_data_url = generate_qr_code_data_url(str(url))
    # Return a modal-style overlay that doesn't shift layout
    return HTMLResponse(templates.get_template("invite_modal.html").render(
        url=url, 
        qr_code_data_url=qr_code_data_url
    ))

@router.get("/invite-tree", response_class=HTMLResponse)
def invite_tree(request: Request, user_session: tuple = Depends(current_user)):
    """Display the complete invite tree for all users to see"""
    user, session = user_session
    
    # Get the complete tree data
    tree_data = get_invite_tree()
    
    # Get invite statistics
    stats = get_invite_stats()
    
    # Get current user's invite path
    user_path = get_user_invite_path(user.display_name)
    
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