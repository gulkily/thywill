# Development Plan: Admin User-Specific Login Links
*Using existing `/claim/{token}?goto=/path` pattern*

## Stage 1: Goto Parameter Support
**Goal**: Add goto query parameter support to existing `/claim/{token}` route
**Dependencies**: None (extends existing route)
**Changes**: Modify claim route in login_routes.py to handle `?goto=/path` parameter after successful login
**Testing**: Integration tests for goto parameter with valid/invalid paths
**Risk**: Open redirect - mitigate by validating goto URLs are relative paths only

## Stage 2: New Token Type for User-Specific Login
**Goal**: Create "user_login" token type that allows existing users to log in without granting admin rights
**Dependencies**: Stage 1 complete
**Changes**: Add "user_login" to token_type field options, modify claim route logic to handle user_login tokens for existing users
**Testing**: Unit tests for new token type validation and existing user login flow
**Risk**: Permission escalation - mitigate by ensuring user_login tokens don't grant additional privileges

## Stage 3: Admin Token Creation UI
**Goal**: Add admin panel interface for creating user-specific login links with redirect
**Dependencies**: Stage 2 complete
**Changes**: Add admin form with username input and goto URL field, generate URLs like `/claim/{token}?goto=/prayer/123`
**Testing**: Functional tests for admin UI token creation and URL generation
**Risk**: UI security - mitigate with existing admin authorization and input validation

## Leveraging Existing Systems

### ✅ Already Implemented (95% Complete)
- **Token Storage**: InviteToken model with expiration and usage tracking
- **Token Generation**: Secure random token creation in token_service.py
- **Token Validation**: Existing `/claim/{token}` route handles token validation
- **Admin Authentication**: Admin role system and route protection
- **Security Logging**: Comprehensive audit logging for token operations
- **User Login Flow**: Existing user authentication and session creation

### 🔧 Minimal Changes Needed
1. **Extend `/claim/{token}`**: Add `?goto=/path` query parameter support
2. **New Token Type**: Add "user_login" type that logs in existing users without privilege changes
3. **Admin UI**: Simple form that generates `/claim/{token}?goto=/path` URLs

## Database Schema Changes
**None required** - uses existing InviteToken model with new token_type value

## Key Functions (Mostly Existing)
- `token_service.create_token_for_user(username, token_type="user_login", hours=12)` → extend existing
- `/claim/{token}?goto=/prayer/123` → extend existing route
- Admin form → generates clear destination URLs showing exactly where user will go

## Testing Strategy
- **Unit Tests**: Model validation, service methods, token security
- **Integration Tests**: Admin authorization, token flow, redirect handling
- **Functional Tests**: End-to-end admin interface workflow
- **Security Tests**: Token uniqueness, expiration, authorization bypass attempts

## Risk Assessment

### High Risk: Token Security
**Issue**: Weak tokens could be guessed or brute-forced
**Mitigation**: Use cryptographically secure random generation (secrets.token_urlsafe), minimum 32 bytes

### Medium Risk: Authorization Bypass  
**Issue**: Non-admins could access token creation endpoints
**Mitigation**: Thorough testing of require_admin() decorator, explicit permission checks

### Low Risk: Resource Accumulation
**Issue**: Expired tokens accumulating in database
**Mitigation**: Regular cleanup process, database indexing on expires_at

### Low Risk: Redirect Injection
**Issue**: Malicious redirect URLs could send users to external sites
**Mitigation**: Validate redirect URLs are relative paths only, no external domains allowed

## Implementation Notes
- Integrate with existing admin authentication patterns
- Follow project naming conventions (snake_case)
- Use existing SecurityLog model for audit trail
- Maintain compatibility with current session management
- All admin routes should use existing admin template layout