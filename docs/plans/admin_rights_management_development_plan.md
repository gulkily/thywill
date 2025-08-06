# Admin Rights Management - Development Plan (Step 2)

## Architecture Overview
**Pattern**: Extend existing admin user management with role assignment functionality
**Integration**: Add to existing `/admin/users` route and template 
**Approach**: Minimal changes leveraging existing role-based system

## Atomic Development Stages

### Stage 1: Create Admin Role Assignment Route (< 2 hours)
**File**: `app_helpers/routes/admin/user_management.py`
**Changes**:
- Add `POST /admin/users/{user_id}/grant-admin` route
- Function: `grant_admin_role_route(user_id, request, user_session)`
- Logic:
  - Verify current user is admin via `is_admin(user)`
  - Check target user exists in database
  - Prevent self-promotion (redundant for existing admins)
  - Use existing `UserRole` model to assign "admin" role
  - Return JSON success/error response for HTMX
- Error handling: User not found, already admin, database errors
- Security: Admin-only access, validation, audit logging

**Validation**: Route accessible only to admins, returns proper responses

### Stage 2: Update Users Template with Admin Grant UI (< 2 hours) 
**File**: `templates/users.html`
**Changes**:
- Add admin promotion button in existing admin controls section
- Show only for non-admin users when `is_admin_view` is True
- Button: "Grant Admin" with confirmation modal
- HTMX integration: `hx-post="/admin/users/{user_id}/grant-admin"`
- JavaScript confirmation: "Are you sure you want to grant admin rights to {username}?"
- Success/error message display using existing patterns
- Button disabled after success to prevent duplicate requests

**Integration**: Fits into existing user card layout, follows current styling

**Validation**: Button only visible to admins, only for non-admin users

### Stage 3: Add Confirmation Modal and JavaScript (< 1 hour)
**File**: `templates/users.html` (continued)
**Changes**:
- Reuse existing modal patterns from codebase
- Add confirmation dialog: "Grant admin rights to {username}?"
- Include warning text about admin privileges
- "Cancel" and "Confirm" buttons
- HTMX request on confirm, close modal on cancel
- Success message shows in existing message area

**Integration**: Uses existing JavaScript modal handlers and styling

**Validation**: Modal appears, confirmation required, proper cancellation

### Stage 4: Update Admin Badge Display Logic (< 1 hour)
**File**: `app_helpers/routes/admin/user_management.py`
**Changes**:
- Ensure `is_admin` check in user stats uses current role system
- Refresh user stats after role assignment
- Return updated user data in success response for live UI update

**Integration**: Existing admin badge display automatically updates

**Validation**: Admin badge appears immediately after promotion

### Stage 5: Add Success Message and UI Feedback (< 1 hour)
**File**: `templates/users.html` 
**Changes**:
- HTMX success handler to update button state
- Show "Admin rights granted!" message
- Hide "Grant Admin" button for newly promoted user
- Update admin badge display without page refresh
- Error message display for failures

**Integration**: Uses existing success/error message patterns

**Validation**: Immediate UI feedback, proper error handling

## Technical Implementation Details

### Route Implementation
```python
@router.post("/admin/users/{user_id}/grant-admin")
def grant_admin_role_route(user_id: str, request: Request, user_session: tuple = Depends(current_user)):
    user, session = user_session
    if not is_admin(user):
        raise HTTPException(403, "Admin privileges required")
    
    with Session(engine) as db:
        # Validate target user
        target_user = db.exec(select(User).where(User.display_name == user_id)).first()
        if not target_user:
            return {"status": "error", "message": "User not found"}
        
        # Check if already admin
        if target_user.has_role("admin", db):
            return {"status": "error", "message": "User is already an admin"}
        
        # Grant admin role using existing system
        # Implementation matches existing role assignment patterns
```

### Template Integration
```html
{% if is_admin_view and not user_data.is_admin and not user_data.is_deactivated %}
<button hx-post="/admin/users/{{ user_data.user.display_name }}/grant-admin"
        hx-confirm="Are you sure you want to grant admin rights to {{ user_data.user.display_name }}?"
        class="bg-purple-600 hover:bg-purple-700 text-white text-xs px-2 py-1 rounded">
  Grant Admin
</button>
{% endif %}
```

## Dependencies and Prerequisites
- Existing role-based auth system (`User.has_role()`, `UserRole` table)
- Current admin user management routes and templates
- HTMX integration patterns
- Existing admin check functions (`is_admin()`)

## Testing Strategy
1. **Stage 1**: Test route with curl/Postman - admin access, proper responses
2. **Stage 2**: Visual verification of button placement and visibility
3. **Stage 3**: Modal functionality testing - confirm/cancel behavior  
4. **Stage 4**: Database verification of role assignment
5. **Stage 5**: End-to-end user promotion workflow testing

## Risk Mitigation
- **Security**: Reuse existing admin auth patterns, no new vulnerabilities
- **Database**: Use existing role system, tested UserRole model
- **UI**: Follow existing patterns, minimal template changes
- **Breaking Changes**: Additive only, no existing functionality modified

## Rollback Plan
Each stage is independent and can be reverted:
1. Remove new route (single function)
2. Remove template changes (isolated section)
3. Remove modal JavaScript (self-contained)
4. Revert logic updates (minimal changes)
5. Remove UI feedback (cosmetic changes)

## Success Metrics
- Admin can promote user in < 30 seconds
- No errors in existing admin functionality
- UI feedback is immediate and clear
- Role assignment persists across sessions
- Security model unchanged