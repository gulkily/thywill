# Auto-Migration on Startup Implementation Plan

## Overview
Automatically check and run pending database migrations when the application starts up, eliminating the need to manually run migrations after git pull.

## Requirements
- **Safety**: Only run in production mode with explicit opt-in
- **Reliability**: Use existing migration infrastructure with locking
- **Visibility**: Clear logging of migration activity
- **Graceful Handling**: Don't crash app if migrations fail

## Implementation

### 1. Environment Configuration
Add new environment variable:
- `AUTO_MIGRATE_ON_STARTUP=true/false` (default: false)
- Only active when `PRODUCTION_MODE=1`

### 2. Startup Integration
**Location**: `app.py` - Add to application startup sequence

**Process**:
1. Check if auto-migration is enabled
2. Import existing migration system
3. Check for pending migrations 
4. Run migrations if needed
5. Log results

### 3. Migration System Integration
**Use existing components**:
- `app_helpers/utils/enhanced_migration.py` - Migration management
- Existing migration lock system
- Dependency resolution and verification

### 4. Error Handling
- Log migration failures but don't crash app
- Provide clear error messages
- Respect migration lock timeouts

## Code Changes

### Files to Modify
- `app.py` - Add startup migration check (10-15 lines)
- `CLAUDE.md` - Document new environment variable

### Implementation Steps
1. Add environment variable check
2. Import migration utilities
3. Add migration check to startup sequence
4. Add appropriate logging
5. Handle errors gracefully

## Safety Considerations
- **Explicit Opt-in**: Requires both `PRODUCTION_MODE=1` and `AUTO_MIGRATE_ON_STARTUP=true`
- **Existing Safeguards**: Leverages migration locking and verification
- **Non-blocking**: App continues even if migrations fail
- **Logging**: Clear visibility into migration activity

## Benefits
- **Developer Experience**: No need to remember manual migration steps
- **Deployment Safety**: Automatic schema updates on deployment
- **Consistency**: Always run latest migrations when app starts
- **Integration**: Works with existing migration system

## Usage
```bash
# Enable auto-migration
export PRODUCTION_MODE=1
export AUTO_MIGRATE_ON_STARTUP=true

# Start application (migrations run automatically)
./thywill start
```

## Rollback Plan
If issues arise, simply set `AUTO_MIGRATE_ON_STARTUP=false` or remove the environment variable. The app will start normally without running migrations.