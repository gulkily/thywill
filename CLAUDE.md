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

# Documentation Tools
python generate_app_overview.py     # Generate app overview with live stats
python md_to_pdf_simple.py <file>   # Convert markdown to PDF
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
**User Attributes**: `is_supporter`, `supporter_since` - Manual supporter status management

## Key Routes
**Main**: `GET /`, `POST /prayers`, `POST /mark/{id}`, `POST /flag/{id}`
**Prayer**: `POST /prayer/{id}/archive|restore|answered`
**Auth**: `GET|POST /login`, `POST /auth/request|approve/{id}`, `GET /claim/{token}`
**Archive**: `GET /api/archive/user/{id}/download`, `GET /api/archive/community/download`

## Features
**Prayer**: AI generation, multiple feeds, status management, text archives, praise reports
**Auth**: Invite-only, multi-device approval, rate limiting, security logging  
**Community**: Content flagging, lifecycle management, testimony sharing, transparency
**UI**: Header logout removed (menu-only), praise reports terminology, updated prayer prompts

## Testing
**Categories**: Unit, integration, functional, CLI
**Markers**: `@pytest.mark.unit|integration|functional|slow`
**Safety**: Use `./thywill test` for isolated testing

## Schema Management & Migration Best Practices
**Validation**: `./thywill validate-schema` - Check database schema compatibility
**Auto-repair**: App startup includes defensive schema validation and repairs
**Production Safety**: Missing columns are automatically added with safe defaults
**Migration Strategy**:
- **Development**: Run migrations normally with `./thywill migrate`
- **Production**: Always backup before deployments, auto-repair handles minor drift
- **Schema Drift**: Use defensive schema checks for critical columns
- **Pre-deployment**: Always run `./thywill validate-schema` before deployment

## Development Patterns
**Prayer Status**: Use `prayer.set_attribute()`, update feeds, add UI controls
**HTMX**: `hx-target="body"` for modals, fixed positioning, escape handlers
**Auth Flows**: Update routes, templates, ensure logging/rate limiting
**Archives**: Use `ArchiveDownloadService`, link from prayer pages
**Username Display**: Use `{{ username|username_display|safe }}` in templates for consistent supporter badges

## Code Consistency
**CRITICAL**: When changing database schema, moving/renaming files, or renaming models/classes:
1. Use `grep -r "old_name" .` to find ALL references
2. Update imports, templates, tests, CLI references
3. Run `./validate_templates.py` and full test suite
4. Use `Task` tool for comprehensive codebase scanning

## Documentation Maintenance
**CRITICAL**: Update documentation after EVERY commit:
1. **CLAUDE.md** - Add new commands, features, environment variables, or significant changes
2. **AI_PROJECT_GUIDE.md** - Update architecture, routes, features, and Recent Updates section
3. Review commit messages and update relevant sections immediately
4. Keep Recent Changes section current with chronological updates

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

**User Attributes Archive**: `text_archives/users/user_attributes.txt`
- Centralized file for all user attributes including supporter status
- Manual editing for easy supporter management (set `is_supporter: true`)
- Bidirectional sync through export/import system
- Format: Username blocks with key-value pairs
- Import with: `./thywill import-all` or `./thywill import text-archives`
- Fully idempotent - safe to run multiple times

## Architecture  
**Modular**: Backward compatibility, dual imports, incremental adoption
**Archive-First**: Text files before DB, human-readable, disaster recovery
**HTMX**: No page reloads, modal workflows, loading indicators

## File Rules
**All .md plans/docs → `docs/plans/`**
**Naming**: lowercase_with_underscores, include type (`*_plan.md`, `*_design.md`)

## Git Workflow
**Post-Commit Documentation**: After every `git commit`, immediately update:
- CLAUDE.md (commands, features, environment variables)
- AI_PROJECT_GUIDE.md (architecture, routes, Recent Updates)
This ensures documentation stays synchronized with codebase changes.

## Production
Whenever you see vmi2648361 in a command log, that means it was run on production.
You don't have access to the production server, so please act accordingly.

## Recent Changes (July 2025)
**Centralized Username Display System**: Implemented comprehensive supporter badge system
- Created `UsernameDisplayService` for centralized username display logic
- Added `username_display` template filter for consistent supporter badges across all templates
- Updated all username display locations (prayer cards, activity feed, profiles, admin, etc.)
- Fixed broken supporter badge implementation in prayer cards
- Added caching for performance optimization
- Integrated user attributes import into `./thywill import-all` command with full idempotency
**User Attributes System**: Implemented bidirectional sync for supporter badges and user attributes
- Added `is_supporter` and `supporter_since` fields to User model
- Created `text_archives/users/user_attributes.txt` for manual supporter management
- Integrated export/import system for user attributes
- Manual editing support for easy supporter status changes
**Terminology**: "Answered Prayers" → "Praise Reports" throughout UI (button text, headers, modals)
**UI**: Logout button removed from header (now menu-only) to prevent accidental logouts
**Prayer Generation**: Updated system prompt with enhanced community focus and Scripture references
**Documentation**: Added `generate_app_overview.py` and `md_to_pdf_simple.py` tools
**Performance**: Refactored recent activity counting in feed functions
**Testing**: User fields standardized to use display_name instead of id
**Cleanup**: Removed unused database files for cleaner repository

---
Faith-focused prayer platform emphasizing reverence, community moderation, secure access.