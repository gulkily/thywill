# Prayer Tracking Visual Indicators - Step 1: Development Plan

## Overview
Implementation plan for adding visual indicators to show when users last prayed each prayer, supporting multiple prayer interactions and session continuity.

## Stage 1: Database Query Foundation (~1.5 hours)
**Goal**: Create efficient database queries to retrieve user prayer interaction history

### Tasks:
- Add helper function to `app_helpers/services/prayer_helpers.py` to get user's last prayer mark timestamp for a prayer
- Create batch query function to get last prayer timestamps for multiple prayers efficiently
- Add optional prayer count query (number of times user has prayed each prayer)
- Write unit tests for new query functions

### Deliverables:
- `get_user_last_prayer_mark(user_id, prayer_id)` function
- `get_user_prayer_mark_batch(user_id, prayer_ids)` function  
- `get_user_prayer_counts(user_id, prayer_ids)` function (optional)
- Unit tests covering edge cases (no marks, multiple marks, etc.)

### Success Criteria:
- Query functions return accurate timestamps
- Batch queries perform efficiently (< 100ms for 50 prayers)
- Tests pass for all edge cases

## Stage 2: Prayer Card Visual Design (~1 hour)
**Goal**: Design and implement visual indicators for prayer cards

### Tasks:
- Design CSS classes for prayer status indicators (prayed recently, not prayed, multiple times)
- Add timestamp formatting utility for "X hours/days ago" display
- Create prayer status indicator HTML template partial
- Implement responsive design for mobile devices

### Deliverables:
- CSS classes: `.prayer-status-indicator`, `.prayed-recently`, `.prayed-multiple`
- JavaScript/template function for relative timestamp formatting
- Template partial: `templates/components/prayer_status_indicator.html`
- Mobile-responsive indicator styling

### Success Criteria:
- Visual indicators are clear and non-intrusive
- Timestamps display in user-friendly format
- Design works across all screen sizes

## Stage 3: Feed Integration (~1.5 hours)
**Goal**: Integrate prayer status indicators into all prayer feeds

### Tasks:
- Update `get_feed_data()` functions to include prayer status data
- Modify prayer card templates to display status indicators
- Update feed rendering logic to batch-query prayer statuses
- Ensure indicators appear in all feed types (main, personal, flagged, etc.)

### Deliverables:
- Updated feed functions with prayer status data
- Modified `templates/components/prayer_card.html` with status indicators
- Status indicators in all feed templates
- Performance optimization for status queries

### Success Criteria:
- All feeds show prayer status indicators
- Feed load times increase by < 20%
- Visual indicators accurately reflect prayer history

## Stage 4: Real-time Updates (~1 hour)
**Goal**: Update prayer status indicators when users pray prayers

### Tasks:
- Update prayer marking JavaScript to refresh status indicators after marking
- Implement HTMX response to update prayer card status without page reload
- Add visual feedback for successful prayer marking
- Test status updates across different feed contexts

### Deliverables:
- Updated prayer marking JavaScript with status refresh
- HTMX response templates for updated prayer cards
- Visual feedback for prayer actions
- Cross-feed update testing

### Success Criteria:
- Prayer status updates immediately after marking
- No page reloads required for status updates
- Visual feedback confirms successful actions

## Stage 5: Feature Flag & Configuration (~30 minutes)
**Goal**: Add feature flag for controlled rollout

### Tasks:
- Add `PRAYER_STATUS_INDICATORS_ENABLED` environment variable
- Update templates to conditionally show status indicators
- Add feature flag to `.env.example` with default value
- Document new environment variable in CLAUDE.md

### Deliverables:
- Feature flag implementation
- Conditional template logic
- Updated environment documentation
- Default configuration for new installations

### Success Criteria:
- Feature can be enabled/disabled via environment variable
- Documentation is complete and accurate
- Default state is appropriate for new users

## Stage 6: Testing & Polish (~1 hour)
**Goal**: Comprehensive testing and user experience refinements

### Tasks:
- Write integration tests for prayer status functionality
- Test performance with large prayer feeds (100+ prayers)
- Add error handling for failed status queries
- Validate accessibility of visual indicators

### Deliverables:
- Integration test suite for prayer status features
- Performance benchmarks and optimizations if needed
- Error handling for database query failures
- Accessibility validation (screen reader compatibility, color contrast)

### Success Criteria:
- All tests pass consistently
- Performance meets requirements (< 20% increase in load time)
- Feature is accessible to users with disabilities
- Graceful degradation when status queries fail

## Technical Architecture

### Database Schema
**No changes required** - leveraging existing `PrayerMark` table:
- `user_id`, `prayer_id`, `created_at` provide all needed data
- Queries will use existing indexes on `user_id` and `prayer_id`

### Performance Considerations
- Batch queries to minimize database round trips
- Consider caching for frequently accessed prayer statuses
- Use efficient SQL with proper JOIN operations
- Monitor query performance in production

### UI/UX Design Principles
- **Subtle but Clear**: Indicators should be noticeable without overwhelming prayer content
- **Consistent**: Same visual language across all feed types
- **Informative**: Timestamps should be meaningful ("2 hours ago" vs "14:30")
- **Accessible**: Proper contrast ratios and screen reader support

## Implementation Dependencies
- Existing `PrayerMark` model and database structure
- Current feed rendering system in `app_helpers/routes/`
- Prayer card template structure
- HTMX integration for dynamic updates

## Risk Mitigation
- **Performance Risk**: Use batch queries and monitor database performance
- **UI Clutter Risk**: Keep indicators minimal and well-designed
- **Browser Compatibility**: Test across modern browsers
- **Mobile Experience**: Ensure indicators work well on small screens

## Post-Implementation Considerations
- Monitor user feedback on indicator usefulness
- Track performance metrics for prayer feeds
- Consider future enhancements (prayer streaks, advanced filtering)
- Evaluate need for user preferences (show/hide indicators)

## Total Estimated Time: ~6.5 hours
This modular approach allows for incremental development and testing, with each stage building on the previous one while maintaining a working system throughout the process.