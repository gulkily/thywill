# ThyWill Installation Guide

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Installation Steps

### 1. Clone the Repository
```bash
git clone <repository-url>
cd thywill
```

### 2. Create Virtual Environment (Recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the project root:
```bash
cp .env.example .env
```

Edit the `.env` file and add your Anthropic API key:
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

Optional configuration variables are documented in `.env.example`.

### 5. Initialize Database
The SQLite database will be created automatically when you first run the application.

### 6. Run the Application
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## First Time Setup

1. When you first start the application, it will generate an admin invite token
2. Look for the token in the console output: `==== First-run invite token (admin): <token> ====`
3. Visit `http://localhost:8000/claim/<token>` to create the admin account
4. Use the admin account to generate invite links for other users

## Configuration

- **Session Duration**: Sessions last 14 days by default
- **Invite Token Expiration**: Invite tokens expire after 12 hours
- **Database**: Uses SQLite (`thywill.db`) by default

## Optional Files

- `prompts.yaml` - Daily prompts (format: `YYYY-MM-DD: "prompt text"`)

## Accessing the Application

- Main feed: `http://localhost:8000/`
- Admin panel: `http://localhost:8000/admin` (admin users only)
- Activity feed: `http://localhost:8000/activity`

## Troubleshooting

### Common Issues

1. **Missing Anthropic API Key**: Ensure `ANTHROPIC_API_KEY` is set in your `.env` file
2. **Port Already in Use**: Change the port number in the uvicorn command
3. **Database Errors**: Delete `thywill.db` to reset the database (will lose all data)

### Environment Variables

Required:
- `ANTHROPIC_API_KEY` - Your Anthropic API key for prayer generation

Optional:
- `MULTI_DEVICE_AUTH_ENABLED` - Enable/disable multi-device authentication (default: true)
- `REQUIRE_APPROVAL_FOR_EXISTING_USERS` - Require approval for existing users on new devices (default: true)  
- `PEER_APPROVAL_COUNT` - Number of peer approvals needed for authentication (default: 2)
- `REQUIRE_VERIFICATION_CODE` - Enhanced security mode for verification codes (default: false)

See `.env.example` for detailed descriptions of all configuration options.

### Development Mode

For development with auto-reload:
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Production Deployment

#### Option 1: Manual Process (Development/Testing)
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

#### Option 2: Systemd Service (Recommended for Production)

1. **Check for existing service:**
```bash
sudo systemctl status thywill
sudo systemctl list-units --type=service | grep -i thywill
```

2. **Create systemd service file:**
```bash
sudo nano /etc/systemd/system/thywill.service
```

3. **Service file content:**
```ini
[Unit]
Description=ThyWill Prayer Platform
After=network.target

[Service]
Type=exec
User=thywill
Group=thywill
WorkingDirectory=/home/thywill/thywill
Environment=PATH=/home/thywill/thywill/venv/bin
ExecStart=/home/thywill/thywill/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

4. **Enable and start the service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable thywill
sudo systemctl start thywill
```

5. **Check service status:**
```bash
sudo systemctl status thywill
```

6. **Service management commands:**
```bash
# Start the service
sudo systemctl start thywill

# Stop the service
sudo systemctl stop thywill

# Restart the service
sudo systemctl restart thywill

# View logs
sudo journalctl -u thywill -f
```

#### Important Notes for Production:
- **Host Binding**: Always use `--host 0.0.0.0` for external access, not `127.0.0.1`
- **Port Conflicts**: If port 8000 is in use, check for existing services with `sudo lsof -i :8000`
- **Firewall**: Ensure port 8000 is open: `sudo ufw allow 8000`
- **SSL/Domain**: For domains, set up reverse proxy (nginx) and SSL certificates
- **Database**: Consider PostgreSQL or MySQL for production
- **Monitoring**: Set up proper logging and monitoring
- **Environment**: Ensure `.env` file has production-appropriate settings

#### Troubleshooting Common Issues:
- **Port already in use**: Kill existing processes with `sudo fuser -k 8000/tcp`
- **Permission denied**: Check user permissions and file ownership
- **Service won't start**: Check logs with `sudo journalctl -u thywill`
- **External access blocked**: Verify firewall and cloud provider security groups