# ThyWill

A community-driven prayer platform that creates a safe, faith-based environment for sharing prayer requests and supporting one another spiritually.

![ThyWill Logo](logo.svg)

## ✨ Features

- **🙏 Prayer Community**: Submit prayer requests and pray for others in a supportive environment
- **🤖 AI-Enhanced Prayer**: Generate proper prayers using Anthropic's Claude AI
- **📧 Invite-Only System**: Controlled growth through invitation tokens to maintain community quality
- **🔐 Multi-Device Authentication**: Secure peer-approval system for accessing accounts from new devices
- **⛪ Religious Preferences**: Support for different faith traditions (Christian, interfaith, etc.)
- **📋 Prayer Lifecycle**: Track answered prayers, archive requests, and celebrate testimonies
- **🛡️ Community Moderation**: Flag inappropriate content and maintain a respectful environment
- **🌳 Invite Tree System**: Track community growth and relationships

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
   
   Create a `.env` file in the project root:
   ```env
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   
   # Optional configuration
   MULTI_DEVICE_AUTH_ENABLED=true
   REQUIRE_APPROVAL_FOR_EXISTING_USERS=true
   PEER_APPROVAL_COUNT=2
   ```

5. **Run the application**
   ```bash
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Initial setup**
   - Look for the admin invite token in console output: `==== First-run invite token (admin): <token> ====`
   - Visit `http://localhost:8000/claim/<token>` to create the admin account
   - Use the admin panel to generate invite links for other users

## 🏗️ Project Structure

```
thywill/
├── app.py                      # Main FastAPI application
├── models.py                   # Database models and schema
├── app_helpers/               # Modular business logic
│   ├── services/             # Core service modules
│   │   ├── auth_helpers.py   # Authentication & security
│   │   ├── prayer_helpers.py # Prayer management
│   │   └── invite_helpers.py # Invite system
│   ├── routes/              # Route modules
│   │   ├── auth_routes.py   # Authentication routes
│   │   ├── prayer_routes.py # Prayer CRUD routes
│   │   ├── admin_routes.py  # Admin panel routes
│   │   └── ...
│   └── utils/               # Utility functions
├── templates/               # Jinja2 HTML templates
├── tests/                  # Test suite
├── docs/                   # Documentation
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
- Invite token expiration: 12 hours
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
- **Rate limiting** on authentication requests
- **Session validation** with device fingerprinting
- **Security audit logs** for all authentication events
- **Invite-only registration** to prevent spam
- **Content moderation** through community flagging

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
- [Development Plans](docs/plans/) - Feature implementation plans

---

*Built with ❤️ for faith communities worldwide*