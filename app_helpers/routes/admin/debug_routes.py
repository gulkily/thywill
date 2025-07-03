# app_helpers/routes/admin/debug_routes.py
"""
Admin debug routes for checking environment configuration.
Only accessible to admin users for troubleshooting production issues.
"""

import os
from datetime import datetime, timedelta
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlmodel import Session

from app_helpers.services.auth_helpers import current_user, is_admin
from models import InviteToken, engine
from app import templates

router = APIRouter()

@router.get("/admin/debug", response_class=HTMLResponse)
def debug_environment(request: Request, user_session: tuple = Depends(current_user)):
    """
    Debug page showing environment configuration and token expiration settings.
    Only accessible to admin users.
    """
    user, session = user_session
    if not session.is_fully_authenticated:
        raise HTTPException(403, "Full authentication required")
    
    if not is_admin(user):
        raise HTTPException(403, "Admin access required")
    
    # Import TOKEN_EXP_H from app to get the actual value being used
    from app import TOKEN_EXP_H
    
    # Gather environment debug information
    debug_info = {
        # Current working directory and .env file detection
        'current_directory': os.getcwd(),
        'env_file_exists': os.path.exists('.env'),
        'env_file_path': os.path.abspath('.env') if os.path.exists('.env') else 'Not found',
        
        # Environment variables
        'invite_token_expiration_hours_env': os.getenv('INVITE_TOKEN_EXPIRATION_HOURS'),
        'token_exp_h_calculated': TOKEN_EXP_H,
        'port': os.getenv('PORT', 'not set'),
        'anthropic_api_key_set': bool(os.getenv('ANTHROPIC_API_KEY')),
        
        # Time information
        'current_utc_time': datetime.utcnow(),
        'server_local_time': datetime.now(),
        
        # All relevant environment variables
        'relevant_env_vars': {
            key: value for key, value in os.environ.items() 
            if any(word in key.upper() for word in ['TOKEN', 'HOUR', 'INVITE', 'PORT', 'ANTHROPIC'])
        }
    }
    
    # Test token creation calculation
    test_creation_time = datetime.utcnow()
    test_expiration_time = test_creation_time + timedelta(hours=TOKEN_EXP_H)
    debug_info['test_token_creation'] = test_creation_time
    debug_info['test_token_expiration'] = test_expiration_time
    debug_info['test_token_hours_valid'] = TOKEN_EXP_H
    debug_info['test_token_days_valid'] = TOKEN_EXP_H / 24
    
    # Get recent invite tokens to check actual stored expiration times
    debug_info['recent_tokens'] = []
    try:
        with Session(engine) as db:
            recent_tokens = db.query(InviteToken).order_by(InviteToken.expires_at.desc()).limit(5).all()
            for token in recent_tokens:
                # Calculate what the creation time would have been based on current TOKEN_EXP_H
                implied_creation = token.expires_at - timedelta(hours=TOKEN_EXP_H)
                debug_info['recent_tokens'].append({
                    'token_preview': token.token[:8] + '...',
                    'created_by': token.created_by_user,
                    'expires_at': token.expires_at,
                    'used': token.used,
                    'implied_creation_time': implied_creation,
                    'hours_until_expiry': (token.expires_at - datetime.utcnow()).total_seconds() / 3600
                })
    except Exception as e:
        debug_info['token_query_error'] = str(e)
    
    return templates.TemplateResponse("admin_debug.html", {
        "request": request,
        "user": user,
        "debug_info": debug_info
    })