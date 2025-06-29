# ThyWill System Administration Guide

## Virtual Environment Management

### The Problem
Many commands fail because the Python virtual environment isn't activated. This guide shows how ThyWill's CLI eliminates this pain point.

### Built-in Solutions

#### 1. Use the ThyWill CLI (Recommended)
The `thywill` CLI automatically handles virtual environment activation:

```bash
# Instead of manual venv activation + uvicorn
source venv/bin/activate
uvicorn app:app --reload

# Use this - handles venv automatically
./thywill start
```

**Key CLI Commands:**
```bash
./thywill start [port]    # Auto-creates venv, installs deps, starts server
./thywill test           # Safe test execution with venv handling
./thywill deploy         # Production deployment
./thywill setup          # Complete environment setup
./thywill install        # Make CLI globally available
```

#### 2. Auto-Detection and Creation
The CLI automatically:
- Detects if `venv/` exists
- Creates virtual environment if missing
- Installs dependencies from `requirements.txt`
- Activates environment before running commands

### Sysadmin Improvements

#### 1. Global CLI Installation
Make `thywill` available from anywhere:
```bash
./thywill install
```

Then use `thywill start` instead of `./thywill start` from any directory.

#### 2. Shell Auto-Activation
Add to `~/.bashrc` or `~/.zshrc` for automatic venv activation:

```bash
# Auto-activate ThyWill venv when in project directory
cd() {
    builtin cd "$@"
    if [[ -f "thywill" && -d "venv" ]]; then
        source venv/bin/activate
        echo "✅ ThyWill virtual environment activated"
    fi
}
```

#### 3. Useful Aliases
Add to your shell configuration:

```bash
# ThyWill shortcuts
alias tw='./thywill'
alias tws='./thywill start'
alias twt='./thywill test'
alias twd='./thywill deploy'
alias twb='./thywill backup'
alias twst='./thywill status'
```

#### 4. Environment Variables
Create `.env` file in project root:
```bash
# Required
ANTHROPIC_API_KEY=your_claude_api_key

# Optional - Multi-device Authentication
MULTI_DEVICE_AUTH_ENABLED=true
REQUIRE_APPROVAL_FOR_EXISTING_USERS=true  
PEER_APPROVAL_COUNT=2
JWT_SECRET=your_jwt_secret_for_tokens

# Optional - Payment Configuration
PAYPAL_USERNAME=your_paypal_username
VENMO_HANDLE=your_venmo_handle

# Optional - Text Archive Settings
TEXT_ARCHIVE_ENABLED=true
TEXT_ARCHIVE_BASE_DIR=./text_archives
```

## Development Workflow

### Quick Start (New Environment)
```bash
# Clone and setup everything automatically
git clone <repo>
cd thywill
./thywill setup    # Complete Ubuntu environment setup
./thywill start    # Start development server
```

### Daily Development
```bash
# Start development server
./thywill start

# Run tests safely
./thywill test

# Check application status
./thywill status

# Create database backup
./thywill backup
```

### Production Deployment
```bash
# Deploy with automatic rollback on failure
./thywill deploy

# Check deployment status
./thywill status

# Monitor logs
journalctl -u thywill -f
```

## Troubleshooting

### Common Issues

#### "Command not found" Errors
**Problem:** Running Python commands without venv activation
**Solution:** Always use `./thywill start` instead of direct `uvicorn` commands

#### "Module not found" Errors  
**Problem:** Dependencies not installed in virtual environment
**Solution:** The CLI handles this automatically:
```bash
./thywill start  # Auto-installs missing dependencies
```

#### Permission Errors
**Problem:** Database or backup directory permissions
**Solution:** 
```bash
# Development
./thywill start  # Uses local project directories

# Production  
sudo chown -R thywill:thywill /home/thywill/thywill/
```

#### Database Issues
**Problem:** Database corruption or missing tables
**Solution:**
```bash
./thywill backup          # Create backup first
./thywill migrate         # Run database migrations
./thywill db init         # Initialize database if needed
```

### Environment Verification
Check your setup:
```bash
# Verify CLI is working
./thywill --help

# Check database status
./thywill status

# Verify all dependencies
./thywill test --dry-run
```

## Advanced Administration

### Automated Backups
Set up cron job for regular backups:
```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /home/thywill/thywill/thywill backup
```

### Log Management
Monitor application logs:
```bash
# Development logs
./thywill start  # Logs to console

# Production logs  
journalctl -u thywill -f         # Follow logs
journalctl -u thywill --since today  # Today's logs
```

### Health Monitoring
Check application health:
```bash
# Application status
./thywill status

# Database integrity
sqlite3 thywill.db "PRAGMA integrity_check;"

# Disk space for backups
df -h /home/thywill/backups/
```

### Security Best Practices

#### Environment Variables
- Never commit `.env` files to version control
- Use strong JWT secrets in production
- Rotate API keys regularly

#### Database Security  
- Regular backups with `./thywill backup`
- Monitor for unusual access patterns
- Keep SQLite database files with restricted permissions

#### System Security
- Run application as dedicated `thywill` user
- Use systemd service for process management
- Monitor logs for security events

## Migration Guide

### From Manual venv to CLI
**Old workflow:**
```bash
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**New workflow:**
```bash
./thywill start
```

### From Development to Production
```bash
# Development
./thywill start

# Production setup
./thywill setup --production
./thywill deploy
```

## Best Practices

### Development
1. **Always use CLI commands** instead of manual Python execution
2. **Run tests before commits** with `./thywill test`
3. **Create backups before major changes** with `./thywill backup`
4. **Use global installation** with `./thywill install` for convenience

### Production
1. **Use systemd service** for process management
2. **Monitor logs regularly** with `journalctl`
3. **Automate backups** with cron jobs
4. **Test deployments** with `./thywill deploy --dry-run` first

### Security
1. **Never commit secrets** to version control
2. **Use environment variables** for configuration
3. **Monitor authentication logs** for unusual activity
4. **Keep dependencies updated** regularly

---

## Quick Reference

### Essential Commands
```bash
./thywill start           # Start development server
./thywill test           # Run test suite
./thywill deploy         # Deploy to production  
./thywill backup         # Create database backup
./thywill status         # Check application status
./thywill setup          # Environment setup
./thywill install        # Global CLI installation
```

### Files to Know
- `thywill` - Main CLI script
- `app.py` - FastAPI application
- `models.py` - Database models
- `requirements.txt` - Python dependencies
- `.env` - Environment configuration
- `thywill.db` - SQLite database
- `deployment/` - Production deployment files

This guide eliminates the "forgot to activate venv" problem by leveraging ThyWill's built-in automation while providing additional sysadmin improvements for power users.