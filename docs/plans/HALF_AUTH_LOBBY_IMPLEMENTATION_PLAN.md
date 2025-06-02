# Half-Authentication Lobby Implementation Plan

## Overview
This plan implements a feature allowing users to half-authenticate and join a "lobby" in the authentication requests section without requiring an invite link. This feature will be controlled by an environment toggle and allows admins to review and approve users who want to join the community without a formal invitation.

## User Story
**As an admin**, I want to have a feature (with a toggle in .env) to allow users to half-authenticate and be added to a "lobby" in the authentication requests section without having an invite link, so that potential community members can request access without needing a direct invitation.

## Current System Analysis
- Authentication currently requires either an invite token or existing user credentials
- Multi-device auth creates `AuthenticationRequest` entries for existing users
- Community approval system exists with peer/admin approval workflows
- Environment toggles already implemented for multi-device auth features

## Implementation Plan

### Phase 1: Environment Configuration
**Files to modify:** `.env`, `app.py`

1. **Add new environment variable**
   ```
   ALLOW_LOBBY_REGISTRATION=false
   ```

2. **Load configuration in app.py**
   ```python
   ALLOW_LOBBY_REGISTRATION = os.getenv('ALLOW_LOBBY_REGISTRATION', 'false').lower() == 'true'
   ```

### Phase 2: Database Schema Updates
**Files to modify:** `models.py`

1. **Extend AuthenticationRequest model**
   - Add `is_lobby_request` boolean field (default False)
   - Add `registration_reason` text field for user-provided reason
   - Add `contact_info` field for email/contact information (optional)

2. **Database migration**
   - Create migration script to add new fields to existing requests
   - Update any related query logic to handle new fields

### Phase 3: New Registration Route
**Files to modify:** `app.py`

1. **Create `/register-lobby` route**
   - Accept POST requests with username, reason, and optional contact info
   - Validate that lobby registration is enabled
   - Check if username already exists (reject if user exists)
   - Create new User record with special lobby status
   - Create AuthenticationRequest with `is_lobby_request=True`
   - Rate limit to prevent spam (max 1 request per IP per hour)

2. **Create lobby registration page route**
   - GET `/register-lobby` to serve registration form
   - Only accessible when `ALLOW_LOBBY_REGISTRATION=true`

### Phase 4: User Interface Updates
**Files to create/modify:** Templates

1. **Create `lobby_registration.html` template**
   - Clean, simple form for username, reason, and optional contact
   - Clear explanation of lobby process and approval requirements
   - Link to community guidelines or expectations
   - Responsive design matching existing auth templates

2. **Update `auth_requests.html` template**
   - Add section for lobby requests with distinct visual styling
   - Show lobby requests separately from multi-device auth requests
   - Display registration reason and contact info for admins
   - Add approve/reject actions specific to lobby requests

3. **Update navigation**
   - Add lobby registration link to appropriate menu locations
   - Only show when feature is enabled
   - Consider placement on login page or main menu

### Phase 5: Backend Logic Updates
**Files to modify:** `app.py`

1. **Extend approval system**
   - Modify `approve_auth_request()` to handle lobby requests
   - When lobby request approved, upgrade user to full community member
   - Set appropriate `invited_by_user_id` (admin or approver)
   - Log lobby approval events in audit trail

2. **Update auth request filtering**
   - Modify auth request queries to distinguish lobby vs multi-device requests
   - Add filters for admins to view lobby requests separately
   - Update statistics and counts to include lobby metrics

3. **Rate limiting and security**
   - Implement IP-based rate limiting for lobby registration
   - Add security logging for lobby registration attempts
   - Validate and sanitize input data (username, reason, contact)

### Phase 6: Admin Management Features
**Files to modify:** `app.py`, templates

1. **Enhanced admin controls**
   - Admin toggle to enable/disable lobby registration
   - Bulk approval/rejection for lobby requests
   - Admin notes field for lobby request decisions
   - Lobby request analytics and reporting

2. **Audit trail enhancements**
   - Log all lobby registration attempts and decisions
   - Track conversion rates from lobby to full members
   - Security monitoring for abuse prevention

### Phase 7: User Experience Enhancements
**Files to modify:** Templates, `app.py`

1. **Status tracking for lobby users**
   - Dedicated page showing lobby request status
   - Email notifications (if contact provided) for status changes
   - Clear messaging about approval process and timeline

2. **Community integration preparation**
   - Limited access views for approved lobby users
   - Onboarding flow after lobby approval
   - Integration with existing invite tree system

## Technical Specifications

### Database Schema Changes
```sql
-- Add columns to authentication_request table
ALTER TABLE authentication_request ADD COLUMN is_lobby_request BOOLEAN DEFAULT FALSE;
ALTER TABLE authentication_request ADD COLUMN registration_reason TEXT;
ALTER TABLE authentication_request ADD COLUMN contact_info TEXT;

-- Add index for lobby request queries
CREATE INDEX idx_auth_request_lobby ON authentication_request(is_lobby_request, created_at);
```

### API Endpoints
- `GET /register-lobby` - Serve lobby registration form
- `POST /register-lobby` - Submit lobby registration request
- `GET /auth/lobby-requests` - Admin view of lobby requests
- `POST /auth/approve-lobby/{request_id}` - Approve lobby request
- `POST /auth/reject-lobby/{request_id}` - Reject lobby request

### Rate Limiting
- Lobby registration: 1 request per IP per hour
- Failed attempts: Track and temporarily block abusive IPs
- Username validation: Prevent duplicate requests

### Security Considerations
- Input validation and sanitization
- CSRF protection on all forms
- Rate limiting to prevent spam
- Audit logging for all lobby activities
- IP tracking and abuse prevention

## Testing Strategy

### Unit Tests
- Lobby registration validation logic
- Rate limiting functionality
- Database model updates
- Approval workflow changes

### Integration Tests
- End-to-end lobby registration flow
- Admin approval process
- Security and rate limiting
- Database migration testing

### Manual Testing
- UI/UX testing for registration flow
- Admin workflow testing
- Edge case handling
- Performance testing with multiple requests

## Deployment Steps

1. **Environment setup**
   - Add `ALLOW_LOBBY_REGISTRATION=false` to production .env
   - Test configuration loading

2. **Database migration**
   - Apply schema changes during maintenance window
   - Verify migration success and data integrity

3. **Feature rollout**
   - Deploy with feature disabled initially
   - Enable feature via environment toggle
   - Monitor for issues and usage patterns

4. **Monitoring and maintenance**
   - Track lobby registration metrics
   - Monitor for abuse and spam
   - Gather admin feedback for improvements

## Success Metrics
- Number of lobby registrations vs approvals
- Admin satisfaction with lobby management tools
- Community growth from lobby feature
- Security incident rate related to lobby feature
- User experience feedback from lobby registrants

## Risk Mitigation
- Feature toggle allows immediate disable if issues arise
- Rate limiting prevents spam and abuse
- Comprehensive audit logging for security monitoring
- Gradual rollout with monitoring at each step
- Clear admin controls for managing unwanted requests

## Future Enhancements
- Automated spam detection using AI/ML
- Integration with external identity providers
- Community voting for lobby approvals
- Advanced analytics and reporting dashboard
- Mobile app support for lobby registration