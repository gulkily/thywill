# app_helpers/routes/auth_routes.py - Authentication route handlers (Refactored)
"""
Authentication route handlers - Main aggregator module.

This module has been refactored into focused sub-modules for better maintainability:
- auth/login_routes.py - Login and registration (claim/login flows)
- auth/multi_device_routes.py - Multi-device authentication workflows  
- auth/verification_routes.py - Authentication status and verification
- auth/notification_routes.py - Notification system endpoints

All routes maintain exact same signatures and logic as original implementation
for 100% backward compatibility.

Usage:
This router is included in the main FastAPI app via:
    from app_helpers.routes.auth_routes import router as auth_router
    app.include_router(auth_router)
"""

from fastapi import APIRouter

# Import required dependencies for backward compatibility with tests
from sqlmodel import Session
from models import engine

# Create main router instance
router = APIRouter()

# Import all sub-module routers and include them
from .auth.login_routes import router as login_router
from .auth.multi_device_routes import router as multi_device_router  
from .auth.verification_routes import router as verification_router
from .auth.notification_routes import router as notification_router
from .auth.session_api_routes import router as session_api_router

# Include all sub-routers to maintain all existing routes
router.include_router(login_router)
router.include_router(multi_device_router)
router.include_router(verification_router)
router.include_router(notification_router)
router.include_router(session_api_router)