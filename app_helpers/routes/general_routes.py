# general_routes.py - General application routes
import os
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app_helpers.services.auth_helpers import current_user
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