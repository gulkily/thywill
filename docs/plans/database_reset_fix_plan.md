# Database Reset Prevention Plan

## Problem
pytest tests are resetting the production database despite conftest.py using in-memory SQLite. Some tests are importing the real `models.engine` directly.

## Root Cause
Tests import `from models import engine` which uses the real database. conftest.py patches `Session` but not the base `engine` import.

## Solution Strategy

### 1. Backup Database Before Testing
```python
def backup_database():
    if os.path.exists('thywill.db'):
        backup_name = f'thywill_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        shutil.copy('thywill.db', backup_name)
```

### 2. Patch Root Engine in conftest.py
Add to test_session fixture:
```python
patch('models.engine', test_engine)
patch('app_helpers.services.text_importer_service.engine', test_engine)
patch('app_helpers.services.archive_first_service.engine', test_engine)
```

### 3. Environment Variable Protection
Set `TEST_MODE=1` in conftest.py to prevent real database operations.

### 4. Suspicious Test Files
- `test_database_operations.py`
- `test_models.py`
- `test_prayer_lifecycle.py` 
- `test_archive_download_integration.py`

### 5. Database Existence Checks
Add safety checks in tests to prevent running against production database.

## Next Steps
1. Backup database before testing
2. Add engine patches to conftest.py
3. Set TEST_MODE environment variable
4. Run individual test files to identify culprit
5. Add database existence checks in tests

## Implementation Priority
1. **IMMEDIATE**: Backup current database
2. **HIGH**: Patch engine imports in conftest.py
3. **HIGH**: Identify specific failing tests
4. **MEDIUM**: Add comprehensive safety checks