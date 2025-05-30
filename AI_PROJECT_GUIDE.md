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
- `app.py` (665 lines) - Main application with all routes and business logic
- `models.py` (40 lines) - Database models and schema
- `templates/` - HTML templates for UI
- `requirements.txt` - Python dependencies
- `generate_token.py` - Utility for creating invite tokens

## Database Schema

### Core Models
1. **User**: Basic user profile (id, display_name, created_at)
2. **Prayer**: Prayer requests (id, author_id, text, generated_prayer, project_tag, flagged)
3. **PrayerMark**: Tracks when users pray for requests (user_id, prayer_id, created_at)
4. **Session**: User authentication sessions (id, user_id, expires_at)
5. **InviteToken**: Invitation system for new users (token, created_by_user, used, expires_at)

## Key Features

### Prayer System
- Users submit prayer requests as prompts
- Claude AI transforms prompts into proper community prayers
- Prayers are written in third person so others can pray FOR the requester
- Community members can mark prayers as "prayed"
- Multiple feed views: all, new/unprayed, most prayed, my prayers, my requests

### Community Moderation System
- **Community Flagging**: All users can flag inappropriate content
- **Content Shielding**: Flagged prayers are hidden but not deleted, showing warning message
- **Admin Review**: Only admins can unflag content after review
- **Immediate Response**: Flagged content is instantly shielded from public view
- **Preview Access**: Admins can see preview of flagged content for review

### Authentication & Access
- Invite-only system (requires valid invite token to join)
- First user becomes admin (id = "admin")
- Cookie-based sessions (14-day expiration)
- Admin can generate invite tokens and manage flagged content

### Feed Types
1. **All**: All unflagged prayers
2. **New & Unprayed**: Prayers with zero prayer marks
3. **Most Prayed**: Sorted by prayer count
4. **My Prayers**: Prayers the user has marked as prayed
5. **My Requests**: Prayers submitted by the user
6. **Recent Activity**: Prayers with marks in last 7 days

## API Endpoints

### Main Routes
- `GET /` - Main feed (supports feed_type parameter)
- `POST /prayers` - Submit new prayer request
- `POST /mark/{prayer_id}` - Mark prayer as prayed (HTMX enabled)
- `GET /activity` - View prayer activity/marks
- `GET /admin` - Admin panel (admin only)
- `POST /flag/{prayer_id}` - Flag/unflag content (community flagging, admin unflagging)
- `GET /claim/{token}` - Claim invite and create account
- `POST /invites` - Generate new invite tokens (HTMX enabled, returns modal overlay)
- `GET /prayer/{prayer_id}/marks` - View who prayed for specific prayer

### Moderation Flow
1. **Any user flags content** → Prayer immediately shielded with warning
2. **Admin reviews flagged content** → Can see preview and unflag if appropriate
3. **Unflagged content** → Restored to full visibility with all functionality

### Authentication Flow
1. User visits `/claim/{token}` with valid invite
2. Creates account with display name
3. Gets session cookie (14-day expiration)
4. Can access main features including community moderation

## Environment Variables
```bash
ANTHROPIC_API_KEY=your_claude_api_key
JWT_SECRET=your_jwt_secret_for_tokens
```

## AI Prayer Generation
- Uses Claude 3.5 Sonnet model
- System prompt ensures prayers are community-focused (third person)
- Transforms user requests into proper, reverent prayers
- Fallback to simple prayer format if API fails
- 2-4 sentence length, accessible to various faith backgrounds

## Development Patterns

### Session Management
- `create_session(user_id)` - Creates new session
- `current_user(request)` - Dependency injection for auth
- `is_admin(user)` - Check admin privileges

### Database Queries
- Uses SQLModel select statements with joins
- Complex aggregations for feed counts
- Proper filtering for flagged content across all views

### HTMX Integration
- **Prayer Marking**: Seamless marking without page reload
- **Content Flagging**: Immediate content shielding with visual feedback
- **Invite Generation**: Modal-based invite link creation with copy functionality and no layout shifts
- **Loading Indicators**: Visual feedback during async operations
- **Context-Aware Responses**: Different behavior for admin panel vs main feed

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

### Database Changes
1. Update models in `models.py`
2. Handle migration manually (SQLite)
3. Update related queries in `app.py`

### Moderation Features
- Flagging logic in `/flag/{pid}` endpoint
- Shielded content HTML templates
- Admin panel management tools
- Community safety measures

## Security Considerations
- **Invite-only system** prevents spam and unauthorized access
- **Community moderation** with immediate content shielding
- **Admin oversight** for final moderation decisions
- **Granular permissions**: Users can flag, only admins can unflag
- **Session expiration** (14 days) with secure cookies
- **Input validation** for prayer content and user data
- **No direct database exposure** through proper ORM usage

## Deployment Notes
- SQLite database file: `thywill.db`
- Run with: `uvicorn app:app --reload`
- Requires valid Anthropic API key
- Static files served from templates directory
- HTMX CDN dependency for interactive features

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
- **HTMX Integration**: Dynamic prayer marking, flagging, and invite generation without page reloads
- **Modal Overlays**: Invite generation uses modal overlay to prevent layout shifts
- **Copy Functionality**: One-click invite link copying with visual feedback
- **Click-Away Interactions**: Modals can be dismissed by clicking backdrop or pressing Escape
- **Visual Feedback**: Clear states for prayed/unprayed items, flagged content, loading indicators
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

**📝 Note for AI Assistants**: This guide reflects the community-driven moderation system with flag functionality accessible to all users, while maintaining admin oversight. The platform emphasizes immediate community response to inappropriate content while preserving admin authority for final decisions.

**🔄 Recent Updates**: The invite generation system has been improved to use modal overlays instead of layout-shifting replacements, providing a better user experience with copy functionality, click-away dismissal, and keyboard shortcuts (Escape key).

This is a faith-focused community platform emphasizing reverence, simplicity, meaningful prayer sharing, and community self-moderation. 