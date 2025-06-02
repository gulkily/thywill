# Logout Button Implementation Plan

## Overview
Implement a logout functionality for the Thy Will prayer application to allow users to securely end their session and clear their authentication cookies.

## Current State Analysis
- The application uses session-based authentication with cookies (`sid`)
- Sessions are stored in the `SessionModel` table with expiration times
- Users are authenticated via the `current_user()` function in `app.py:54`
- No existing logout functionality exists

## Implementation Requirements

### 1. Backend Route (`app.py`)
- **Route**: `POST /logout`
- **Functionality**:
  - Clear the user's session from the database
  - Remove the `sid` cookie from the browser
  - Redirect to the login/home page
  - Log the logout action for security audit

### 2. Frontend UI Updates

#### A. Base Template (`templates/base.html`)
- Add logout button to the header navigation (line 86-102)
- Position next to the theme toggle and menu button
- Use appropriate styling consistent with existing UI

#### B. Menu Page (`templates/menu.html`)
- Add logout option to the quick actions or main menu sections
- Include appropriate icon and styling

### 3. Security Considerations
- Use POST method to prevent CSRF attacks
- Clear session from database to prevent session reuse
- Log logout events for audit purposes
- Consider invalidating all sessions for the user (optional)

## Implementation Steps

### Step 1: Backend Implementation
1. Add logout route handler in `app.py`
2. Implement session cleanup logic
3. Add security logging for logout events
4. Test route functionality

### Step 2: Frontend Implementation
1. Add logout button to header in `base.html`
2. Add logout option to menu in `menu.html`
3. Implement proper form/HTMX handling
4. Style buttons consistently with existing UI

### Step 3: Testing
1. Test logout functionality across different pages
2. Verify session is properly cleared
3. Test that logged-out users cannot access protected pages
4. Verify security logging works correctly

## Technical Details

### Database Changes
- No schema changes required
- Will delete records from `SessionModel` table

### Code Changes Required
- `app.py`: Add logout route handler
- `templates/base.html`: Add logout button to header
- `templates/menu.html`: Add logout option to menu

### Security Logging
- Log logout action in `SecurityLog` table
- Include user ID, IP address, and timestamp
- Use existing logging infrastructure

## User Experience
- Logout button will be clearly visible in the header
- Single click logout with immediate redirect
- Clear indication that user has been logged out
- Consistent with existing UI patterns and styling

## Edge Cases to Handle
- Handle logout when session is already expired
- Handle multiple logout attempts
- Ensure proper cleanup if database operation fails
- Handle logout from different devices/sessions

## Future Enhancements (Optional)
- "Logout from all devices" functionality
- Logout confirmation dialog
- Auto-logout after inactivity period
- Remember last visited page for post-login redirect