# ThyWill Deployment and Backup Strategy

## Overview

This guide provides a comprehensive deployment and backup strategy for ThyWill to prevent data loss and enable quick rollbacks when deployments fail.

## Key Features

- **Automated Backup System**: Multiple backup schedules (hourly, daily, weekly)
- **Safe Deployment**: Pre-deployment backups with automatic rollback on failure
- **Health Monitoring**: Built-in health checks for deployment verification
- **Data Integrity**: Checksum verification and integrity checks
- **Remote Backup Support**: Optional remote backup location
- **Easy Restoration**: Simple restore commands with verification

## File Structure

```
deployment/
├── deploy.sh                 # Main deployment script with rollback
├── backup_management.sh      # Advanced backup management
├── health_check.py          # Standalone health check utility
├── crontab_backups.txt      # Automated backup schedule
└── DEPLOYMENT_GUIDE.md      # This guide
```

## Quick Start

### 1. Initial Setup

```bash
# Make scripts executable
chmod +x deployment/deploy.sh
chmod +x deployment/backup_management.sh
chmod +x backup_database.sh
chmod +x pre_deploy_backup.sh

# Create required directories
sudo mkdir -p /home/thywill/backups/{hourly,daily,weekly}
sudo mkdir -p /home/thywill/deploy_logs
sudo mkdir -p /home/thywill/logs
sudo chown -R thywill:thywill /home/thywill/backups
sudo chown -R thywill:thywill /home/thywill/deploy_logs
sudo chown -R thywill:thywill /home/thywill/logs
```

### 2. Setup Automated Backups

```bash
# Install crontab entries for automated backups
crontab -e
# Copy contents from deployment/crontab_backups.txt
```

### 3. Test Health Check

```bash
# Test the health check endpoint
curl http://127.0.0.1:8000/health
```

## Deployment Process

### Safe Deployment with Automatic Rollback

```bash
# Navigate to your app directory
cd /home/thywill/thywill

# Pull latest changes (if using git)
git pull origin main

# Create backup before deployment
./thywill backup

# Run database migrations (if needed)
./thywill migrate

# Run safe deployment  
./deployment/deploy.sh
```

The deployment script will:
1. Create pre-deployment backup
2. Create code snapshot
3. Stop the service
4. Update dependencies
5. Start the service
6. Perform health checks
7. **Automatically rollback if health checks fail**

### Manual Deployment Steps (if needed)

```bash
# 1. Create backup
./pre_deploy_backup.sh

# 2. Stop service
sudo systemctl stop thywill

# 3. Update code (your deployment process)
git pull origin main

# 4. Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# 5. Start service
sudo systemctl start thywill

# 6. Verify health
curl http://127.0.0.1:8000/health
```

## Backup Management

### Create Backups

```bash
# Create different types of backups
./deployment/backup_management.sh hourly   # For frequent changes
./deployment/backup_management.sh daily    # For daily backups
./deployment/backup_management.sh weekly   # For long-term storage
```

### List Available Backups

```bash
./deployment/backup_management.sh list
```

### Restore from Backup

```bash
# List backups first to find the one you want
./deployment/backup_management.sh list

# Restore from specific backup
./deployment/backup_management.sh restore /home/thywill/backups/daily/thywill_daily_20231201_120000.db
```

### Cleanup Old Backups

```bash
./deployment/backup_management.sh cleanup
```

## Backup Schedule

The automated backup system creates:

- **Hourly Backups**: Every hour during business hours (9 AM - 5 PM, Mon-Fri)
- **Daily Backups**: Every day at 2 AM
- **Weekly Backups**: Every Sunday at 3 AM
- **Monthly Cleanup**: First day of each month at 4 AM
- **Integrity Checks**: Every day at 1 AM

## Rollback Procedures

### Automatic Rollback

The deployment script automatically rolls back if:
- Health check fails after deployment
- Service fails to start
- Database connectivity issues

### Manual Rollback

If you need to manually rollback:

```bash
# 1. Stop the service
sudo systemctl stop thywill

# 2. Restore from backup
./deployment/backup_management.sh restore /path/to/backup.db

# 3. If you have code changes to revert
git reset --hard PREVIOUS_COMMIT_HASH

# 4. Reinstall dependencies (if needed)
source venv/bin/activate
pip install -r requirements.txt

# 5. Start service
sudo systemctl start thywill
```

## Monitoring and Alerts

### Health Check Endpoint

The application includes a `/health` endpoint that:
- Verifies database connectivity
- Tests basic database operations
- Returns JSON status with timestamps
- Returns HTTP 200 for healthy, 500 for unhealthy

### Log Locations

- **Deployment Logs**: `/home/thywill/deploy_logs/deploy_YYYYMMDD_HHMMSS.log`
- **Backup Logs**: `/home/thywill/logs/backup.log`
- **Integrity Logs**: `/home/thywill/logs/integrity.log`
- **Application Logs**: Check systemd journal with `journalctl -u thywill`

### Monitoring Commands

```bash
# Check application status
sudo systemctl status thywill

# View recent logs
journalctl -u thywill -f

# Test health endpoint
curl -s http://127.0.0.1:8000/health | jq

# Check backup status
ls -la /home/thywill/backups/daily/ | tail -5

# Check database integrity
sqlite3 /home/thywill/thywill/thywill.db "PRAGMA integrity_check;"
```

## Disaster Recovery

### Complete System Recovery

1. **Restore Database**:
   ```bash
   ./deployment/backup_management.sh restore /path/to/latest/backup.db
   ```

2. **Restore Code** (if needed):
   ```bash
   git reset --hard LAST_KNOWN_GOOD_COMMIT
   ```

3. **Verify System**:
   ```bash
   curl http://127.0.0.1:8000/health
   ```

### Data Loss Prevention

- **Multiple Backup Types**: Hourly, daily, weekly retention
- **Checksum Verification**: All backups include SHA256 checksums
- **Integrity Checks**: Automated database integrity verification
- **Pre-deployment Backups**: Always backup before changes
- **Remote Backups**: Optional remote backup location support

## Security Considerations

- Backup files are stored with proper permissions
- Database connections are verified before restore operations
- Service stops/starts are logged for audit trails
- Failed operations trigger automatic rollbacks
- All scripts use `set -euo pipefail` for error handling

## Troubleshooting

### Deployment Fails

1. Check deployment log: `/home/thywill/deploy_logs/deploy_YYYYMMDD_HHMMSS.log`
2. Verify health endpoint: `curl http://127.0.0.1:8000/health`
3. Check service status: `sudo systemctl status thywill`
4. Review application logs: `journalctl -u thywill -n 50`

### Backup Issues

1. Check backup directory permissions
2. Verify disk space: `df -h /home/thywill/backups`
3. Test database integrity: `sqlite3 thywill.db "PRAGMA integrity_check;"`
4. Check backup logs: `tail -50 /home/thywill/logs/backup.log`

### Restore Problems

1. Verify backup file exists and is readable
2. Check backup integrity before restore
3. Ensure sufficient disk space
4. Verify service permissions

## Best Practices

1. **Always backup before deployments**
2. **Test health checks after changes**
3. **Monitor backup success regularly**
4. **Keep multiple backup types**
5. **Document any manual interventions**
6. **Test restore procedures periodically**
7. **Monitor disk space for backup storage**
8. **Set up alerts for backup failures**

## Emergency Contacts

- **System Administrator**: [Your contact info]
- **Database Administrator**: [Your contact info]
- **On-call Developer**: [Your contact info]

## Version History

- **v1.0**: Initial deployment and backup strategy
- **Date**: 2024-01-XX
- **Author**: Claude Code Assistant