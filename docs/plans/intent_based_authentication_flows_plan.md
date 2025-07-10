# Intent-Based Authentication Flows Plan

## Overview
Redesign authentication system to prevent accidental account merging by implementing intent-based invite tokens. This addresses the core issue where two different people with the same name (e.g., "Ilya") could accidentally merge into the same account.

## Current Authentication Flows (Issues Identified)

### 1. Invite Token Claim (`/claim/{token}`)
**Current Behavior:**
- User enters display name
- System searches for existing users with equivalent usernames
- If found: **Immediately logs into existing account** (problematic)
- If not found: Creates new account

**Problem:** Two people named "Ilya" both using invite tokens would merge into same account.

### 2. Login Form (`/login`)
**Current Behavior:**
- User enters username
- System validates username exists
- Creates authentication request for multi-device approval
- Redirects to pending status page

**Status:** Works correctly for intended use case.

### 3. Multi-Device Authentication (`/auth/request`, `/auth/approve/{id}`)
**Current Behavior:**
- Creates authentication request for existing user
- Requires peer approval (default 2 approvals)
- Upgrades to full authentication when approved

**Status:** Works correctly for intended use case.

### 4. Authentication Status (`/auth/status`)
**Current Behavior:**
- Shows pending authentication status
- Displays approval progress
- Auto-upgrades to full authentication when approved

**Status:** Works correctly.

## Proposed Solution: Intent-Based Token System

### Database Schema Changes

Add `token_type` field to `InviteToken` table:
```sql
ALTER TABLE invite_tokens ADD COLUMN token_type VARCHAR(20) DEFAULT 'new_user';
```

**Token Types:**
- `new_user`: For registering new accounts (prevent username conflicts)
- `multi_device`: For logging into existing accounts (allow username matching)

### New Authentication Flows

#### 1. New User Registration Flow
**Token Type:** `new_user`
**Process:**
1. User clicks invite link → `/claim/{token}`
2. System validates token and checks `token_type = 'new_user'`
3. User enters display name
4. **NEW:** If username exists, reject with error: "Username already taken, please choose a different name"
5. If username available, create new account normally

#### 2. Multi-Device Login Flow
**Token Type:** `multi_device`
**Process:**
1. User clicks device-specific link → `/claim/{token}`
2. System validates token and checks `token_type = 'multi_device'`
3. User enters display name
4. **NEW:** If username exists, log into existing account (current behavior)
5. If username doesn't exist, show error: "Username not found, this device token is for an existing account"

### UI Changes

#### 1. Menu Page Reorganization
**Current Issues:**
- Mixed user-specific and site-wide functions
- "Authentication Requests" buried in middle
- No clear separation of concerns

**Proposed Structure:**
```
User Account Section:
- My Profile
- My Devices (moved from Auth Requests)
- Export My Data
- Log Out

Community Section:
- View Members
- Invite Tree  
- Community Activity
- Authentication Requests (help others)

Site Information:
- How It Works
- What's New (Changelog)
- Support ThyWill
- Export Community (admin/special)
```

#### 2. New "Add Device" Feature
**Location:** User Account section in menu
**Process:**
1. User clicks "Add Device" in menu
2. System generates `multi_device` token tied to current user
3. Displays QR code + link for easy device transfer
4. Token expires in 24 hours
5. Device uses token to access existing account

### Implementation Plan

#### Phase 1: Database Schema
- [ ] Add `token_type` column to `InviteToken` table
- [ ] Create migration script
- [ ] Update model definitions
- [ ] Default existing tokens to `new_user`

#### Phase 2: Backend Logic
- [ ] Modify `/claim/{token}` route to check token type
- [ ] Implement new user registration validation (reject conflicts)
- [ ] Implement multi-device login validation (require existing user)
- [ ] Add device token generation endpoints
- [ ] Update invite creation to specify token type

#### Phase 3: Frontend Updates
- [ ] Reorganize menu page structure
- [ ] Add "Add Device" button to user section
- [ ] Create device token generation page
- [ ] Update claim form messaging based on token type
- [ ] Add clearer error messages for username conflicts

#### Phase 4: Admin Features
- [ ] Admin interface to create both token types
- [ ] Token analytics and management
- [ ] Bulk token creation for onboarding

### Security Considerations

#### 1. Token Type Validation
- Validate token type on every claim attempt
- Log suspicious token usage (wrong type for flow)
- Rate limit token generation per user

#### 2. Device Token Security
- Short expiration (24 hours)
- Single use tokens
- IP/device fingerprinting for additional security
- User notification when device token used

#### 3. Username Conflict Prevention
- Strict validation: exact case-sensitive matching for new users
- Clear error messages explaining the conflict
- Suggest alternative usernames
- Prevent accidental merging completely

### Migration Strategy

#### 1. Backward Compatibility
- Default all existing tokens to `new_user` type
- Existing invite links continue working
- No breaking changes to current flows

#### 2. Gradual Rollout
- Phase 1: Add schema, deploy with feature flag
- Phase 2: Update backend logic, test thoroughly
- Phase 3: Update UI, enable new features
- Phase 4: Full deployment, monitor for issues

#### 3. Data Migration
- Update existing `InviteToken` records
- Preserve all existing functionality
- Add audit logging for token type changes

### Testing Strategy

#### 1. Unit Tests
- Token type validation logic
- Username conflict detection
- Device token generation
- Security boundary testing

#### 2. Integration Tests
- End-to-end registration flows
- Multi-device authentication
- Menu page reorganization
- Admin token management

#### 3. Security Tests
- Token type manipulation attempts
- Username conflict exploitation
- Device token security
- Rate limiting effectiveness

### User Experience Improvements

#### 1. Clear Intent Communication
- "Join as New Member" vs "Add Device"
- Different URLs for different purposes
- Contextual help text explaining each flow

#### 2. Better Error Messages
- "Username 'Ilya' already exists. Please choose: Ilya_Smith, Ilya_2024, etc."
- "This device link is for account 'John'. Enter 'John' to continue."
- Clear distinction between registration and login

#### 3. Progressive Enhancement
- QR codes for device transfers
- Browser notification for device approvals
- Real-time status updates

### Documentation Updates

#### 1. User Guide
- How to invite new members
- How to add devices
- Understanding different token types
- Troubleshooting common issues

#### 2. Admin Guide
- Token management
- Security monitoring
- Handling username conflicts
- Community moderation

#### 3. Developer Guide
- API documentation
- Token type specifications
- Security considerations
- Migration procedures

## Success Metrics

#### 1. Security Metrics
- Zero accidental account merges
- Reduced support tickets about login issues
- Improved authentication audit trail

#### 2. User Experience Metrics
- Faster device setup process
- Reduced confusion about invite links
- Better menu navigation

#### 3. Technical Metrics
- Successful token type validation
- Proper error handling
- Performance maintenance

## Timeline

- **Week 1**: Database schema changes, backend logic
- **Week 2**: Frontend updates, menu reorganization
- **Week 3**: Admin features, security testing
- **Week 4**: Documentation, deployment, monitoring

## Risk Assessment

#### 1. Low Risk
- Menu reorganization (cosmetic)
- New error messages (improved UX)
- Additional validation (defensive)

#### 2. Medium Risk
- Database schema changes (requires migration)
- Token type logic (needs thorough testing)
- User workflow changes (requires communication)

#### 3. High Risk
- Breaking existing invite links (mitigated by backward compatibility)
- User confusion during transition (mitigated by clear documentation)
- Security vulnerabilities (mitigated by security testing)

## Conclusion

This plan provides a comprehensive solution to the username conflict issue while improving overall authentication UX. The intent-based token system clearly separates new user registration from multi-device login, preventing accidental account merging while maintaining all existing functionality.

The phased approach ensures minimal disruption while the menu reorganization provides better user experience. Security considerations are addressed throughout, and the migration strategy maintains backward compatibility.