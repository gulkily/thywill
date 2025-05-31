# ThyWill - AI Assistant Project Guide

## Project Overview
**ThyWill** is a community prayer platform built with FastAPI and SQLModel. It allows users to submit prayer requests, generate proper prayers using AI (Anthropic's Claude), track community prayer activity, and moderate content through community-driven flagging.

## Core Architecture

### Technology Stack
- **Backend**: FastAPI (Python web framework)
- **Database**: SQLite with SQLModel ORM
- **AI Integration**: Anthropic Claude API for prayer generation
- **Frontend**: Jinja2 templates with HTML/CSS/JavaScript + HTMX
- **Authentication**: Cookie-based sessions with JWT tokens for invites

### Key Files
- `app.py` (1500+ lines) - Main application with all routes and business logic
- `models.py` (120+ lines) - Database models and schema including multi-device auth
- `templates/` - HTML templates for UI including authentication flows
- `requirements.txt` - Python dependencies
- `generate_token.py` - Utility for creating invite tokens
- `MULTI_DEVICE_AUTH_GUIDE.md` - Comprehensive documentation for authentication system

## Database Schema

### Core Models
1. **User**: Basic user profile (id, display_name, created_at)
2. **Prayer**: Prayer requests (id, author_id, text, generated_prayer, project_tag, flagged)
3. **PrayerMark**: Tracks when users pray for requests (user_id, prayer_id, created_at)
4. **Session**: Enhanced user sessions (id, user_id, expires_at, auth_request_id, device_info, ip_address, is_fully_authenticated)
5. **InviteToken**: Invitation system for new users (token, created_by_user, used, expires_at)

### Enhanced Prayer Management Models (New)
6. **PrayerAttribute**: Flexible prayer status system (id, prayer_id, attribute_name, attribute_value, created_at, created_by)
7. **PrayerActivityLog**: Audit trail for prayer status changes (id, prayer_id, user_id, action, old_value, new_value, created_at)

### Multi-Device Authentication Models
8. **AuthenticationRequest**: Login requests from new devices (id, user_id, device_info, ip_address, status, expires_at)
9. **AuthApproval**: Individual approval votes (id, auth_request_id, approver_user_id, created_at)
10. **AuthAuditLog**: Complete audit trail for authentication actions (id, auth_request_id, action, actor_user_id, actor_type, details)
11. **SecurityLog**: Security events and monitoring (id, event_type, user_id, ip_address, user_agent, details)

### Prayer Attributes System
The prayer system now uses a flexible attributes approach instead of simple boolean flags:
- **Multiple simultaneous statuses**: Prayers can be archived AND answered AND flagged
- **Extensible design**: New attributes can be added without schema changes
- **Audit trail**: All status changes are logged for accountability
- **Efficient querying**: Proper indexing for performance with attribute filtering

### Prayer Status Attributes
- **archived**: Prayer hidden from public feeds but preserved with history
- **answered**: Prayer marked as resolved, with optional answer_date and answer_testimony
- **flagged**: Prayer requires moderation (migrated from boolean)
- **answer_date**: ISO timestamp when prayer was answered
- **answer_testimony**: User's testimony of how prayer was answered

## Key Features

### Prayer System
- Users submit prayer requests as prompts
- Claude AI transforms prompts into proper community prayers
- Prayers are written in third person so others can pray FOR the requester
- Community members can mark prayers as "prayed"
- Multiple feed views: all, new/unprayed, most prayed, my prayers, my requests, answered, archived

### Prayer Lifecycle Management (New)
- **Prayer Author Controls**: Authors can manage their own prayer requests
- **Archive System**: Hide prayers from public feeds while preserving history
- **Answered Prayers**: Mark prayers as resolved with optional testimony sharing
- **Status Combinations**: Prayers can have multiple statuses simultaneously
- **Activity Logging**: Complete audit trail of all status changes
- **Community Celebration**: Dedicated feeds for celebrating answered prayers

### Prayer Status Management
- **Archive/Restore**: Prayer authors can archive prayers (hide from public) and restore them
- **Mark as Answered**: Authors can mark prayers as answered with optional testimony
- **Testimony Sharing**: Community can see how God moved in answered prayers
- **Status Preservation**: Prayer marks and community engagement preserved across status changes

### Enhanced Community Features
- **Answered Prayers Feed**: Public celebration of resolved prayer requests
- **Personal Archive**: Private view of author's archived prayers
- **Prayer Statistics**: Answer rates, community engagement metrics
- **Testimony Collection**: Stories of how prayers were answered for community encouragement

### Community Moderation System
- **Community Flagging**: All users can flag inappropriate content
- **Content Shielding**: Flagged prayers are hidden but not deleted, showing warning message
- **Admin Review**: Only admins can unflag content after review
- **Immediate Response**: Flagged content is instantly shielded from public view
- **Preview Access**: Admins can see preview of flagged content for review

### Authentication & Access
- **Invite-only system** (requires valid invite token to join)
- **First user becomes admin** (id = "admin")
- **Multi-device authentication** with approval workflows
- **Half-authenticated state** for pending approvals
- **Three approval methods**: Admin instant approval, self-approval from trusted devices, peer approval by community
- **Configurable approval requirements** via environment variables
- **Cookie-based sessions** (14-day expiration) with device tracking
- **Security monitoring** with rate limiting and audit logging

### Feed Types
1. **All**: All unflagged, non-archived prayers (includes answered prayers for celebration)
2. **New & Unprayed**: Prayers with zero prayer marks (excludes archived)
3. **Most Prayed**: Sorted by prayer count (excludes archived)
4. **My Prayers**: Prayers the user has marked as prayed (includes all statuses)
5. **My Requests**: Prayers submitted by the user (includes all statuses for self-management)
6. **Recent Activity**: Prayers with marks in last 7 days (excludes archived)
7. **Answered**: Public celebration feed showing all answered prayers with testimonies
8. **Archived**: Private feed showing user's own archived prayers only

## API Endpoints

### Main Routes
- `GET /` - Main feed (supports feed_type parameter including answered, archived)
- `POST /prayers` - Submit new prayer request (requires full authentication)
- `POST /mark/{prayer_id}` - Mark prayer as prayed (HTMX enabled, requires full authentication)
- `GET /activity` - View prayer activity/marks
- `GET /admin` - Admin panel with flagged content and auth requests (admin only)
- `POST /flag/{prayer_id}` - Flag/unflag content (community flagging, admin unflagging)
- `GET /claim/{token}` - Claim invite and create account (supports multi-device flow)
- `POST /invites` - Generate new invite tokens (HTMX enabled, requires full authentication)
- `GET /prayer/{prayer_id}/marks` - View who prayed for specific prayer
- `GET /answered` - Answered prayers celebration page with community metrics

### Prayer Status Management Routes (New)
- `POST /prayer/{prayer_id}/archive` - Archive prayer (author only, HTMX enabled)
- `POST /prayer/{prayer_id}/restore` - Restore archived prayer (author only, HTMX enabled)
- `POST /prayer/{prayer_id}/answered` - Mark prayer as answered with optional testimony (author only, HTMX enabled)

### Multi-Device Authentication Routes
- `POST /auth/request` - Create authentication request for existing username
- `GET /auth/status` - View authentication status (half-authenticated users)
- `GET /auth/pending` - View pending requests for approval (requires full authentication)
- `POST /auth/approve/{request_id}` - Approve an authentication request
- `POST /auth/reject/{request_id}` - Reject an authentication request (admin only)
- `GET /auth/my-requests` - View own authentication requests for self-approval

### Admin Authentication Routes
- `GET /admin/auth-audit` - View comprehensive audit log (admin only)
- `POST /admin/bulk-approve` - Bulk approve all pending requests (admin only)

### Moderation Flow
1. **Any user flags content** → Prayer immediately shielded with warning
2. **Admin reviews flagged content** → Can see preview and unflag if appropriate
3. **Unflagged content** → Restored to full visibility with all functionality

### Authentication Flow

#### New User Registration
1. User visits `/claim/{token}` with valid invite
2. Creates account with unique display name
3. Gets full authentication session cookie (14-day expiration)
4. Can access all features immediately

#### Existing User Multi-Device Login
1. User visits `/claim/{token}` with existing display name
2. System creates authentication request (if enabled via config)
3. User enters half-authenticated state with limited access
4. Approval required via one of three methods:
   - **Admin approval**: Instant approval by any administrator
   - **Self approval**: Approval from user's existing fully-authenticated device
   - **Peer approval**: Approval from configured number of community members
5. Once approved, session upgraded to full authentication

## Environment Variables
```bash
# Required
ANTHROPIC_API_KEY=your_claude_api_key

# Authentication Configuration (Optional - defaults shown)
MULTI_DEVICE_AUTH_ENABLED=true              # Enable/disable multi-device authentication
REQUIRE_APPROVAL_FOR_EXISTING_USERS=true    # Require approval for existing users
PEER_APPROVAL_COUNT=2                       # Number of peer approvals needed

# Optional
JWT_SECRET=your_jwt_secret_for_tokens       # For invite token generation
```

### Configuration Options
- **MULTI_DEVICE_AUTH_ENABLED**: `false` disables multi-device auth entirely, users login directly
- **REQUIRE_APPROVAL_FOR_EXISTING_USERS**: `false` allows existing users to login from new devices without approval
- **PEER_APPROVAL_COUNT**: Any positive integer, controls how many community members need to approve

## AI Prayer Generation
- Uses Claude 3.5 Sonnet model
- System prompt ensures prayers are community-focused (third person)
- Transforms user requests into proper, reverent prayers
- Fallback to simple prayer format if API fails
- 2-4 sentence length, accessible to various faith backgrounds

## Development Patterns

### Session Management
- `create_session(user_id, auth_request_id, device_info, ip_address, is_fully_authenticated)` - Creates new session with device tracking
- `current_user(request)` - Returns (User, Session) tuple with authentication status
- `require_full_auth(request)` - Dependency that requires full authentication
- `is_admin(user)` - Check admin privileges

### Multi-Device Authentication Functions
- `create_auth_request(user_id, device_info, ip_address)` - Create authentication request
- `approve_auth_request(request_id, approver_id)` - Process approval with configurable logic
- `check_rate_limit(user_id, ip_address)` - Validate request frequency (3/hour limit)
- `validate_session_security(session, request)` - Session security monitoring
- `log_auth_action()` - Comprehensive audit logging
- `log_security_event()` - Security event monitoring
- `cleanup_expired_requests()` - Automatic cleanup of expired requests (7 days)

### Prayer Status Management Functions (New)
- `prayer.set_attribute(name, value, user_id, session)` - Set prayer attribute with activity logging
- `prayer.remove_attribute(name, session, user_id)` - Remove prayer attribute with activity logging
- `prayer.has_attribute(name, session)` - Check if prayer has specific attribute
- `prayer.get_attribute(name, session)` - Get attribute value
- `prayer.is_archived(session)` - Check if prayer is archived
- `prayer.is_answered(session)` - Check if prayer is answered
- `prayer.answer_date(session)` - Get answer date
- `prayer.answer_testimony(session)` - Get answer testimony

### Database Queries
- Uses SQLModel select statements with joins
- Complex aggregations for feed counts with attribute filtering
- Proper filtering for flagged content and archived prayers across all views
- Optimized queries with composite indexes for prayer attributes

### HTMX Integration
- **Prayer Marking**: Seamless marking without page reload
- **Content Flagging**: Immediate content shielding with visual feedback
- **Prayer Status Management**: Archive, restore, and mark as answered with instant UI updates
- **Testimony Collection**: Modal-based testimony input with celebration themes
- **Status-Aware Styling**: Dynamic CSS classes for archived (amber) and answered (green) prayers
- **Invite Generation**: Modal-based invite link creation with copy functionality and no layout shifts
- **Loading Indicators**: Visual feedback during async operations
- **Context-Aware Responses**: Different behavior for admin panel vs main feed vs celebration pages

### Error Handling
- HTTPException for authentication failures
- Graceful fallbacks for AI generation
- Database transaction safety
- Permission checks for sensitive operations

## Common Development Tasks

### Adding New Feed Types
1. Add logic to main feed route in `app.py`
2. Update `get_feed_counts()` function
3. Add UI option in templates

### Creating Modal Interactions
1. Use HTMX `hx-target="body"` and `hx-swap="beforeend"` for modals
2. Return HTML with fixed positioning and backdrop
3. Add JavaScript functions for close/escape/click-away behavior
4. Include copy functionality with clipboard API and fallback selection

### Modifying Prayer Generation
- Edit system prompt in `generate_prayer()` function
- Adjust model parameters (temperature, max_tokens)
- Test fallback behavior

### Adding Prayer Status Features
1. **New Status Attributes**: Add helper methods to Prayer model using `set_attribute()`
2. **Feed Filtering**: Update queries to exclude/include based on attributes
3. **UI Status Indicators**: Add CSS classes and visual feedback for new statuses
4. **HTMX Endpoints**: Create status management routes with permission checks
5. **Activity Logging**: Ensure all status changes are logged for audit trail

### Database Changes
1. Update models in `models.py`
2. Handle migration manually (SQLite) or use migration scripts for attributes
3. Update related queries in `app.py` with proper attribute filtering
4. Add database indexes for performance optimization

### Moderation Features
- Flagging logic in `/flag/{pid}` endpoint
- Shielded content HTML templates
- Admin panel management tools
- Community safety measures

## Security Considerations

### Core Security
- **Invite-only system** prevents spam and unauthorized access
- **Community moderation** with immediate content shielding
- **Admin oversight** for final moderation decisions
- **Granular permissions**: Users can flag, only admins can unflag
- **Session expiration** (14 days) with secure cookies
- **Input validation** for prayer content and user data
- **No direct database exposure** through proper ORM usage

### Multi-Device Authentication Security
- **Rate limiting**: 3 authentication requests per hour per user/IP
- **Session hijacking detection**: IP address monitoring and logging
- **Device fingerprinting**: Browser and device information tracking
- **Audit trail**: Complete logging of all authentication actions
- **Request expiration**: 7-day automatic expiration of pending requests
- **Configurable approval requirements**: Flexible security based on community needs
- **Security event monitoring**: Comprehensive logging of suspicious activity

## Deployment Notes
- SQLite database file: `thywill.db` (auto-migrates for multi-device auth)
- Run with: `uvicorn app:app --reload`
- Requires valid Anthropic API key
- Static files served from templates directory
- HTMX CDN dependency for interactive features
- Automatic database migration on startup for existing installations
- Environment variables configurable via `.env` file (see `.env.example`)

## UI/UX Design Patterns

### Simplified Front Page Layout (Current)
- **Header Section**: Clean title with compact action buttons (Invite & Add Prayer)
- **Collapsible Prayer Form**: Hidden by default, toggles with JavaScript for cleaner interface
- **Compact Feed Navigation**: Smaller tabs with counts, mobile-friendly horizontal scroll
- **Subtle Daily Prompt**: Minimal amber-colored section, only shows when prompt exists
- **Prayer-Focused Content**: Main feed prominently displays prayers with clear hierarchy

### Design Principles
- **Prayer-First**: Prayer content is the primary focus, other features are secondary
- **Progressive Disclosure**: Advanced features (form, invites) are accessible but not prominent
- **Layout Stability**: Modal overlays prevent layout shifts during interactions
- **Mobile-Responsive**: Horizontal scrolling navigation, stacked mobile layout
- **Clean Typography**: Clear visual hierarchy between prayers, requests, and metadata
- **Accessible Colors**: Purple/gray theme with proper contrast ratios

### Interactive Elements
- **Toggle-based Form**: JavaScript-powered show/hide for prayer submission
- **HTMX Integration**: Dynamic prayer marking, flagging, status management, and invite generation without page reloads
- **Modal Overlays**: Invite generation uses modal overlay to prevent layout shifts
- **Copy Functionality**: One-click invite link copying with visual feedback
- **Click-Away Interactions**: Modals can be dismissed by clicking backdrop or pressing Escape
- **Visual Feedback**: Clear states for prayed/unprayed items, flagged content, archived/answered status, loading indicators
- **Responsive Navigation**: Auto-hiding scrollbars, mobile swipe hints
- **Immediate Actions**: No confirmation dialogs for smoother community moderation

### Content Organization
- Generated prayers are prominently displayed in larger text
- Original requests are shown in secondary gray boxes
- Prayer statistics and actions are in footer area
- **Flagged content** shown with warning banners and admin controls
- Empty states provide clear guidance for next actions

### Community Moderation UI
- **Accessible Flag Button**: Available to all users for community moderation
- **Shielded Content Display**: Clear warning with admin-only preview
- **Context-Aware Controls**: Different buttons and actions based on user role
- **Immediate Visual Feedback**: Loading states and seamless content updates

---

**📝 Note for AI Assistants**: This guide reflects the complete prayer lifecycle management system with flexible attributes architecture, community-driven moderation, and comprehensive multi-device authentication. The platform balances security with usability through configurable approval workflows while maintaining admin oversight for content moderation, authentication management, and prayer status transitions. The prayer attributes system allows unlimited status combinations and extensibility without breaking changes.

**🔄 Recent Updates**: 
- **Prayer Archive & Answered System**: Flexible prayer status management with multi-status support (archived + answered + flagged), activity logging, and celebration features
- **Enhanced Feed System**: New answered prayers celebration feed and private archived feed with improved filtering and community metrics
- **Prayer Attributes Architecture**: Flexible attributes table system enabling unlimited status combinations without schema changes
- **Multi-Device Authentication System**: Comprehensive implementation with half-authenticated states, configurable approval workflows (admin/self/peer), security monitoring, and audit logging
- **Configurable Security**: Environment variables control authentication requirements and approval counts
- **Enhanced UI**: Prayer status management controls, celebration themes, authentication status pages, and testimony collection modals
- **Automatic Migration**: Seamless upgrade for existing installations with preserved data and flagged prayer migration
- **Performance Optimizations**: Database indexing, WAL mode, and efficient query patterns for attribute-based filtering

This is a faith-focused community platform emphasizing reverence, simplicity, meaningful prayer sharing, community self-moderation, and secure multi-device access. 