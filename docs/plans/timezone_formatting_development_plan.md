# Timezone-Aware Timestamp Formatting Development Plan

## Implementation Steps

### Step 1: Create Timezone Utility Functions
- **File**: `app_helpers/timezone_utils.py` (new)
- **Functions**:
  - `format_timestamp_for_timezone(dt, timezone_str)` - Convert UTC to user timezone
  - `get_timezone_display_name(timezone_str)` - Get friendly timezone name
  - `validate_timezone(timezone_str)` - Ensure timezone is valid

### Step 2: Frontend Timezone Detection
- **File**: `templates/base.html`
- **Add**: JavaScript timezone detection script
- **Store**: User timezone in sessionStorage
- **Send**: Timezone with HTMX requests via headers

### Step 3: Update Backend Route Handlers
- **File**: `app_helpers/routes.py`
- **Modify**: Extract timezone from request headers
- **Update**: Pass timezone to template context
- **Routes**: Feed, prayer detail, archive pages

### Step 4: Create Template Filter
- **File**: `app.py` or `app_helpers/template_filters.py`
- **Add**: Jinja2 filter `|timezone_format` for timestamp conversion
- **Usage**: `{{ prayer.created_at|timezone_format(user_timezone) }}`

### Step 5: Update Templates
- **Files**: All templates with timestamps
- **Change**: Replace raw timestamp displays with timezone filter
- **Templates**:
  - `templates/index.html` - Prayer feed
  - `templates/prayer_detail.html` - Prayer details
  - `templates/archive.html` - Archive timestamps
  - Any other timestamp displays

### Step 6: Handle Edge Cases
- **JavaScript disabled**: Fallback to server timezone
- **Invalid timezone**: Fallback to UTC
- **Empty timezone**: Default to UTC

### Step 7: Testing
- **Unit tests**: Timezone utility functions
- **Integration tests**: Template rendering with timezones
- **Manual tests**: Different timezone scenarios

## Code Examples

### Timezone Utility Function
```python
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional

def format_timestamp_for_timezone(dt: datetime, timezone_str: Optional[str] = None) -> str:
    if not timezone_str:
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    
    try:
        user_tz = ZoneInfo(timezone_str)
        local_dt = dt.replace(tzinfo=ZoneInfo("UTC")).astimezone(user_tz)
        return local_dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
```

### JavaScript Timezone Detection
```javascript
// Store user timezone
const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
sessionStorage.setItem('userTimezone', userTimezone);

// Add to HTMX requests
document.body.addEventListener('htmx:configRequest', function(evt) {
    evt.detail.headers['X-User-Timezone'] = sessionStorage.getItem('userTimezone') || 'UTC';
});
```

### Template Filter
```python
@app.template_filter('timezone_format')
def timezone_format_filter(dt, timezone_str=None):
    return format_timestamp_for_timezone(dt, timezone_str)
```

## Files to Create/Modify

### New Files
- `app_helpers/timezone_utils.py`

### Modified Files
- `templates/base.html` - Add timezone detection
- `app.py` - Register template filter
- `app_helpers/routes.py` - Extract timezone from headers
- `templates/index.html` - Update timestamp displays
- `templates/prayer_detail.html` - Update timestamp displays
- Any other templates with timestamps

## Validation Checklist
- [ ] Timezone detection works in browser
- [ ] Timestamps display in user's local timezone
- [ ] Fallback works when JavaScript disabled
- [ ] Invalid timezones handled gracefully
- [ ] All timestamp displays updated
- [ ] Tests pass
- [ ] No performance degradation

## Estimated Time
- Step 1-2: 1 hour
- Step 3-4: 1 hour  
- Step 5: 2 hours
- Step 6-7: 1 hour
- Total: 5 hours