# ThyWill - AI Assistant Project Guide

## Project Overview
**ThyWill** is a community prayer platform built with FastAPI and SQLModel. It allows users to submit prayer requests, generate proper prayers using AI (Anthropic's Claude), and track community prayer activity.

## Core Architecture

### Technology Stack
- **Backend**: FastAPI (Python web framework)
- **Database**: SQLite with SQLModel ORM
- **AI Integration**: Anthropic Claude API for prayer generation
- **Frontend**: Jinja2 templates with HTML/CSS
- **Authentication**: Cookie-based sessions with JWT tokens for invites

### Key Files
- `app.py` (533 lines) - Main application with all routes and business logic
- `models.py` (39 lines) - Database models and schema
- `templates/` - HTML templates for UI
- `requirements.txt` - Python dependencies (8 packages)
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
- `POST /` - Submit new prayer request
- `POST /pray/{prayer_id}` - Mark prayer as prayed
- `GET /activity` - View prayer activity/marks
- `GET /admin` - Admin panel (admin only)
- `POST /admin/flag/{prayer_id}` - Flag inappropriate content
- `GET /claim/{token}` - Claim invite and create account

### Authentication Flow
1. User visits `/claim/{token}` with valid invite
2. Creates account with display name
3. Gets session cookie (14-day expiration)
4. Can access main features

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
- Proper filtering for flagged content

### Error Handling
- HTTPException for authentication failures
- Graceful fallbacks for AI generation
- Database transaction safety

## Common Development Tasks

### Adding New Feed Types
1. Add logic to main feed route in `app.py`
2. Update `get_feed_counts()` function
3. Add UI option in templates

### Modifying Prayer Generation
- Edit system prompt in `generate_prayer()` function
- Adjust model parameters (temperature, max_tokens)
- Test fallback behavior

### Database Changes
1. Update models in `models.py`
2. Handle migration manually (SQLite)
3. Update related queries in `app.py`

## Security Considerations
- Invite-only system prevents spam
- Admin flagging system for moderation
- Session expiration (14 days)
- Input validation for prayer content
- No direct database exposure

## Deployment Notes
- SQLite database file: `thywill.db`
- Run with: `uvicorn app:app --reload`
- Requires valid Anthropic API key
- Static files served from templates directory

## UI/UX Patterns
- Clean, minimal design focused on prayer content
- Different visual states for prayed/unprayed items
- Mobile-responsive layout
- Easy navigation between feed types
- Clear submission and marking workflows

---

**📝 Note for AI Assistants**: Please update this guide whenever you make changes to the project structure, API endpoints, database models, or core features.

This is a faith-focused community platform emphasizing reverence, simplicity, and meaningful prayer sharing. 