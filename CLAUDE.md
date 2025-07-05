# ThyWill - Claude Code Configuration

## Project Overview
Prayer platform with FastAPI/SQLModel, Claude AI integration, HTMX frontend, invite-only auth.

## Key Commands
```bash
# Setup
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt && chmod +x thywill
./thywill init

# Development  
./thywill start        # Production server
./thywill test         # Safe testing
./thywill status       # Database status
pytest                 # Run tests

# Template Validation
./validate_templates.py  # Comprehensive template field validation
./check_templates.sh     # Quick static analysis for common issues

# Database
./thywill backup
./thywill restore <file>
./thywill migrate
./thywill import <file>
./thywill heal-archives   # Comprehensive archive healing with full activity data
```

## Architecture
- `app.py` - Main FastAPI app
- `models.py` - Database schema  
- `app_helpers/` - Services, routes, utils
- `templates/` - Jinja2 HTML
- `docs/plans/` - All .md plans go here

## Key Functions
**Auth**: `create_session()`, `current_user()`, `require_full_auth()`, `is_admin()`
**Prayer**: `generate_prayer()`, `get_feed_counts()`, `prayer.set_attribute()`
**Multi-device**: `create_auth_request()`, `approve_auth_request()`, rate limiting

## Environment Variables
```bash
# Required
ANTHROPIC_API_KEY=your_claude_api_key

# Server Configuration
PORT=8000                          # Server port (default: 8000)

# Optional Auth
MULTI_DEVICE_AUTH_ENABLED=true
PEER_APPROVAL_COUNT=2
JWT_SECRET=changeme

# Migration Settings
AUTO_MIGRATE_ON_STARTUP=true      # Auto-run migrations on app startup (production only)
DEFAULT_INVITE_MAX_USES=1          # Default max uses for new invite tokens

# Optional  
TEXT_ARCHIVE_ENABLED=true
PAYPAL_USERNAME=
VENMO_HANDLE=
```

## Database Models
**Core**: User, Prayer, PrayerMark, Session, InviteToken
**Advanced**: PrayerAttribute, AuthenticationRequest, AuthApproval, SecurityLog

## Key Routes
**Main**: `GET /`, `POST /prayers`, `POST /mark/{id}`, `POST /flag/{id}`
**Prayer**: `POST /prayer/{id}/archive|restore|answered`
**Auth**: `GET|POST /login`, `POST /auth/request|approve/{id}`, `GET /claim/{token}`
**Archive**: `GET /api/archive/user/{id}/download`, `GET /api/archive/community/download`

## Features
**Prayer**: AI generation, multiple feeds, status management, text archives
**Auth**: Invite-only, multi-device approval, rate limiting, security logging  
**Community**: Content flagging, lifecycle management, testimony sharing, transparency

## Testing
**Categories**: Unit, integration, functional, CLI
**Markers**: `@pytest.mark.unit|integration|functional|slow`
**Safety**: Use `./thywill test` for isolated testing

## Development Patterns
**Prayer Status**: Use `prayer.set_attribute()`, update feeds, add UI controls
**HTMX**: `hx-target="body"` for modals, fixed positioning, escape handlers
**Auth Flows**: Update routes, templates, ensure logging/rate limiting
**Archives**: Use `ArchiveDownloadService`, link from prayer pages

## Code Consistency
**CRITICAL**: When changing database schema, moving/renaming files, or renaming models/classes:
1. Use `grep -r "old_name" .` to find ALL references
2. Update imports, templates, tests, CLI references
3. Run `./validate_templates.py` and full test suite
4. Use `Task` tool for comprehensive codebase scanning

## Security
**Auth**: 3/hour rate limit, IP monitoring, device fingerprinting, audit logging
**Content**: Invite-only, community moderation, admin oversight, input validation

## Archive Operations (Enhanced Idempotency)
**heal-archives**: Creates comprehensive archive files with complete activity history
- Includes prayer marks, attributes, activity logs in chronological order
- Fully idempotent - safe to run multiple times, detects incomplete archives
- Content-based verification ensures archives contain all database activity
- Round-trip compatible with text-archives import for complete data restoration

**import text-archives**: Fully idempotent import from text archive files
- Restores complete database state including all activity data
- Duplicate detection prevents data corruption on repeated imports
- Both operations guarantee full data coverage and integrity

## Architecture  
**Modular**: Backward compatibility, dual imports, incremental adoption
**Archive-First**: Text files before DB, human-readable, disaster recovery
**HTMX**: No page reloads, modal workflows, loading indicators

## File Rules
**All .md plans/docs → `docs/plans/`**
**Naming**: lowercase_with_underscores, include type (`*_plan.md`, `*_design.md`)

## Production
Whenever you see vmi2648361 in a command log, that means it was run on production.
You don't have access to the production server, so please act accordingly.

---
Faith-focused prayer platform emphasizing reverence, community moderation, secure access.