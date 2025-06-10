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

# Create environment file from template
cp deployment/sample.env .env
nano .env  # Edit with your actual values
```

Edit `.env` file with your actual values:
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

# Check for existing thywill service first
systemctl status thywill
systemctl list-units --type=service | grep -i thywill

# Copy the pre-made service file (recommended)
cp /home/thywill/thywill/deployment/thywill.service /etc/systemd/system/

# OR create manually with nano if you prefer
nano /etc/systemd/system/thywill.service
```

**Important:** Choose the correct host binding based on your setup:

### Option A: With Nginx Reverse Proxy (Recommended)
```ini
[Unit]
Description=ThyWill FastAPI Application
After=network.target

[Service]
Type=exec
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

### Option B: Direct Access (No Nginx)
```ini
[Unit]
Description=ThyWill FastAPI Application
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

**Key Differences:**
- `--host 127.0.0.1`: Only accessible through localhost (requires nginx proxy)
- `--host 0.0.0.0`: Accessible from external IPs (direct access via IP:8000)

## Step 5: Configure Nginx

```bash
# Remove default nginx config
rm /etc/nginx/sites-enabled/default

# Copy the appropriate pre-made config file (recommended)
# Choose ONE of these based on your setup:

# For domain-based setup:
cp /home/thywill/thywill/deployment/nginx-domain.conf /etc/nginx/sites-available/thywill

# For IP-only setup:
cp /home/thywill/thywill/deployment/nginx-ip-only.conf /etc/nginx/sites-available/thywill

# For specific IP setup (edit the IP first):
cp /home/thywill/thywill/deployment/nginx-specific-ip.conf /etc/nginx/sites-available/thywill

# OR create manually with nano if you prefer
nano /etc/nginx/sites-available/thywill
```

**Pre-made configuration files are available in `/home/thywill/thywill/deployment/` or you can create manually:**

### Option A: With Domain Name
```nginx
server {
    listen 80;
    server_name thywill.live www.thywill.live;

    # Custom error pages for better user experience during restarts
    error_page 502 503 504 /static/502.html;
    location = /static/502.html {
        root /home/thywill/thywill;
        internal;
    }

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
        
        # Improve handling during service restarts
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }

    # Serve static files directly
    location /static/ {
        alias /home/thywill/thywill/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Serve favicon directly to prevent 404s
    location = /favicon.ico {
        alias /home/thywill/thywill/static/favicon.ico;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
}
```

### Option B: IP Address Only (No Domain)
```nginx
server {
    listen 80 default_server;
    server_name _;  # Catches any server name/IP

    # Custom error pages for better user experience during restarts
    error_page 502 503 504 /static/502.html;
    location = /static/502.html {
        root /home/thywill/thywill;
        internal;
    }

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
        
        # Improve handling during service restarts
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }

    # Serve static files directly
    location /static/ {
        alias /home/thywill/thywill/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Serve favicon directly to prevent 404s
    location = /favicon.ico {
        alias /home/thywill/thywill/static/favicon.ico;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
}
```

### Option C: Specific IP Address
```nginx
server {
    listen 80;
    server_name 192.168.1.100;  # Replace with your actual server IP

    # Custom error pages for better user experience during restarts
    error_page 502 503 504 /static/502.html;
    location = /static/502.html {
        root /home/thywill/thywill;
        internal;
    }

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
        
        # Improve handling during service restarts
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
    }

    # Serve static files directly
    location /static/ {
        alias /home/thywill/thywill/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Serve favicon directly to prevent 404s
    location = /favicon.ico {
        alias /home/thywill/thywill/static/favicon.ico;
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }
}
```

Enable the site:
```bash
ln -s /etc/nginx/sites-available/thywill /etc/nginx/sites-enabled/
nginx -t  # Test configuration
```

## Step 6: Configure Firewall

### Option A: With Nginx (Recommended)
```bash
# Allow SSH, HTTP, and HTTPS
ufw allow ssh
ufw allow 'Nginx Full'
ufw --force enable
```

### Option B: Direct Access (No Nginx)
```bash
# Allow SSH and application port
ufw allow ssh
ufw allow 8000
ufw --force enable
```

**Note:** If using direct access, you'll access the site at `http://your-server-ip:8000`

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

## Step 8: Set Up SSL Certificate (Optional - Domain Required)

**Only if you have a domain name and used Option A in nginx config:**

```bash
# Get SSL certificate from Let's Encrypt
certbot --nginx -d thywill.live -d www.thywill.live

# Test auto-renewal
certbot renew --dry-run
```

**Note:** SSL certificates require a domain name. If using IP-only access (Options B or C), skip this step.

## Step 9: Initial Setup

1. Visit your domain (or server IP if no domain)
2. Look for the admin invite token in the application logs:
   ```bash
   journalctl -u thywill -f
   ```
3. Find the line: `==== First-run invite token (admin): <token> ====`
4. Visit `https://thywill.live/claim/<token>` to create admin account
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

## Deployment Files

All configuration files are pre-made and available in the `/home/thywill/thywill/deployment/` directory:

- `thywill.service` - Systemd service configuration
- `nginx-domain.conf` - Nginx config for domain-based setup
- `nginx-ip-only.conf` - Nginx config for IP-only access
- `nginx-specific-ip.conf` - Nginx config for specific IP
- `sample.env` - Environment variables template
- `README.md` - Quick reference for using these files

## Improved Error Handling During Restarts

The nginx configurations above include several improvements to handle service restarts gracefully:

### Custom 502 Error Page
- **Location**: `/home/thywill/thywill/static/502.html`
- **Features**: 
  - Auto-refreshes every 5 seconds during maintenance
  - Branded design matching your application
  - Clear messaging about temporary unavailability
  - "Try Again" button for manual refresh

### Nginx Configuration Benefits
- **Faster timeouts**: Reduced proxy timeouts prevent long waits
- **Error page coverage**: Handles 502, 503, and 504 errors
- **Static file serving**: Error page served directly by nginx (no backend required)

### Graceful Restart Procedure
For smoother restarts with minimal downtime:

```bash
# 1. Update your application code
su - thywill
cd thywill
git pull
source venv/bin/activate
pip install -r requirements.txt
exit

# 2. Restart service (users will see the custom error page briefly)
systemctl restart thywill

# 3. Verify the service is running
systemctl status thywill
curl -f http://localhost:8000/ || echo "Service not ready yet"
```

### Testing the Error Page
To test the error page without affecting users:

```bash
# Temporarily stop the service
systemctl stop thywill

# Visit your site - you should see the custom 502 page
# Start the service back up
systemctl start thywill
```

## Troubleshooting

**Port already in use:**
```bash
# Check what's using port 8000
sudo lsof -i :8000

# Kill existing uvicorn processes
sudo fuser -k 8000/tcp

# Or kill specific process ID
sudo kill -9 <process_id>
```

**Application won't start:**
```bash
# Check logs
journalctl -u thywill -n 50

# Check if service exists and is running
systemctl status thywill

# Test manually (choose correct host based on your setup)
su - thywill
cd thywill
source venv/bin/activate

# For nginx setup:
uvicorn app:app --host 127.0.0.1 --port 8000

# For direct access:
uvicorn app:app --host 0.0.0.0 --port 8000
```

**Systemd service conflicts:**
```bash
# Stop existing service
sudo systemctl stop thywill

# Disable auto-start
sudo systemctl disable thywill

# Check for multiple service files
ls /etc/systemd/system/thywill*

# Reload systemd after changes
sudo systemctl daemon-reload
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