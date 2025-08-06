# Feature: Email Association for Account Recovery

## Problem
Users who lose access to their devices or have persistent cookie/session issues have no way to recover their accounts or prove their identity. The current invite-only system works for initial access but provides no recovery mechanism for established community members. Users must create new accounts and lose their prayer history, connections, and community standing when device access is lost.

## User Stories
- As an established user, I want to associate an email with my account so that I can recover access if I lose my device or sessions
- As a user with persistent browser issues, I want an alternative way to prove my identity without waiting for community approval every time
- As a mobile user who switches devices, I want a secure way to transfer my account to a new phone without losing my prayer history
- As a privacy-conscious user, I want my email to be stored securely and used only for account recovery, not marketing or notifications
- As a community member, I want account recovery to be secure and prevent impersonation while still being accessible to legitimate users

## Core Requirements
1. **Optional Email Association**: Users can optionally add an email to their existing account for recovery purposes
2. **Secure Email Storage**: Email addresses are encrypted at rest and access is logged for security
3. **Email Verification**: Email addresses must be verified before they can be used for account recovery
4. **Recovery Email Flow**: Users can request a secure recovery link sent to their verified email
5. **Limited Recovery Window**: Recovery links expire quickly and can only be used once
6. **Recovery Logging**: All account recovery attempts are logged for security monitoring
7. **Email Management**: Users can update or remove their associated email address
8. **No Email Required**: Email association remains completely optional - existing auth flows unchanged

## User Flow

### Email Association Flow
1. **Opt-in**: Logged-in user chooses to add email recovery option in settings
2. **Email Entry**: User enters email address → system sends verification email
3. **Verification**: User clicks link in email → email is verified and associated with account
4. **Confirmation**: User sees confirmation that email recovery is now available

### Account Recovery Flow
1. **Access Lost**: User loses access (cleared cookies, new device, etc.)
2. **Recovery Option**: Login page shows "Recover with Email" option for users with lost sessions
3. **Email Entry**: User enters their email address → system sends recovery link (if email is verified for any account)
4. **Email Recovery**: User clicks recovery link → immediately logged in to associated account
5. **Security Notification**: System logs recovery event and optionally notifies user of successful recovery

### Email Management Flow
1. **Settings Access**: User accesses account settings
2. **Email Management**: User can view current email, change email (requires verification), or remove email
3. **Verification Updates**: Email changes require verification of new email before old email is replaced

## Success Criteria
- Users can successfully associate and verify email addresses with their accounts
- Email recovery links work reliably and securely restore account access
- Recovery process is faster than waiting for community approval
- Email data is properly encrypted and access is audited
- System prevents email-based account takeover attempts
- Users can manage their email settings independently
- No impact on users who choose not to associate an email

## Constraints
- Email addresses must be encrypted at rest using strong encryption
- Recovery links must be single-use and short-lived (1 hour max)
- System must prevent enumeration attacks (don't reveal if email exists)
- Must comply with data protection requirements for PII storage
- Email sending requires reliable SMTP configuration
- Should integrate with existing session management without conflicts
- Must prevent recovery abuse (rate limiting, monitoring)
- Should be clearly marked as optional and for recovery only