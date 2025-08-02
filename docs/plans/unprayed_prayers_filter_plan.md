# Unprayed Prayers Filter Implementation Plan

## User Story
**As a user, I want to see prayers that I have not prayed yet, so I can discover new prayers to pray for and expand my prayer participation.**

## Current State Analysis

### Existing Prayer Marking System
- **Models**: `PrayerMark` table tracks when users pray for specific prayers
  - Fields: `id`, `username`, `prayer_id`, `created_at`, `text_file_path`
  - Links prayers to users who have prayed for them
- **Query Pattern**: System already has "new_unprayed" feed showing prayers with zero marks
- **Feed Types**: 7 existing feed types including `new_unprayed` (prayers never prayed by anyone)

### Current Feed Architecture
- **Location**: `app_helpers/routes/prayer/feed_operations.py:feed()`
- **Navigation**: `templates/components/feed_navigation.html`
- **Count Logic**: `app_helpers/services/prayer_helpers.py:get_feed_counts()`
- **Database Patterns**: Uses `LEFT JOIN` with `PrayerMark` and `HAVING COUNT() = 0` for unprayed detection

## Proposed Solution

### 1. New Feed Type: "my_unprayed"
Add a new feed type to show prayers the current user specifically hasn't prayed yet.

**Database Query Logic**:
```sql
SELECT Prayer.*, User.display_name 
FROM Prayer
LEFT JOIN User ON Prayer.author_username = User.display_name
LEFT JOIN PrayerMark ON Prayer.id = PrayerMark.prayer_id AND PrayerMark.username = :current_user
WHERE Prayer.flagged = False 
  AND Prayer.id NOT IN (SELECT prayer_id FROM PrayerAttribute WHERE attribute_name = 'archived')
  AND PrayerMark.id IS NULL
ORDER BY Prayer.created_at DESC
```

### 2. Implementation Steps

#### Phase 1: Backend Query Implementation
**File**: `app_helpers/routes/prayer/feed_operations.py`

1. **Add new feed type condition** in `feed()` function:
   ```python
   elif feed_type == "my_unprayed":
       # Prayers the current user has NOT prayed yet
       stmt = (
           select(Prayer, User.display_name)
           .outerjoin(User, Prayer.author_username == User.display_name)
           .outerjoin(PrayerMark, 
               (Prayer.id == PrayerMark.prayer_id) & 
               (PrayerMark.username == user.display_name))
           .where(Prayer.flagged == False)
           .where(exclude_archived())
           .where(PrayerMark.id.is_(None))  # User hasn't prayed this
           .order_by(Prayer.created_at.desc())
       )
   ```

2. **Add count logic** in `app_helpers/services/prayer_helpers.py:get_feed_counts()`:
   ```python
   # My unprayed (prayers user hasn't marked yet)
   counts['my_unprayed'] = s.exec(
       select(func.count(Prayer.id))
       .select_from(Prayer)
       .outerjoin(PrayerMark, 
           (Prayer.id == PrayerMark.prayer_id) & 
           (PrayerMark.username == user_id))
       .where(Prayer.flagged == False)
       .where(exclude_archived())
       .where(PrayerMark.id.is_(None))
   ).first()
   ```

#### Phase 2: UI Integration
**File**: `templates/components/feed_navigation.html`

1. **Add navigation tab** after "My Prayers":
   ```html
   <a href="/?feed_type=my_unprayed" 
      class="flex-shrink-0 inline-flex items-center gap-1.5 px-2 py-1.5 text-sm font-medium rounded-md transition-all duration-200 {% if current_feed == 'my_unprayed' %}bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-200 shadow-sm{% else %}text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-50 dark:hover:bg-gray-700{% endif %}">
     <span>🔍 Not Prayed Yet</span>
     {% if feed_counts.my_unprayed > 0 %}
       <span class="inline-flex items-center justify-center w-4 h-4 text-xs font-semibold bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 rounded-full">{{ feed_counts.my_unprayed }}</span>
     {% else %}
       <span class="inline-flex items-center justify-center w-4 h-4 text-xs font-semibold {% if current_feed == 'my_unprayed' %}bg-blue-200 dark:bg-blue-800 text-blue-800 dark:text-blue-100{% else %}bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300{% endif %} rounded-full">0</span>
     {% endif %}
   </a>
   ```

2. **Update feed description** in route docstring to include new feed type

#### Phase 3: Template Integration
**File**: `app_helpers/routes/prayer/feed_operations.py`

1. **Add feed type to template context** (already handled by existing template response)
2. **Ensure categorization filters apply** to new feed type (already handled by `apply_category_filters()`)

### 3. Technical Considerations

#### Performance Optimization
- **Query Performance**: Uses efficient `LEFT JOIN` with `IS NULL` pattern
- **Index Requirements**: Existing indexes on `prayer_id` and `username` in `PrayerMark` table sufficient
- **Scaling**: Query complexity remains O(n) with proper indexing

#### User Experience
- **Positioning**: Place after "My Prayers" tab for logical flow
- **Badge Color**: Use blue theme to distinguish from existing feeds
- **Icon**: 🔍 to represent discovery/search functionality
- **Empty State**: Show helpful message when no unprayed prayers available

#### Archive Integration
- **Compatibility**: Integrates with existing archive-first architecture
- **Text Archives**: No additional text archive fields needed (uses existing `PrayerMark` logging)
- **Export/Import**: Existing `PrayerMark` export/import handles this automatically

### 4. Testing Strategy

#### Unit Tests
**File**: `tests/unit/test_feed_filtering.py`
- Test `my_unprayed` query returns correct prayers
- Test count calculation accuracy
- Test exclusion of prayers user has already prayed
- Test archive filtering integration

#### Integration Tests
**File**: `tests/integration/test_prayer_feeds.py`  
- Test UI navigation to new feed type
- Test feed count display accuracy
- Test categorization filter compatibility

### 5. Deployment Considerations

#### Feature Flag Support
- **Optional**: Could add `MY_UNPRAYED_FEED_ENABLED` environment variable
- **Default**: Enable by default as it's core functionality
- **Rollback**: Easy to disable by removing navigation tab

#### Database Migration
- **Required**: None - uses existing table structure
- **Performance**: No schema changes needed

#### Backward Compatibility
- **Complete**: New feed type doesn't affect existing functionality
- **Safe**: Falls back to "all" feed if invalid feed_type provided

## Implementation Priority

### High Priority
1. ✅ Backend query implementation  
2. ✅ Count calculation logic
3. ✅ UI navigation integration

### Medium Priority  
4. Unit test coverage
5. Integration test coverage
6. Performance optimization review

### Low Priority
7. Feature flag implementation (optional)
8. Advanced filtering (if needed)
9. Mobile UI optimization

## Success Metrics

### Functional Requirements
- ✅ Users can access "Not Prayed Yet" feed via navigation
- ✅ Feed shows only prayers user hasn't marked as prayed
- ✅ Count badge accurately reflects number of unprayed prayers
- ✅ Excludes archived and flagged prayers
- ✅ Compatible with existing categorization filters

### Performance Requirements
- Query response time < 500ms for typical datasets
- Navigation loads without page refresh (existing HTMX)
- Count calculation doesn't impact other feed load times

### User Experience Requirements
- Intuitive placement in navigation flow
- Clear visual distinction from other feed types  
- Helpful empty state messaging
- Mobile-responsive design

## Risk Assessment

### Low Risk
- **Technical**: Uses existing, proven query patterns
- **Performance**: Leverages existing database indexes
- **UI**: Follows established navigation patterns

### Mitigation Strategies
- **Query Performance**: Monitor with existing database performance tools
- **User Confusion**: Clear labeling and positioning in navigation
- **Edge Cases**: Comprehensive test coverage for various user states

## Conclusion

This implementation provides users with a highly requested feature to discover prayers they haven't prayed yet, using the existing robust architecture. The solution is low-risk, high-value, and maintains consistency with the platform's existing patterns and performance characteristics.

**Estimated Implementation Time**: 2-4 hours
**Technical Complexity**: Low  
**User Value**: High
**Maintenance Overhead**: Minimal