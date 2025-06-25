# Community Database Export Feature Design Plan

## Overview
Design a feature that allows users to download a complete community database backup for maintenance purposes and community forking, while maintaining security by excluding sensitive authentication data.

## Requirements

### Functional Requirements
- Any user can download a complete database export containing all community data
- Forked communities retain all prayers (except flagged ones), users, relationships, and settings
- Export excludes session salts and flagged prayer requests
- Export format supports easy import into new ThyWill instances

### Security Requirements
- Session salts must be excluded from exports (if they exist)
- Exclude flagged prayer requests and related data
- Exclude temporary authentication and session data
- Exclude security monitoring logs
- All other community data is public information and safe to export

## Technical Design

### Export Format
**Recommended Format**: JSON with structured sections
```json
{
  "export_metadata": {
    "version": "1.0",
    "export_date": "2025-01-11T10:30:00Z",
    "source_instance": "community_name",
    "schema_version": "current_db_version"
  },
  "users": [...],
  "prayers": [...],
  "prayer_attributes": [...],
  "prayer_marks": [...],
  "prayer_skips": [...],
  "prayer_activity_log": [...],
  "roles": [...],
  "user_roles": [...],
  "invite_tokens": [...],
  "changelog_entries": [...]
}
```

### Database Tables to Include
1. **User** - User profiles, religious preferences, invite tree relationships
2. **Prayer** - All non-flagged prayers with content and metadata  
3. **PrayerAttribute** - Prayer attributes (archived, answered, etc.) for non-flagged prayers
4. **PrayerMark** - User prayer marks/interactions
5. **PrayerSkip** - User prayer skips
6. **PrayerActivityLog** - Prayer activity history for non-flagged prayers
7. **Role** - User role definitions
8. **UserRole** - User role assignments
9. **InviteToken** - Invite tokens and usage history
10. **ChangelogEntry** - Community development history

### Database Fields to Exclude
1. **session_salt** - Critical security exclusion (not in database models, but mentioned for completeness)
2. **flagged prayers** - Prayers with flagged=True or 'flagged' attribute
3. **Active sessions** - Session table contains temporary authentication data
4. **Authentication requests** - AuthenticationRequest, AuthApproval, AuthAuditLog (temporary auth data)
5. **Security logs** - SecurityLog contains sensitive security monitoring data
6. **Notification state** - NotificationState is ephemeral UI state
7. **Verification codes** - Any verification codes in AuthenticationRequest

### Implementation Approach

#### Phase 1: Export Functionality
1. **Create export service** (`app_helpers/services/export_service.py`)
   - Database query functions for each table
   - Data sanitization and filtering
   - JSON serialization with proper formatting

2. **Add export route** (`app_helpers/routes/general_routes.py`)
   - Available to any authenticated user
   - Streaming response for large datasets
   - Rate limiting to prevent abuse

3. **Export UI** (main navigation)
   - Export button accessible to all users
   - Progress indicator
   - Download link generation

#### Phase 2: Import Functionality (for forked communities)
1. **Create import service** (`app_helpers/services/import_service.py`)
   - JSON validation and parsing
   - Database schema compatibility checking
   - Conflict resolution for existing data

2. **Import command line tool**
   - Standalone script for new instance setup
   - Database initialization and population
   - User notification about password resets

#### Phase 3: UI Enhancement
1. **Enhanced export interface**
   - Export history and re-download options
   - Export progress tracking
   - Clear documentation about excluded content

### API Endpoints

#### Community Export
```
GET /export/database
- Requires user authentication
- Returns streaming JSON response
- Content-Type: application/json
- Content-Disposition: attachment; filename="community_export_YYYY-MM-DD.json"
```

#### Export Status (for large datasets)
```
GET /export/status/{export_id}
- Returns export progress
- Allows cancellation of in-progress exports
```

### File Structure
```
app_helpers/
├── services/
│   ├── export_service.py      # Core export logic
│   └── import_service.py      # Import functionality
├── routes/
│   └── general_routes.py      # Add export endpoints
└── utils/
    └── data_sanitization.py   # Security filtering utilities

scripts/
└── import_community.py        # Command-line import tool

templates/
└── base.html                  # Add export link to navigation
```

### Security Considerations

1. **Access Control**
   - Available to any authenticated user
   - Rate limiting to prevent abuse
   - Monitor for excessive download patterns

2. **Data Filtering**
   - Exclude session salts (if they exist)
   - Filter out flagged prayers and their related data (PrayerAttribute, PrayerActivityLog)
   - Exclude temporary authentication data (Session, AuthenticationRequest, etc.)
   - Exclude security monitoring data (SecurityLog, AuthAuditLog)
   - Exclude ephemeral UI state (NotificationState)

3. **Download Security**
   - Rate limiting per user
   - Monitor download patterns
   - Standard web security headers

### Performance Considerations

1. **Large Dataset Handling**
   - Streaming responses for memory efficiency
   - Chunked processing for large tables
   - Background job processing for very large exports

2. **Database Impact**
   - Read-only queries to minimize lock time
   - Optional read replica usage
   - Export scheduling during low-traffic periods

### User Experience

1. **User Interface**
   - Clear export button accessible to all users
   - Progress indication and estimated completion time
   - Download history and re-download options

2. **Community Communication**
   - Clear documentation about what's included/excluded
   - Instructions for community forking
   - Information about flagged content exclusion

### Testing Strategy

1. **Unit Tests**
   - Export service data filtering
   - JSON serialization accuracy
   - Security field exclusion verification

2. **Integration Tests**
   - Complete export/import cycle
   - Large dataset performance
   - Error handling and recovery

3. **Security Tests**
   - Verify session salt exclusion (if applicable)
   - Confirm flagged prayers and related data are filtered out
   - Verify authentication/session data exclusion
   - Confirm security logs are not included
   - Export file content validation

## Implementation Timeline

### Week 1: Core Export Service
- Implement export_service.py
- Add basic user-accessible route
- Create data filtering utilities

### Week 2: User UI and Testing
- Add export interface to main navigation
- Implement comprehensive test suite
- Security review and validation

### Week 3: Import Functionality
- Create import service and CLI tool
- Test complete export/import cycle
- Documentation and user guides

### Week 4: Polish and Deployment
- Performance optimization
- User experience improvements
- Production deployment and monitoring

## Configuration Options

Add to application configuration:
```python
# Export feature settings
COMMUNITY_EXPORT_ENABLED = True
EXPORT_MAX_FILE_SIZE = "100MB"
EXPORT_RATE_LIMIT = "1 per hour per user"
EXPORT_RETENTION_DAYS = 7
```

## Success Metrics

- Successful export/import of complete community data
- Proper exclusion of session salts and flagged prayers
- Performance acceptable for communities up to 10,000 users
- User satisfaction with forked community completeness
- Community confidence in backup accessibility

This design provides a transparent, comprehensive community export feature that enables both backup maintenance and community forking while excluding only the minimal necessary data (session salts and flagged content).