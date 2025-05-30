# Multi-Device Authentication System

## Overview

This system allows users to log in from multiple devices with a secure approval workflow. When users attempt to log in with an existing username, they enter a "half-authenticated" state that requires approval from admins, their own existing sessions, or peer users.

## Features

### 🔐 **Authentication States**
- **Full Authentication**: Complete access to all features
- **Half Authentication**: Limited access, pending approval

### 🛡️ **Approval Methods**
1. **Admin Approval**: Instant approval by administrators
2. **Self Approval**: Users can approve their own requests from trusted devices
3. **Peer Approval**: Any 2 community members can approve together

### 📊 **Security Features**
- Rate limiting (3 requests per hour per user/IP)
- Session security validation
- IP change detection
- Comprehensive audit logging
- Device fingerprinting

## User Experience

### New User Registration
1. Use invite link
2. Enter unique display name
3. Get full authentication immediately

### Existing User Login
1. Use invite link with existing username
2. Enter half-authenticated state
3. Wait for approval (or approve from another device)
4. Get upgraded to full authentication

### Half-Authenticated Users Can:
- ✅ View prayers and community content
- ✅ See their authentication status
- ✅ Help approve other requests (if they have full auth elsewhere)
- ❌ Submit new prayers
- ❌ Mark prayers as prayed
- ❌ Create invite links

## Administrative Interface

### Admin Panel Features
- View all pending authentication requests
- One-click approve/reject for individual requests
- Bulk approve all pending requests
- View comprehensive audit logs
- Monitor security events

### Audit Logging
All authentication actions are logged including:
- Request creation
- Approval votes
- Final approvals/rejections
- Request expirations
- Security events (rate limits, IP changes)

## API Endpoints

### Authentication Routes
- `POST /auth/request` - Create authentication request
- `GET /auth/status` - View authentication status
- `GET /auth/pending` - View pending requests for approval
- `POST /auth/approve/{request_id}` - Approve a request
- `POST /auth/reject/{request_id}` - Reject a request (admin only)
- `GET /auth/my-requests` - View own authentication requests

### Admin Routes
- `GET /admin` - Admin panel with auth requests
- `GET /admin/auth-audit` - View audit log
- `POST /admin/bulk-approve` - Bulk approve all requests

## Database Schema

### New Tables
- **AuthenticationRequest**: Tracks login requests
- **AuthApproval**: Individual approval votes
- **AuthAuditLog**: Complete audit trail
- **SecurityLog**: Security events and monitoring

### Modified Tables
- **Session**: Added device info, IP tracking, auth status

## Security Considerations

### Rate Limiting
- 3 authentication requests per hour per user
- 3 authentication requests per hour per IP address
- Automatic security logging for violations

### Session Security
- Session hijacking detection via IP monitoring
- Device fingerprinting for suspicious activity detection
- Automatic cleanup of expired requests (7 days)

### Audit Trail
- Every action is logged with timestamps
- Actor identification (admin/self/peer/system)
- IP addresses and user agents tracked
- Details and context for each action

## Configuration

### Environment Variables
```python
SESSION_DAYS = 14                    # Session duration
TOKEN_EXP_H = 12                     # Invite link expiration
MAX_AUTH_REQUESTS_PER_HOUR = 3       # Rate limit
MAX_FAILED_ATTEMPTS = 5              # Future: failed login blocking
BLOCK_DURATION_MINUTES = 15          # Future: block duration
```

## Implementation Details

### Core Functions
- `create_auth_request()` - Creates new authentication request
- `approve_auth_request()` - Processes approval with logic
- `check_rate_limit()` - Validates request frequency
- `validate_session_security()` - Session security checks
- `log_auth_action()` - Audit logging
- `log_security_event()` - Security monitoring

### Database Migration
The system includes automatic database migration for existing installations:
- Adds new columns to existing session table
- Creates new tables for auth requests and logging
- Preserves existing data and sessions

## Testing

### Manual Testing Scenarios
1. **New User Registration**: Use invite link with new username
2. **Existing User Multi-Device**: Use invite link with existing username
3. **Admin Approval**: Test admin instant approval
4. **Self Approval**: Approve own request from another device
5. **Peer Approval**: Get 2 community members to approve
6. **Rate Limiting**: Attempt multiple requests quickly
7. **Session Security**: Change IP address during session

### Automated Testing
```python
# Test helper functions
from app import create_session, create_auth_request, approve_auth_request

# Test session creation
sid = create_session('user_id', is_fully_authenticated=False)

# Test auth request
req_id = create_auth_request('user_id', 'Chrome', '127.0.0.1')

# Test approval
result = approve_auth_request(req_id, 'admin')
```

## Monitoring and Maintenance

### Regular Maintenance
- Review audit logs for suspicious activity
- Monitor rate limiting effectiveness
- Clean up old authentication requests
- Review security logs for patterns

### Key Metrics to Monitor
- Authentication request volume
- Approval success rates
- Rate limiting triggers
- Session security violations
- Average approval times

## Future Enhancements

### Planned Features
- Real-time notifications for approval requests
- Mobile app authentication support
- Advanced device management
- SSO integration
- Emergency admin override codes
- Trusted device designation
- Geographic anomaly detection

### Security Enhancements
- CAPTCHA for repeated requests
- Email verification for new devices
- SMS/2FA integration
- Advanced bot detection
- Machine learning for anomaly detection

## Troubleshooting

### Common Issues

**"Too many requests" error**
- Wait 1 hour before making new requests
- Check if multiple requests from same IP

**Authentication never approved**
- Check if 2 peers have voted
- Verify admin approval process
- Check request expiration (7 days)

**Session security warnings**
- Normal for mobile users (IP changes)
- Could indicate session hijacking
- Review audit logs for patterns

### Debug Information
- All actions logged in `AuthAuditLog` table
- Security events in `SecurityLog` table
- Session details in `Session` table with device info
- Check console output for migration messages

## Support

For issues or questions:
1. Check audit logs in admin panel
2. Review security logs for violations
3. Verify database migration completed
4. Test with clean browser/device

## License and Legal

This authentication system:
- Logs user IP addresses and device information
- Stores approval history and user interactions
- Implements rate limiting and security monitoring
- Ensure compliance with applicable privacy laws
- Consider data retention policies for audit logs