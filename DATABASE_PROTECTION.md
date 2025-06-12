# Database Protection System

## 🚨 CRITICAL ISSUE RESOLVED

**Problem**: The previous codebase had `SQLModel.metadata.create_all(engine)` running on every import of `models.py`, which **wiped and recreated the production database** every time tests were run or the app was restarted.

**Root Cause**: 
- `models.py` line 296 called `SQLModel.metadata.create_all(engine)` unconditionally
- `migrate_to_attributes.py` also called this function during tests
- Running tests imported these modules, triggering database recreation

## ✅ Protection Measures Implemented

### 1. Safe Database Initialization
- Database tables are only created when `INIT_DATABASE=true` environment variable is set
- Import of `models.py` no longer automatically recreates tables
- Backup system activated before any schema changes

### 2. Backup System
```bash
# Create backup
python backup_database.py create

# List backups
python backup_database.py list

# Restore from backup
python backup_database.py restore thywill_backup_20241206_123456.db
```

### 3. Safe Startup Scripts
```bash
# Safe application startup (recommended)
python safe_start.py

# Initialize database (first time only)
python init_database.py

# Manual initialization (with protection)
INIT_DATABASE=true python -c "import models"
```

### 4. Protected Migration Scripts
- Migration scripts now create only required tables
- No longer call `create_all()` which recreates everything
- Use table inspection to check what exists

## 🛡️ Safe Operating Procedures

### Running Tests Safely
```bash
# Tests now use in-memory SQLite and won't affect production
pytest
```

### Updating Code Safely
```bash
# 1. Create backup first
python backup_database.py create

# 2. Pull code changes
git pull

# 3. Run tests (safe now)
pytest

# 4. Restart server (safe now)
python safe_start.py
```

### Database Migrations
```bash
# 1. Always backup first
python backup_database.py create

# 2. Run migration with protection
python migrate_to_attributes.py

# 3. Verify data integrity
python -c "from models import *; print('Database accessible')"
```

## 🔍 Verification

### Check Database Size
```bash
ls -la thywill.db
# Should show substantial size (not empty)
```

### Verify Tables Exist
```bash
sqlite3 thywill.db ".tables"
# Should list all your tables
```

### Check Record Counts
```bash
sqlite3 thywill.db "SELECT COUNT(*) FROM prayer;"
sqlite3 thywill.db "SELECT COUNT(*) FROM user;"
```

## ⚠️ Emergency Recovery

If data is lost again:

1. **Check for backups**:
   ```bash
   python backup_database.py list
   ```

2. **Restore latest backup**:
   ```bash
   python backup_database.py restore <latest_backup_filename>
   ```

3. **Check recent git history** for any dangerous commits:
   ```bash
   git log --oneline -10
   ```

## 🎯 Prevention Rules

### ✅ DO
- Always use `python backup_database.py create` before major changes
- Use `python safe_start.py` to start the application
- Set `INIT_DATABASE=true` only when you actually want to initialize
- Run tests regularly (they're now safe)

### ❌ DON'T
- Never run `SQLModel.metadata.create_all(engine)` on production engine
- Don't directly call migration scripts without backups
- Don't set `INIT_DATABASE=true` in production unless needed
- Don't ignore database size changes

## 🔧 Environment Variables

- `ENVIRONMENT=production` - Enables production protections
- `INIT_DATABASE=true` - Allows table creation (use carefully)
- `FORCE_YES=true` - Skips confirmation prompts (automation only)

This protection system ensures your production data is safe while maintaining development flexibility.