# Schema-Only Migrations Implementation Plan

**Problem:** Users get logged out and accounts disappear during upgrades because the deployment process completely replaces the database file, destroying sessions and potentially user data.

**Solution:** Replace full database replacement with schema-only migrations that preserve all user data and sessions.

## Overview

Transform the current deployment system from:
- ❌ **Database Replacement**: Copy backup file over current database
- ✅ **Schema Migrations**: Apply structural changes only, preserve all data
- ✅ **Automatic Runtime Migrations**: Detect and apply migrations automatically when app starts

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

#### 1.4 Add Automatic Runtime Migration Detection
- **Application startup migration check**: Detect pending migrations on app start
- **Background migration monitoring**: Check for new migrations periodically
- **Zero-downtime migrations**: Apply migrations without stopping the application
- **Migration state tracking**: Persistent tracking of migration status
- **Automatic rollback on failure**: Immediate rollback if migration fails

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
        self.lock_file = "migration.lock"
        
    def get_current_version(self):
        """Get current database schema version"""
        
    def get_pending_migrations(self):
        """Get list of unapplied migrations in dependency order"""
        
    def apply_migration(self, migration_id):
        """Apply a specific migration with safety checks and database locking"""
        
    def rollback_migration(self, migration_id):
        """Safely rollback a migration"""
        
    def validate_migration(self, migration_id):
        """Validate migration can be applied safely"""
        
    def auto_migrate_on_startup(self):
        """Automatically detect and apply pending migrations at startup"""
        
    def check_for_pending_migrations(self):
        """Check if there are any pending migrations (for monitoring)"""
        
    def resolve_migration_dependencies(self, migrations):
        """Sort migrations by dependency order"""
        
    def acquire_migration_lock(self):
        """Acquire exclusive lock for migration operations"""
        
    def release_migration_lock(self):
        """Release migration lock"""
        
    def validate_schema_integrity(self):
        """Validate database schema matches expected state"""
        
    def handle_partial_migration_recovery(self, migration_id):
        """Recover from partially applied migrations"""
        
    def estimate_migration_time(self, migration_id):
        """Estimate time required for migration based on data size"""
        
    def should_enable_maintenance_mode(self, migration_id):
        """Determine if migration requires maintenance mode"""
```

### Step 2: Create Migration Files Structure

```
migrations/
├── 001_initial_schema/
│   ├── up.sql
│   ├── down.sql
│   └── metadata.json
├── 002_add_session_columns/
│   ├── up.sql
│   ├── down.sql
│   └── metadata.json
├── 003_add_invite_tree/
│   ├── up.sql
│   ├── down.sql
│   └── metadata.json
├── 004_add_text_archive_tracking/
│   ├── up.sql
│   ├── down.sql
│   └── metadata.json
└── schema_versions.json
```

**Migration File Format:**
```json
// metadata.json
{
    "migration_id": "002_add_session_columns",
    "description": "Add session tracking columns to users table",
    "depends_on": ["001_initial_schema"],
    "estimated_duration_seconds": 5,
    "requires_maintenance_mode": false,
    "data_size_threshold_mb": 100
}
```

```sql
-- up.sql
ALTER TABLE users ADD COLUMN last_session_id TEXT;
ALTER TABLE users ADD COLUMN session_expires_at TIMESTAMP;
CREATE INDEX idx_users_session_expires ON users(session_expires_at);

-- down.sql
DROP INDEX IF EXISTS idx_users_session_expires;
ALTER TABLE users DROP COLUMN session_expires_at;
ALTER TABLE users DROP COLUMN last_session_id;
```

### Step 3: Update Deployment Flow

**New Deployment Process:**
1. ✅ Create pre-deployment backup (existing)
2. 🆕 **Acquire migration lock** (prevent concurrent access)
3. 🆕 **Estimate migration time** (determine if maintenance mode needed)
4. 🆕 **Enable maintenance mode if required** (for long-running migrations)
5. ✅ Stop service (existing, only if maintenance mode enabled)
6. 🆕 **Run schema migrations with recovery handling** (instead of database replacement)
7. 🆕 **Validate schema integrity** (ensure migrations completed correctly)
8. ✅ Install dependencies (existing)
9. ✅ Start service (existing)
10. 🆕 **Release migration lock** 
11. ✅ Health check (existing)
12. 🆕 **Migration rollback on failure** (instead of file rollback)

### Step 4: Preserve Sessions During Migrations

```python
def migrate_with_session_preservation():
    """Run migrations while preserving active user sessions"""
    # 1. Extract active sessions
    # 2. Acquire database lock
    # 3. Run schema migrations with partial recovery handling
    # 4. Validate schema integrity post-migration
    # 5. Restore sessions if compatible
    # 6. Clean up invalid sessions
    # 7. Release database lock

def apply_migration_with_recovery(migration_id):
    """Apply migration with comprehensive error handling"""
    try:
        # 1. Begin transaction
        # 2. Create migration checkpoint
        # 3. Apply migration steps incrementally
        # 4. Validate each step
        # 5. Commit transaction
    except Exception:
        # 1. Rollback to checkpoint
        # 2. Log partial migration state
        # 3. Mark migration as failed
        # 4. Preserve any completed steps that are safe
```

### Step 5: Integrate Automatic Migrations into Application

**Application Startup Integration** (`app.py`):
```python
# In app.py - add to startup
from app_helpers.utils.enhanced_migration import MigrationManager

@app.on_event("startup") 
async def startup_migrations():
    """Run automatic migrations on application startup"""
    migration_manager = MigrationManager()
    
    try:
        # Check for migration lock from previous failed attempt
        if migration_manager.is_migration_locked():
            print("⚠️  Migration lock detected - checking for partial migrations...")
            migration_manager.handle_partial_migration_recovery()
        
        # Resolve dependencies and check pending migrations
        pending = migration_manager.get_pending_migrations()  # Returns in dependency order
        if pending:
            print(f"🔄 Applying {len(pending)} pending migrations...")
            
            # Check if any migration requires maintenance mode
            for migration in pending:
                if migration_manager.should_enable_maintenance_mode(migration):
                    print(f"⚠️  Migration {migration} requires maintenance mode - manual deployment needed")
                    return
            
            # Apply migrations with locking
            migration_manager.auto_migrate_on_startup()
            
            # Validate final schema state
            migration_manager.validate_schema_integrity()
            print("✅ Automatic migrations completed")
        else:
            print("✅ Database schema is up to date")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        # Application can still start with warnings, but log the issue
```

**Background Migration Check** (Optional):
```python
# Periodic check for new migrations (useful for multi-instance deployments)
import schedule
import threading

def check_migrations_background():
    """Background thread to check for new migrations periodically"""
    migration_manager = MigrationManager()
    
    while True:
        try:
            if migration_manager.check_for_pending_migrations():
                print("⚠️  New migrations detected - restart application to apply")
        except Exception as e:
            print(f"Migration check error: {e}")
        
        time.sleep(300)  # Check every 5 minutes

# Start background migration checker
threading.Thread(target=check_migrations_background, daemon=True).start()
```

**Admin Endpoint** (For manual control):
```python
# Add to admin routes
@app.get("/admin/migrations/status")
def migration_status():
    """Get current migration status"""
    migration_manager = MigrationManager()
    return {
        "current_version": migration_manager.get_current_version(),
        "pending_migrations": migration_manager.get_pending_migrations(),
        "last_migration_date": migration_manager.get_last_migration_date()
    }

@app.post("/admin/migrations/apply")  
def apply_migrations():
    """Manually trigger migrations"""
    migration_manager = MigrationManager()
    result = migration_manager.auto_migrate_on_startup()
    return {"success": True, "migrations_applied": result}
```

## Benefits

### ✅ **User Experience**
- No more unexpected logouts during upgrades
- User accounts never disappear
- Seamless upgrade experience
- Preserved user sessions and preferences
- **Zero-downtime deployments**: Migrations happen automatically without service interruption

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
- **Automatic migration detection**: No manual intervention required
- **Self-healing deployments**: Database automatically stays up-to-date
- **Admin visibility**: Migration status and manual control endpoints

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

### 4. Automatic Migration Testing
- **Startup migration testing**: Verify migrations run correctly on app start
- **Multiple restart scenarios**: Test repeated startups don't re-run migrations
- **Failure recovery testing**: Ensure failed migrations don't prevent app startup
- **Background monitoring testing**: Verify migration detection works correctly
- **Admin endpoint testing**: Test manual migration triggers and status endpoints
- **Dependency resolution testing**: Verify migrations run in correct dependency order
- **Concurrent access testing**: Test migration locks prevent database corruption
- **Partial migration recovery testing**: Test recovery from interrupted migrations
- **Large data migration testing**: Test performance with realistic data volumes
- **Schema validation testing**: Verify post-migration schema integrity checks

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

### **Risk**: Concurrent Database Access
- **Mitigation**: Migration locking mechanism to prevent concurrent access
- **Fallback**: Queue requests during migration, retry after completion

### **Risk**: Partial Migration Completion
- **Mitigation**: Transaction-based migrations with checkpoints
- **Recovery**: Automatic detection and recovery of partial migrations on startup

### **Risk**: Migration Dependencies
- **Mitigation**: Dependency resolution and validation before applying migrations
- **Recovery**: Clear error messages and dependency conflict resolution

### **Risk**: Large Data Migration Performance
- **Mitigation**: Data size estimation and automatic maintenance mode for large migrations
- **Fallback**: Manual migration scheduling for very large datasets

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

## Documentation Updates

### Required Documentation Changes
1. **Update deployment runbooks**: Replace database replacement procedures with migration workflows
2. **Create migration authoring guide**: Document how to create new migrations with proper metadata
3. **Update rollback procedures**: Document new migration-based rollback process
4. **Add troubleshooting guide**: Document common migration issues and recovery procedures
5. **Update development setup**: Include migration system in local development documentation

## Next Steps

1. **Approve Plan**: Review and approve implementation approach
2. **Create Branch**: Create feature branch for migration system
3. **Implement Phase 1**: Enhanced migration framework with dependency resolution
4. **Create Initial Migrations**: Convert current schema to migration format
5. **Test Thoroughly**: Comprehensive testing including all new safety mechanisms
6. **Update Documentation**: Revise all deployment and development documentation
7. **Deploy Gradually**: Phased rollout to production

---

*This plan addresses the root cause of logout/account issues by implementing industry-standard database migrations that preserve user data and sessions during upgrades.*