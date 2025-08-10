# Daily Priority Prayers - Development Plan

## Stage 1: Core Service Logic (1.5 hours)
**Goal**: Implement priority management using existing PrayerAttribute system
**Dependencies**: None (uses existing schema)
**Changes**:
- Create `set_daily_priority(prayer_id, admin_user)` function using `prayer.set_attribute()`
- Create `remove_daily_priority(prayer_id)` function using `prayer.remove_attribute()`
- Create `expire_old_priorities()` scheduled task that removes old priority attributes
- Create `is_daily_priority(prayer, session)` helper function
**Testing**: Priority setting, removal, and automatic expiration using attributes
**Risks**: Timezone handling for midnight expiration

## Stage 2: Admin Menu Integration (1 hour)
**Goal**: Add admin menu options for priority management
**Dependencies**: Stage 1 complete, existing admin role system
**Changes**:
- Add "Mark as Daily Priority" menu option to prayer cards (admin only)
- Add "Remove Daily Priority" menu option for current priorities
- Update prayer menu template with conditional admin options
- Create priority management route handlers using attribute system
**Testing**: Menu visibility, admin-only access, functionality
**Risks**: Template integration conflicts

## Stage 3: Visual Indicators & UI (1 hour)
**Goal**: Add visual distinction for priority prayers in existing displays
**Dependencies**: Stage 2 complete
**Changes**:
- Add priority badge/icon to prayer cards
- Add CSS styling for priority prayer highlighting
- Update prayer card templates with priority detection
- Add data attributes for JavaScript priority handling
**Testing**: Visual indicators, responsive design, accessibility
**Risks**: CSS conflicts, template integration

## Stage 4: Admin Logging & Cleanup (0.5 hours)
**Goal**: Add system maintenance and scheduled expiration
**Dependencies**: Stage 3 complete
**Changes**:
- Schedule midnight expiration task in application startup
- Add priority status to prayer card data attributes for UI
- Ensure SecurityLog entries via existing `set_attribute()` logging
**Testing**: Scheduled task execution, automatic cleanup
**Risks**: Task scheduling reliability

## Database Changes
- **No schema changes required** - uses existing `PrayerAttribute` table
- Priority stored as attribute: `daily_priority` = date string (e.g., "2025-08-09")
- Automatic expiration by comparing attribute date to current date

## Function Signatures
```python
def set_daily_priority(prayer_id: str, admin_user: User, session: Session) -> bool
def remove_daily_priority(prayer_id: str, session: Session) -> bool  
def expire_old_priorities(session: Session) -> int
def is_daily_priority(prayer: Prayer, session: Session) -> bool
```

## Attribute System Usage
- **Attribute name**: `daily_priority`
- **Attribute value**: Current date string (YYYY-MM-DD format)
- **Expiration logic**: Remove attributes where value < current date
- **Logging**: Automatic via existing `prayer.set_attribute()` system

## Testing Strategy
- Unit tests for priority management functions using attributes
- Integration tests for admin menu functionality  
- Visual tests for priority badge display
- Attribute expiration tests for cleanup logic

## Risk Assessment
**High**: Timezone handling for midnight expiration
**Medium**: Template integration, CSS styling conflicts
**Low**: Admin permission integration, attribute-based logging

## Future Feed Integration Notes
This implementation provides the foundation for future priority-focused feeds without modifying existing feed behavior. The `is_daily_priority()` helper and attribute system will make it easy to create dedicated priority feeds or modify existing feeds as separate feature requests.