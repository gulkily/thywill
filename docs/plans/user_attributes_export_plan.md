# User Attributes Export Plan

## Overview
Implement bidirectional sync for user attributes through a dedicated `user_attributes.txt` archive file, addressing the current gap where user attribute changes stay only in the database.

## Current State Analysis

### Existing Export Capabilities
- **Complete database export**: `export_service.py` exports all database data to text archives
- **Real-time sync**: Prayer activities and user registrations sync bidirectionally
- **Manual export**: `./thywill export-all` command for full database → archive sync

### Current Gap
- **User attributes**: Changes like `welcome_message_dismissed` are not synced back to archives
- **Missing bidirectional sync**: User attribute changes stay only in database
- **No user attributes file**: Currently exports only `notification_states.txt` for users

## Implementation Plan

### 1. Create User Attributes File Structure
**Location**: `text_archives/users/user_attributes.txt`

**Format**:
```
User Attributes

username: ilyag
is_supporter: true
supporter_since: 2025-07-01
welcome_message_dismissed: true

username: testmic
is_supporter: false
welcome_message_dismissed: false

username: Alice_Johnson
is_supporter: true
supporter_since: 2025-07-15
welcome_message_dismissed: true
```

### 2. Export Service Integration
**Add to `export_service.py`**:
```python
def export_user_attributes(self):
    """Export user attributes to text archive"""
    # Query all users with their attributes
    # Write to text_archives/users/user_attributes.txt
    # Include: is_supporter, supporter_since, welcome_message_dismissed
```

### 3. Import Service Integration
**Add to `text_importer_service.py`**:
```python
def import_user_attributes(self):
    """Import user attributes from text archive"""
    # Parse text_archives/users/user_attributes.txt
    # Update User model fields in database
    # Handle missing users gracefully
```

### 4. Real-time Sync (Optional)
**Add archive update functions**:
```python
def update_user_attribute_in_archive(user_id: str, attribute: str, value: any):
    """Update user attribute in archive file immediately"""
    # Update specific user attribute in user_attributes.txt
    # Maintain archive-first philosophy
```

## Technical Implementation

### Files to Modify
1. **`app_helpers/services/export_service.py`** - Add user attributes export
2. **`app_helpers/services/text_importer_service.py`** - Add user attributes import
3. **`app_helpers/services/text_archive_service.py`** - Add real-time attribute sync (optional)
4. **`archive_management.py`** - Update export/import commands

### Database Schema
User attributes already exist in User model:
```python
welcome_message_dismissed: bool = Field(default=False)
# New fields for supporter badges:
is_supporter: bool = Field(default=False)
supporter_since: datetime | None = Field(default=None)
```

### Export Integration
Add to existing export categories in `export_service.py`:
```python
def export_all_database_data(self):
    # ... existing exports ...
    self.export_user_attributes()  # Add this line
```

## Benefits
- **Bidirectional sync**: Manual archive edits and database changes stay in sync
- **Centralized attributes**: All user flags in one manageable file
- **Archive-first compliance**: Maintains system philosophy
- **Easy management**: Simple text file editing for attribute changes
- **Backup/restore**: User attributes included in full archive exports

## Testing
- Export user attributes to archive file
- Import attributes from archive file
- Verify attribute changes sync bidirectionally
- Test with missing users/attributes
- Validate file format consistency

## Timeline
- **Phase 1**: Export service integration (2 hours)
- **Phase 2**: Import service integration (2 hours)
- **Phase 3**: Real-time sync (1 hour, optional)
- **Phase 4**: Testing and validation (1 hour)

**Total**: 5-6 hours implementation