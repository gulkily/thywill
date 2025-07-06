# ThyWill Backup Features Deprecation Catalog

Based on review of the backup documentation in `docs/plans/backup_export_import_features.md` and the current system implementation, this document catalogs features that can be deprecated following the implementation of the new `export-all` and `import-all` commands.

## Features That Can Be Deprecated

### 1. **Legacy Archive Commands** (High Priority)
- `./thywill sync-users` - Replaced by `export-all`
- `./thywill export-sessions` - Now handled by `export-all`
- `./thywill sync-archives` - Redundant with `export-all`
- `./thywill repair-archives` - Functionality covered by `heal-archives`
- `./thywill reconstruct-from-archives` - Replaced by `import-all`

### 2. **Redundant Validation Commands** (Medium Priority)
- `./thywill validate-consistency` - Overlap with `validate-archives`
- `./thywill recovery-report` - Information available through `test-recovery`

### 3. **JSON Prayer Import** (Medium Priority)
- `./thywill import prayers <file>` - JSON format superseded by text archives
- `app_helpers/cli/prayer_import.py` - Module can be removed
- Related JSON import functionality

### 4. **Session Management Tools** (Low Priority)
- `tools/export_active_sessions.py` - Now integrated into `export-all`
- `tools/restore_active_sessions.py` - Now integrated into `import-all`

### 5. **Legacy Recovery Script** (Medium Priority)
- `tools/restore_from_archives_username_based.py` - Replaced by `import-all` command

### 6. **Standalone Import Script** (Low Priority)
- `scripts/utils/import_text_archives.py` - Functionality now in `import-all` command

## Features to Keep

### Essential Commands
- `./thywill backup/restore/list/cleanup/verify` - Core database backup system
- `./thywill heal-archives` - Creates missing archive files
- `./thywill validate-archives` - Archive integrity checking
- `./thywill test-recovery` - Recovery testing
- `./thywill full-recovery` - Complete database reconstruction
- `./thywill import text-archives` - Text archive imports
- **NEW: `./thywill export-all`** - Complete database export
- **NEW: `./thywill import-all`** - Complete database import

### Essential Services
- Archive Download Service - User/admin archive downloads
- Text Archive Service - Core archive management
- Deployment backup scripts - Production backup automation

## Deprecation Impact

**Estimated cleanup:** ~8 CLI commands, 3-4 Python modules, multiple scripts
**Risk level:** Low - new `export-all`/`import-all` provide comprehensive coverage
**Migration path:** Update any existing scripts/documentation to use new commands

## Notes

The new `export-all` and `import-all` commands provide complete functionality that supersedes most of the legacy backup features while maintaining the same human-readable text archive format. This deprecation would significantly simplify the backup system while maintaining all essential functionality.

## Assessment and Concerns

### Key Concerns
1. **Production Dependencies**: Need to verify no production scripts/automation rely on deprecated commands
2. **Testing Coverage**: Must ensure `export-all`/`import-all` handle all edge cases that legacy commands covered
3. **Data Integrity**: Risk of data loss if new commands don't fully replicate legacy functionality
4. **Migration Timeline**: Need sufficient testing period before removing deprecated features

### Obstacles
- **Unknown Usage**: Some legacy commands may be used in undocumented scripts or workflows
- **Feature Parity**: Need to verify complete functional equivalence between old and new commands
- **Rollback Strategy**: Must maintain ability to revert if issues discovered with new commands

## Deprecation Checklists

### High Priority - "Replaced By" Features

#### Legacy Archive Commands → `export-all`/`import-all`
- [ ] Verify `export-all` includes all data from `sync-users`
- [ ] Confirm `export-all` covers `export-sessions` functionality
- [ ] Test `export-all` replicates `sync-archives` behavior
- [ ] Validate `import-all` fully replaces `reconstruct-from-archives`
- [ ] Check `heal-archives` still needed or covered by new commands

#### Redundant Commands → Existing Commands
- [ ] Map `repair-archives` functionality to `heal-archives`
- [ ] Verify `validate-consistency` overlap with `validate-archives`
- [ ] Confirm `recovery-report` data available in `test-recovery`

### Medium Priority Categories

#### JSON Prayer Import Deprecation
- [ ] Audit codebase for JSON import dependencies
- [ ] Verify text archive format covers all JSON import use cases
- [ ] Test migration path from JSON to text archives
- [ ] Remove `app_helpers/cli/prayer_import.py` safely
- [ ] Update any documentation referencing JSON imports

#### Legacy Recovery Scripts
- [ ] Compare `restore_from_archives_username_based.py` with `import-all`
- [ ] Test edge cases handled by legacy script
- [ ] Verify user mapping functionality preserved
- [ ] Validate error handling equivalence

### Low Priority Categories

#### Session Management Tools
- [ ] Confirm `export-all` includes active session data
- [ ] Verify `import-all` restores sessions correctly
- [ ] Test session continuity across backup/restore
- [ ] Remove standalone tools after validation

#### Standalone Scripts
- [ ] Map `import_text_archives.py` functionality to `import-all`
- [ ] Test command-line argument compatibility
- [ ] Verify batch processing capabilities
- [ ] Check error handling and logging equivalence

## Pre-Deprecation Testing Checklist

### Functional Equivalence
- [ ] Run side-by-side comparison of old vs new commands
- [ ] Test with production-like data volumes
- [ ] Verify identical output between legacy and new commands
- [ ] Test edge cases and error conditions

### Production Safety
- [ ] Audit production server for usage of deprecated commands
- [ ] Review deployment scripts and automation
- [ ] Check monitoring and alerting dependencies
- [ ] Verify backup/restore procedures use only retained commands

### Documentation and Communication
- [ ] Update all user-facing documentation
- [ ] Add deprecation warnings to commands
- [ ] Create migration guide for existing users
- [ ] Notify any external integrations

## Implementation Recommendation

1. **Phase 1:** Mark deprecated commands with warning messages
2. **Phase 2:** Update documentation to reference new commands
3. **Phase 3:** Remove deprecated code after testing period
4. **Phase 4:** Update any production scripts or automation