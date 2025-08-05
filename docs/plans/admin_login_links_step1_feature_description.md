# Feature: Admin User-Specific Login Links

## Problem
Admins need a way to create direct login links for users who have lost access to all their devices or need emergency access. Currently, users must go through the multi-device approval process even when an admin wants to grant immediate access for support purposes.

## User Stories
- As an **admin**, I want to create instant login links for specific users so that I can help users who are locked out without requiring them to wait for approval
- As an **admin**, I want to create login links that redirect to specific pages so that I can send users directly to relevant content or prayers
- As a **user**, I want to click an admin-provided link and be instantly logged in so that I can quickly access my account when I've lost my devices
- As an **admin**, I want login links to expire automatically so that I don't create long-term security risks
- As a **security-conscious admin**, I want full audit logs of login link creation and usage so that I can track emergency access grants

## Core Requirements
1. **Admin-Only Creation**: Only authenticated admins can create these login tokens
2. **User-Specific**: Each link is tied to a specific existing user account  
3. **One-Click Access**: No username entry or approval process required
4. **Time-Limited**: Links expire after 12 hours to limit security exposure
5. **Unlimited Uses**: Safe for link preview tools and multiple clicks
6. **Optional Redirection**: Can redirect to specific pages after login (e.g., `/prayer/123`)
7. **Security Logging**: Complete audit trail of creation and usage

## User Flow
1. Admin visits admin panel and selects "Create Login Link"
2. Admin types in username and optionally sets redirect URL
3. System generates secure link and displays it to admin
4. Admin copies link and sends to user via secure channel
5. User clicks link and is immediately logged in with full authentication
6. User is redirected to specified page or main feed
7. System logs all creation and usage events for security audit

## Success Criteria
- Admin can successfully create login links for any existing user
- Links provide instant authentication without approval process
- Optional redirect functionality works correctly  
- Links expire after 12 hours as specified
- All creation and usage events are logged for security audit
- Links work reliably across different browsers and devices
- No security vulnerabilities in token generation or validation

## Constraints
- **Security**: Only relative URLs allowed for redirection (no external sites)
- **Access Control**: Feature requires admin authentication
- **Expiration**: Fixed 12-hour expiration cannot be extended
- **Compatibility**: Must work with existing session management system