# Multi-Device Authentication Implementation Plan

## Overview
Implement a multi-device authentication system where users can log in from multiple devices with a "half-authenticated" state that requires approval from admins, existing sessions, or peer users.

## Requirements Summary
- Users can log in multiple times from different devices
- New logins for existing usernames enter "half-authenticated" state
- Half-authenticated users have limited functionality and see their pending status
- Approval sources: admin, another session from same user, or 2 other users
- Pending authentications expire after 7 days
- No real-time notifications initially

## Current System Analysis
- Session-based auth with 14-day cookie expiry
- Single session per user in `Session` table
- Simple admin role (`id="admin"`)
- Invite token registration system

---

## Stage 1: Database Schema Extensions

### New Models to Add:
```python
class AuthenticationRequest(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    user_id: str  # User requesting authentication
    device_info: str | None = None  # Browser/device identifier
    ip_address: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime  # 7 days from creation
    status: str = "pending"  # "pending", "approved", "rejected", "expired"
    approved_by_user_id: str | None = None
    approved_at: datetime | None = None

class AuthApproval(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex, primary_key=True)
    auth_request_id: str
    approver_user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### Modifications to Existing Models:
```python
class Session(SQLModel, table=True):
    # Add new fields
    auth_request_id: str | None = None  # Link to authentication request
    device_info: str | None = None
    ip_address: str | None = None
    is_fully_authenticated: bool = Field(default=True)  # For existing sessions
```

---

## Stage 2: Authentication Request Flow

### New Routes:
- `POST /auth/request` - Create authentication request for existing username
- `GET /auth/pending` - View pending authentication requests (for approvers)
- `POST /auth/approve/{request_id}` - Approve an authentication request
- `POST /auth/reject/{request_id}` - Reject an authentication request
- `GET /auth/status` - Check current authentication status

### Modified Routes:
- Update `/claim/{token}` to handle both new users and existing username requests
- Modify `current_user()` dependency to handle half-authenticated state
- Update session creation logic to support authentication requests

### Key Functions:
```python
def create_auth_request(user_id: str, device_info: str, ip_address: str) -> str
def approve_auth_request(request_id: str, approver_id: str) -> bool
def get_pending_requests_for_user(user_id: str) -> List[AuthenticationRequest]
def cleanup_expired_requests() -> None
```

---

## Stage 3: Half-Authenticated State Management

### Session State Handling:
- Modify `current_user()` to return user with authentication status
- Create `require_full_auth()` dependency for routes needing full access
- Add middleware to redirect half-authenticated users to appropriate pages

### Limited Functionality Design:
- Half-authenticated users can:
  - View their authentication status
  - See pending approval requests
  - Access basic profile information
  - View limited app content (to be defined)
- Half-authenticated users cannot:
  - Submit prayers
  - Mark prayers as prayed
  - Access admin functions
  - Create invite tokens

### New Templates:
- `auth_pending.html` - Show pending authentication status
- `auth_requests.html` - List pending requests for approval
- Update existing templates to handle half-auth state

---

## Stage 4: Approval System Implementation

### Admin Approval:
- Admins can approve any authentication request
- Admin panel shows pending authentication requests
- One-click approval/rejection interface

### Self-Approval (Same User):
- Users with existing full sessions can approve new device requests
- Show pending requests in user's account/menu
- Secure verification that approver owns the account

### Peer Approval (2 Users):
- Any 2 users can collectively approve a request
- Track individual approvals in `AuthApproval` table
- Auto-approve when 2nd approval is received
- Prevent duplicate approvals from same user

### Approval Logic:
```python
def process_approval(request_id: str, approver_id: str, approver_role: str) -> bool:
    # Check if approver is admin -> instant approval
    # Check if approver is same user with full session -> instant approval  
    # Check if approver is regular user -> add to approval count
    # If 2 peer approvals -> auto-approve
```

---

## Stage 5: Security & UX Enhancements

### Security Measures:
- Rate limiting on authentication requests (max 3 per hour per IP)
- Device fingerprinting for better security
- Automatic cleanup of expired requests
- Session invalidation options
- Audit logging for all approval actions

### User Experience:
- Clear status indicators for half-authenticated state
- Email notifications for approval requests (future enhancement)
- Mobile-friendly approval interface
- Bulk approval options for admins
- Grace period for trusted devices

### Monitoring & Analytics:
- Track authentication request patterns
- Monitor approval response times
- Alert on suspicious authentication attempts
- Generate reports on multi-device usage

### Additional Features:
- Device naming/management
- Trusted device designation
- Emergency admin override
- Batch operations for cleaning up old sessions

---

## Implementation Notes

### Testing Strategy:
- Unit tests for new authentication logic
- Integration tests for approval workflows
- Manual testing with multiple browsers/devices
- Security testing for edge cases

### Migration Plan:
- Existing sessions remain fully authenticated
- Gradual rollout with feature flags
- Backup plan to disable multi-device auth if needed

### Performance Considerations:
- Index on `user_id` and `expires_at` for auth requests
- Optimize approval queries
- Consider caching for frequent status checks

### Future Enhancements:
- Real-time notifications via WebSocket
- Mobile app authentication
- SSO integration
- Advanced device management