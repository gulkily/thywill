# ThyWill

A community-driven prayer platform that creates a safe, faith-based environment for sharing prayer requests and supporting one another spiritually.

![ThyWill Logo](static/logos/logo.svg)

## ✨ Features

- **🙏 Prayer Community**: Submit prayer requests and pray for others in a supportive environment
- **🤖 AI-Enhanced Prayer**: Generate proper prayers using Anthropic's Claude AI
- **📧 Invite-Only System**: Controlled growth through invitation tokens to maintain community quality
- **🔐 Multi-Device Authentication**: Secure peer-approval system for accessing accounts from new devices
- **⛪ Religious Preferences**: Support for different faith traditions (Christian, interfaith, etc.)
- **📋 Prayer Lifecycle**: Track answered prayers, archive requests, and celebrate testimonies
- **🛡️ Community Moderation**: Flag inappropriate content and maintain a respectful environment
- **🌳 Invite Tree System**: Track community growth and relationships
- **📁 Text Archive System**: Archive-first data storage with human-readable backups

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Anthropic API key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd thywill
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your Anthropic API key:
   ```env
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```
   
   **Optional**: Configure payment settings for donations:
   ```env
   # Leave empty to disable donations
   PAYPAL_USERNAME=
   VENMO_HANDLE=
   ```
   
   All other settings have sensible defaults. See `.env.example` for the complete configuration options.

5. **Initialize database**
   ```bash
   # Make CLI executable
   chmod +x thywill
   
   # Initialize database safely
   ./thywill init
   ```

6. **Run the application**
   ```bash
   # Start server with protection
   ./thywill start
   
   # Or manually with uvicorn (advanced)
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Initial setup**
   - Look for the admin invite token in console output: `==== First-run invite token (admin): <token> ====`
   - Visit `http://localhost:8000/claim/<token>` to create the admin account
   - Use the admin panel to generate invite links for other users

## 🛠️ ThyWill CLI

The `thywill` command provides a unified interface for all database and server operations:

### Database Operations
```bash
./thywill init                    # Initialize database tables
./thywill backup                  # Create database backup
./thywill restore <backup_file>   # Restore from backup
./thywill status                  # Show database status
```

### Import/Export
```bash
./thywill import <export.zip>     # Import community data
./thywill import <file> --dry-run # Preview import
./thywill export                  # Guide for creating exports
```

### Server Management
```bash
./thywill start                   # Start server with protection
./thywill test                    # Run test suite
./thywill migrate                 # Run database migrations
```

### Examples
```bash
# Daily operations
./thywill backup                              # Create backup
./thywill start                               # Start server

# Data recovery
./thywill import community_export_2024.zip   # Restore from export
./thywill import backup.zip --dry-run        # Preview restore

# Development
./thywill test                                # Run tests safely
./thywill status                              # Check database health
```

⚠️ **Important**: Always use `./thywill start` instead of running Python directly to prevent accidental data loss.

## 🏗️ Project Structure

```
thywill/
├── app.py                      # Main FastAPI application
├── models.py                   # Database models and schema
├── thywill                     # CLI management tool
├── app_helpers/               # Modular business logic
│   ├── services/             # Core service modules
│   │   ├── auth_helpers.py   # Authentication & security
│   │   ├── prayer_helpers.py # Prayer management
│   │   ├── invite_helpers.py # Invite system
│   │   ├── text_archive_service.py    # Text archive operations
│   │   └── archive_first_service.py   # Archive-first workflows
│   ├── routes/              # Route modules
│   │   ├── auth_routes.py   # Authentication routes
│   │   ├── prayer_routes.py # Prayer CRUD routes
│   │   ├── admin_routes.py  # Admin panel routes
│   │   └── ...
│   └── utils/               # Utility functions
├── templates/               # Jinja2 HTML templates
├── tests/                  # Test suite
├── docs/                   # Documentation
│   ├── TEXT_ARCHIVE_DOCUMENTATION.md    # Text archive system docs
│   ├── TEXT_ARCHIVE_IMPLEMENTATION_PLAN.md # Implementation details
│   ├── DATABASE_PROTECTION.md           # Safety documentation
│   ├── UBUNTU_HOSTING_GUIDE.md           # Deployment guide
│   ├── plans/              # Feature implementation plans
│   └── guides/             # User and developer guides
├── backups/                # Database backups
├── text_archives/          # Human-readable data archives
├── AI_PROJECT_GUIDE.md     # Development documentation
└── requirements.txt        # Python dependencies
```

## 🗄️ Database Schema

### Core Models
- **User**: User profiles with religious preferences
- **Prayer**: Prayer requests with AI-generated prayers
- **PrayerMark**: Track when users pray for requests
- **Session**: Enhanced user sessions with device tracking
- **InviteToken**: Invitation system for controlled growth

### Advanced Features
- **PrayerAttribute**: Flexible prayer status system (answered, archived, flagged)
- **AuthenticationRequest**: Multi-device login approvals
- **AuthApproval**: Peer approval voting system
- **SecurityLog**: Comprehensive security audit trail
- **Text Archive Integration**: All models include `text_file_path` for archive linking

## 🛡️ Database Safety

ThyWill includes comprehensive database protection to prevent accidental data loss:

### ⚠️ Critical Safety Rules
- **Always use `./thywill start`** instead of running Python directly
- **Never run tests in production** without the CLI (now safe)
- **Create backups** before major changes: `./thywill backup`
- **Use dry-run mode** for imports: `./thywill import file.zip --dry-run`

### Protection Features
- ✅ **Automatic backups** before destructive operations
- ✅ **Environment-based protection** prevents accidental table recreation
- ✅ **Safe import/export** system with validation
- ✅ **User confirmation** for dangerous operations
- ✅ **Comprehensive error handling** with recovery suggestions

### Emergency Recovery
```bash
# List available backups
./thywill backup list

# Restore from backup
./thywill restore backup_filename.db

# Import from community export
./thywill import community_export.zip
```

See `DATABASE_PROTECTION.md` for complete safety documentation.

## 🔧 Configuration

### Environment Variables

**Required:**
- `ANTHROPIC_API_KEY` - Your Anthropic API key for prayer generation

**Optional:**
- `MULTI_DEVICE_AUTH_ENABLED` - Enable multi-device authentication (default: true)
- `REQUIRE_APPROVAL_FOR_EXISTING_USERS` - Require approval for existing users on new devices (default: true)
- `PEER_APPROVAL_COUNT` - Number of peer approvals needed (default: 2)

### Application Settings
- Session duration: 14 days
- Invite token expiration: 12 hours (configurable via `INVITE_TOKEN_EXPIRATION_HOURS`)
- Max authentication requests per hour: 3
- Failed login attempt limit: 5 (15-minute block)

## 🌐 API Endpoints

### Core Routes
- `GET /` - Main prayer feed
- `POST /prayer` - Submit new prayer request
- `POST /prayer/{id}/mark` - Mark prayer as prayed for
- `GET /admin` - Admin panel (admin users only)

### Authentication
- `GET /claim/{token}` - Claim invite and create account
- `POST /auth/request` - Request authentication on new device
- `POST /auth/approve/{request_id}` - Approve authentication request

### User Management
- `GET /profile` - User profile and preferences
- `POST /profile/religious-preference` - Update religious preferences
- `GET /invite-tree` - View community invite tree

## 🧪 Testing

Run the test suite:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
```

## 🔒 Security Features

- **Multi-device authentication** with peer approval system
- **Verification code system** for enhanced login security
- **Rate limiting** on authentication requests
- **Session validation** with device fingerprinting
- **Security audit logs** for all authentication events
- **Invite-only registration** to prevent spam
- **Content moderation** through community flagging

### Authentication Security Options

The platform supports two verification modes controlled by the `REQUIRE_VERIFICATION_CODE` environment variable:

**Standard Mode** (`REQUIRE_VERIFICATION_CODE=false`, default):
- Verification codes are displayed to both requesting and approving devices
- Users can approve requests by confirming the displayed code
- Suitable for trusted environments

**Enhanced Security Mode** (`REQUIRE_VERIFICATION_CODE=true`):
- Verification codes are only shown on the requesting device
- Approving users must enter the code from the requesting device
- Prevents unauthorized approvals even if approval device is compromised
- Recommended for high-security environments

## 📊 Admin Features

- User management and authentication audit
- Prayer moderation and flagging system
- Community statistics and growth metrics
- Religious preference analytics
- Invite tree visualization
- Bulk approval operations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Support

For support, questions, or feature requests, please open an issue on GitHub.

## 🔗 Related Documentation

- [Installation Guide](INSTALL.md) - Detailed setup instructions
- [AI Project Guide](AI_PROJECT_GUIDE.md) - Development documentation
- [Login Feature Specification](docs/LOGIN_FEATURE_SPECIFICATION.md) - Authentication system details
- [Text Archive Documentation](docs/TEXT_ARCHIVE_DOCUMENTATION.md) - Archive-first data system
- [Text Archive Implementation Plan](docs/TEXT_ARCHIVE_IMPLEMENTATION_PLAN.md) - Technical implementation details
- [Database Protection](docs/DATABASE_PROTECTION.md) - Safety documentation
- [Ubuntu Hosting Guide](docs/UBUNTU_HOSTING_GUIDE.md) - Deployment guide
- [Development Plans](docs/plans/) - Feature implementation plans

---

*Built with ❤️ for faith communities worldwide*