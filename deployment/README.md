# ThyWill Deployment Files

This directory contains all the deployment, backup, and management tools for ThyWill.

## ThyWill CLI - Git-Style Command Tool

**Main CLI**: `../thywill` - Complete command-line utility for all operations

### Quick Start
```bash
# Make executable
chmod +x ../thywill

# Initialize environment
../thywill init

# View all commands
../thywill help

# Daily operations
../thywill health
../thywill backup daily
../thywill deploy
```

## Deployment & Backup Scripts

## Files Included

### Service Configuration
- `thywill.service` - Systemd service file for the application

### Nginx Configurations
- `nginx-domain.conf` - For deployment with a domain name
- `nginx-ip-only.conf` - For IP-only access (any IP)
- `nginx-specific-ip.conf` - For specific IP address access

### Environment Configuration
- `sample.env` - Sample environment variables file

## Usage

### 1. Copy systemd service
```bash
sudo cp thywill.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 2. Copy nginx configuration
Choose the appropriate nginx config for your setup:

```bash
# For domain-based setup
sudo cp nginx-domain.conf /etc/nginx/sites-available/thywill

# For IP-only setup
sudo cp nginx-ip-only.conf /etc/nginx/sites-available/thywill

# For specific IP setup (edit the IP address first)
sudo cp nginx-specific-ip.conf /etc/nginx/sites-available/thywill
```

Then enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/thywill /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 3. Create environment file
```bash
cp sample.env /home/thywill/thywill/.env
# Edit .env with your actual values
```

### 4. Set proper permissions
```bash
# Make directories accessible to nginx
sudo chmod 755 /home/thywill
sudo chmod 755 /home/thywill/thywill
sudo chmod 755 /home/thywill/thywill/static
sudo chmod 644 /home/thywill/thywill/static/*
```

## Notes

- Remember to update the domain name in `nginx-domain.conf` 
- Remember to update the IP address in `nginx-specific-ip.conf`
- All configurations include the favicon fix to prevent 404 errors
- All configurations include the custom 502 error page for better UX during restarts