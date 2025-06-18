# Schema-Only Migrations Implementation Plan

**Problem:** Users get logged out and accounts disappear during upgrades because the deployment process completely replaces the database file, destroying sessions and potentially user data.

**Solution:** Replace full database replacement with schema-only migrations that preserve all user data and sessions.

## Overview

Transform the current deployment system from:
- ❌ **Database Replacement**: Copy backup file over current database
- ✅ **Schema Migrations**: Apply structural changes only, preserve all data

## Implementation Phases

### Phase 1: Enhanced Migration System (2-3 hours)

#### 1.1 Upgrade Database Migration Function
- **File**: `app_helpers/utils/database_helpers.py`
- **Current**: Basic column additions with ALTER TABLE
- **Target**: Comprehensive migration system with:
  - Version tracking
  - Rollback capabilities
  - Validation checks
  - Error handling

#### 1.2 Add Migration Versioning
- Track applied migrations in database
- Prevent duplicate migrations
- Support migration rollbacks
- Log migration history

#### 1.3 Enhance Migration Safety
- Pre-migration data validation
- Post-migration integrity checks
- Automatic backup before migrations
- Rollback on failure

### Phase 2: Deployment Script Overhaul (2-3 hours)

#### 2.1 Modify Deploy Script
- **File**: `deployment/deploy.sh`
- **Change**: Replace database file copy with migration calls
- **Add**: Pre-deployment migration preparation
- **Remove**: Direct database file replacement

#### 2.2 Update Backup Management
- **File**: `deployment/backup_management.sh`
- **Change**: Add "migration-safe" restore option
- **Add**: Data preservation during restore
- **Keep**: Full restore for disaster recovery

#### 2.3 Add Migration CLI Commands
- **File**: `thywill` (CLI script)
- **Add**: `thywill migrate` command
- **Add**: `thywill migrate --check` for validation
- **Add**: `thywill migrate --rollback` for rollbacks

### Phase 3: Safety Mechanisms (1-2 hours)

#### 3.1 Migration Validation
- Check migration prerequisites
- Validate database state before/after
- Ensure no data loss during migrations
- Report migration impact

#### 3.2 Session Preservation
- Identify active sessions before migrations
- Preserve session data during schema changes
- Validate sessions after migrations
- Clean up invalid sessions safely

#### 3.3 Rollback Safety
- Create pre-migration snapshots
- Support granular rollbacks
- Validate rollback safety
- Preserve recent data during rollbacks

## Detailed Implementation

### Step 1: Create Enhanced Migration Framework

```python
# app_helpers/utils/enhanced_migration.py
class MigrationManager:
    def __init__(self):
        self.db_path = "thywill.db"
        self.migrations_dir = "migrations/"
        
    def get_current_version(self):
        """Get current database schema version"""
        
    def get_pending_migrations(self):
        """Get list of unapplied migrations"""
        
    def apply_migration(self, migration_id):
        """Apply a specific migration with safety checks"""
        
    def rollback_migration(self, migration_id):
        """Safely rollback a migration"""
        
    def validate_migration(self, migration_id):
        """Validate migration can be applied safely"""
```

### Step 2: Create Migration Files Structure

```
migrations/
├── 001_initial_schema.sql
├── 002_add_session_columns.sql
├── 003_add_invite_tree.sql
├── 004_add_text_archive_tracking.sql
└── schema_versions.json
```

### Step 3: Update Deployment Flow

**New Deployment Process:**
1. ✅ Create pre-deployment backup (existing)
2. ✅ Stop service (existing)
3. 🆕 **Run schema migrations** (instead of database replacement)
4. ✅ Install dependencies (existing)
5. ✅ Start service (existing)
6. ✅ Health check (existing)
7. 🆕 **Migration rollback on failure** (instead of file rollback)

### Step 4: Preserve Sessions During Migrations

```python
def migrate_with_session_preservation():
    """Run migrations while preserving active user sessions"""
    # 1. Extract active sessions
    # 2. Run schema migrations
    # 3. Restore sessions if compatible
    # 4. Clean up invalid sessions
```

## Benefits

### ✅ **User Experience**
- No more unexpected logouts during upgrades
- User accounts never disappear
- Seamless upgrade experience
- Preserved user sessions and preferences

### ✅ **Data Safety**
- Zero data loss during normal upgrades
- Schema changes only, data preserved
- Rollback without losing recent data
- Comprehensive backup strategy

### ✅ **Operational**
- Industry standard migration approach
- Better upgrade reliability
- Detailed migration logging
- Granular rollback capabilities

## Testing Strategy

### 1. Migration Testing
- Test each migration in isolation
- Verify data preservation
- Test rollback scenarios
- Load test with real data volumes

### 2. Deployment Testing
- Staging environment testing
- Simulate various failure scenarios
- Test session preservation
- Validate rollback procedures

### 3. Integration Testing
- End-to-end deployment process
- User experience during upgrades
- Session continuity testing
- Data integrity validation

## Rollout Plan

### Phase A: Development & Testing (1 week)
1. Implement enhanced migration system
2. Update deployment scripts
3. Create test migrations
4. Comprehensive testing on staging

### Phase B: Gradual Deployment (1 week)
1. Deploy to staging environment
2. Test with real user data
3. Validate session preservation
4. Monitor for issues

### Phase C: Production Deployment (1 day)
1. Schedule maintenance window
2. Deploy new migration system
3. Run first schema-only upgrade
4. Monitor user experience

## Risk Mitigation

### **Risk**: Migration Failure
- **Mitigation**: Automatic rollback to pre-migration state
- **Backup**: Full database backup before any migration
- **Validation**: Pre-migration safety checks

### **Risk**: Session Loss
- **Mitigation**: Session preservation logic during migrations
- **Fallback**: Graceful session cleanup and re-authentication

### **Risk**: Data Corruption
- **Mitigation**: Post-migration integrity checks
- **Recovery**: Point-in-time restoration capabilities

## Success Metrics

### User Experience
- ✅ Zero unexpected logouts during upgrades
- ✅ No account disappearance reports
- ✅ Reduced user complaints about upgrades

### Technical
- ✅ 100% data preservation during migrations
- ✅ Sub-30-second migration times
- ✅ Zero migration rollbacks in production

### Operational
- ✅ Reduced deployment complexity
- ✅ Faster upgrade deployments
- ✅ Improved system reliability

## Next Steps

1. **Approve Plan**: Review and approve implementation approach
2. **Create Branch**: Create feature branch for migration system
3. **Implement Phase 1**: Enhanced migration framework
4. **Test Thoroughly**: Comprehensive testing on staging
5. **Deploy Gradually**: Phased rollout to production

---

*This plan addresses the root cause of logout/account issues by implementing industry-standard database migrations that preserve user data and sessions during upgrades.*