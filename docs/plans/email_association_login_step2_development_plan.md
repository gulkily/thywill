# Step 2: Email Association Login - Development Plan

*Building on existing `/claim/{token}` infrastructure*

## Stage 1: Separate Email Database Setup (<2 hours)
**Goal**: Create dedicated email database with user associations and encryption support

**Dependencies**: None

**Database Changes**:
- Create new `UserEmail` model in separate database file (`email.db`)
- Fields: `user_id: str` (FK to User.display_name), `email_encrypted: str`, `email_verified: bool`, `verification_token: str | None`, `added_at: datetime`
- No changes to main User model in `thywill.db` - keeps email data completely isolated
- Separate SQLModel engine configuration for email database alongside existing `thywill.db`

**High-level Changes**:
- Create `models_email.py` with UserEmail model
- Setup separate database engine (`email_engine`) similar to existing `engine` setup
- Add email encryption/decryption utility functions
- Database initialization script for `email.db` (alongside existing `thywill.db`)

**Testing**: 
- Verify separate `email.db` creation works
- Test email encryption/decryption functions
- Confirm main `thywill.db` remains untouched
- Test cross-database user lookups between `thywill.db` and `email.db`

**Risks**: 
- Separate database backup/restore procedures needed
- Cross-database referential integrity requires application logic

---

## Stage 2: Email Management Service (<2 hours)  
**Goal**: Create service for secure email operations and verification token generation

**Dependencies**: Stage 1 complete

**High-level Changes**:
- Create `EmailManagementService` class
- Functions: `encrypt_email()`, `decrypt_email()`, `generate_verification_token()`, `validate_email_format()`
- Integration with existing environment variables pattern
- Reuse existing token generation patterns from InviteToken

**Testing**:
- Unit tests for encryption/decryption
- Email format validation tests
- Token generation and validation tests

**Risks**:
- Encryption key rotation strategy needed
- Token collision possibility (use UUID patterns)

---

## Stage 3: Email Verification Flow (<2 hours)
**Goal**: Implement email verification using existing `/claim/{token}` infrastructure  

**Dependencies**: Stages 1-2 complete

**High-level Changes**:
- Extend InviteToken model with new token_type: `"email_verification"`
- Create verification email template (reuse existing email infrastructure)
- Add verification route: `GET /verify-email/{token}` (redirects to `/claim/{token}`)
- Email service integration using existing SMTP configuration

**Function Signatures**:
```python
def send_verification_email(user: User, email: str) -> str  # Returns verification token
def verify_email_token(token: str) -> User | None  # Cross-database lookup
def mark_email_verified(user_id: str, email: str) -> bool  # Updates email.db
```

**Testing**:
- Mock email sending in tests
- Verify token validation works correctly
- Test email verification success/failure flows

**Risks**:
- SMTP configuration dependency
- Email delivery reliability

---

## Stage 4: Recovery Token System (<2 hours)
**Goal**: Create email recovery tokens using existing `user_login` token type

**Dependencies**: Stages 1-3 complete

**High-level Changes**:
- Reuse existing `token_type="user_login"` system from `/claim/{token}`
- Create recovery email template
- Add function to generate recovery tokens for verified email users
- Recovery tokens auto-login like existing user_login tokens

**Function Signatures**:  
```python  
def send_recovery_email(email: str) -> bool  # Returns success status, looks up user via email.db
def create_recovery_token(user: User) -> str  # Creates user_login token in main db
```

**Testing**:
- Test recovery email generation and sending
- Verify recovery tokens work with existing `/claim/{token}` flow
- Test email enumeration protection

**Risks**:
- Email enumeration attacks if not properly handled
- Recovery token security (short expiration, single use)

---

## Stage 5: Settings UI Integration (<2 hours)
**Goal**: Add email management to user settings page

**Dependencies**: Stages 1-4 complete

**High-level Changes**:
- Extend existing settings page template with email section
- Forms: add email, change email, remove email  
- Use existing HTMX patterns for interactive forms
- Integration with existing user authentication middleware

**Routes**:
- `POST /settings/email/add` - Add and verify email
- `POST /settings/email/change` - Change email (requires new verification)
- `POST /settings/email/remove` - Remove email association

**Testing**:
- UI tests for email management forms
- Integration tests with existing settings page
- HTMX form validation and success/error handling

**Risks**:
- Form validation edge cases
- Session management during email changes

---

## Stage 6: Login Page Recovery Option (<1 hour)
**Goal**: Add email recovery option to existing login page

**Dependencies**: Stages 1-5 complete

**High-level Changes**:
- Add "Recover with Email" form to existing login template
- Single email input field with recovery submission
- Use existing HTMX patterns and styling
- Route: `POST /auth/email-recovery`

**Function Signatures**:
```python
def handle_email_recovery(email: str, request: Request) -> Response  # Send recovery or generic message
```

**Testing**:
- UI integration with existing login page
- Form validation and submission
- Generic success message regardless of email existence

**Risks**:
- UI layout compatibility with existing login page
- Email enumeration prevention

---

## Stage 7: Security Logging Integration (<1 hour)
**Goal**: Add email recovery events to existing security logging

**Dependencies**: Stages 1-6 complete  

**High-level Changes**:
- Extend existing SecurityLog model usage
- Log events: email_added, email_verified, email_recovery_requested, email_recovery_used
- Integration with existing IP tracking and device fingerprinting

**Testing**:
- Verify security events are logged correctly
- Test log filtering and monitoring capabilities

**Risks**:
- Log storage space for email events
- PII handling in security logs

---

## Overall Architecture

**Leverages Existing Systems**:
- `/claim/{token}` infrastructure for email verification and recovery
- InviteToken model with new token types: `email_verification` and existing `user_login`
- SecurityLog system for audit trails
- HTMX frontend patterns and styling
- Environment variable configuration for SMTP
- Existing user authentication and session management

**New Components**:
- Separate email database (`email.db`) with UserEmail model
- Email encryption/decryption utilities
- EmailManagementService for cross-database operations
- Email templates for verification and recovery
- Settings page email management UI
- Login page recovery option

**Integration Points**:
- Cross-database queries linking User.display_name to UserEmail.user_id
- Settings page email management section
- Login page recovery form  
- Security logging for email-related events (main db)

**Data Flow**:
1. User adds email → encrypted storage in `email.db` → verification email sent
2. User clicks verification → `/claim/{token}` → email marked verified in `email.db`
3. User loses access → enters email → cross-database lookup → recovery email sent
4. User clicks recovery → `/claim/{token}` → automatic login via existing user_login flow

**Security Measures**:
- Email encryption at rest using AES in separate database
- Separate database file provides additional security isolation  
- Single-use, short-lived tokens (1 hour)
- Rate limiting on recovery requests
- Generic responses to prevent email enumeration
- Security event logging for audit trails (main db)
- Email verification required before recovery use
- Cross-database queries minimize data exposure