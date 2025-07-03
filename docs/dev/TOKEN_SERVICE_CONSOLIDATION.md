# Token Service Consolidation

## Overview

The invite token generation system has been consolidated into a centralized service to eliminate code duplication and ensure consistent behavior across the application.

## Centralized Service

### Location
- **Primary Service**: `app_helpers/services/token_service.py`

### Key Functions
- `create_invite_token()` - Create user invite tokens
- `create_system_token()` - Create admin/system tokens  
- `generate_invite_token()` - Generate secure token strings
- `calculate_expiration_time()` - Calculate expiration timestamps
- `get_token_expiration_config()` - Get configuration info for debugging

### Configuration
- **Single Source**: `TOKEN_EXP_H` defined in `token_service.py`
- **Environment Variable**: `INVITE_TOKEN_EXPIRATION_HOURS` (default: 12)

## Migration Summary

### Before Consolidation
- `TOKEN_EXP_H` defined in **4 different files**
- Token generation logic duplicated across modules
- Inconsistent expiration calculations
- Hardcoded values mixed with environment variables

### After Consolidation
- **Single definition** of `TOKEN_EXP_H`
- **Centralized functions** for all token operations
- **Consistent behavior** across all creation paths
- **Session management** handled properly

## Updated Files

### Core Service
- ✅ `app_helpers/services/token_service.py` - New centralized service

### Routes Updated
- ✅ `app_helpers/routes/invite_routes.py` - Uses `create_invite_token()`
- ✅ `app_helpers/routes/auth/login_routes.py` - Imports `TOKEN_EXP_H`
- ✅ `app_helpers/routes/admin/debug_routes.py` - Imports from token_service

### Scripts Updated  
- ✅ `scripts/admin/create_admin_token.py` - Uses `create_system_token()`

### Infrastructure Updated
- ✅ `app.py` - First-run seeding uses `create_system_token()`
- ✅ `app_helpers/services/invite_helpers.py` - Imports `TOKEN_EXP_H`
- ✅ `tests/factories.py` - Uses centralized configuration
- ✅ `tests/integration/test_admin_invite_authentication.py` - Uses `TOKEN_EXP_H`

### Templates Updated
- ✅ `templates/claim.html` - Shows dynamic expiration time
- ✅ `templates/admin_debug.html` - Displays current configuration

## Usage Examples

### Creating User Invite Tokens
```python
from app_helpers.services.token_service import create_invite_token

token_info = create_invite_token(created_by_user="username")
print(f"Token: {token_info['token']}")
print(f"Expires: {token_info['expires_at']}")
```

### Creating Admin Tokens
```python
from app_helpers.services.token_service import create_system_token

token_info = create_system_token(custom_expiration_hours=720)
print(f"Admin token: {token_info['token']}")
```

### Getting Configuration
```python
from app_helpers.services.token_service import get_token_expiration_config

config = get_token_expiration_config()
print(f"Current expiration: {config['calculated_hours']} hours")
```

## Environment Configuration

### Setting Custom Expiration
```bash
# In .env file or environment
INVITE_TOKEN_EXPIRATION_HOURS=720  # 30 days

# Or for systemd service
Environment="INVITE_TOKEN_EXPIRATION_HOURS=720"
```

### Debug Page
Visit `/admin/debug` to verify environment configuration and see:
- Current `TOKEN_EXP_H` value
- Environment variable status
- Recent token expiration times
- Configuration diagnostics

## Benefits

1. **Single Source of Truth**: All token logic in one place
2. **Easy Maintenance**: Changes only need to be made once
3. **Consistent Behavior**: No more hardcoded vs environment variable conflicts
4. **Better Testing**: Centralized logic is easier to test
5. **Proper Session Management**: Avoids SQLAlchemy session detachment issues

## Troubleshooting

### Token Expiration Issues
1. Check `/admin/debug` page for current configuration
2. Verify `INVITE_TOKEN_EXPIRATION_HOURS` environment variable
3. Restart service after environment changes

### Import Errors
All imports should now use:
```python
from app_helpers.services.token_service import TOKEN_EXP_H, create_invite_token
```

### Session Errors
The service returns dictionaries instead of ORM objects to avoid session detachment issues.