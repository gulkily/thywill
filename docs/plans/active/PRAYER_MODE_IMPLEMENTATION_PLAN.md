# Prayer Mode Feature Implementation Plan

## Core Feature Overview
A full-screen, distraction-free prayer experience where users can:
- View one prayer at a time in a focused layout
- Mark prayers as "prayed" or "skip" to next
- Navigate through a curated set of prayers
- Return to normal feed view when done

## Current Prayer System Architecture Summary

### Core Models & Data Structure

**Prayer Model** (`/home/wsl/thywill/models.py`):
- **Primary fields**: `id`, `author_id`, `text`, `generated_prayer`, `project_tag`, `created_at`, `target_audience`
- **Status tracking**: Uses attribute system (`PrayerAttribute` model) for `archived`, `answered`, `flagged` states
- **Religious targeting**: `target_audience` field supports "all" or "christians_only"
- **Convenience methods**: `is_archived()`, `is_answered()`, `is_flagged_attr()`, `answer_date()`, `answer_testimony()`

**Prayer Interaction Models**:
- **PrayerMark**: Tracks when users pray for prayers (allows multiple marks per user)
- **PrayerAttribute**: Flexible key-value system for prayer metadata
- **PrayerActivityLog**: Audit trail for prayer status changes

### Current Prayer Display & Navigation

**Feed System** (`/home/wsl/thywill/app_helpers/routes/prayer/feed_operations.py`):
- **8 feed types**: `all`, `new_unprayed`, `most_prayed`, `my_prayers`, `my_requests`, `recent_activity`, `answered`, `archived`
- **Navigation**: Horizontal tab-based navigation with counts and scroll support
- **Filtering**: Religious preference filtering, archived/flagged exclusion

**Prayer Card Component** (`/home/wsl/thywill/templates/components/prayer_card.html`):
- **Layout**: Generated prayer prominent, original request collapsible
- **Visual status**: Color-coded borders (green=answered, amber=archived, purple=active)
- **Interactive elements**: "I Prayed This" button, dropdown menu for actions
- **Prayer stats**: Shows prayer count and distinct user count

### Prayer Status & Marking System

**Prayer Status Management** (`/home/wsl/thywill/app_helpers/routes/prayer/prayer_status.py`):
- **Mark prayer**: `/mark/{prayer_id}` - HTMX-enabled, allows multiple marks per user
- **Archive/Restore**: `/prayer/{prayer_id}/archive` and `/prayer/{prayer_id}/restore`
- **Mark answered**: `/prayer/{prayer_id}/answered` with optional testimony

**Prayer Interaction Flow**:
1. Users click "I Prayed This" button
2. HTMX updates prayer stats in real-time
3. Prayer count and user count update dynamically
4. Button changes color to indicate user has prayed

### Current UI Patterns & Navigation

**Modal/Overlay Patterns**:
- **Fixed overlay**: `fixed inset-0 bg-black bg-opacity-50 z-50`
- **Centered modal**: `flex items-center justify-center`
- **Keyboard support**: Escape key closes modals
- **Click-outside**: Background click closes modals

**Full-screen/Immersive Patterns**:
- No existing full-screen prayer experience
- Current focus is card-based feed layout
- Answered prayers have dedicated celebration page (`/answered`)

**JavaScript Architecture**:
- **HTMX**: Used for dynamic updates (prayer marking, archiving)
- **Vanilla JS**: Form handling, dropdowns, toggles
- **Preview system**: Prayer submission uses preview flow before final submission

## Implementation Plan

### Phase 1: Backend Foundation
1. **New Route**: `/prayer-mode` - Entry point for prayer mode
2. **Prayer Queue API**: `/api/prayer-mode/next` - HTMX endpoint to fetch next prayer
3. **Prayer Filtering**: Leverage existing feed filtering (`new_unprayed`, `most_prayed`) for prayer selection
4. **Session State**: Track current position in prayer queue using session storage

### Phase 2: Frontend Implementation
1. **Prayer Mode Template**: New full-screen template (`templates/prayer_mode.html`)
2. **Prayer Card Adaptation**: Simplified version of existing prayer card for full-screen display
3. **Navigation Controls**: "Prayed", "Skip", "Exit Prayer Mode" buttons
4. **Keyboard Support**: Spacebar (prayed), Arrow keys (next/previous), Escape (exit)

### Phase 3: Integration Points
1. **Feed Entry Point**: Add "Prayer Mode" button to feed navigation
2. **Prayer Selection**: Allow starting prayer mode from specific feed types
3. **Progress Tracking**: Show "X of Y prayers" indicator
4. **Return Navigation**: Seamless return to original feed position

## Technical Implementation Details

### Backend Routes (`app_helpers/routes/prayer_routes.py`):
```python
@prayer_routes.route('/prayer-mode')
@prayer_routes.route('/prayer-mode/<feed_type>')
def prayer_mode(feed_type='new_unprayed'):
    # Initialize prayer queue based on feed type
    # Store queue in session
    # Render prayer mode template

@prayer_routes.route('/api/prayer-mode/next')
def next_prayer():
    # HTMX endpoint to get next prayer in queue
    # Update session position
    # Return prayer card HTML fragment
```

### Frontend Template (`templates/prayer_mode.html`):
- Full-screen overlay (`fixed inset-0`)
- Centered prayer card with optimized typography
- Bottom action bar with large touch-friendly buttons
- Progress indicator at top
- Dark background for focus

### JavaScript Enhancements:
- Keyboard event handlers for navigation
- HTMX integration for seamless prayer loading
- Local storage for prayer mode preferences
- Exit confirmation for long prayer sessions

## MVP Feature Set

### Essential Features:
1. **Full-screen prayer display** - One prayer at a time, no scrolling needed
2. **"I Prayed" action** - Mark prayer and advance to next automatically
3. **Skip functionality** - Move to next prayer without marking as prayed
4. **Exit prayer mode** - Return to normal feed view
5. **Progress tracking** - "Prayer 3 of 15" indicator

### Prayer Selection Options:
- Start from "New & Unprayed" feed (default)
- Start from "Most Prayed" feed
- Start from current feed position

### Navigation Controls:
- Large, touch-friendly buttons
- Keyboard shortcuts (spacebar, arrows, escape)
- Swipe gestures on mobile (if technically feasible)

## Additional Considerations for MVP

### Features You Might Have Missed:

1. **Prayer Session Analytics**:
   - Track session duration
   - Count prayers prayed in session
   - Show completion celebration

2. **Distraction-Free Mode**:
   - Hide header/footer completely
   - Disable notifications during prayer mode
   - Optional timer/duration tracking

3. **Prayer Context**:
   - Show prayer author (with permission)
   - Display prayer age ("Posted 2 days ago")
   - Show how many others have prayed this

4. **Accessibility Features**:
   - Large text option for prayer content
   - High contrast mode
   - Screen reader optimization
   - Font size controls

5. **Session Persistence**:
   - Resume prayer mode from where you left off
   - Save incomplete sessions
   - Cross-device synchronization consideration

6. **Prayer Mode Variants**:
   - "Quick Prayer" mode (5-10 prayers)
   - "Extended Prayer" mode (20+ prayers)
   - "My Requests Follow-up" mode

## Key Files for Implementation

### Backend Routes:
- `/home/wsl/thywill/app_helpers/routes/prayer/feed_operations.py` - Feed queries and filtering
- `/home/wsl/thywill/app_helpers/routes/prayer/prayer_status.py` - Prayer marking and status changes
- `/home/wsl/thywill/app_helpers/services/prayer_helpers.py` - Helper functions and AI generation

### Frontend Templates:
- `/home/wsl/thywill/templates/components/prayer_card.html` - Current prayer display component
- `/home/wsl/thywill/templates/feed.html` - Main feed layout and navigation
- `/home/wsl/thywill/templates/base.html` - Base layout with header/footer
- `/home/wsl/thywill/templates/components/feed_scripts.html` - Prayer-related JavaScript

### Styling Patterns:
- **Purple theme**: Primary color scheme (`purple-600`, `purple-800`)
- **Status colors**: Green (answered), amber (archived), red (flagged)
- **Dark mode**: Full dark mode support with `dark:` classes
- **Responsive**: Mobile-first design with `sm:` breakpoints