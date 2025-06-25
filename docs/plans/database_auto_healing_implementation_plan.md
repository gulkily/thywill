# Database Auto-Healing Implementation Plan

## Overview
Implement automatic database corruption recovery by regenerating the SQLite database from text archives when corruption is detected.

## Problem Statement
SQLite database corruption (`sqlite3.DatabaseError: database disk image is malformed`) causes complete application failure. The current system has text archives that can serve as the source of truth for data recovery.

## Solution Approach
Create an auto-healing mechanism that:
1. Detects database corruption during startup/operations
2. Automatically backs up the corrupted database
3. Regenerates the database from text archives
4. Resumes normal operation

## Implementation Tasks

### 1. Database Corruption Detection
- **Location**: `app_helpers/utils/database_helpers.py`
- **Function**: `check_database_health()`
- **Implementation**:
  - Test basic database connectivity
  - Catch `sqlite3.DatabaseError` and `sqlalchemy.exc.DatabaseError`
  - Return boolean health status

### 2. Auto-Healing Service
- **Location**: `app_helpers/services/auto_healing_service.py` (new file)
- **Functions**:
  - `heal_database()` - Main healing orchestration
  - `backup_corrupted_db()` - Rename corrupted DB with timestamp
  - `regenerate_from_archives()` - Rebuild database from text files
  - `verify_healing_success()` - Validate regenerated database

### 3. Text Archive Parser
- **Location**: `app_helpers/services/archive_parser_service.py` (new file)
- **Functions**:
  - `parse_prayer_archives()` - Extract prayer data from text files
  - `parse_user_archives()` - Extract user data from text files
  - `rebuild_database_schema()` - Recreate all tables
  - `populate_from_parsed_data()` - Insert parsed data into new DB

### 4. Application Startup Integration
- **Location**: `app.py` startup event
- **Implementation**:
  - Call `check_database_health()` on startup
  - If unhealthy, trigger `heal_database()`
  - Log healing attempts and outcomes
  - Fail gracefully if healing unsuccessful

### 5. Runtime Error Handling
- **Location**: Database middleware/error handlers
- **Implementation**:
  - Catch database errors during normal operations
  - Trigger healing process automatically
  - Return user-friendly error messages during healing
  - Implement circuit breaker to prevent healing loops

## Technical Specifications

### Archive File Structure
```
text_archives/
├── prayers/
│   ├── prayer_1.txt
│   ├── prayer_2.txt
│   └── ...
├── users/
│   ├── user_1.txt
│   ├── user_2.txt
│   └── ...
└── metadata/
    ├── prayer_marks.txt
    ├── sessions.txt
    └── ...
```

### Healing Process Flow
1. **Detection**: Database operation fails with corruption error
2. **Backup**: `mv thywill.db thywill_corrupted_$(date +%Y%m%d_%H%M%S).db`
3. **Initialize**: Create fresh database with `./thywill init`
4. **Parse**: Extract data from all text archive files
5. **Populate**: Insert parsed data into new database
6. **Verify**: Test basic operations on healed database
7. **Resume**: Return control to application

### Error Handling
- **Partial Archives**: Handle missing or incomplete archive files
- **Data Conflicts**: Resolve inconsistencies between archive files
- **Healing Failures**: Provide manual recovery instructions
- **Multiple Corruption**: Prevent infinite healing loops

### Configuration
```python
# Environment variables
AUTO_HEALING_ENABLED=true
MAX_HEALING_ATTEMPTS=3
HEALING_TIMEOUT_SECONDS=300
CORRUPTED_DB_RETENTION_DAYS=30
```

## Testing Strategy

### Unit Tests
- `test_database_health_check()`
- `test_archive_parsing()`
- `test_database_regeneration()`

### Integration Tests
- `test_full_healing_process()`
- `test_healing_with_partial_archives()`
- `test_healing_failure_scenarios()`

### Functional Tests
- Simulate database corruption
- Verify application continues after healing
- Test data integrity post-healing

## Security Considerations
- Validate archive file integrity before parsing
- Sanitize parsed data before database insertion
- Log all healing activities for audit trail
- Prevent unauthorized access to corrupted database backups

## Performance Considerations
- Healing process may take several minutes for large datasets
- Implement progress indicators for user feedback
- Consider background healing for non-critical operations
- Optimize archive parsing for large files

## Rollout Plan
1. **Development**: Implement core healing functionality
2. **Testing**: Comprehensive test suite with corruption simulation
3. **Staging**: Deploy with detailed logging and monitoring
4. **Production**: Gradual rollout with feature flags

## Success Criteria
- Application automatically recovers from database corruption
- Zero data loss when text archives are complete
- Healing process completes within 5 minutes for typical datasets
- User experience minimally disrupted during healing
- Comprehensive logging for troubleshooting

## Future Enhancements
- Real-time archive synchronization
- Distributed healing across multiple instances
- Advanced corruption prediction and prevention
- Automated archive integrity verification