# Future Upgrade Strategy: Text Archive-Based Approach

## What Gets Preserved ✅

### Core Community Data
- **Users**: Display names, registration dates, invite relationships
- **Prayers**: Full text, generated prayers, submission timestamps
- **Prayer Marks**: Who prayed for what, when
- **Prayer Attributes**: Archived, answered, flagged status
- **Activity Logs**: Complete prayer interaction history
- **Invite Tree**: User invitation relationships

### Archive Metadata
- **File Paths**: Links between database and archive files
- **Timestamps**: Accurate creation/modification times
- **Relationships**: User-prayer, user-mark associations

## What Gets Lost ⚠️

### Session & Authentication Data
- **Active Sessions**: Users need to re-login after import
- **Authentication Requests**: Multi-device auth pending requests
- **Security Logs**: Auth attempt history
- **Device Information**: Registered device fingerprints

### System Configuration
- **Feature Flags**: Environment-specific settings
- **Admin Roles**: User permission assignments
- **Invite Tokens**: Active invitation links
- **Rate Limiting State**: Current rate limit counters

### Database Metadata
- **Auto-increment Counters**: Sequence numbers reset
- **Database Indexes**: Need recreation (but CLI handles this)
- **Constraints**: Need recreation during schema setup
- **Triggers**: Custom database triggers

### Application State
- **Cached Data**: In-memory caches cleared
- **Notification States**: Unread notification tracking
- **User Preferences**: UI settings, dismissed messages
- **Analytics**: Usage statistics and metrics

## Pre-Upgrade Checklist

### 1. Export Critical Data
```bash
# Export active sessions
PRODUCTION_MODE=1 python tools/export_active_sessions.py

# Export user roles/permissions (if applicable)
# Export active invite tokens (if applicable)
```

### 2. Validate Archive Completeness
```bash
# Ensure all data is archived
./thywill heal-archives

# Validate archive integrity
PRODUCTION_MODE=1 python tools/analysis/validate_archive_consistency.py
```

### 3. Document Custom Configuration
- Environment variables
- Feature flag states
- Admin user list
- Active invite tokens

### 4. Create Recovery Plan
```bash
# Full database backup
./thywill backup

# Test import process
PRODUCTION_MODE=1 python -c "
from app_helpers.services.text_importer_service import TextImporterService
importer = TextImporterService()
result = importer.import_from_archive_directory(dry_run=True)
print(result)
"
```

## Post-Import Recovery Steps

### 1. Restore System State
```bash
# Restore user sessions (keeps users logged in)
PRODUCTION_MODE=1 python tools/restore_active_sessions.py

# Recreate admin users (if lost)
./thywill add-admin-user <username>

# Regenerate invite tokens (if needed)
```

### 2. Validate Import Success
```bash
# Check data integrity
PRODUCTION_MODE=1 python tools/analysis/validate_archive_consistency.py

# Verify UI functionality
curl -s http://localhost:8000/health
```

### 3. Update Configuration
- Set environment variables
- Configure feature flags
- Update payment settings
- Restore monitoring

## Recommended Upgrade Process

### Safe Upgrade Procedure
1. **Archive Everything**: `./thywill heal-archives`
2. **Export State**: `python tools/export_active_sessions.py`
3. **Backup Database**: `./thywill backup`
4. **Test Import**: `./thywill import text-archives --dry-run`
5. **Deploy Code**: Update application code
6. **Import Data**: `./thywill import text-archives`
7. **Restore Sessions**: `python tools/restore_active_sessions.py`
8. **Restore Config**: Manual admin/token restoration
9. **Validate**: Comprehensive testing

### Rollback Strategy
```bash
# If upgrade fails, rollback to backup
cp thywill.db.backup.pre-upgrade thywill.db
```

## Long-Term Improvements

### Enhanced Archive System
- **System State Archives**: Include sessions, roles, tokens
- **Configuration Archives**: Environment settings
- **Metadata Preservation**: Database statistics, indexes
- **Incremental Imports**: Update-only imports vs full rebuild

### Automated Recovery
- **Migration Scripts**: Automated post-import setup
- **State Restoration**: Automated session/config recovery
- **Validation Suite**: Comprehensive post-import testing
- **Monitoring Integration**: Upgrade success metrics

## Conclusion

**The text archive approach is highly reliable for preserving core community data**, but requires manual attention to restore system state and configuration. This trade-off provides:

**Benefits**:
- ✅ Data integrity guaranteed
- ✅ Human-readable archives
- ✅ Platform independence
- ✅ Long-term durability

**Costs**:
- ⚠️ Session disruption (users re-login)
- ⚠️ Configuration recreation
- ⚠️ Manual state restoration
- ⚠️ Testing overhead

**Recommendation**: Use this approach for major upgrades where data integrity is paramount, and the operational overhead is acceptable.