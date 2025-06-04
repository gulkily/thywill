# Login Feature Specification

## Overview
This document specifies the behavior of the direct login feature that allows existing users to access the lobby authentication system without invite links.

## Feature Toggle Control

### Environment Variable
- **Variable**: `MULTI_DEVICE_AUTH_ENABLED`
- **Default**: `"true"`
- **Values**: `"true"` (enabled) or `"false"` (disabled)

### Feature Availability
- ✅ **When Enabled**: Login options visible, `/login` route accessible
- ❌ **When Disabled**: Login options hidden, `/login` route returns 404 or redirect

## User Interface Behavior

### Login Options Visibility

#### Template Locations Showing Login Options:
1. **`templates/logged_out.html`** - "Login as Existing User" button
2. **`templates/unauthorized.html`** - "Access Required" page  
3. **`templates/login.html`** - Login form itself

#### Conditional Display Logic:
```jinja2
{% if MULTI_DEVICE_AUTH_ENABLED %}
  <!-- Show login button/form -->
{% endif %}
```

### Route Access Control

#### `/login` Route Behavior:
- **When Feature Enabled**: Show login form or process login
- **When Feature Disabled**: Return 404 Not Found or redirect to logged_out

## Username Handling Specification

### Scenario 1: Existing Username Login

#### Prerequisites:
- Username exists in `User` table
- `MULTI_DEVICE_AUTH_ENABLED = true`
- `REQUIRE_APPROVAL_FOR_EXISTING_USERS = true` (default)

#### Flow:
1. **User submits existing username**
2. **System validates username exists** ✅
3. **Rate limiting check** (3 requests/hour per user/IP)
4. **Duplicate request check** (no pending requests from same IP/device in last hour)
5. **Create authentication request** using existing `create_auth_request()` helper
6. **Create half-authenticated session** with `is_fully_authenticated = false`
7. **Redirect to `/auth/status`** (existing lobby page)

#### Security Checks:
- ✅ Rate limiting via `check_rate_limit(user_id, ip_address)`
- ✅ Device fingerprinting via User-Agent header
- ✅ IP address logging
- ✅ Audit trail via `log_auth_action()`
- ✅ Duplicate request prevention

#### Approval Process:
- **Same as existing multi-device auth**:
  - Admin approval (instant)
  - Self-approval (if user has another fully authenticated device)
  - Peer approval (2 community members by default)

#### Success Outcome:
- User gains full authentication
- Session upgraded to `is_fully_authenticated = true`
- Automatic redirect to main feed (`/`)

### Scenario 2: Non-Existing Username Login

#### Prerequisites:
- Username does NOT exist in `User` table
- User submits username via `/login` form

#### Current Behavior:
```python
if not existing_user:
    return templates.TemplateResponse(
        "login.html", 
        {
            "request": request, 
            "error": "Username not found. Please check your username or request an invite link to create a new account.",
            "username": username.strip()
        }
    )
```

#### Design Decision Analysis:

##### Option A: Error Message Only (Current Implementation)
**Pros:**
- Clear messaging about what went wrong
- Directs users to proper registration flow
- Prevents username enumeration attacks
- Simple implementation

**Cons:**
- Requires users to know exact existing usernames
- No path for new user registration via login form

##### Option B: Automatic New User Registration
**Pros:**
- Streamlined user experience
- Single entry point for all users

**Cons:**
- Security risk - anyone can create accounts
- Bypasses invite-only community model
- Could enable spam/abuse
- Conflicts with existing invite-based registration

##### Option C: Hybrid Approach with Feature Flag
**Pros:**
- Configurable behavior
- Maintains security when needed
- Flexibility for different deployment scenarios

**Cons:**
- Additional complexity
- More configuration to manage

#### Recommended Approach: Option A (Current Implementation)

**Rationale:**
1. **Preserves Community Model**: The application is designed as an invite-only community
2. **Maintains Security**: Prevents unauthorized account creation
3. **Clear User Guidance**: Error message directs users to proper registration path
4. **Consistent with Existing System**: Aligns with current invite-based workflow

#### Security Considerations for Non-Existing Usernames:

##### Username Enumeration Protection:
- **Current**: Error message reveals username doesn't exist
- **Risk Level**: Low (community members likely know each other)
- **Mitigation Options**:
  - Generic error: "Invalid login credentials"
  - Rate limiting on failed attempts
  - Honeypot detection

##### Brute Force Protection:
- ✅ **Current**: Rate limiting via IP address
- ✅ **Enhancement**: Failed attempt tracking per username
- ✅ **Security**: Temporary blocks after repeated failures

## Error Handling Specification

### Error Categories and Messages:

#### 1. Feature Disabled
- **Condition**: `MULTI_DEVICE_AUTH_ENABLED = false`
- **Response**: 404 Not Found or redirect
- **User Message**: Login options not visible

#### 2. Username Not Found
- **Condition**: Username doesn't exist in database
- **Response**: 400 Bad Request with error template
- **User Message**: "Username not found. Please check your username or request an invite link to create a new account."

#### 3. Rate Limited
- **Condition**: Exceeded 3 requests per hour per user/IP
- **Response**: 429 Too Many Requests with error template  
- **User Message**: "Too many login attempts. Please try again later."

#### 4. Duplicate Request
- **Condition**: Pending request from same IP/device within 1 hour
- **Response**: 400 Bad Request with error template
- **User Message**: "You already have a pending login request from this device. Please wait for approval."

#### 5. Validation Error
- **Condition**: Empty/invalid username format
- **Response**: 422 Unprocessable Entity
- **User Message**: Form validation errors

### Error Response Format:
```python
return templates.TemplateResponse(
    "login.html", 
    {
        "request": request, 
        "error": "User-friendly error message",
        "username": submitted_username  # Preserve input
    }
)
```

## Configuration Matrix

### Feature Flag Combinations:

| MULTI_DEVICE_AUTH_ENABLED | REQUIRE_APPROVAL_FOR_EXISTING_USERS | Login Feature Behavior |
|---------------------------|--------------------------------------|----------------------|
| `false` | `false` | ❌ Login options hidden, route disabled |
| `false` | `true` | ❌ Login options hidden, route disabled |
| `true` | `false` | ⚠️ Login bypasses approval (instant auth) |
| `true` | `true` | ✅ Login requires approval (lobby flow) |

### Recommended Production Settings:
```env
MULTI_DEVICE_AUTH_ENABLED=true
REQUIRE_APPROVAL_FOR_EXISTING_USERS=true
PEER_APPROVAL_COUNT=2
```

## User Experience Flow Diagrams

### Successful Login Flow:
```
User visits /login 
    ↓
Enters existing username
    ↓
System validates + creates auth request
    ↓
Redirected to /auth/status (lobby)
    ↓
Waits for approval (auto-refresh page)
    ↓
Gets approved by admin/self/peers
    ↓
Auto-redirected to main feed
```

### Failed Login Flow:
```
User visits /login
    ↓
Enters non-existing username
    ↓
System returns error message
    ↓
User sees preserved username + error
    ↓
User can retry or request invite link
```

## Integration Points

### Existing Systems Used:
- ✅ **Authentication Helper**: `create_auth_request()`, `create_session()`
- ✅ **Security System**: `check_rate_limit()`, rate limiting, audit logging
- ✅ **Lobby System**: `/auth/status`, `/auth/pending`, approval workflow
- ✅ **Session Management**: Half-authenticated sessions, automatic upgrades

### No Changes Required To:
- Database schema
- Approval workflow logic
- Security infrastructure  
- Existing authentication flows
- Admin interfaces

## Testing Requirements

### Unit Tests:
- [ ] Login form renders correctly when feature enabled/disabled
- [ ] Username validation (existing vs non-existing)
- [ ] Rate limiting enforcement
- [ ] Error message accuracy
- [ ] Session creation and redirection

### Integration Tests:
- [ ] Complete login flow for existing users
- [ ] Error handling for non-existing users
- [ ] Feature flag toggle behavior
- [ ] Integration with existing lobby system
- [ ] Rate limiting across multiple requests

### Security Tests:
- [ ] Username enumeration protection
- [ ] Rate limiting effectiveness
- [ ] Session security validation
- [ ] CSRF protection
- [ ] Input sanitization

## Future Enhancements

### Potential Improvements:
1. **Username Suggestions**: "Did you mean..." for typos
2. **Contact Form**: Allow non-existing users to request invites
3. **Registration Queue**: Lobby for new user requests (admin approval)
4. **Enhanced Security**: Device fingerprinting, anomaly detection
5. **User Feedback**: Progress indicators, estimated approval times

### Feature Flags for Future:
- `ALLOW_NEW_USER_REQUESTS`: Enable registration requests from login form
- `REQUIRE_EMAIL_VERIFICATION`: Email verification for login attempts
- `ENABLE_USERNAME_SUGGESTIONS`: Suggest similar existing usernames

## Success Metrics

### Key Performance Indicators:
- Login success rate (existing users)
- Average time to approval in lobby
- Error rate reduction vs invite-link flow
- User satisfaction with login experience
- Security incident rate

### Monitoring Points:
- Login attempt frequency
- Error type distribution
- Rate limiting triggers
- Approval time metrics
- Community growth via login feature