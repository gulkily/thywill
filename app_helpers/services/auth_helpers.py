# app_helpers/services/auth_helpers.py
"""
Authentication helper functions - Main aggregator module.

This module has been refactored into focused sub-modules for better maintainability:
- auth/session_helpers.py - Session creation, validation, and user retrieval
- auth/token_helpers.py - Authentication request lifecycle and notifications
- auth/validation_helpers.py - Security validation, logging, and rate limiting

All functions maintain exact same signatures and logic as original implementation
for 100% backward compatibility.

Usage:
This module is imported throughout the application via:
    from app_helpers.services.auth_helpers import current_user, is_admin, ...
"""

# Import all functions from sub-modules to maintain backward compatibility
from .auth.session_helpers import (
    create_session,
    current_user, 
    require_full_auth,
    validate_session_security
)

from .auth.token_helpers import (
    create_auth_request,
    approve_auth_request,
    get_pending_requests_for_approval,
    cleanup_expired_requests,
    create_auth_notification,
    get_unread_auth_notifications,
    mark_notification_read,
    get_notification_count,
    cleanup_expired_notifications
)

from .auth.validation_helpers import (
    is_admin,
    log_auth_action,
    log_security_event,
    check_rate_limit
)

# Re-export constants for backward compatibility
from .auth.session_helpers import SESSION_DAYS
from .auth.token_helpers import PEER_APPROVAL_COUNT
from .auth.validation_helpers import MAX_AUTH_REQUESTS_PER_HOUR

# Re-export Session for backward compatibility with tests
from sqlmodel import Session