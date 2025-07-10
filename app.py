# app.py ─ complete micro-MVP
import os, uuid
from datetime import datetime, timedelta, date
from typing import Optional
from dotenv import load_dotenv
import anthropic

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlmodel import Session, select, func

# Load environment variables first
load_dotenv()

# Database path is now configured in models.py via intelligent detection

from models import engine, User, Prayer, InviteToken, Session as SessionModel, PrayerMark, PrayerSkip, AuthenticationRequest, AuthApproval, AuthAuditLog, SecurityLog, PrayerAttribute, PrayerActivityLog
from sqlmodel import text
import sqlite3

# ───────── Config ─────────
SESSION_DAYS = 14
# TOKEN_EXP_H moved to app_helpers/services/token_service.py for centralization
MAX_AUTH_REQUESTS_PER_HOUR = 3  # Rate limit for auth requests
MAX_FAILED_ATTEMPTS = 5   # Max failed login attempts before temporary block
BLOCK_DURATION_MINUTES = 15  # How long to block after max failed attempts

# Multi-device authentication settings
MULTI_DEVICE_AUTH_ENABLED = os.getenv("MULTI_DEVICE_AUTH_ENABLED", "true").lower() == "true"
REQUIRE_APPROVAL_FOR_EXISTING_USERS = os.getenv("REQUIRE_APPROVAL_FOR_EXISTING_USERS", "true").lower() == "true"
REQUIRE_INVITE_LOGIN_VERIFICATION = os.getenv("REQUIRE_INVITE_LOGIN_VERIFICATION", "false").lower() == "true"
PEER_APPROVAL_COUNT = int(os.getenv("PEER_APPROVAL_COUNT", "2"))

# Auto-migration settings
AUTO_MIGRATE_ON_STARTUP = os.getenv("AUTO_MIGRATE_ON_STARTUP", "false").lower() == "true"

# Text Archive Settings
TEXT_ARCHIVE_ENABLED = os.getenv("TEXT_ARCHIVE_ENABLED", "true").lower() == "true"
TEXT_ARCHIVE_BASE_DIR = os.getenv("TEXT_ARCHIVE_BASE_DIR", "./text_archives")
TEXT_ARCHIVE_COMPRESSION_AFTER_DAYS = int(os.getenv("TEXT_ARCHIVE_COMPRESSION_AFTER_DAYS", "365"))

# Prayer Mode Settings
PRAYER_MODE_ENABLED = os.getenv("PRAYER_MODE_ENABLED", "true").lower() == "true"

# Use shared templates instance with filters registered
from app_helpers.shared_templates import templates

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
    get_feed_counts, find_compatible_prayer_partner,
    todays_prompt, generate_prayer
)
from app_helpers.services.invite_helpers import (
    get_invite_tree, get_user_descendants, get_user_invite_path,
    get_invite_stats, _build_user_tree_node, _collect_descendants, _calculate_max_depth
)
from app_helpers.utils.database_helpers import migrate_database
from app_helpers.utils.enhanced_migration import MigrationManager

# ───────── Import extracted route modules ─────────
from app_helpers.routes.auth_routes import router as auth_router
from app_helpers.routes.prayer_routes import router as prayer_router
from app_helpers.routes.admin_routes import router as admin_router
from app_helpers.routes.user_routes import router as user_router
from app_helpers.routes.invite_routes import router as invite_router
from app_helpers.routes.general_routes import router as general_router
from app_helpers.routes.changelog_routes import router as changelog_router
from app_helpers.routes.archive_routes import router as archive_router

app = FastAPI()

# Health check endpoint for deployment monitoring
@app.get("/health")
async def health_check():
    """Health check endpoint that verifies database connectivity"""
    try:
        # Check database connectivity
        db_path = "thywill.db"
        if not os.path.exists(db_path):
            return JSONResponse(
                content={
                    "status": "unhealthy",
                    "error": "Database file not found"
                },
                status_code=500
            )
        
        # Try to connect and run a simple query
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        
        return JSONResponse(
            content={
                "status": "healthy",
                "database": "connected",
                "timestamp": datetime.now().isoformat()
            },
            status_code=200
        )
        
    except Exception as e:
        return JSONResponse(
            content={
                "status": "unhealthy",
                "error": str(e)
            },
            status_code=500
        )

# Test route for share functionality
@app.get("/test-share", response_class=HTMLResponse)
async def test_share(request: Request):
    """Test page for share functionality across different browsers"""
    return templates.TemplateResponse("test_share.html", {
        "request": request,
        "test_url": "https://thywill.com/claim/abcd1234test5678",
        "test_title": "Join ThyWill Prayer Community"
    })

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
# Include archive routes
app.include_router(archive_router)
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
    # For API routes, return JSON responses
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc.detail) if exc.detail else "Not found"}
        )
    
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
    # For API routes, return JSON responses
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=403,
            content={"detail": str(exc.detail) if exc.detail else "Forbidden"}
        )
    
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


# ───────── Schema validation functions (module level for CLI access) ─────────
def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    with engine.connect() as conn:
        from sqlalchemy import text
        result = conn.execute(text(f"PRAGMA table_info({table_name})"))
        columns = [row[1] for row in result.fetchall()]
        return column_name in columns

def validate_schema_compatibility() -> tuple[bool, list[str]]:
    """Validate that database schema matches model expectations"""
    required_columns = {
        'invitetoken': ['token', 'created_by_user', 'usage_count', 'max_uses', 'expires_at', 'used_by_user_id', 'token_type'],
        'user': ['display_name', 'created_at', 'invited_by_username', 'invite_token_used', 'welcome_message_dismissed', 'text_file_path'],
        'prayer': ['id', 'author_username', 'text', 'generated_prayer', 'project_tag', 'created_at', 'flagged', 'text_file_path'],
        'session': ['id', 'username', 'created_at', 'expires_at', 'auth_request_id', 'device_info', 'ip_address', 'is_fully_authenticated'],
        'prayermark': ['id', 'username', 'prayer_id', 'created_at', 'text_file_path'],
        'role': ['id', 'name', 'description', 'permissions', 'created_at', 'created_by', 'is_system_role'],
        'user_roles': ['id', 'user_id', 'role_id', 'granted_by', 'granted_at', 'expires_at']
    }
    
    missing_columns = []
    for table, columns in required_columns.items():
        for column in columns:
            if not column_exists(table, column):
                missing_columns.append(f"{table}.{column}")
    
    is_valid = len(missing_columns) == 0
    return is_valid, missing_columns

# ───────── Startup: seed first invite ─────────
@app.on_event("startup")
def startup():
    # Auto-migration on startup (if enabled and using file-based database)
    from models import DATABASE_PATH
    if AUTO_MIGRATE_ON_STARTUP and DATABASE_PATH != ':memory:':
        print("🔄 Auto-migration enabled - checking for pending migrations...")
        try:
            migration_manager = MigrationManager()
            
            # Check for migration lock from previous failed attempt
            if migration_manager.is_migration_locked():
                print("⚠️  Migration lock detected - checking for partial migrations...")
                migration_manager.handle_partial_migration_recovery()
            
            # Check for pending migrations
            pending = migration_manager.get_pending_migrations()
            if pending:
                print(f"🔄 Auto-applying {len(pending)} pending migrations...")
                
                # Check if any migration requires maintenance mode
                requires_maintenance = any(
                    migration_manager.should_enable_maintenance_mode(migration)
                    for migration in pending
                )
                
                if requires_maintenance:
                    print("⚠️  Some migrations require maintenance mode - skipping auto-migration")
                    print("   Please run migrations manually: ./thywill migrate new")
                else:
                    # Apply migrations automatically
                    applied = migration_manager.auto_migrate_on_startup()
                    migration_manager.validate_schema_integrity()
                    
                    if applied:
                        print(f"✅ Auto-migration completed: {', '.join(applied)}")
                    else:
                        print("✅ No migrations applied")
            else:
                print("✅ Database schema is up to date")
                
        except Exception as e:
            print(f"❌ Auto-migration failed: {e}")
            print("   Application will continue - please run migrations manually")
    
    # Run enhanced migrations on manual startup or fallback
    elif not AUTO_MIGRATE_ON_STARTUP:
        try:
            migration_manager = MigrationManager()
            
            # Check for migration lock from previous failed attempt
            if migration_manager.is_migration_locked():
                print("⚠️  Migration lock detected - checking for partial migrations...")
                migration_manager.handle_partial_migration_recovery()
            
            # Resolve dependencies and check pending migrations
            pending = migration_manager.get_pending_migrations()  # Returns in dependency order
            if pending:
                print(f"🔄 Applying {len(pending)} pending migrations...")
                
                # Check if any migration requires maintenance mode
                for migration in pending:
                    if migration_manager.should_enable_maintenance_mode(migration):
                        print(f"⚠️  Migration {migration['id']} requires maintenance mode - manual deployment needed")
                        print("   Falling back to legacy migrations...")
                        migrate_database()
                        break
                else:
                    # Apply migrations with locking
                    applied = migration_manager.auto_migrate_on_startup()
                    
                    # Validate final schema state
                    migration_manager.validate_schema_integrity()
                    if applied:
                        print(f"✅ Enhanced migrations completed: {', '.join(applied)}")
                    else:
                        print("✅ No migrations needed - database is up to date")
            else:
                print("✅ Database schema is up to date")
                
        except Exception as e:
            print(f"❌ Enhanced migration failed: {e}")
            print("   Falling back to legacy migrations...")
            # Fallback to legacy migration system
            migrate_database()
    
    # Run duplicate user migration
    try:
        from migrations.duplicate_user_migration import run_duplicate_user_migration
        run_duplicate_user_migration()
    except Exception as e:
        print(f"❌ Duplicate user migration failed: {e}")
        # Continue startup - this is not critical for basic functionality
    
    # Run schema validation
    print("🔍 Validating database schema compatibility...")
    is_valid, missing_columns = validate_schema_compatibility()
    
    if not is_valid:
        print(f"⚠️  Schema validation found {len(missing_columns)} missing columns:")
        for col in missing_columns:
            print(f"   - {col}")
        print("🔧 Attempting defensive schema repairs...")
    else:
        print("✅ Schema validation passed - all required columns present")
    
    # Add missing columns if they don't exist
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            repairs_made = 0
            
            # Add token_type column to invitetoken table if missing
            if not column_exists('invitetoken', 'token_type'):
                print("🔧 Adding missing token_type column to invitetoken table...")
                conn.execute(text("ALTER TABLE invitetoken ADD COLUMN token_type TEXT DEFAULT 'new_user'"))
                conn.commit()
                print("✅ Added token_type column")
                repairs_made += 1
            
            # Add other critical missing columns as needed
            # (Future defensive repairs can be added here)
            
            if repairs_made > 0:
                print(f"✅ Schema repairs completed: {repairs_made} columns added")
            
    except Exception as e:
        print(f"⚠️  Schema fix warning: {e}")
        # Continue startup - this is defensive, not critical
    
    # Then seed invite using centralized token service
    with Session(engine) as s:
        if not s.exec(select(InviteToken)).first():
            from app_helpers.services.token_service import create_system_token
            token_info = create_system_token()
            print("\n==== First-run invite token (admin):", token_info['token'], "====\n")


# Invite routes moved to app_helpers/routes/invite_routes.py

# User routes moved to app_helpers/routes/user_routes.py

# General routes moved to app_helpers/routes/general_routes.py

# ───────── Authentication request routes moved to app_helpers/routes/auth_routes.py ─────────

# Auth audit log route moved to app_helpers/routes/admin_routes.py

# Bulk approve route moved to app_helpers/routes/admin_routes.py

# Religious Preference Management API moved to app_helpers/routes/user_routes.py

# Logout and logged-out routes moved to app_helpers/routes/user_routes.py and app_helpers/routes/general_routes.py

# Religious stats API route moved to app_helpers/routes/admin_routes.py
