# Step 2: Development Plan - Profile Card Interactive Links

## Implementation Strategy

This feature will extend the existing profile system to add clickable links to prayer statistics. We'll create new routes and views while maintaining the current architecture and design patterns.

## Stage 1: Backend Route Infrastructure (≤ 2 hours)

### 1.1 Add New Profile Routes (45 minutes)
**File**: `/home/wsl/thywill/app_helpers/routes/user_routes.py`

Add three new routes that extend the existing profile system:
- `GET /profile/{user_id}/prayers` - User's prayer requests
- `GET /profile/{user_id}/prayed` - Prayers user has marked/prayed for  
- `GET /profile/{user_id}/unique` - Unique prayers breakdown

**Implementation Details**:
- Follow existing pattern from `user_profile()` function (lines 26-147)
- Reuse existing query patterns from lines 45-62 (prayers authored, prayers marked, distinct prayers)
- Add pagination support (default 20 items per page)
- Implement proper permission checks (same as current profile visibility)
- Include user timezone support via `get_user_timezone_from_request()`

### 1.2 Create Service Functions (45 minutes)  
**File**: `/home/wsl/thywill/app_helpers/services/profile_data_service.py` (new)

Create reusable service functions:
- `get_user_prayer_requests(user_id, page, per_page, session)`
- `get_user_prayers_marked(user_id, page, per_page, session)` 
- `get_user_unique_prayers_info(user_id, page, per_page, session)`

**Benefits**:
- Consolidates database logic
- Provides consistent pagination
- Enables reuse across routes
- Maintains existing database query patterns from user_routes.py

### 1.3 URL Structure & Routing (30 minutes)
Register new routes in main application following existing patterns:
- Consistent with current `/user/{user_id}` structure
- SEO-friendly URLs with clear intent
- Proper HTTP status codes and error handling

## Stage 2: Frontend Template System (≤ 2 hours)

### 2.1 Update Profile Card Template (30 minutes)
**File**: `/home/wsl/thywill/templates/profile.html`

Modify the Prayer Statistics section (lines 250-268):
- Transform static numbers into clickable links when count > 0
- Add hover states and visual indicators (cursor: pointer)
- Maintain existing color scheme (purple, green, blue for each stat)
- Keep zero values as plain text (non-clickable)

**HTML Structure**:
```html
<!-- Instead of static spans, use conditional links -->
{% if stats.prayers_authored > 0 %}
  <a href="/profile/{{ profile_user.display_name }}/prayers" 
     class="font-medium text-purple-600 dark:text-purple-400 hover:text-purple-800 dark:hover:text-purple-300 hover:underline cursor-pointer">
    {{ stats.prayers_authored }}
  </a>
{% else %}
  <span class="font-medium text-purple-600 dark:text-purple-400">0</span>
{% endif %}
```

### 2.2 Create New View Templates (90 minutes)
Create three new templates following existing design patterns:

**Template**: `/home/wsl/thywill/templates/profile_prayers.html`
- Shows user's prayer requests in chronological order
- Uses existing prayer card layout (similar to main feed)
- Includes breadcrumb navigation back to profile
- Pagination controls at bottom

**Template**: `/home/wsl/thywill/templates/profile_prayed.html`  
- Lists prayers user has marked with original authors
- Shows when each prayer was marked/prayed
- Links to original prayers
- Author attribution with supporter badges

**Template**: `/home/wsl/thywill/templates/profile_unique.html`
- Shows count breakdown and summary stats
- Optional list view of unique prayers
- Summary cards showing engagement metrics

**Common Elements**:
- Extend existing `base.html` template
- Use consistent header styling and navigation
- Maintain dark mode support
- Include user timezone formatting
- Responsive design for mobile/desktop

## Stage 3: Frontend Interactivity & Polish (≤ 1 hour)

### 3.1 CSS Styling Updates (20 minutes)
**Files**: Existing CSS or inline styles
- Add hover states for clickable statistics
- Ensure visual consistency with existing link styles
- Loading states for new page transitions
- Maintain accessibility (proper contrast, focus states)

### 3.2 JavaScript Enhancements (20 minutes)
**Optional**: Add subtle loading indicators or transition effects
- Maintain existing JavaScript patterns
- No complex client-side logic needed
- Focus on progressive enhancement

### 3.3 Navigation & UX Polish (20 minutes)
- Clear breadcrumb trails on new pages
- "Back to Profile" links on all new views
- Page titles that reflect current view
- Meta descriptions for better SEO

## Stage 4: Testing & Validation (≤ 1 hour)

### 4.1 Database Query Testing (30 minutes)
- Test with users who have zero counts (ensure non-clickable)
- Test with high-activity users (pagination works)
- Verify performance with existing database indices
- Test edge cases (users with no prayers, etc.)

### 4.2 UI/UX Testing (20 minutes)
- Mobile responsiveness on new pages
- Dark mode consistency
- Link hover states work properly
- Navigation flows are intuitive

### 4.3 Permission & Privacy Testing (10 minutes)  
- Verify privacy controls work on new views
- Test with different user roles (admin, regular user)
- Ensure archived/flagged prayers are properly filtered

## Technical Implementation Notes

### Database Integration
- Leverage existing query patterns from `user_routes.py:45-62`
- Use existing pagination patterns from prayer feed system
- Maintain existing performance characteristics (no new complex joins)

### URL Structure
```
/profile/{user_id}/prayers    # Prayer requests by user
/profile/{user_id}/prayed     # Prayers user has marked  
/profile/{user_id}/unique     # Unique prayers info
```

### Template Hierarchy
```
base.html
├── profile.html (modified - clickable stats)
├── profile_prayers.html (new)
├── profile_prayed.html (new)
└── profile_unique.html (new)
```

### Existing Code Integration Points
- **Routes**: Extend `app_helpers/routes/user_routes.py`
- **Templates**: Modify `templates/profile.html`, create 3 new templates
- **Services**: Create new `app_helpers/services/profile_data_service.py`
- **Styling**: Leverage existing CSS classes and color scheme

## Risk Mitigation

### Performance Risks
- **Issue**: New routes could be slow for active users
- **Solution**: Implement pagination early, monitor query performance
- **Fallback**: Cache frequently accessed profile data

### UI/UX Risks  
- **Issue**: Links might not be obvious to users
- **Solution**: Clear hover states and visual indicators
- **Testing**: User testing on mobile and desktop

### Data Consistency Risks
- **Issue**: Statistics might be inconsistent between profile card and detailed views
- **Solution**: Share query logic via service layer
- **Validation**: Automated tests comparing counts

## Success Metrics

### Technical Success
- [ ] All routes return data within 2 seconds
- [ ] Pagination handles 100+ prayers smoothly
- [ ] Zero visual regression on existing profile pages
- [ ] Mobile responsive design maintains usability

### User Experience Success
- [ ] Click-through rate on statistics > 10% (analytics)
- [ ] Users successfully navigate back to profile
- [ ] Zero values remain visually non-interactive
- [ ] Consistent supporter badge display across all views

## Dependencies

### Required Components
- Existing user authentication system ✅
- Current profile statistics queries ✅  
- Template rendering system ✅
- Pagination utilities (from prayer feed) ✅

### Integration Points
- Profile route system (`user_routes.py`)
- Prayer feed filtering logic (`feed_operations.py`)
- Template filter system (`shared_templates.py`)
- Supporter badge service (`UsernameDisplayService`)

## Future Extension Points

This implementation creates foundation for:
- Prayer activity timeline views
- Advanced filtering within profile views
- Social features (prayer connections, community insights)
- Export functionality for personal prayer history
- Prayer analytics and engagement metrics

---

**Estimated Total Time**: 5-6 hours across 4 stages
**Priority**: Medium complexity, high user value
**Risk Level**: Low (extends existing patterns, no schema changes)