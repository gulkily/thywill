# Database Path Configuration Migration Plan

## Overview
Replace the PRODUCTION_MODE environment variable flag with intelligent database path configuration to simplify the codebase while enhancing test safety. This migration provides better flexibility for different environments while maintaining robust safety mechanisms for production data protection.

## Impact Assessment
- **Files affected**: 19 files
- **Estimated effort**: 4-6 hours
- **Risk level**: Low (with reliable backups)
- **Testing impact**: Minimal (tests use isolated in-memory databases)

## Current State Analysis
PRODUCTION_MODE currently serves two purposes:
1. **Database Safety**: Prevents accidental production database access in models.py
2. **Service Access Control**: Blocks database operations in import/export services

## Implementation Phases

### Phase 1: Core Database Engine Simplification with Safety
**Goal**: Replace PRODUCTION_MODE with intelligent database path configuration that maintains test safety

**Files to modify**:
- `models.py` (lines 331-350)
- `tests/conftest.py` (add safety layer)

**Changes**:
1. Replace PRODUCTION_MODE conditional with `get_database_path()` function that implements:
   - **Test environment detection**: Automatic in-memory database for pytest
   - **Explicit configuration**: `DATABASE_PATH` environment variable override
   - **Safe defaults**: Production database for normal operation
2. Add database path logging for visibility
3. Keep performance optimizations (WAL mode, indexes) for all environments
4. Enhance conftest.py with additional safety layer

**Implementation Details**:
```python
# New get_database_path() function in models.py
def get_database_path():
    """
    Multi-layer safety approach:
    1. Test environment detection (highest priority)
    2. Explicit DATABASE_PATH configuration
    3. Default production database path
    """
    # Safety: Detect test environment
    if ('pytest' in sys.modules or 
        'PYTEST_CURRENT_TEST' in os.environ or
        any('pytest' in arg for arg in sys.argv)):
        return ':memory:'
    
    # Explicit configuration
    if 'DATABASE_PATH' in os.environ:
        return os.environ['DATABASE_PATH']
    
    # Default production
    return 'thywill.db'
```

**Verification**:
- Run `pytest` - should automatically detect tests and use `:memory:`
- Run `DATABASE_PATH=dev.db ./thywill start` - should use dev.db
- Run `./thywill start` - should use thywill.db (production default)
- Verify logs show which database is being used
- Test safety: `DATABASE_PATH=thywill.db pytest` should still use `:memory:` due to test detection

**Expected outcome**: System maintains all functionality with enhanced safety - tests automatically use in-memory database while production uses file database.

---

### Phase 2: Application and CLI Cleanup
**Goal**: Remove hardcoded PRODUCTION_MODE settings from app and CLI

**Files to modify**:
- `app.py` (line 18)
- `thywill` CLI script (line 82)

**Changes**:
1. Remove `os.environ['PRODUCTION_MODE'] = '1'` from app.py
2. Remove `PRODUCTION_MODE=1` from `run_python()` function in CLI
3. Update startup migration logic that checks PRODUCTION_MODE (lines 243, 284)

**Verification**:
- Run test suite: `pytest`
- Start development server: `./thywill start`
- Test CLI commands: `./thywill migrate status`, `./thywill admin list`
- Verify migrations work on startup
- Confirm health check endpoint works: `curl localhost:8000/health`

**Expected outcome**: Core application and CLI work without PRODUCTION_MODE references.

---

### Phase 3: Service Layer Cleanup
**Goal**: Remove PRODUCTION_MODE checks from import/export services

**Files to modify**:
- `app_helpers/services/import_service.py` (line 34)
- `app_helpers/services/export_service.py` (line 34)
- `scripts/utils/import_database_exports.py`

**Changes**:
1. Remove PRODUCTION_MODE checks that prevent database access
2. Remove related error messages
3. Services will always attempt database operations when called

**Verification**:
- Test import functionality: `./thywill import text-archives --dry-run`
- Test export functionality: `./thywill export-all`
- Test healing functionality: `./thywill heal-archives`
- Run integration tests: `pytest tests/integration/`

**Expected outcome**: All database import/export operations work without PRODUCTION_MODE.

---

### Phase 4: Tools and Scripts Cleanup
**Goal**: Remove PRODUCTION_MODE references from utility tools and scripts

**Files to modify**:
- `tools/restore_active_sessions.py`
- `tools/export_active_sessions.py`
- `tools/repair/fix_archive_paths.py`
- `tools/analysis/analyze_production_issues.py`
- `migrations/008_multi_use_invite_tokens/migrate.py`

**Changes**:
1. Remove PRODUCTION_MODE environment variable checks
2. Remove conditional logic that depends on PRODUCTION_MODE
3. Tools will always operate on the database when invoked

**Verification**:
- Test session export: `./thywill export-sessions`
- Test archive repair tools
- Test migration rollback: `./thywill migrate rollback`
- Run full test suite: `pytest`

**Expected outcome**: All utility tools work without PRODUCTION_MODE dependency.

---

### Phase 5: Documentation and Environment Cleanup
**Goal**: Update documentation and environment examples to remove PRODUCTION_MODE references

**Files to modify**:
- `deployment/sample.env`
- `CLAUDE.md` (if any references exist)
- Documentation files in `docs/plans/`

**Changes**:
1. Remove PRODUCTION_MODE from sample environment files
2. Update documentation that references PRODUCTION_MODE
3. Update CLI help text if needed
4. Remove PRODUCTION_MODE from any deployment scripts

**Verification**:
- Review all documentation for consistency
- Test fresh setup process without PRODUCTION_MODE
- Verify deployment guides work without PRODUCTION_MODE
- Run complete system test

**Expected outcome**: Documentation and examples are consistent with new implementation.

---

## Testing Strategy

### Production Test Safety Analysis
**Risk Level After Implementation: Very Low**

The new implementation provides multiple overlapping safety mechanisms:
1. **Automatic test detection** - Tests automatically use `:memory:` database
2. **Explicit configuration safety** - Even if `DATABASE_PATH=thywill.db` is set, test detection overrides it
3. **conftest.py safety layer** - Additional protection in test fixtures
4. **Clear logging** - Database path is always logged for verification

### Automated Testing
- Run full test suite after each phase: `pytest`
- Tests automatically use in-memory databases via multi-layer detection
- Add verification test to ensure database path safety
- Test explicit configuration: `DATABASE_PATH=test.db pytest`

### Manual Testing
- Development server startup: `./thywill start`
- Database operations: `./thywill sqlite`
- CLI commands: `./thywill status`, `./thywill admin list`
- Import/export operations: `./thywill heal-archives`
- Migration operations: `./thywill migrate status`
- **Safety verification**: Check logs show correct database path

### Integration Testing
- Fresh database initialization: `./thywill db init`
- Complete application workflow
- Backup and restore operations
- **Multi-environment testing**:
  - `pytest` (should use `:memory:`)
  - `DATABASE_PATH=dev.db ./thywill start` (should use dev.db)
  - Production deployment (should use thywill.db)

### Test Safety Verification
Add new test file `tests/test_database_safety.py`:
```python
def test_database_path_safety():
    """Verify test environment uses safe database"""
    from models import DATABASE_PATH
    assert DATABASE_PATH == ':memory:', f"Tests must use in-memory database, got: {DATABASE_PATH}"

def test_production_safety_override():
    """Verify test detection overrides explicit production path"""
    # Even if someone tries to force production database,
    # test detection should prevent it
    import os
    original = os.environ.get('DATABASE_PATH')
    try:
        os.environ['DATABASE_PATH'] = 'thywill.db'
        # Test environment detection should still return :memory:
        from models import get_database_path
        assert get_database_path() == ':memory:'
    finally:
        if original:
            os.environ['DATABASE_PATH'] = original
        elif 'DATABASE_PATH' in os.environ:
            del os.environ['DATABASE_PATH']
```

## Rollback Strategy
If issues arise, rollback can be done by:
1. Reverting commits for each completed phase
2. Each phase is atomic and leaves system in working state
3. Database operations are non-destructive

## Risk Mitigation
- **Backup before starting**: Create database backup
- **Atomic phases**: Each phase maintains system functionality
- **Gradual rollout**: Test each phase thoroughly before proceeding
- **Version control**: Commit after each successful phase

## Success Criteria
- [ ] All 19 files updated to remove PRODUCTION_MODE
- [ ] `get_database_path()` function implemented with multi-layer safety
- [ ] Enhanced conftest.py with additional safety layer
- [ ] Database safety verification tests added and passing
- [ ] Full test suite passes with automatic in-memory database usage
- [ ] Development server starts without PRODUCTION_MODE
- [ ] CLI commands work without PRODUCTION_MODE
- [ ] Import/export services function properly
- [ ] Database operations work in all environments
- [ ] Database path logging provides clear visibility
- [ ] Multi-environment testing confirms correct database usage
- [ ] Documentation updated and consistent

## Post-Implementation Benefits
- **Enhanced Safety**: Multiple overlapping safety mechanisms protect production data
- **Simplified codebase**: Remove PRODUCTION_MODE conditional logic
- **Intelligent defaults**: Automatic test detection with explicit configuration options
- **Better visibility**: Clear logging of database path selection
- **Flexible configuration**: Support for development, testing, and production environments
- **Future-proof**: Easy to extend detection methods or add new safety layers
- **Consistent behavior**: Same code paths with environment-appropriate database selection
- **Reduced complexity**: Replace binary flag with intelligent path configuration

## Database Path Configuration Reference

After implementation, the system will use this decision hierarchy:

1. **Test Environment** (Highest Priority)
   - Automatic detection via pytest modules, environment variables, or command line
   - Always uses `:memory:` database for safety
   - Cannot be overridden by configuration

2. **Explicit Configuration**
   - Set `DATABASE_PATH` environment variable
   - Examples:
     - `DATABASE_PATH=dev.db` for development
     - `DATABASE_PATH=staging.db` for staging
     - `DATABASE_PATH=/path/to/custom.db` for custom locations

3. **Production Default**
   - Uses `thywill.db` in current directory
   - No configuration required
   - Standard production behavior

## Usage Examples
```bash
# Tests (automatic safety)
pytest                                    # Uses :memory: automatically

# Development with separate database  
DATABASE_PATH=dev.db ./thywill start     # Uses dev.db

# Staging environment
DATABASE_PATH=staging.db ./thywill start # Uses staging.db

# Production (default behavior)
./thywill start                          # Uses thywill.db

# Safety verification
DATABASE_PATH=thywill.db pytest         # Still uses :memory: (test detection overrides)
```