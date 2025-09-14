# Membership Application - Development Plan

## Overview
Implement membership application system using existing database models and admin infrastructure. Leverage AuthenticationRequest 
model and invite token system.

## Development Stages

### Stage 1: Database Model Assessment (<1 hour)
**Goal**: Confirm existing AuthenticationRequest model can store applications
**Dependencies**: None
**Changes**:
- Review AuthenticationRequest model fields
- Confirm username, contact_info, and request_reason fields sufficient
- Document field mapping strategy
**Testing**: Database schema validation
**Risks**: Low - existing model analysis only

### Stage 2: Application Form UI (<2 hours)
**Goal**: Create application form on public homepage
**Dependencies**: Stage 1 complete
**Changes**:
- Add application section to homepage template
- Create form with username, essay, contact fields
- Add client-side validation and character limits
- Style form to match existing UI patterns
**Testing**: Form validation, responsive design
**Risks**: Medium - UI integration complexity

### Stage 3: Application Submission Backend (<2 hours)
**Goal**: Process form submissions and store applications
**Dependencies**: Stage 2 complete
**Changes**:
- Add POST /apply route to handle form submissions
- Create ApplicationService for business logic
- Implement rate limiting (reuse existing patterns)
- Store applications using AuthenticationRequest model
**Testing**: Form submission, rate limiting, data persistence
**Risks**: Medium - rate limiting integration

### Stage 4: Admin Review Interface (<2 hours)
**Goal**: Display applications in admin panel
**Dependencies**: Stage 3 complete
**Changes**:
- Add applications section to admin dashboard
- Display pending applications with all details
- Add approve/reject buttons for each application
- Show application count in admin navigation
**Testing**: Admin panel display, button interactions
**Risks**: Low - leveraging existing admin UI patterns

### Stage 5: Application Processing (<1.5 hours)
**Goal**: Handle approve/reject decisions
**Dependencies**: Stage 4 complete
**Changes**:
- Add POST /admin/applications/{id}/approve route
- Add POST /admin/applications/{id}/reject route
- Generate invite tokens for approved applications
- Update application status in database
**Testing**: Approval workflow, invite token generation
**Risks**: Low - using existing invite token system

### Stage 6: Integration Testing (<1 hour)
**Goal**: Verify complete application workflow
**Dependencies**: All stages complete
**Changes**:
- End-to-end testing of application flow
- Verify admin workflow completeness
- Test edge cases and error handling
**Testing**: Complete workflow, error scenarios
**Risks**: Low - integration verification only

## Database Strategy
**Model**: Reuse AuthenticationRequest with type field
- `username` → existing username field
- `essay` → request_reason field
- `contact` → contact_info field
- `type` → "membership_application" to distinguish from device auth
- `status` → existing status field (pending/approved/rejected)

**Benefits**:
- No database migration required
- Leverages existing admin approval patterns
- Reuses proven security and rate limiting
- Maintains consistent data model

## Function Signatures

### ApplicationService
```python
class ApplicationService:
    def create_application(username: str, essay: str, contact: str = None) -> AuthenticationRequest
    def get_pending_applications() -> List[AuthenticationRequest]
    def approve_application(app_id: int, admin_user: User) -> InviteToken
    def reject_application(app_id: int, admin_user: User) -> bool
```

### Routes
```python
@app.post("/apply")
def submit_application(username: str, essay: str, contact: str = None)

@app.post("/admin/applications/{app_id}/approve")
def approve_application(app_id: int)

@app.post("/admin/applications/{app_id}/reject")
def reject_application(app_id: int)
```

## Testing Strategy

### Unit Tests
- ApplicationService methods
- Form validation logic
- Rate limiting enforcement
- Database operations

### Integration Tests
- Complete application submission workflow
- Admin approval/rejection process
- Invite token generation for approved applications
- Rate limiting across form submissions

### Manual Tests
- Form UX and validation
- Admin panel integration
- Application display and processing
- Error message clarity

## Risk Assessment

### High Risk
- **Form spam**: Rate limiting and validation critical
  - *Mitigation*: IP-based rate limiting, required essay field

### Medium Risk
- **Admin UI complexity**: Integration with existing admin panel
  - *Mitigation*: Follow established admin UI patterns

### Low Risk
- **Database model reuse**: AuthenticationRequest model compatibility
  - *Mitigation*: Model analysis completed in Stage 1

## Dependencies
- Existing AuthenticationRequest model and admin infrastructure
- Current rate limiting system for form protection
- Invite token generation system for approved applications
- Public prayers feature for form placement context

## Completion Criteria
- Application form accessible on public homepage
- Form submissions stored and rate limited
- Admin panel displays pending applications
- Approve/reject functionality generates/manages invite tokens
- Complete workflow tested end-to-end
- No database migrations required