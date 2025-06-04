# general_routes.py - General application routes
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app_helpers.services.auth_helpers import current_user

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
        "me": None  # Explicitly set user to None
    })