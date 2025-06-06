# Notification System Manual Testing Guide

## Overview
This guide walks through comprehensive testing of the authentication notification system using two browsers (Chrome and Firefox) to simulate real multi-device scenarios.

## Prerequisites
- Application running locally (usually `uvicorn app:app --reload`)
- Two browsers: Chrome and Firefox
- At least one existing user account
- Understanding of the two security modes:
  - **Standard Mode**: `REQUIRE_VERIFICATION_CODE=false` (shows codes in notifications)
  - **Enhanced Security Mode**: `REQUIRE_VERIFICATION_CODE=true` (requires manual code entry)

## Test Environment Setup

### Step 1: Configure Security Mode
1. Open `.env` file
2. Set `REQUIRE_VERIFICATION_CODE=false` (we'll test Standard Mode first)
3. Restart the application

### Step 2: Browser Setup
- **Chrome**: Will be our "authenticated device"
- **Firefox**: Will be our "requesting device"

## Test Scenarios

---

## Scenario 1: Standard Mode - Self-Approval Workflow

### Phase 1: Setup Authenticated Session (Chrome)
1. **Open Chrome** → Navigate to your app (e.g., `http://localhost:8000`)
2. **Login normally** with existing credentials
3. **Verify full authentication**: 
   - Should see main feed/dashboard
   - Check that notification bell appears in header (purple bell icon)
   - Bell should show no badge initially

### Phase 2: Create Authentication Request (Firefox)
4. **Open Firefox** → Navigate to same app URL
5. **Access login page**: Should see username input
6. **Enter the same username** as logged in Chrome user
7. **Submit login form**
8. **Verify redirect**: Should go to `/auth/pending` page
9. **Note the verification code** displayed on the pending page
10. **Keep Firefox on this page** for now

### Phase 3: Verify Notification Appears (Chrome)
11. **Switch back to Chrome**
12. **Check notification bell**:
    - Should show red badge with "1"
    - Badge should be pulsing/animated
13. **Click the notification bell**
14. **Verify dropdown opens**:
    - Should show "Authentication Requests" header
    - Should show "1 pending"
    - Should display the login request with device info
    - Should show verification code prominently in blue box
    - Should show "Enter the code shown above to confirm" field

### Phase 4: Test Notification Functionality (Chrome)
15. **Test copy button**: Click "Copy Code" next to verification code
16. **Verify code copied**: Paste somewhere to confirm
17. **Test refresh button**: Click refresh icon in notification header
18. **Verify refresh works**: Content should reload (show loading briefly)
19. **Test dismiss**: Click X button on notification
20. **Verify dismiss**: Notification should disappear, badge should show 0

### Phase 5: Re-create and Approve (Chrome)
21. **Re-create notification** by repeating steps 4-7 in Firefox
22. **In Chrome notification**: Enter the verification code in the text field
23. **Verify button enables**: "Enter Code to Approve" button should become enabled
24. **Click approve button**
25. **Verify success**:
    - Should show green success message
    - Notification should disappear
    - Badge should show 0

### Phase 6: Verify Login Success (Firefox)
26. **Switch to Firefox**
27. **Verify automatic redirect**: Should automatically redirect to main app
28. **Verify full authentication**: Should see main feed/dashboard
29. **Verify session**: Check that user is fully logged in

---

## Scenario 2: Enhanced Security Mode - Peer Approval

### Phase 1: Switch to Enhanced Security Mode
1. **Stop the application**
2. **Edit .env**: Set `REQUIRE_VERIFICATION_CODE=true`
3. **Restart application**
4. **Clear both browser sessions** (logout or clear cookies)

### Phase 2: Setup Two Different Users
5. **Chrome**: Login as User A (e.g., admin or first user)
6. **Firefox**: Start login process as User B (different user)
7. **Follow steps 4-10 from Scenario 1** but with User B

### Phase 3: Verify Enhanced Security Notification (Chrome)
8. **In Chrome** (logged in as User A):
9. **Check notification bell**: Should show badge with "1"
10. **Click notification bell**
11. **Verify enhanced security mode**:
    - Should NOT show verification code in notification
    - Should show "Enter the verification code shown on the requesting device"
    - Text field should be empty
    - Button should say "Verify & Approve Request"

### Phase 4: Test Enhanced Security Approval
12. **In Firefox**: Note the verification code on pending page
13. **In Chrome**: Enter the code from Firefox into the notification text field
14. **Verify button behavior**: Should enable when code is entered
15. **Click "Verify & Approve Request"**
16. **Verify approval**: Should show success message and clear notification

### Phase 5: Verify Cross-User Authentication
17. **Switch to Firefox**
18. **Verify User B login**: Should be logged in successfully
19. **Verify correct user**: Should show User B's name/identity

---

## Scenario 3: Error Handling and Edge Cases

### Phase 1: Invalid Code Testing
1. **Create new auth request** (Firefox)
2. **In Chrome notification**: Enter incorrect verification code
3. **Click approve**: Should show red error message
4. **Verify error handling**: Error should be clear and actionable

### Phase 2: Expired Request Testing
5. **Wait for request to expire** (or manually expire in database)
6. **Try to approve expired request**
7. **Verify expiry handling**: Should show appropriate error

### Phase 3: Multiple Notifications
8. **Create multiple auth requests** from different devices/browsers
9. **Verify multiple notifications**: Badge should show correct count
10. **Test individual approval**: Each notification should work independently

### Phase 4: Mobile Responsiveness
11. **Resize Chrome window** to mobile size (< 640px)
12. **Click notification bell**
13. **Verify mobile modal**: Should open full-screen modal instead of dropdown
14. **Test mobile functionality**: All features should work in modal
15. **Test close**: Modal should close properly

---

## Scenario 4: Performance and Real-time Updates

### Phase 1: Auto-refresh Testing
1. **Open Chrome with notifications**
2. **Create auth request in Firefox**
3. **Wait 10 seconds** (auto-refresh interval)
4. **Verify auto-update**: New notification should appear automatically

### Phase 2: Multiple Browser Windows
5. **Open multiple Chrome windows** with same user
6. **Create auth request**
7. **Verify all windows get notifications**: All should show badge updates

### Phase 3: Load Testing
8. **Create several auth requests quickly**
9. **Verify performance**: Notifications should load quickly
10. **Test approval speed**: Approvals should be near-instant

---

## Expected Results Summary

### Standard Mode (`REQUIRE_VERIFICATION_CODE=false`)
- ✅ Verification codes visible in notifications
- ✅ "Enter the code shown above to confirm" text
- ✅ Auto-approval workflow for same-user authentication
- ✅ Copy code functionality works

### Enhanced Security Mode (`REQUIRE_VERIFICATION_CODE=true`)
- ✅ No verification codes shown in notifications
- ✅ "Enter the verification code shown on the requesting device" text
- ✅ Manual code entry required
- ✅ Cross-user approval workflow

### General Functionality
- ✅ Real-time notifications with 10-second auto-refresh
- ✅ Mobile-responsive (dropdown → modal)
- ✅ Badge count accuracy
- ✅ Proper error handling
- ✅ Performance within 2 seconds
- ✅ Notification dismissal works
- ✅ Manual refresh works

## Troubleshooting Common Issues

### Notifications Not Appearing
- Check browser console for errors
- Verify HTMX is loading correctly
- Check server logs for API errors
- Ensure user has full authentication

### Approval Not Working
- Verify verification code matches exactly
- Check that auth request hasn't expired
- Ensure user hasn't already approved
- Check server logs for validation errors

### Mobile Issues
- Test in actual mobile browser or device
- Verify touch events work correctly
- Check that modal z-index is sufficient

### Performance Issues
- Check network tab for slow requests
- Verify database queries are optimized
- Monitor server resources during testing

## Test Data Cleanup

After testing:
1. **Clear test authentication requests** from database
2. **Clear notifications** from database
3. **Reset environment variables** as needed
4. **Clear browser sessions** if desired

## Automation Opportunities

This manual testing process could be automated using:
- Selenium WebDriver for browser automation
- Multiple browser instances
- Database fixtures for test data
- API testing for backend verification

---

**Testing Completed By**: ________________  
**Date**: ________________  
**Environment**: ________________  
**Issues Found**: ________________