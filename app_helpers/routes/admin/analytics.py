"""
Admin Analytics Routes

Contains routes for statistical analysis and reporting.
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from sqlmodel import Session

# Import models
from models import engine

# Import helper functions
from app_helpers.services.auth_helpers import current_user, is_admin

# Create router for this module
router = APIRouter()


# Religious preference analytics endpoints have been removed
# as part of the religious preference cleanup