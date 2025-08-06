# Ubuntu SMTP Setup Guide

Simple guide to set up email sending on Ubuntu production servers.

## Quick Start

1. **Test what's already available:**
   ```bash
   python tools/test_email.py --test-all
   ```

2. **Interactive setup (easiest):**
   ```bash
   python tools/test_email.py --config
   ```

## Option 1: SendGrid (Recommended)

**Why:** Most reliable, free tier (100 emails/day), works everywhere.

1. Sign up at [sendgrid.com](https://sendgrid.com)
2. Create API key in dashboard
3. Test:
   ```bash
   python tools/test_email.py --provider sendgrid --to your-email@example.com
   # Username: apikey
   # Password: your-sendgrid-api-key
   ```

## Option 2: Gmail App Password

**Why:** Easy if you have Gmail/Google Workspace.

1. Enable 2FA on your Google account
2. Create App Password: Google Account → Security → App passwords
3. Test:
   ```bash
   python tools/test_email.py --provider gmail --to your-email@example.com
   # Username: your-gmail@gmail.com  
   # Password: your-app-password
   ```

## Option 3: Local Postfix

**Why:** No external dependencies, but requires proper server setup.

```bash
# Install
sudo apt update && sudo apt install postfix mailutils

# Choose "Internet Site" when prompted
# Set hostname to your domain

# Test
python tools/test_email.py --provider local --to your-email@example.com
```

## Common Issues

**Port 25 blocked (most cloud providers):**
- Use external SMTP (SendGrid/Gmail) instead of local

**Firewall blocking:**
```bash
sudo ufw allow 587
```

**Wrong hostname:**
```bash
sudo hostnamectl set-hostname yourdomain.com
```

## Add to .env File

After testing works, add to your `.env`:
```bash
# The test script will output these for you
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-api-key
SMTP_FROM_EMAIL=noreply@yourdomain.com
```

## Recommendation

1. Try SendGrid first (most reliable)
2. Use Gmail if you have Google account
3. Only use local Postfix if you have proper domain/DNS setup