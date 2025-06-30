# ThyWill - Claude Code Configuration

## Project Overview
ThyWill is a community-driven prayer platform built with FastAPI and SQLModel that creates a safe, faith-based environment for sharing prayer requests and supporting one another spiritually.

## Key Technologies
- **Backend**: FastAPI (Python web framework)
- **Database**: SQLite with SQLModel ORM  
- **AI Integration**: Anthropic Claude API for prayer generation
- **Frontend**: Jinja2 templates with HTML/CSS/JavaScript + HTMX
- **Authentication**: Cookie-based sessions with JWT tokens for invites

## Development Commands

### Setup & Installation
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Make CLI executable
chmod +x thywill

# Initialize database
./thywill init
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/functional/

# CLI testing (uses bats framework)
cd tests/cli && bats test_thywill_*.bats
```

### Server Management
```bash
# Start server with protection
./thywill start

# Manual start (development only)
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Run test suite safely
./thywill test

# Check database status
./thywill status
```

### Database Operations
```bash
# Create backup
./thywill backup

# Restore from backup
./thywill restore <backup_file>

# Run migrations
./thywill migrate

# Import/export data
./thywill import <export.zip>
./thywill import <file> --dry-run  # Preview import
./thywill export  # Export guide
```

## Code Style & Conventions

### File Organization
- `app.py` - Main FastAPI application with routes
- `models.py` - Database models and schema
- `app_helpers/` - Modular business logic
  - `services/` - Core service modules (auth, prayer, invite, archive, archive_download)
  - `routes/` - Route modules (auth, prayer, admin, user, invite, general, archive)
  - `utils/` - Utility functions (database helpers)
- `templates/` - Jinja2 HTML templates
- `tests/` - Test suite (unit, integration, functional, CLI)
- `docs/` - Documentation and planning documents
  - `plans/` - Implementation plans and design documents (CREATE ALL .md PLANS HERE)

### Import Patterns
The codebase supports dual import paths for backward compatibility:
```python
# Option 1: Import from app.py (backward compatibility)
from app import create_session, current_user, get_feed_counts

# Option 2: Import directly from helper modules (new code)
from app_helpers.services.auth_helpers import create_session, current_user
from app_helpers.services.prayer_helpers import get_feed_counts
```

### Key Functions

#### Authentication & Security
- `create_session(user_id, auth_request_id, device_info, ip_address, is_fully_authenticated)`
- `current_user(request)` - Returns (User, Session) tuple
- `require_full_auth(request)` - Dependency requiring full authentication
- `is_admin(user)` - Check admin privileges

#### Prayer Management
- `generate_prayer(request_text)` - AI prayer generation using Claude
- `get_feed_counts(session, user_id)` - Get prayer counts for different feeds
- `prayer.set_attribute(name, value, user_id, session)` - Set prayer status attributes
- `prayer.is_archived(session)` / `prayer.is_answered(session)` - Status checks

#### Multi-Device Authentication
- `create_auth_request(user_id, device_info, ip_address)`
- `approve_auth_request(request_id, approver_id)`
- `check_rate_limit(user_id, ip_address)` - 3/hour limit
- `log_security_event()` - Security audit logging

## Environment Variables

### Required
```bash
ANTHROPIC_API_KEY=your_claude_api_key
```

### Optional Authentication Configuration
```bash
MULTI_DEVICE_AUTH_ENABLED=true              # Enable multi-device auth
REQUIRE_APPROVAL_FOR_EXISTING_USERS=true    # Require approval for existing users  
PEER_APPROVAL_COUNT=2                       # Number of peer approvals needed
REQUIRE_VERIFICATION_CODE=false             # Enhanced verification security
INVITE_TOKEN_EXPIRATION_HOURS=12            # Invite link expiration time in hours
JWT_SECRET=your_jwt_secret_for_tokens       # For invite token generation
```

### Optional Payment Configuration
```bash
PAYPAL_USERNAME=your_paypal_username
VENMO_HANDLE=your_venmo_handle
```

### Text Archive Settings
```bash
TEXT_ARCHIVE_ENABLED=true
TEXT_ARCHIVE_BASE_DIR=./text_archives
```

## Database Schema

### Core Models
- **User**: User profiles with religious preferences
- **Prayer**: Prayer requests with AI-generated prayers and text archive links
- **PrayerMark**: Track when users pray for requests
- **Session**: Enhanced user sessions with device tracking
- **InviteToken**: Invitation system for controlled growth

### Advanced Features
- **PrayerAttribute**: Flexible prayer status system (archived, answered, flagged)
- **AuthenticationRequest**: Multi-device login approvals
- **AuthApproval**: Peer approval voting system
- **SecurityLog**: Comprehensive security audit trail
- **NotificationState**: Real-time authentication notifications

## API Endpoints

### Main Application Routes
- `GET /` - Main prayer feed (supports feed_type parameter)
- `POST /prayers` - Submit new prayer request
- `POST /mark/{prayer_id}` - Mark prayer as prayed (HTMX)
- `POST /flag/{prayer_id}` - Flag/unflag content
- `GET /admin` - Admin panel (admin only)

### Prayer Status Management
- `POST /prayer/{prayer_id}/archive` - Archive prayer (author only)
- `POST /prayer/{prayer_id}/restore` - Restore archived prayer
- `POST /prayer/{prayer_id}/answered` - Mark as answered with testimony

### Authentication Routes
- `GET /claim/{token}` - Claim invite and create account
- `GET /login` - User-friendly login form
- `POST /login` - Process username login
- `POST /auth/request` - Create authentication request
- `GET /auth/pending` - View pending requests for approval
- `POST /auth/approve/{request_id}` - Approve authentication request

### Notification System
- `GET /auth/notifications` - Get unread notifications (HTMX)
- `POST /auth/notifications/{id}/read` - Mark notification as read
- `POST /auth/notifications/{id}/verify` - Validate verification code

### Archive Download Routes
- `GET /api/archive/user/{user_id}/download` - Download user's text archive as ZIP
- `GET /api/archive/user/{user_id}/metadata` - Get user's archive metadata
- `GET /api/archive/community/list` - List community archive files
- `GET /api/archive/community/download` - Download complete community archive
- `GET /api/archive/prayer/{prayer_id}/file` - Download prayer's text file
- `DELETE /api/archive/downloads/cleanup` - Clean up old download files (admin)

## Key Features

### Prayer System
- AI-generated community prayers using Claude 3.5 Sonnet
- Multiple feed views (all, new, most prayed, answered, archived)
- Flexible prayer status attributes (archived, answered, flagged)
- Text archive system for human-readable data storage
- Archive download functionality for users and community data

### Authentication & Security
- Invite-only registration system
- Multi-device authentication with approval workflows
- Real-time notification system for auth requests
- Comprehensive security audit logging
- Rate limiting and session monitoring

### Community Features
- Community-driven content moderation via flagging
- Prayer lifecycle management (archive, answer, restore)
- Testimony sharing for answered prayers
- Invite tree system for tracking community growth
- Complete data transparency with archive downloads

## Testing Guidelines

### Test Categories
- **Unit Tests**: Individual components and functions (`tests/unit/`)
- **Integration Tests**: Component interactions (`tests/integration/`)
- **Functional Tests**: End-to-end scenarios (`tests/functional/`)
- **CLI Tests**: Command-line interface testing (`tests/cli/`)

### Test Markers
```python
@pytest.mark.unit         # Unit tests
@pytest.mark.integration  # Integration tests  
@pytest.mark.functional   # Functional tests
@pytest.mark.slow         # Long-running tests
```

### Test Safety
- Use `./thywill test` to run tests safely with database protection
- Tests automatically use isolated test database
- No risk of data loss when running tests properly

## Common Development Tasks

### Adding New Prayer Statuses
1. Use `prayer.set_attribute(name, value, user_id, session)` for new attributes
2. Update feed filtering queries to include/exclude based on attributes
3. Add UI controls and HTMX endpoints for status management
4. Ensure activity logging for audit trail

### Creating HTMX Interactions
1. Use `hx-target="body"` and `hx-swap="beforeend"` for modals
2. Return HTML with fixed positioning and backdrop
3. Include JavaScript for close/escape/click-away behavior
4. Add visual feedback and loading indicators

### Modifying Authentication Flows
1. Update routes in `app_helpers/routes/auth_routes.py`
2. Modify templates with feature-flag controlled visibility
3. Ensure security logging and rate limiting
4. Test multi-device approval workflows

### Working with Archive Downloads
1. Use `ArchiveDownloadService` for creating user and community archives
2. All users can download complete site archives for transparency
3. Individual prayer pages include links to text archive files
4. Archive metadata includes comprehensive statistics and file paths
5. ZIP downloads include organized folders for personal and community data

## Security Considerations

### Authentication Security
- Rate limiting: 3 authentication requests per hour per user/IP
- Session hijacking detection via IP monitoring
- Device fingerprinting for security tracking
- Comprehensive audit logging of all auth actions
- Configurable approval requirements for flexible security

### Content Security
- Invite-only system prevents unauthorized access
- Community moderation with immediate content shielding
- Admin oversight for content moderation decisions
- Input validation for all user data

## Deployment Notes

### Production Deployment
- Use `./thywill start` instead of direct Python execution
- Requires valid Anthropic API key
- SQLite database with automatic migrations
- Text archive system for backup and recovery
- Environment variables configurable via `.env` file

### Database Safety
- Always use CLI commands for database operations
- Automatic backups before destructive operations
- Emergency recovery from text archives
- Environment-based protection prevents accidental data loss

## Architecture Patterns

### Modular Design
- Resilient refactoring approach maintaining backward compatibility
- Zero breaking changes during code reorganization
- Dual import paths for flexibility
- Incremental adoption of new patterns

### Archive-First Philosophy
- Text files written FIRST, then database records created
- Human-readable archives for ultimate data durability
- Automatic healing for legacy data
- Complete disaster recovery capability

### HTMX Integration
- Seamless interactions without page reloads
- Modal-based workflows for better UX
- Context-aware responses based on user role
- Loading indicators and visual feedback

## File Creation Rules

**CRITICAL: Always follow these file placement rules**

### Documentation Files
- **Implementation Plans**: ALWAYS create in `docs/plans/` directory
- **Design Documents**: ALWAYS create in `docs/plans/` directory  
- **Technical Specifications**: ALWAYS create in `docs/plans/` directory
- **NEVER create .md files in project root** - always use appropriate subdirectories

### File Naming Convention
- Use descriptive, lowercase filenames with underscores
- Include file type in name: `*_implementation_plan.md`, `*_design_doc.md`
- Examples: `prayer_editing_implementation_plan.md`, `user_authentication_design.md`

---

This project emphasizes reverence, community self-moderation, secure multi-device access, and meaningful prayer sharing in a faith-focused environment.