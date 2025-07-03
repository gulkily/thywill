"""
Admin Routes Module - Import Aggregator

This module maintains backward compatibility by importing all admin route handlers
from their respective sub-modules. All existing imports will continue to work unchanged.

The admin functionality is now organized into focused modules:
- dashboard.py: Main admin dashboard and audit logging
- auth_management.py: Authentication request management
- analytics.py: Statistical analysis and reporting
- user_management.py: User management and deactivation
- moderation.py: Content moderation (flagging/unflagging)
"""

from fastapi import APIRouter

# Import all route handlers from sub-modules
from .admin.dashboard import *
from .admin.auth_management import *
from .admin.analytics import *
from .admin.user_management import *
from .admin.moderation import *
from .admin.debug_routes import *

# Create main router and include all sub-module routers
router = APIRouter()

# Import routers from sub-modules
from .admin.dashboard import router as dashboard_router
from .admin.auth_management import router as auth_mgmt_router
from .admin.analytics import router as analytics_router
from .admin.user_management import router as user_mgmt_router
from .admin.moderation import router as moderation_router
from .admin.debug_routes import router as debug_router

# Include all sub-module routes
router.include_router(dashboard_router)
router.include_router(auth_mgmt_router)
router.include_router(analytics_router)
router.include_router(user_mgmt_router)
router.include_router(moderation_router)
router.include_router(debug_router)