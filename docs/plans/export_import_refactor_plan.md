# Export/Import System Refactoring Plan

## Overview
Refactor export-all and import-all to use existing text archive format/locations and eliminate problematic inline scripts.

## Goals
1. **Unified Archive System**: Use existing `text_archives/` structure for all data
2. **Clean Code**: Eliminate inline scripts, use proper modules  
3. **Complete Coverage**: Export/import all database tables
4. **Consistency**: Follow established ThyWill archive patterns

## Current Problems
- Inline scripts are unmaintainable (200+ lines in strings)
- Duplicate archive locations (`database_exports/` vs existing structure)
- Users need to run both `import text-archives` AND `import-all`
- No syntax highlighting or proper debugging for embedded code

## Solution Architecture

### Archive Structure (Unified)
```
text_archives/
├── prayers/           # Existing + all prayer-related data
├── users/            # Existing + all user-related data
├── sessions/         # Administrative data (from database_exports)
├── authentication/   # Auth requests, approvals, audit logs
├── invites/          # Invite tokens and usage
├── roles/            # Roles and user role assignments
├── security/         # Security logs (existing location)
└── system/           # Changelog, migrations (new)
```

### Code Structure (Clean Modules)
```
app_helpers/services/
├── export_service.py      # Clean export functions
├── import_service.py      # Clean import functions
└── archive_service.py     # Shared archive utilities
```

## Implementation Steps

### Phase 1: Create Clean Export Service
- `app_helpers/services/export_service.py`
- Move all export functions from inline script
- Add missing table exports (prayer attributes, user data, etc.)
- Use existing archive format and locations

### Phase 2: Create Clean Import Service  
- `app_helpers/services/import_service.py`
- Move all import functions from separate script
- Add missing table imports
- Handle both existing archives and new data

### Phase 3: Update CLI Commands
- Refactor `export-all` to call `ExportService.export_all()`
- Refactor `import-all` to call `ImportService.import_all()`
- Remove inline scripts and subprocess calls
- Add proper error handling and progress reporting

### Phase 4: Integration Testing
- Test export-all → rm → import-all roundtrip
- Verify zero database differences
- Ensure compatibility with existing archives
- Update documentation

## Benefits
- **Maintainable**: Proper Python modules with syntax highlighting
- **Unified**: Single archive system, single import command
- **Complete**: All database tables covered
- **Debuggable**: Proper stack traces and error handling
- **Performant**: No subprocess overhead
- **Consistent**: Follows ThyWill patterns

## Success Criteria
- `export-all` exports complete database to unified archive structure
- `import-all` imports complete database from unified archives
- Database comparison shows zero differences after roundtrip
- No inline scripts remain
- Code is maintainable and well-structured

## File Changes
- **New**: `app_helpers/services/export_service.py`
- **New**: `app_helpers/services/import_service.py`  
- **Modified**: `app_helpers/cli/archive_management.py` (remove inline scripts)
- **Modified**: `scripts/utils/import_database_exports.py` (integrate with new system)
- **Remove**: `text_archives/database_exports/` (consolidate into main structure)

## Timeline
1. Create export service (30 min)
2. Create import service (30 min)  
3. Update CLI commands (15 min)
4. Integration testing (15 min)

Total: ~90 minutes