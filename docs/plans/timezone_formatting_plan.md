# Timezone-Aware Timestamp Formatting Plan

## Overview
Implement user timezone detection and formatting to display all timestamps in the user's local timezone instead of server time.

## Current State Analysis
- All timestamps currently displayed in server timezone (likely UTC)
- User sees timestamps that don't match their local time
- No timezone preference storage or detection

## Implementation Strategy

### Phase 1: Frontend Timezone Detection
- Add JavaScript timezone detection using `Intl.DateTimeFormat().resolvedOptions().timeZone`
- Store user timezone in session/localStorage
- Send timezone info to server on relevant requests

### Phase 2: Backend Timezone Support
- Add timezone parameter to timestamp formatting functions
- Create utility functions for timezone conversion
- Update all timestamp display endpoints to accept timezone

### Phase 3: Database Schema (Optional)
- Consider adding `timezone` field to User model for persistent preference
- Fallback to browser detection if no stored preference

## Technical Implementation

### Frontend Changes
- Add timezone detection script to base template
- Create JavaScript utility functions for timezone handling
- Update HTMX requests to include timezone data

### Backend Changes
- Create `format_timestamp_for_timezone()` utility function
- Update template filters/functions for timezone-aware formatting
- Modify API responses with timezone-aware timestamps

### Templates to Update
- Prayer feed timestamps
- Prayer detail page timestamps
- Archive timestamps
- Activity log timestamps
- Any other user-facing time displays

## Files to Modify
- `templates/base.html` - Add timezone detection script
- `app_helpers/utils.py` - Add timezone formatting utilities
- `app_helpers/routes.py` - Update routes to handle timezone
- Template files with timestamp displays
- JavaScript files for timezone handling

## Considerations
- Handle users with JavaScript disabled (fallback to server time)
- Timezone abbreviation display (PST, EST, etc.)
- Daylight saving time transitions
- Performance impact of timezone conversions
- Caching considerations for timezone-aware content

## Testing
- Test across different timezones
- Test daylight saving time boundaries
- Test JavaScript disabled scenarios
- Verify all timestamp displays are converted

## Timeline
- Phase 1: 2-3 hours (frontend detection)
- Phase 2: 3-4 hours (backend integration)  
- Phase 3: 1-2 hours (optional DB storage)
- Testing: 1-2 hours

Total estimated effort: 6-11 hours