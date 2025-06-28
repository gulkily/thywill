# JSON Archive Removal Implementation Plan

## Overview
Remove the JSON archive functionality from ThyWill now that text archives are the primary archival system. This plan addresses the systematic removal of JSON export/import systems while preserving essential functionality.

## Scope
This plan covers the removal of JSON-based community data export/import functionality that was used before text archives were implemented. Text archives now serve as the primary backup and recovery mechanism.

## Components to Remove vs Preserve

### ✅ PRESERVE (Text Archive System - Essential)
- `app_helpers/services/text_archive_service.py` - Core text archive functionality  
- `app_helpers/services/archive_download_service.py` - ZIP creation for text archives
- `app_helpers/routes/archive_routes.py` - Text archive download API endpoints
- `import_text_archives.py` - Text archive import functionality
- All text archive test files and ZIP download functionality

### ❌ REMOVE (JSON Export System - Redundant)

#### Remove: `app_helpers/services/export_service.py`
- **Impact**: Removes `CommunityExportService` class entirely (JSON exports only)
- **Dependencies**: Used by `/export/database` endpoint
- **Action**: Delete entire file
- **Note**: This is separate from text archive functionality

#### Remove: `import_community_data.py`
- **Impact**: Removes `CommunityImportService` class entirely (JSON imports only)
- **Dependencies**: Used by CLI JSON import commands
- **Action**: Delete entire file
- **Note**: Text archive imports remain via `import_text_archives.py`

### 2. API Routes (HIGH PRIORITY)

#### Modify: `app_helpers/routes/general_routes.py`
- **Remove Lines 95-167**: Both `/export/info` and `/export/database` endpoints
- **Impact**: Eliminates JSON export API functionality
- **Preserve**: Other routes in the file remain unchanged

### 3. CLI Commands (MEDIUM PRIORITY)

#### Modify: `thywill` CLI script
- **Remove**: `import community <file>` command for JSON imports only
- **PRESERVE**: Text archive import functionality (`import_text_archives.py`)
- **Update**: Help text to remove JSON import references
- **Preserve**: All other CLI functionality including text archive commands

### 4. Templates and Frontend (MEDIUM PRIORITY)

#### Modify: `templates/export.html`
- **Remove Lines 90-120**: Export UI with JSON references
- **Remove Lines 227-251**: Database export section  
- **Remove Lines 261-278**: Technical details about JSON files
- **Update**: Focus template on text archive functionality only
- **Preserve**: Text archive download sections

#### Modify: `templates/menu.html`
- **Remove**: Menu link to JSON export functionality
- **Preserve**: All other menu items

### 5. Database Model Cleanup (LOW PRIORITY)

#### Review: `models.py`
- **Keep**: JSON handling for role permissions (still needed)
- **Action**: No changes required - JSON usage here is for role permissions, not archives

### 6. Archive Service Cleanup (CAREFUL REVIEW REQUIRED)

#### Review: `app_helpers/services/archive_download_service.py`
- **PRESERVE**: All text archive ZIP creation functionality
- **PRESERVE**: Archive metadata JSON (needed for text archive system)
- **Review carefully**: Only remove JSON export-specific code, not text archive JSON metadata
- **Preserve**: All text archive functionality

#### Review: `app_helpers/services/archive_writers.py`
- **PRESERVE**: All functionality - this supports text archives
- **Keep**: JSON usage for role permissions in archives
- **Action**: No changes required - this JSON usage supports text archives

### 7. Test Suite Updates (MEDIUM PRIORITY)

#### Tests to Remove (Complete List)

##### Delete Entire Test File:
- **`tests/unit/test_export_service.py`** - 48 comprehensive test methods including:
  - Export metadata structure validation
  - Data filtering (flagged content exclusion)  
  - JSON serialization and structure validation
  - ZIP creation with individual JSON files
  - Caching functionality
  - Export statistics and info generation
  - Complete `CommunityExportService` class functionality

#### PRESERVE: Text Archive Test Files (No Changes Needed)
- **KEEP**: `tests/unit/test_archive_download_service.py` (text archive ZIP creation)
- **KEEP**: `tests/integration/test_archive_download_integration.py` (text archive workflows)  
- **KEEP**: `tests/unit/test_archive_routes.py` (text archive API endpoints)
- **KEEP**: `tests/cli/test_thywill_import.bats` (community ZIP import - text archives)
- **KEEP**: `tests/cli/test_thywill_errors.bats` (file handling - not JSON export)
- **KEEP**: All other test files (no JSON export functionality found)

#### Test Coverage Impact
- **Removed**: 48 test methods covering JSON export functionality
- **Preserved**: All text archive functionality tests (ZIP creation, downloads, imports)
- **No Route Tests**: No specific tests found for `/export/info` or `/export/database` endpoints

### 8. Documentation Updates (LOW PRIORITY)

#### Update Documentation Files
- **Modify**: `CLAUDE.md` - Remove JSON export references from API endpoints section
- **Update**: Remove or archive `docs/plans/completed/COMMUNITY_DATABASE_EXPORT_PLAN.md`
- **Preserve**: All text archive documentation

### 9. Configuration Cleanup (LOW PRIORITY)

#### Remove Environment Variables
- **Remove**: `EXPORT_CACHE_TTL_MINUTES` if only used for JSON exports
- **Remove**: `EXPORT_RATE_LIMIT_MINUTES` if only used for JSON exports
- **Review**: Determine if these are used elsewhere

## Implementation Strategy

### Phase 1: Core Removal (Breaking Changes)
1. Remove `app_helpers/services/export_service.py`
2. Remove `import_community_data.py`  
3. Remove JSON export routes from `general_routes.py`
4. Update CLI to remove import commands

### Phase 2: UI and Template Updates
1. Update `templates/export.html` to focus on text archives
2. Update `templates/menu.html` to remove JSON export links
3. Test UI changes to ensure no broken links

### Phase 3: Test Suite Cleanup
1. Remove `tests/unit/test_export_service.py`
2. Update remaining test files to remove JSON-specific tests
3. Run full test suite to ensure no regressions

### Phase 4: Documentation and Configuration
1. Update `CLAUDE.md` and other documentation
2. Remove unused environment variables
3. Clean up migration scripts if needed

## Risk Assessment

### High Risk Areas
- **Breaking Changes**: Removing export routes will break any existing bookmarks/scripts
- **CLI Changes**: Users relying on import commands will need migration
- **Template Updates**: Must ensure no broken UI elements

### Mitigation Strategies
- **Gradual Removal**: Implement in phases to catch issues early
- **Test Coverage**: Run comprehensive tests after each phase
- **Documentation**: Update user-facing docs to explain text archive advantages

## Testing Strategy

### Unit Tests
- Verify removed functionality is completely gone
- Ensure text archive functionality remains intact
- Test CLI commands work without import functionality

### Integration Tests  
- Test full application functionality after removal
- Verify export page works with only text archives
- Test archive download functionality

### Manual Testing
- Test all menu links and navigation
- Verify export page functionality
- Test text archive downloads still work

## Success Criteria

### Functional Requirements
- [ ] All JSON export/import functionality removed
- [ ] Text archive functionality remains fully operational
- [ ] No broken links or UI elements
- [ ] CLI commands work without import functionality
- [ ] All tests pass

### Non-Functional Requirements
- [ ] Codebase is cleaner with less complexity
- [ ] No unused dependencies or configurations
- [ ] Documentation accurately reflects current functionality
- [ ] Performance impact is minimal or positive

## Post-Removal Verification

### Verification Checklist
1. **API Endpoints**: Verify JSON export endpoints (`/export/info`, `/export/database`) return 404
2. **Text Archive Endpoints**: Verify all `/api/archive/*` endpoints still work
3. **CLI Commands**: Verify JSON `import` commands are removed, text archive imports remain
4. **UI Elements**: Verify export page shows text archive options only
5. **ZIP Downloads**: Verify text archive ZIP downloads work completely
6. **Tests**: Verify all tests pass, text archive tests remain, JSON export tests removed
7. **Archives**: Verify text archive functionality works completely

### Rollback Plan
If issues arise, the removed files can be restored from git history:
- `git checkout HEAD~1 -- app_helpers/services/export_service.py`
- `git checkout HEAD~1 -- import_community_data.py`
- Restore specific routes and templates as needed

## Estimated Timeline
- **Phase 1**: 2-3 hours (core removal)
- **Phase 2**: 1-2 hours (UI updates)  
- **Phase 3**: 1-2 hours (test cleanup)
- **Phase 4**: 1 hour (documentation)
- **Total**: 5-8 hours

## Dependencies
- No external dependencies
- Requires text archive functionality to be fully operational
- Should coordinate with any pending export/import feature requests

## Notes
- This removal simplifies the codebase significantly
- Text archives provide superior human-readable backup/recovery
- Users benefit from reduced complexity and faster performance
- Archive transparency is maintained through text archives