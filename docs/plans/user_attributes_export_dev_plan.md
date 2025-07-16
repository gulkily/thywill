# User Attributes Export - Development Plan

## Overview
Step-by-step development plan for implementing bidirectional sync between database and `user_attributes.txt` archive file.

## Prerequisites
- Review current export/import services in `app_helpers/services/`
- Understand User model fields in `models.py`
- Test current export/import commands

## Phase 1: Database Schema (30 minutes)

### Task 1.1: Add supporter fields to User model
**File**: `models.py`
**Action**: Add fields after existing user fields
```python
is_supporter: bool = Field(default=False)
supporter_since: datetime | None = Field(default=None)
```

### Task 1.2: Create database migration
**Command**: `./thywill migrate`
**Verify**: Check migration applies cleanly

### Task 1.3: Test new fields
**Action**: Create test user with supporter fields
**Verify**: Database stores new fields correctly

## Phase 2: Export Implementation (2 hours)

### Task 2.1: Create user attributes export method
**File**: `app_helpers/services/export_service.py`
**Action**: Add new method to ExportService class
```python
def export_user_attributes(self):
    """Export user attributes to text archive"""
    # Implementation steps:
    # 1. Query all users from database
    # 2. Format as username blocks with key-value pairs
    # 3. Write to text_archives/users/user_attributes.txt
    # 4. Handle missing directory creation
    # 5. Include error handling
```

### Task 2.2: Integrate into main export function
**File**: `app_helpers/services/export_service.py`
**Action**: Add call to `export_user_attributes()` in `export_all_database_data()`
**Location**: After existing user exports

### Task 2.3: Test export functionality
**Command**: `./thywill export-all`
**Verify**: 
- `user_attributes.txt` file created
- Contains all users with correct format
- Handles users with/without supporter status

## Phase 3: Import Implementation (2 hours)

### Task 3.1: Create user attributes parser
**File**: `app_helpers/services/text_importer_service.py`
**Action**: Add parsing method
```python
def _parse_user_attributes_file(self, file_path: str):
    """Parse user attributes from text file"""
    # Implementation steps:
    # 1. Read file line by line
    # 2. Parse username blocks
    # 3. Extract key-value pairs
    # 4. Return structured data
    # 5. Handle malformed entries gracefully
```

### Task 3.2: Create user attributes import method
**File**: `app_helpers/services/text_importer_service.py`
**Action**: Add import method
```python
def import_user_attributes(self):
    """Import user attributes from text archive"""
    # Implementation steps:
    # 1. Call parser method
    # 2. Update User records in database
    # 3. Handle missing users
    # 4. Log import results
    # 5. Commit changes
```

### Task 3.3: Integrate into main import function
**File**: `app_helpers/services/text_importer_service.py`
**Action**: Add call to `import_user_attributes()` in main import method
**Location**: After existing user imports

### Task 3.4: Test import functionality
**Steps**:
1. Manually edit `user_attributes.txt`
2. Run import command
3. Verify database reflects changes
4. Test with missing users, malformed data

## Phase 4: CLI Integration (30 minutes)

### Task 4.1: Update export command
**File**: `archive_management.py`
**Action**: Ensure `export-all` command includes user attributes
**Verify**: Command documentation updated

### Task 4.2: Update import command
**File**: `archive_management.py`
**Action**: Ensure import commands include user attributes
**Verify**: Command documentation updated

## Phase 5: Testing & Validation (1 hour)

### Task 5.1: Create test user attributes file
**Action**: Create sample `user_attributes.txt` with various scenarios:
- Users with supporter status
- Users without supporter status
- Missing users
- Malformed entries

### Task 5.2: Test full round-trip
**Steps**:
1. Export current database
2. Modify `user_attributes.txt`
3. Import changes
4. Export again
5. Verify consistency

### Task 5.3: Test error handling
**Scenarios**:
- Missing file
- Malformed data
- Database connection issues
- Permission errors

### Task 5.4: Run existing tests
**Command**: `pytest`
**Verify**: No regressions in existing functionality

## Phase 6: Documentation (15 minutes)

### Task 6.1: Update CLAUDE.md
**Action**: Add user attributes commands and file format
**Section**: Commands and File Rules sections

### Task 6.2: Update command help text
**Files**: CLI command files
**Action**: Update help text to mention user attributes

## Acceptance Criteria

### Export Requirements
- [ ] `user_attributes.txt` file created in correct location
- [ ] All users exported with correct format
- [ ] Supporter fields included when present
- [ ] File readable by humans
- [ ] Export integrated into `./thywill export-all`

### Import Requirements
- [ ] Parses `user_attributes.txt` correctly
- [ ] Updates database with imported values
- [ ] Handles missing users gracefully
- [ ] Logs import results
- [ ] Import integrated into existing import commands

### File Format Requirements
- [ ] Clean username blocks
- [ ] Key-value pairs for attributes
- [ ] Consistent formatting
- [ ] Empty lines between user blocks

### Error Handling
- [ ] Graceful handling of missing files
- [ ] Validation of malformed data
- [ ] Proper error messages
- [ ] No data corruption on errors

## Timeline
- **Phase 1**: 30 minutes
- **Phase 2**: 2 hours
- **Phase 3**: 2 hours
- **Phase 4**: 30 minutes
- **Phase 5**: 1 hour
- **Phase 6**: 15 minutes

**Total**: 6 hours 15 minutes

## Dependencies
- Working database connection
- Existing export/import services
- Write access to `text_archives/users/` directory

## Risk Mitigation
- Test with database backups
- Implement rollback functionality
- Validate file format before import
- Add comprehensive error logging