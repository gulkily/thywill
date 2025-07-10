# Phase 0: Intent-Based Authentication Implementation Plan

## Overview
Developer implementation guide for the intent-based authentication system that prevents username conflicts. This is the prerequisite foundation for cryptographic authentication and solves the urgent "Ilya problem" where two people with the same name could accidentally merge accounts.

## Implementation Goals
1. **Prevent Username Conflicts**: Stop accidental account merging during registration
2. **Separate Flows**: Distinguish new user registration from multi-device login
3. **Maintain Security**: Preserve all existing authentication security measures
4. **Foundation for Crypto**: Create token type infrastructure for future crypto system

## Database Schema Changes

### Step 1: Add token_type to InviteToken Table
```sql
-- Migration: Add token_type column
ALTER TABLE invite_tokens ADD COLUMN token_type VARCHAR(20) DEFAULT 'new_user';

-- Update existing tokens to 'new_user' type for backward compatibility
UPDATE invite_tokens SET token_type = 'new_user' WHERE token_type IS NULL;

-- Add index for performance
CREATE INDEX idx_invite_tokens_token_type ON invite_tokens(token_type);
```

### Step 2: Update InviteToken Model
```python
# models.py
class InviteToken(SQLModel, table=True):
    # ... existing fields ...
    token_type: str = Field(default="new_user", max_length=20)  # 'new_user' or 'multi_device'
```

## Backend Implementation

### Step 3: Update Invite Creation Logic
```python
# app_helpers/services/invite_helpers.py

def create_invite_token(created_by_user: str, token_type: str = "new_user", max_uses: int = 1) -> str:
    """
    Create invite token with specified type.
    
    Args:
        created_by_user: User creating the invite
        token_type: 'new_user' for registration, 'multi_device' for device addition
        max_uses: Maximum number of uses (default 1)
    """
    if token_type not in ["new_user", "multi_device"]:
        raise ValueError("token_type must be 'new_user' or 'multi_device'")
    
    token = uuid.uuid4().hex
    expires_at = datetime.utcnow() + timedelta(hours=TOKEN_EXP_H)
    
    invite = InviteToken(
        token=token,
        created_by_user=created_by_user,
        token_type=token_type,
        max_uses=max_uses,
        expires_at=expires_at
    )
    
    # Save to database and archive
    with Session(engine) as session:
        session.add(invite)
        session.commit()
        
    return token

def create_device_token(user_id: str) -> str:
    """Create a multi-device token for adding new devices."""
    return create_invite_token(
        created_by_user=user_id,
        token_type="multi_device",
        max_uses=1
    )
```

### Step 4: Update Claim Route Logic
```python
# app_helpers/routes/auth/login_routes.py

@router.post("/claim/{token}")
def claim_post(token: str, display_name: str = Form(...), request: Request = None):
    """
    Process invite token claim with token type validation.
    """
    with Session(engine) as s:
        inv = s.get(InviteToken, token)
        if not inv or inv.expires_at < datetime.utcnow():
            return templates.TemplateResponse("claim.html", {
                "request": request, 
                "token": token,
                "error": "This invite link has expired or is not valid."
            })
        
        # Check usage limits
        if inv.max_uses is not None and inv.usage_count >= inv.max_uses:
            return templates.TemplateResponse("claim.html", {
                "request": request, 
                "token": token,
                "error": f"This invite link has reached its usage limit."
            })

        # Validate and normalize username
        is_valid, normalized_display_name = validate_username(display_name)
        if not is_valid:
            return templates.TemplateResponse("claim.html", {
                "request": request, 
                "token": token,
                "error": "Please enter a valid username."
            })
        
        # Check for existing users
        existing_users = find_users_with_equivalent_usernames(s, normalized_display_name)
        existing_user = existing_users[0] if existing_users else None
        
        # TOKEN TYPE VALIDATION - This is the key change
        if inv.token_type == "new_user":
            # NEW USER REGISTRATION: Reject if username exists
            if existing_user:
                return templates.TemplateResponse("claim.html", {
                    "request": request,
                    "token": token,
                    "error": f"Username '{display_name}' already exists. Please choose a different name like {display_name}_2024, {display_name}_Smith, etc."
                })
            
            # Create new user account
            return create_new_user_account(token, normalized_display_name, request, s)
            
        elif inv.token_type == "multi_device":
            # MULTI-DEVICE LOGIN: Require existing username
            if not existing_user:
                return templates.TemplateResponse("claim.html", {
                    "request": request,
                    "token": token,
                    "error": f"This device link is for an existing account. Username '{display_name}' not found. Please enter the exact username for the account you want to access."
                })
            
            # Log into existing account
            return login_to_existing_account(token, existing_user, request, s)
        
        else:
            # Invalid token type
            return templates.TemplateResponse("claim.html", {
                "request": request,
                "token": token,
                "error": "Invalid invite link type. Please request a new invite."
            })

def create_new_user_account(token: str, display_name: str, request: Request, session: Session):
    """Create new user account (extracted for clarity)."""
    # ... existing new user creation logic ...
    pass

def login_to_existing_account(token: str, user: User, request: Request, session: Session):
    """Log into existing user account (extracted for clarity)."""
    # ... existing user login logic ...
    pass
```

## Frontend Implementation

### Step 5: Update Menu Page - Add Device Button
```python
# app_helpers/routes/general_routes.py

@router.get("/menu", response_class=HTMLResponse)
def menu_page(request: Request, user_session: tuple = Depends(current_user)):
    """Menu page with device addition option."""
    user, session = user_session
    
    # Check if user can create device tokens
    can_create_device_token = session.is_fully_authenticated
    
    return templates.TemplateResponse("menu.html", {
        "request": request,
        "user": user,
        "session": session,
        "can_create_device_token": can_create_device_token,
        "is_admin": is_admin(user)
    })

@router.post("/create-device-token")
def create_device_token_route(request: Request, user_session: tuple = Depends(require_full_auth)):
    """Create a device token for current user."""
    user, session = user_session
    
    try:
        token = create_device_token(user.display_name)
        device_url = f"{request.base_url}claim/{token}"
        
        return templates.TemplateResponse("device_token_modal.html", {
            "request": request,
            "token": token,
            "device_url": device_url,
            "expires_hours": TOKEN_EXP_H
        })
    except Exception as e:
        return HTTPException(500, f"Failed to create device token: {str(e)}")
```

### Step 6: Update Menu Template
```html
<!-- templates/menu.html -->
<!-- Add to User Account Section -->
<div class="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
  <div class="flex items-center mb-4">
    <div class="w-12 h-12 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center mr-4 flex-shrink-0">
      <svg class="w-6 h-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
      </svg>
    </div>
    <div>
      <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100">My Devices</h3>
      <p class="text-sm text-gray-600 dark:text-gray-400">Add devices or manage your account access</p>
    </div>
  </div>
  <div class="space-y-2">
    {% if can_create_device_token %}
    <button 
      hx-post="/create-device-token"
      hx-target="body" 
      hx-swap="beforeend"
      class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900 hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors w-full justify-center">
      📱 Add New Device
    </button>
    {% endif %}
    <a href="/auth/my-requests" class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900 hover:bg-green-200 dark:hover:bg-green-800 transition-colors w-full justify-center">
      🔑 My Login Requests
    </a>
  </div>
</div>
```

### Step 7: Create Device Token Modal
```html
<!-- templates/device_token_modal.html -->
<div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" 
     onclick="if(event.target === this) this.remove()">
  <div class="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 max-w-md w-full mx-4" onclick="event.stopPropagation()">
    <div class="flex justify-between items-center mb-4">
      <h3 class="text-lg font-medium text-gray-900 dark:text-gray-100">Add New Device</h3>
      <button onclick="this.closest('.fixed').remove()" class="text-gray-400 hover:text-gray-600">
        <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
        </svg>
      </button>
    </div>
    
    <div class="mb-4">
      <p class="text-sm text-gray-600 dark:text-gray-400 mb-3">
        Use this link on your new device to add it to your account:
      </p>
      <div class="bg-gray-50 dark:bg-gray-700 rounded p-3 break-all text-sm">
        <span id="device-url">{{ device_url }}</span>
      </div>
    </div>
    
    <div class="mb-4">
      <button onclick="copyDeviceUrl()" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded transition-colors">
        📋 Copy Link
      </button>
    </div>
    
    <div class="text-xs text-gray-500 dark:text-gray-400">
      <p>⏰ Expires in {{ expires_hours }} hours</p>
      <p>🔒 This link is for your account only</p>
    </div>
  </div>
</div>

<script>
function copyDeviceUrl() {
  const url = document.getElementById('device-url').textContent;
  navigator.clipboard.writeText(url).then(() => {
    const button = event.target;
    const originalText = button.textContent;
    button.textContent = '✅ Copied!';
    button.classList.remove('bg-blue-600', 'hover:bg-blue-700');
    button.classList.add('bg-green-600');
    setTimeout(() => {
      button.textContent = originalText;
      button.classList.remove('bg-green-600');
      button.classList.add('bg-blue-600', 'hover:bg-blue-700');
    }, 2000);
  }).catch(() => {
    // Fallback for older browsers
    const range = document.createRange();
    range.selectNode(document.getElementById('device-url'));
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
    document.execCommand('copy');
    window.getSelection().removeAllRanges();
  });
}

// Close modal on Escape key
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    document.querySelector('.fixed.inset-0')?.remove();
  }
});
</script>
```

### Step 8: Update Claim Template for Better UX
```html
<!-- templates/claim.html - Update form section -->
<form method="post" action="/claim/{{ token }}" class="space-y-4" aria-label="Complete invitation">
  <div>
    <label for="display_name" class="block text-sm font-medium text-gray-700 dark:text-gray-200 mb-2">
      {% if token_type == 'multi_device' %}
        Enter Your Existing Username
      {% else %}
        Choose Your Display Name
      {% endif %}
    </label>
    <input id="display_name" name="display_name" maxlength="40" required
           {% if token_type == 'multi_device' %}
           placeholder="Enter your exact username"
           {% else %}
           placeholder="e.g., Sarah, John M., PrayerWarrior"
           {% endif %}
           class="w-full border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg px-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent" />
    <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">
      {% if token_type == 'multi_device' %}
        This device link is for accessing an existing account
      {% else %}
        No email required • Visible to community members
      {% endif %}
    </p>
  </div>

  <button type="submit"
          class="w-full bg-purple-600 hover:bg-purple-700 dark:bg-purple-700 dark:hover:bg-purple-600 text-white font-semibold py-4 text-lg rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2">
    {% if token_type == 'multi_device' %}
      Access My Account
    {% else %}
      Join ThyWill Community
    {% endif %}
  </button>
</form>
```

## Admin Interface Updates

### Step 9: Update Admin Token Creation
```python
# app_helpers/routes/admin/user_management.py

@router.post("/admin/create-invite")
def create_invite_admin(
    token_type: str = Form("new_user"),
    max_uses: int = Form(1),
    user_session: tuple = Depends(require_admin)
):
    """Admin interface for creating invite tokens."""
    user, session = user_session
    
    if token_type not in ["new_user", "multi_device"]:
        raise HTTPException(400, "Invalid token type")
    
    try:
        token = create_invite_token(
            created_by_user=user.display_name,
            token_type=token_type,
            max_uses=max_uses
        )
        
        return {
            "success": True,
            "token": token,
            "type": token_type,
            "url": f"/claim/{token}"
        }
    except Exception as e:
        raise HTTPException(500, f"Failed to create invite: {str(e)}")
```

## Testing Requirements

### Step 10: Test Cases
```python
# tests/unit/test_intent_based_auth.py

def test_new_user_token_rejects_existing_username():
    """Test that new_user tokens reject existing usernames."""
    # Create user "Alice"
    # Create new_user token
    # Attempt to claim with "Alice" username
    # Should fail with appropriate error message

def test_multi_device_token_requires_existing_username():
    """Test that multi_device tokens require existing usernames."""
    # Create multi_device token
    # Attempt to claim with non-existent username
    # Should fail with appropriate error message

def test_multi_device_token_allows_existing_username():
    """Test that multi_device tokens allow existing usernames."""
    # Create user "Bob"
    # Create multi_device token
    # Claim with "Bob" username
    # Should succeed and log into existing account

def test_backward_compatibility():
    """Test that existing tokens work as new_user type."""
    # Create token without token_type (defaults to new_user)
    # Should behave as new_user token

def test_device_token_creation():
    """Test device token creation from menu."""
    # Login as user
    # Create device token
    # Verify token has multi_device type
    # Verify token works for device addition

def test_username_suggestions():
    """Test error messages provide helpful suggestions."""
    # Attempt new_user registration with existing username
    # Verify error message suggests alternatives
```

## Migration and Deployment

### Step 11: Database Migration Script
```python
# migrations/009_intent_based_tokens/migrate.py

def migrate_up():
    """Add token_type column and set defaults."""
    with engine.begin() as conn:
        # Add column
        conn.execute(text("ALTER TABLE invite_tokens ADD COLUMN token_type VARCHAR(20) DEFAULT 'new_user'"))
        
        # Update existing tokens
        conn.execute(text("UPDATE invite_tokens SET token_type = 'new_user' WHERE token_type IS NULL"))
        
        # Add index
        conn.execute(text("CREATE INDEX idx_invite_tokens_token_type ON invite_tokens(token_type)"))

def migrate_down():
    """Remove token_type column."""
    with engine.begin() as conn:
        conn.execute(text("DROP INDEX IF EXISTS idx_invite_tokens_token_type"))
        conn.execute(text("ALTER TABLE invite_tokens DROP COLUMN token_type"))
```

### Step 12: Environment Variables
```bash
# .env additions
# Intent-based authentication settings
DEFAULT_TOKEN_TYPE=new_user                 # Default token type for invite creation
DEVICE_TOKEN_EXPIRY_HOURS=24               # Device token expiration (shorter than regular invites)
MAX_DEVICE_TOKENS_PER_USER=3               # Limit device tokens per user
```

## Success Criteria

### Phase 0 Complete When:
1. ✅ **Database**: `token_type` field added and working
2. ✅ **New User Flow**: Registration rejects existing usernames
3. ✅ **Multi-Device Flow**: Device addition requires existing usernames  
4. ✅ **UI**: "Add Device" button in menu generates device tokens
5. ✅ **Security**: All existing authentication security measures preserved
6. ✅ **Testing**: Full test coverage for both token types
7. ✅ **Admin**: Admin can create both token types
8. ✅ **Migration**: Existing tokens work without breaking changes

### Validation Tests:
- [ ] Two people named "Ilya" cannot merge accounts
- [ ] Device addition works smoothly for existing users
- [ ] Error messages are helpful and clear
- [ ] All existing functionality continues working
- [ ] Performance impact is minimal

## Timeline
- **Day 1-2**: Database migration and model updates
- **Day 3-4**: Backend logic implementation
- **Day 5-6**: Frontend UI updates
- **Day 7**: Admin interface updates
- **Day 8-9**: Testing and bug fixes
- **Day 10**: Documentation and deployment

## Risk Mitigation
- **Backward Compatibility**: All existing tokens default to `new_user` type
- **Gradual Rollout**: Feature can be feature-flagged if needed
- **Rollback Plan**: Migration script includes down migration
- **Testing**: Comprehensive test coverage before deployment

This implementation provides the foundation for cryptographic authentication while solving the immediate username conflict issue.