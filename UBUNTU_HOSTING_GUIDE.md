# ThyWill Ubuntu Server Hosting Guide

This guide will help you deploy ThyWill on an Ubuntu server in the simplest way possible.

## Prerequisites
- Ubuntu 20.04+ server
- Root access
- Domain name pointing to your server IP (optional but recommended)

## Step 1: Update System and Install Dependencies

```bash
# Update system packages
apt update && apt upgrade -y

# Install Python, pip, nginx, and other essentials
apt install -y python3 python3-pip python3-venv nginx git ufw

# Install certbot for SSL (optional)
apt install -y certbot python3-certbot-nginx
```

## Step 2: Create Application User

```bash
# Create a dedicated user for the application
adduser thywill --disabled-password --gecos ""

# Add user to sudo group (optional, for maintenance)
usermod -aG sudo thywill
```

## Step 3: Deploy Application

```bash
# Switch to application user
su - thywill

# Clone your repository (replace with your actual repo URL)
git clone https://github.com/yourusername/thywill.git
cd thywill

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
nano .env
```

Add to `.env` file:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
MULTI_DEVICE_AUTH_ENABLED=true
REQUIRE_APPROVAL_FOR_EXISTING_USERS=true
PEER_APPROVAL_COUNT=2
REQUIRE_VERIFICATION_CODE=false
```

## Step 4: Create Systemd Service

Exit back to root user and create the service file:

```bash
exit  # Back to root

# Create systemd service file
nano /etc/systemd/system/thywill.service
```

Add this content:
```ini
[Unit]
Description=ThyWill FastAPI Application
After=network.target

[Service]
Type=simple
User=thywill
Group=thywill
WorkingDirectory=/home/thywill/thywill
Environment=PATH=/home/thywill/thywill/venv/bin
ExecStart=/home/thywill/thywill/venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

## Step 5: Configure Nginx

```bash
# Remove default nginx config
rm /etc/nginx/sites-enabled/default

# Create new config for ThyWill
nano /etc/nginx/sites-available/thywill
```

Add this content (replace `your-domain.com` with your actual domain):
```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # Serve static files directly
    location /static/ {
        alias /home/thywill/thywill/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable the site:
```bash
ln -s /etc/nginx/sites-available/thywill /etc/nginx/sites-enabled/
nginx -t  # Test configuration
```

## Step 6: Configure Firewall

```bash
# Allow SSH, HTTP, and HTTPS
ufw allow ssh
ufw allow 'Nginx Full'
ufw --force enable
```

## Step 7: Start Services

```bash
# Start and enable ThyWill service
systemctl daemon-reload
systemctl start thywill
systemctl enable thywill

# Start and enable Nginx
systemctl start nginx
systemctl enable nginx

# Check service status
systemctl status thywill
systemctl status nginx
```

## Step 8: Set Up SSL Certificate (Recommended)

```bash
# Get SSL certificate from Let's Encrypt
certbot --nginx -d your-domain.com -d www.your-domain.com

# Test auto-renewal
certbot renew --dry-run
```

## Step 9: Initial Setup

1. Visit your domain (or server IP if no domain)
2. Look for the admin invite token in the application logs:
   ```bash
   journalctl -u thywill -f
   ```
3. Find the line: `==== First-run invite token (admin): <token> ====`
4. Visit `https://your-domain.com/claim/<token>` to create admin account
5. Use admin panel to generate invite links for other users

## Management Commands

```bash
# View application logs
journalctl -u thywill -f

# Restart application
systemctl restart thywill

# Update application
su - thywill
cd thywill
git pull
source venv/bin/activate
pip install -r requirements.txt
exit
systemctl restart thywill

# Check system status
systemctl status thywill nginx
```

## Troubleshooting

**Application won't start:**
```bash
# Check logs
journalctl -u thywill -n 50

# Test manually
su - thywill
cd thywill
source venv/bin/activate
uvicorn app:app --host 127.0.0.1 --port 8000
```

**Nginx errors:**
```bash
# Check nginx logs
tail -f /var/log/nginx/error.log

# Test nginx config
nginx -t
```

**Database issues:**
The application uses SQLite by default, stored in the application directory. No additional database setup required.

## Security Notes

- The application runs on localhost (127.0.0.1) and is only accessible through Nginx
- Firewall blocks all ports except SSH and HTTP/HTTPS
- SSL certificate provides encryption
- Application runs under dedicated user account

Your ThyWill application should now be running at your domain!