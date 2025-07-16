# Supporter Badges Implementation Plan

## Overview
Add supporter badges for users who financially support ThyWill, with manual marking through text archives and simple UI display.

## Architecture

### 1. Database Schema
**Add to User model in `models.py`:**
```python
is_supporter: bool = Field(default=False)  # Manual supporter flag
supporter_since: datetime | None = Field(default=None)  # When they became a supporter
```

### 2. Text Archive Integration
**Dedicated user attributes file:** `text_archives/users/user_attributes.txt`
- Separate file for all user attributes including supporter status
- Clean format with username blocks and key-value pairs
- Manual editing for easy supporter management
- Bidirectional sync with database through export/import system

### 3. UI Display
**Badge locations:**
- User display names (prayers, comments, profiles)
- Simple heart icon (♥) or "Supporter" text next to name
- Consistent styling across all views

## Implementation Steps

### Phase 1: Database Schema & Archive Integration
1. Add supporter fields to User model
2. Create migration for new columns
3. Implement user attributes export/import (see `user_attributes_export_plan.md`)
4. Test archive import/export with new fields

### Phase 2: UI Integration
1. Add supporter badge display helper function
2. Update templates to show badges:
   - Prayer cards (`templates/prayer_card.html`)
   - Prayer feed (`templates/index.html`)
   - User profiles (if applicable)
3. Add simple CSS styling for badges

### Phase 3: Admin Tools (Optional)
1. Add supporter toggle to admin interface
2. Bulk supporter management if needed

## Technical Details

### Database Migration
```sql
ALTER TABLE user ADD COLUMN is_supporter BOOLEAN DEFAULT FALSE;
ALTER TABLE user ADD COLUMN supporter_since DATETIME;
```

### Template Helper
```python
def render_supporter_badge(user):
    if user.is_supporter:
        return '<span class="supporter-badge">♥</span>'
    return ''
```

### Text Archive Format
**File**: `text_archives/users/user_attributes.txt`
```
User Attributes

username: ilyag
is_supporter: true
supporter_since: 2025-07-01
welcome_message_dismissed: true

username: testmic
is_supporter: false
welcome_message_dismissed: false
```

## Benefits
- **Manual Control**: Full control over supporter status
- **Archive-First**: Integrates with existing text archive system
- **Simple**: No payment processing complexity
- **Flexible**: Easy to add/remove supporter status
- **Transparent**: Clear audit trail through archives

## Files to Modify
- `models.py` - Add supporter fields
- `templates/prayer_card.html` - Add badge display
- `templates/index.html` - Add badge display
- `app_helpers/template_helpers.py` - Add badge helper function
- `app_helpers/services/export_service.py` - Add user attributes export
- `app_helpers/services/text_importer_service.py` - Add user attributes import
- Migration file - Database schema update

## Testing
- Archive import/export with supporter fields
- Badge display in all UI locations
- Migration rollback safety
- Manual supporter status changes

## Timeline
- **Phase 1**: 3-4 hours (database schema + archive integration)
- **Phase 2**: 2-3 hours (UI integration)
- **Phase 3**: 1 hour (admin tools, optional)

**Total**: 6-8 hours implementation

## Dependencies
- See `user_attributes_export_plan.md` for detailed archive integration implementation