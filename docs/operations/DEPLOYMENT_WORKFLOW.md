# ThyWill Production Deployment Workflow

## **Complete Deployment Process**

### **Step 1: Pull Latest Code**
```bash
cd /home/thywill/thywill
git pull origin main  # Get latest code
```

### **Step 2: Run Safe Deployment**
```bash
thywill deploy  # This does everything automatically with rollback protection
```

## **What Happens Behind the Scenes**

The `thywill deploy` command runs through these steps:

### **1. Pre-Deployment Backup**
- Creates timestamped database backup: `thywill_backup_YYYYMMDD_HHMMSS.db`
- Verifies backup integrity (file size check)
- **STOPS deployment if backup fails**

### **2. Code Snapshot**
- Creates complete code backup in `/home/thywill/backups/code_YYYYMMDD_HHMMSS/`
- Excludes git files, cache files
- This allows rollback to exact previous state

### **3. Service Management**
```bash
sudo systemctl stop thywill    # Stop application safely
```

### **4. Dependency Updates**
```bash
source venv/bin/activate       # Activate virtual environment
pip install -r requirements.txt  # Update dependencies
```

### **5. Database Migrations** (if any)
- Runs any pending database migrations
- Currently placeholder - add your migration commands here

### **6. Service Restart**
```bash
sudo systemctl start thywill   # Start application
```

### **7. Health Check & Auto-Rollback**
- Tests health endpoint: `http://127.0.0.1:8000/health`
- Waits up to 60 seconds for service to respond
- **If health check fails:**
  - Automatically stops failed service
  - Restores database from backup
  - Restores code from snapshot
  - Reinstalls previous dependencies
  - Restarts service with previous version
  - Verifies rollback worked

### **8. Success Cleanup**
- Removes old deployment logs (keeps last 10)
- Removes old code backups (keeps last 30 days)
- Logs deployment success

## **Manual Deployment Process (if needed)**

If you prefer manual control or need to debug:

```bash
# 1. Create backup first
thywill backup daily

# 2. Stop service
sudo systemctl stop thywill

# 3. Update dependencies
cd /home/thywill/thywill
source venv/bin/activate
pip install -r requirements.txt

# 4. Run any database migrations (if needed)
# python migrate.py  # Add your migration commands here

# 5. Start service
sudo systemctl start thywill

# 6. Check health
thywill health

# 7. View logs if there are issues
thywill logs 50
```

## **Rollback Procedures**

### **Automatic Rollback (Recommended)**

The deployment script automatically rolls back if health checks fail, but you can also trigger manual rollbacks:

```bash
# Quick rollback to most recent backup
thywill rollback

# This will:
# 1. Stop the current service
# 2. Find the most recent backup
# 3. Restore database
# 4. Restore code (if needed)
# 5. Restart service
# 6. Verify rollback success
```

### **Rollback to Specific Backup**

```bash
# 1. List all available backups
thywill list

# Output shows:
# Hourly backups (last 48 hours):
# -rw-r--r-- 1 thywill thywill 2.1M Dec  1 14:30 thywill_hourly_20231201_143000.db
# 
# Daily backups (last 30 days):
# -rw-r--r-- 1 thywill thywill 2.0M Dec  1 02:00 thywill_daily_20231201_020000.db
# -rw-r--r-- 1 thywill thywill 1.9M Nov 30 02:00 thywill_daily_20231130_020000.db
#
# Weekly backups (last 12 weeks):
# -rw-r--r-- 1 thywill thywill 1.8M Nov 26 03:00 thywill_weekly_20231126_030000.db

# 2. Rollback to specific backup
thywill rollback /home/thywill/backups/daily/thywill_daily_20231201_020000.db
```

### **Manual Rollback Process**

If you need complete manual control:

```bash
# 1. Stop the service
sudo systemctl stop thywill

# 2. Verify backup integrity first
thywill verify /path/to/backup.db

# 3. Backup current state (just in case)
cp /home/thywill/thywill/thywill.db /home/thywill/backups/pre_rollback_$(date +%Y%m%d_%H%M%S).db

# 4. Restore database
cp /path/to/backup.db /home/thywill/thywill/thywill.db

# 5. If rolling back code changes, use git
cd /home/thywill/thywill
git log --oneline -10  # See recent commits
git reset --hard COMMIT_HASH  # Rollback to specific commit

# 6. Reinstall dependencies (if requirements.txt changed)
source venv/bin/activate
pip install -r requirements.txt

# 7. Start service
sudo systemctl start thywill

# 8. Verify rollback success
thywill health
thywill status
```

### **Emergency Rollback (Complete System Recovery)**

If everything is broken and you need to restore from scratch:

```bash
# 1. Stop service
sudo systemctl stop thywill

# 2. Find the best backup to restore from
thywill list

# 3. Restore database from known good backup
thywill restore /home/thywill/backups/daily/thywill_daily_YYYYMMDD_020000.db
# This command handles all verification and restoration

# 4. If code is also corrupted, restore from git
cd /home/thywill/thywill
git status  # Check current state
git reset --hard origin/main  # Reset to last known good state
# OR
git reset --hard LAST_KNOWN_GOOD_COMMIT

# 5. Reinstall environment
source venv/bin/activate
pip install -r requirements.txt

# 6. Start service
sudo systemctl start thywill

# 7. Verify everything works
thywill health
curl http://your-domain.com  # Test from outside
```

## **Rollback Decision Matrix**

| Situation | Recommended Action |
|-----------|-------------------|
| Deployment failed, auto-rollback triggered | Check logs, investigate issue |
| App running but behaving strangely | `thywill rollback` (quick) |
| Database corruption detected | `thywill restore /path/to/backup.db` |
| Code changes broke functionality | Manual git rollback + restart |
| Complete system failure | Emergency rollback procedure |
| Need to go back several versions | Rollback to specific old backup |

## **Monitoring During Deployment**

### **Real-time Monitoring**

```bash
# Watch deployment logs in real-time (in separate terminal)
tail -f /home/thywill/deploy_logs/deploy_$(date +%Y%m%d)*.log

# Monitor service status
watch -n 2 'thywill status'

# Check application logs
thywill logs -f  # Follow logs in real-time
```

### **Health Checks**

```bash
# Basic health check
thywill health

# Manual health verification
curl -s http://127.0.0.1:8000/health | jq  # Pretty JSON output
curl -s http://your-domain.com/health | jq  # External check

# Service-level checks
sudo systemctl status thywill
journalctl -u thywill -f  # Follow service logs
```

### **Performance Verification**

```bash
# Check response times
time curl -s http://127.0.0.1:8000/ > /dev/null

# Check database performance
sqlite3 /home/thywill/thywill/thywill.db "PRAGMA integrity_check;"

# Check disk space
df -h /home/thywill/

# Check memory usage
free -h
ps aux | grep thywill
```

## **Backup Verification Before Rollback**

Always verify backup integrity before rolling back:

```bash
# Verify backup file integrity
thywill verify /path/to/backup.db

# Manual verification steps:
# 1. Check file size is reasonable
ls -lah /path/to/backup.db

# 2. Verify database integrity
sqlite3 /path/to/backup.db "PRAGMA integrity_check;"

# 3. Check backup timestamp makes sense
stat /path/to/backup.db

# 4. Verify checksum (if available)
sha256sum -c /path/to/backup.db.sha256
```

## **Post-Rollback Verification**

After any rollback, verify these items:

```bash
# 1. Service is running
thywill status

# 2. Health endpoint responds
thywill health

# 3. Application loads properly
curl -s http://your-domain.com | grep -i "thywill\|prayer"

# 4. Database is accessible
sqlite3 /home/thywill/thywill/thywill.db "SELECT COUNT(*) FROM users;"

# 5. No error logs
thywill logs 20 | grep -i error

# 6. Check recent activity works
# (test login, submit prayer, etc.)
```

## **Rollback Troubleshooting**

### **Rollback Failed**

If rollback itself fails:

```bash
# 1. Check what went wrong
thywill logs 50

# 2. Manual intervention
sudo systemctl stop thywill

# 3. Manually restore database
cp /home/thywill/backups/daily/thywill_daily_YYYYMMDD_020000.db /home/thywill/thywill/thywill.db

# 4. Check file permissions
sudo chown thywill:thywill /home/thywill/thywill/thywill.db
chmod 644 /home/thywill/thywill/thywill.db

# 5. Try starting service
sudo systemctl start thywill
```

### **Service Won't Start After Rollback**

```bash
# 1. Check service logs
journalctl -u thywill -n 50

# 2. Check file permissions
ls -la /home/thywill/thywill/

# 3. Check virtual environment
cd /home/thywill/thywill
source venv/bin/activate
python -c "import app"  # Test if app loads

# 4. Check database file
sqlite3 /home/thywill/thywill/thywill.db ".schema" | head -5

# 5. Manual restart
cd /home/thywill/thywill
source venv/bin/activate
uvicorn app:app --host 127.0.0.1 --port 8000  # Test manually
```

## **Prevention Best Practices**

1. **Always backup before deployments**: `thywill backup daily`
2. **Test in development first**: Never deploy untested changes
3. **Use feature flags**: Deploy code disabled, enable after verification
4. **Monitor deployments**: Watch logs during deployment
5. **Have rollback plan**: Know which backup to restore to
6. **Document changes**: Note what changed in each deployment
7. **Test rollbacks**: Periodically test rollback procedures
8. **Keep multiple backup types**: Hourly, daily, weekly backups

## **Emergency Contacts & Resources**

- **Deployment Logs**: `/home/thywill/deploy_logs/`
- **Backup Directory**: `/home/thywill/backups/`
- **Service Logs**: `journalctl -u thywill`
- **Health Endpoint**: `http://127.0.0.1:8000/health`
- **All Commands**: `thywill help`

## **Quick Reference Commands**

```bash
# Deployment
thywill deploy                    # Safe deployment with auto-rollback
thywill health                    # Check application health
thywill status                    # Show system status

# Rollback
thywill rollback                  # Quick rollback to latest backup
thywill list                      # List all available backups
thywill rollback /path/to/backup  # Rollback to specific backup

# Monitoring
thywill logs 50                   # Show recent logs
tail -f /home/thywill/deploy_logs/deploy_*.log  # Watch deployment

# Emergency
sudo systemctl stop thywill      # Emergency stop
sudo systemctl start thywill     # Emergency start
thywill restore /path/to/backup  # Emergency restore
```

Remember: **When in doubt, rollback first, investigate later**. It's better to have a working application with old code than a broken application with new code.