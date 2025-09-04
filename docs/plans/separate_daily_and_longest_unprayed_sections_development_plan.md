# Separate Daily and Longest Unprayed Sections - Development Plan

## Stage 1: Create New Feed Type for Prayers Needing Attention (<2 hours)
**Goal**: Add new "prayers_needing_attention" feed type that shows prayers sorted by longest time since last prayer mark

**Dependencies**: None

**Changes**:
- Add new feed type "prayers_needing_attention" to feed_operations.py 
- Create SQL query to find prayers with oldest last prayer mark (excluding daily priorities)
- Add feed count calculation in prayer_helpers.py get_feed_counts()
- Update navigation template with new feed tab
- Update feed display template with appropriate section header

**Testing**: Verify new feed type shows correct prayers in chronological order (oldest prayer marks first)

**Risks**: Low - Similar to existing recent_activity feed logic but inverted

## Stage 2: Modify Daily Prayer Feed to Show Only Priority Prayers (<2 hours)
**Goal**: Update existing "daily_prayer" feed type to display only prayers marked with is_daily_priority=true

**Dependencies**: Stage 1 complete

**Changes**:
- Modify daily_prayer query in feed_operations.py to filter only is_daily_priority=true prayers
- Remove hybrid sorting logic that combines priority and non-priority prayers
- Update daily_prayer feed count to count only priority prayers
- Update feed template description to clarify it shows only daily priorities

**Testing**: Verify daily prayer feed shows only manually marked priority prayers

**Risks**: Low - Simplifies existing query logic

## Stage 3: Update UI Labels and Navigation (<1 hour)
**Goal**: Update section headers and navigation to clearly distinguish the two feed types

**Dependencies**: Stages 1-2 complete

**Changes**:
- Update feed.html template headers:
  - "Daily Prayer Focus" → "Daily Priority Prayers"
  - Add "Prayers Needing Attention" header for new feed type
- Update feed_navigation.html:
  - Change "⭐ Daily" tab label if needed for clarity
  - Add "Prayers Needing Attention" navigation tab with appropriate icon
- Update empty state messages for both feed types

**Testing**: Verify clear visual distinction between the two sections and intuitive navigation

**Risks**: Very low - UI text changes only

## Stage 4: Test Integration and Performance (<1 hour)
**Goal**: Ensure both feeds work correctly together and maintain performance

**Dependencies**: Stages 1-3 complete

**Changes**:
- Test feed switching between daily priorities and prayers needing attention
- Verify feed counts are accurate for both sections
- Test with various prayer states (new, prayed, archived, flagged)
- Confirm existing daily priority management features still work

**Testing**: 
- Load test with multiple feed types
- Verify prayer marking functionality works in both feeds
- Test admin daily priority controls remain functional

**Risks**: Low - Both feeds use existing prayer query patterns

## Database Schema
No database changes required - uses existing Prayer, PrayerMark, and PrayerAttribute tables

## Function Signatures
```python
# New function in prayer_helpers.py
def get_prayers_needing_attention(session: Session, limit: int = 50) -> list[Prayer]

# Modified function signature (no change to external interface)  
def get_feed_counts(user_id: str) -> dict  # Add 'prayers_needing_attention' key
```

## Testing Strategy
- Unit tests for new prayers needing attention query logic
- Integration tests for both feed types working independently 
- UI tests for navigation between feeds
- Performance tests for database queries with realistic data volumes

## Risk Assessment
**Low Risk**: All changes use existing database schema and proven query patterns. Separation of concerns reduces complexity rather than adding it. No breaking changes to existing functionality.