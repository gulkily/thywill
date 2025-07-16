# Centralized Username Display and Supporter Badge Implementation Plan

## Overview
Create a centralized system for displaying usernames with supporter badges consistently across all templates, fixing the current partial implementation and ensuring badges appear everywhere usernames are shown.

## Current State Analysis

### Issues Identified
1. **Broken Supporter Badge**: Prayer cards expect `p.author` object but only receive `p.author_name` string
2. **Missing User Objects**: Feed operations don't provide User objects needed for supporter badges
3. **Inconsistent Display Patterns**: Different templates use different field names and patterns
4. **Missing Badge Coverage**: Supporter badges only partially implemented in one template

### Username Display Locations
1. **Prayer Cards**: `templates/components/prayer_card.html` - Main prayer feed (broken badge)
2. **Activity Feed**: `templates/activity.html` - Prayer activity (no badges)
3. **User Profiles**: `templates/profile.html` - Profile pages (no badges)
4. **Users Directory**: `templates/users.html` - Community members (no badges)
5. **Admin Panel**: `templates/admin.html` - Flagged prayers (no badges)
6. **Header**: `templates/base.html` - User greeting (no badges)
7. **Auth Requests**: `templates/auth_requests.html` - Authentication system (no badges)
8. **Invite Tree**: `templates/invite_tree.html` - Invitation hierarchy (no badges)

## Implementation Plan

### Phase 1: Create Centralized Username Display Helper (1 hour)

#### Task 1.1: Create Username Display Service
**File**: `app_helpers/services/username_display_service.py`
**Purpose**: Centralized service for username display with supporter badges

```python
class UsernameDisplayService:
    def get_user_display_data(self, username: str, session: Session) -> Dict:
        """Get complete user display data including supporter status"""
        
    def render_username_with_badge(self, username: str, session: Session) -> str:
        """Render username with supporter badge HTML"""
        
    def add_user_objects_to_prayers(self, prayers: List[Dict], session: Session) -> List[Dict]:
        """Add user objects to prayer dictionaries for badge support"""
```

#### Task 1.2: Create Template Helper Function
**File**: `app_helpers/template_filters.py`
**Add**: `username_display_filter` that works with just a username string

```python
def username_display_filter(username: str) -> str:
    """Display username with supporter badge from username string"""
```

### Phase 2: Update Data Structures (2 hours)

#### Task 2.1: Fix Feed Operations
**File**: `app_helpers/routes/prayer/feed_operations.py`
**Update**: `build_prayer_dict()` to include User objects

```python
# Current prayer dict structure
prayer_dict = {
    'author_name': str,
    'author_id': str,
    # Add:
    'author': User object,
    'author_display_html': str with badge
}
```

#### Task 2.2: Update Activity Feed Data
**File**: `app_helpers/routes/prayer/feed_operations.py`
**Update**: Activity feed queries to include User objects for both authors and markers

#### Task 2.3: Update User Profile Data
**File**: `app_helpers/routes/user_routes.py`
**Update**: Profile page data to include User objects in recent activity

### Phase 3: Template Updates (2 hours)

#### Task 3.1: Update Prayer Card Template
**File**: `templates/components/prayer_card.html`
**Fix**: Current broken supporter badge implementation
**Change**: From `{{ p.author|supporter_badge|safe }}` to working implementation

#### Task 3.2: Update Activity Template
**File**: `templates/activity.html`
**Add**: Supporter badges to `{{ item.marker_name }}` and `{{ item.author_name }}`

#### Task 3.3: Update Profile Template  
**File**: `templates/profile.html`
**Add**: Supporter badges to profile display and recent activity

#### Task 3.4: Update Users Directory
**File**: `templates/users.html`
**Add**: Supporter badges to community members grid

#### Task 3.5: Update Admin Panel
**File**: `templates/admin.html`
**Add**: Supporter badges to flagged prayer authors

#### Task 3.6: Update Header Display
**File**: `templates/base.html`
**Add**: Supporter badge to header greeting

#### Task 3.7: Update Auth Templates
**File**: `templates/auth_requests.html`
**Add**: Supporter badges to requester and approver names

#### Task 3.8: Update Invite Tree
**File**: `templates/invite_tree.html`
**Add**: Supporter badges to invitation hierarchy

### Phase 4: Testing & Validation (1 hour)

#### Task 4.1: Test All Username Display Locations
- Verify supporter badges appear in all identified locations
- Test with both supporter and non-supporter users
- Verify consistent styling and behavior

#### Task 4.2: Test Manual Archive Management
- Verify setting `is_supporter: true` in archives works
- Test export/import maintains supporter status
- Verify badges update after archive changes

#### Task 4.3: Performance Testing
- Ensure User object queries don't impact performance
- Test with large user datasets
- Optimize queries if needed

### Phase 5: Documentation (15 minutes)

#### Task 5.1: Update Documentation
- Add centralized username display to CLAUDE.md
- Update AI_PROJECT_GUIDE.md with new patterns
- Document the new template filter usage

## Technical Implementation Details

### Centralized Username Display Pattern
```python
# In template filters
def username_display_filter(username: str) -> str:
    """Display username with supporter badge from database lookup"""
    with Session(engine) as session:
        user = session.exec(select(User).where(User.display_name == username)).first()
        if user and user.is_supporter:
            return f'{username}<span class="supporter-badge" title="Supporter">♥</span>'
        return username
```

### Template Usage Pattern
```jinja2
<!-- Old inconsistent patterns -->
{{ p.author_name }}
{{ item.marker_name }}
{{ user.display_name }}

<!-- New consistent pattern -->
{{ p.author_name|username_display|safe }}
{{ item.marker_name|username_display|safe }}
{{ user.display_name|username_display|safe }}
```

### Data Structure Updates
```python
# Enhanced prayer dictionary
prayer_dict = {
    'id': prayer.id,
    'text': prayer.text,
    'author_name': author_name,
    'author_id': prayer.author_username,
    'author_display_html': username_display_service.render_username_with_badge(author_name, session),
    # ... other fields
}
```

## Files to Modify

### New Files
- `app_helpers/services/username_display_service.py`

### Modified Files
- `app_helpers/template_filters.py` - Add username_display_filter
- `app_helpers/routes/prayer/feed_operations.py` - Update prayer data structures
- `app_helpers/routes/user_routes.py` - Update profile data
- `templates/components/prayer_card.html` - Fix supporter badge
- `templates/activity.html` - Add supporter badges
- `templates/profile.html` - Add supporter badges
- `templates/users.html` - Add supporter badges
- `templates/admin.html` - Add supporter badges
- `templates/base.html` - Add supporter badge to header
- `templates/auth_requests.html` - Add supporter badges
- `templates/invite_tree.html` - Add supporter badges

## Benefits

1. **Consistent Display**: All usernames displayed with same pattern
2. **Complete Badge Coverage**: Supporter badges appear everywhere usernames are shown
3. **Maintainable**: Single source of truth for username display logic
4. **Performance**: Efficient database queries with proper caching
5. **Extensible**: Easy to add new username display features in the future

## Timeline
- **Phase 1**: 1 hour (Centralized helper)
- **Phase 2**: 2 hours (Data structure updates)
- **Phase 3**: 2 hours (Template updates)
- **Phase 4**: 1 hour (Testing)
- **Phase 5**: 15 minutes (Documentation)

**Total**: 6 hours 15 minutes

## Risk Mitigation
- Test with backup database to prevent data loss
- Implement caching for User lookups to maintain performance
- Gradual rollout to verify each template works correctly
- Maintain backward compatibility with existing templates