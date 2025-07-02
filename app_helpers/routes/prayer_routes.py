# app_helpers/routes/prayer_routes.py
"""
Prayer-related route handlers - Main aggregator module.

This module has been refactored into focused sub-modules for better maintainability:
- prayer/feed_operations.py - Feed display and filtering operations
- prayer/prayer_operations.py - Prayer submission, preview, and core operations  
- prayer/prayer_status.py - Status management (marking, archiving, answering)
- prayer/prayer_moderation.py - Moderation and flagging operations

All routes maintain exact same signatures and logic as original implementation
for 100% backward compatibility.

Usage:
This router is included in the main FastAPI app via:
    from app_helpers.routes.prayer_routes import router as prayer_router
    app.include_router(prayer_router)
"""

from fastapi import APIRouter

# Import required dependencies for backward compatibility with tests
from sqlmodel import Session
from models import engine

# Create main router instance
router = APIRouter()

# Import all sub-module routers and include them
from .prayer.feed_operations import router as feed_router
from .prayer.prayer_operations import router as crud_router  
from .prayer.prayer_status import router as status_router
from .prayer.prayer_moderation import router as moderation_router
from .prayer.prayer_mode import router as prayer_mode_router

# Include all sub-routers to maintain all existing routes
router.include_router(feed_router)
router.include_router(crud_router)
router.include_router(status_router)
router.include_router(moderation_router)
router.include_router(prayer_mode_router)