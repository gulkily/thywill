# app.py ─ complete micro-MVP
import os, uuid, yaml
from datetime import datetime, timedelta, date
from typing import Optional
from dotenv import load_dotenv
import anthropic

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select, func

from models import engine, User, Prayer, InviteToken, Session as SessionModel, PrayerMark, AuthenticationRequest, AuthApproval, AuthAuditLog, SecurityLog, PrayerAttribute, PrayerActivityLog
from sqlmodel import text

# Load environment variables
load_dotenv()

# ───────── Config ─────────
SESSION_DAYS = 14
TOKEN_EXP_H = 12          # invite links valid 12 h
MAX_AUTH_REQUESTS_PER_HOUR = 3  # Rate limit for auth requests
MAX_FAILED_ATTEMPTS = 5   # Max failed login attempts before temporary block
BLOCK_DURATION_MINUTES = 15  # How long to block after max failed attempts

# Multi-device authentication settings
MULTI_DEVICE_AUTH_ENABLED = os.getenv("MULTI_DEVICE_AUTH_ENABLED", "true").lower() == "true"
REQUIRE_APPROVAL_FOR_EXISTING_USERS = os.getenv("REQUIRE_APPROVAL_FOR_EXISTING_USERS", "true").lower() == "true"
REQUIRE_INVITE_LOGIN_VERIFICATION = os.getenv("REQUIRE_INVITE_LOGIN_VERIFICATION", "false").lower() == "true"
PEER_APPROVAL_COUNT = int(os.getenv("PEER_APPROVAL_COUNT", "2"))

templates = Jinja2Templates(directory="templates")

# Initialize Anthropic client
anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ───────── Import extracted helper functions for backward compatibility ─────────
# These imports maintain all existing function entry points in app.py namespace
from app_helpers.services.auth_helpers import (
    create_session, current_user, require_full_auth, is_admin,
    create_auth_request, approve_auth_request, get_pending_requests_for_approval,
    log_auth_action, log_security_event, check_rate_limit, 
    validate_session_security, cleanup_expired_requests
)
from app_helpers.services.prayer_helpers import (
    get_feed_counts, get_filtered_prayers_for_user, find_compatible_prayer_partner,
    get_religious_preference_stats, todays_prompt, generate_prayer
)
from app_helpers.services.invite_helpers import (
    get_invite_tree, get_user_descendants, get_user_invite_path,
    get_invite_stats, _build_user_tree_node, _collect_descendants, _calculate_max_depth
)
from app_helpers.utils.database_helpers import migrate_database

# ───────── Import extracted route modules ─────────
from app_helpers.routes.auth_routes import router as auth_router
from app_helpers.routes.prayer_routes import router as prayer_router
from app_helpers.routes.admin_routes import router as admin_router
from app_helpers.routes.user_routes import router as user_router
from app_helpers.routes.invite_routes import router as invite_router
from app_helpers.routes.general_routes import router as general_router
from app_helpers.routes.changelog_routes import router as changelog_router

app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include authentication routes
app.include_router(auth_router)
# Include prayer routes
app.include_router(prayer_router)
# Include admin routes
app.include_router(admin_router)
# Include user routes
app.include_router(user_router)
# Include invite routes
app.include_router(invite_router)
# Include general routes
app.include_router(general_router)
# Include changelog routes
app.include_router(changelog_router)

# Custom exception handler for 401 unauthorized errors
@app.exception_handler(401)
async def unauthorized_exception_handler(request: Request, exc: HTTPException):
    """Custom handler for 401 unauthorized errors to show user-friendly page"""
    reason = exc.detail if exc.detail else "no_session"
    return templates.TemplateResponse("unauthorized.html", {
        "request": request,
        "reason": reason,
        "return_url": request.url.path,
        "MULTI_DEVICE_AUTH_ENABLED": MULTI_DEVICE_AUTH_ENABLED
    }, status_code=401)

# Custom exception handler for 404 not found errors
@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: HTTPException):
    """Custom handler for 404 not found errors to show user-friendly page"""
    # Check if this is an auth-related 404
    if request.url.path.startswith("/auth/") and "Authentication request not found" in str(exc.detail):
        return templates.TemplateResponse("auth_not_found.html", {
            "request": request,
            "MULTI_DEVICE_AUTH_ENABLED": MULTI_DEVICE_AUTH_ENABLED
        }, status_code=404)
    
    # For other 404s, show generic error page
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error_code": 404,
        "error_title": "Page Not Found",
        "error_message": "The page you're looking for doesn't exist or has been moved."
    }, status_code=404)

# Custom exception handler for 500 internal server errors
@app.exception_handler(500)
async def internal_error_exception_handler(request: Request, exc: Exception):
    """Custom handler for 500 internal server errors"""
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error_code": 500,
        "error_title": "Internal Server Error",
        "error_message": "Something went wrong on our end. Please try again later."
    }, status_code=500)

# Custom exception handler for 403 forbidden errors
@app.exception_handler(403)
async def forbidden_exception_handler(request: Request, exc: HTTPException):
    """Custom handler for 403 forbidden errors"""
    return templates.TemplateResponse("error.html", {
        "request": request,
        "error_code": 403,
        "error_title": "Access Forbidden",
        "error_message": "You don't have permission to access this resource."
    }, status_code=403)

# ───────── Extracted functions now imported from helper modules ─────────
# Auth functions: create_session, current_user, require_full_auth, is_admin, etc.
# Prayer functions: get_feed_counts, get_filtered_prayers_for_user, etc.
# Invite functions: get_invite_tree, get_user_descendants, etc.
# Database functions: migrate_database


# ───────── Routes ─────────
# Prayer routes moved to app_helpers/routes/prayer_routes.py



# Admin route moved to app_helpers/routes/admin_routes.py

# ───────── Invite-claim flow routes moved to app_helpers/routes/auth_routes.py ─────────


# ───────── Startup: seed first invite ─────────
@app.on_event("startup")
def startup():
    # Run database migration first
    migrate_database()
    
    # Then seed invite
    with Session(engine) as s:
        if not s.exec(select(InviteToken)).first():
            token = uuid.uuid4().hex
            s.add(InviteToken(
                token=token,
                created_by_user="system",
                expires_at=datetime.utcnow() + timedelta(hours=TOKEN_EXP_H)))
            s.commit()
            print("\n==== First-run invite token (admin):", token, "====\n")


# Invite routes moved to app_helpers/routes/invite_routes.py

# User routes moved to app_helpers/routes/user_routes.py

# General routes moved to app_helpers/routes/general_routes.py

# ───────── Authentication request routes moved to app_helpers/routes/auth_routes.py ─────────

# Auth audit log route moved to app_helpers/routes/admin_routes.py

# Bulk approve route moved to app_helpers/routes/admin_routes.py

# Religious Preference Management API moved to app_helpers/routes/user_routes.py

# Logout and logged-out routes moved to app_helpers/routes/user_routes.py and app_helpers/routes/general_routes.py

# Religious stats API route moved to app_helpers/routes/admin_routes.py
