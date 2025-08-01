"""
Shared templates instance with custom filters registered.
This ensures all route modules use the same Jinja2Templates instance with filters.
"""

from fastapi.templating import Jinja2Templates

# Create the shared templates instance
templates = Jinja2Templates(directory="templates")

# Register custom template filters
from app_helpers.template_filters import register_filters
register_filters(templates)