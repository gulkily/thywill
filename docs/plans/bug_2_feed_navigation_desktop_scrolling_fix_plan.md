# Bug #2 Fix Plan: Desktop Feed Navigation Scrolling

## Problem Description
Feed navigation selector is horizontally scrollable on mobile but not accessible to desktop users without touch capability. The "Archived" prayers option and potentially other feed options become hidden when the navigation overflows on desktop screens.

## Current Implementation Analysis
- Navigation uses `overflow-x-auto` with `scrollbar-hide` CSS
- Works perfectly on mobile with touch scrolling
- Desktop users cannot scroll without touch/trackpad capability
- Only shows scroll hint on mobile (`sm:hidden`)

**Location**: `templates/components/feed_navigation.html:4-84`

## Root Cause
The navigation relies solely on native scrolling behavior, which requires:
- Touch devices: Touch scrolling (works)
- Desktop: Mouse wheel over scrollable area or dragging scrollbar (hidden by CSS)
- Trackpad: Two-finger scrolling (works)

Desktop mouse users have no way to access hidden navigation items.

## Solution Design

### Phase 1: Add Desktop Mouse Wheel Support
- Add JavaScript to enable mouse wheel scrolling over the navigation area
- Horizontal scroll when mouse wheel is used over the nav container

### Phase 2: Add Visual Scroll Indicators
- Show subtle arrow indicators on desktop when content overflows
- Hide indicators when all content is visible
- Position indicators at left/right edges of navigation

### Phase 3: Add Click-to-Scroll Controls (Optional Enhancement)
- Clickable arrow buttons for precise navigation control
- Auto-hide when not needed

## Implementation Steps

### Step 1: Mouse Wheel Scrolling JavaScript
Add JavaScript to handle horizontal scrolling with mouse wheel:

```javascript
// Add to navigation container
document.addEventListener('DOMContentLoaded', function() {
    const nav = document.querySelector('.feed-nav-scroll');
    if (nav) {
        nav.addEventListener('wheel', function(e) {
            if (e.deltaY !== 0) {
                e.preventDefault();
                nav.scrollLeft += e.deltaY;
            }
        });
    }
});
```

### Step 2: Visual Scroll Indicators
Add CSS and JavaScript for scroll state indicators:

```html
<!-- Left/Right scroll indicators -->
<div class="feed-nav-indicators hidden lg:block">
    <div class="scroll-indicator left" id="scrollLeft">←</div>
    <div class="scroll-indicator right" id="scrollRight">→</div>
</div>
```

```css
.feed-nav-indicators {
    position: absolute;
    pointer-events: none;
}
.scroll-indicator {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    opacity: 0.5;
    transition: opacity 0.2s;
}
.scroll-indicator.left { left: 8px; }
.scroll-indicator.right { right: 8px; }
```

### Step 3: Scroll State Management
JavaScript to show/hide indicators based on scroll position:

```javascript
function updateScrollIndicators() {
    const nav = document.querySelector('.feed-nav-scroll');
    const leftIndicator = document.getElementById('scrollLeft');
    const rightIndicator = document.getElementById('scrollRight');
    
    if (nav.scrollLeft > 0) {
        leftIndicator.style.opacity = '0.7';
    } else {
        leftIndicator.style.opacity = '0.2';
    }
    
    if (nav.scrollLeft < nav.scrollWidth - nav.clientWidth) {
        rightIndicator.style.opacity = '0.7';
    } else {
        rightIndicator.style.opacity = '0.2';
    }
}
```

## Files to Modify

1. **templates/components/feed_navigation.html**
   - Add CSS class `feed-nav-scroll` to navigation container
   - Add scroll indicators HTML
   - Add JavaScript for mouse wheel and indicator management

## Testing Plan

### Desktop Testing
- [ ] Chrome/Firefox/Safari on Windows/Mac/Linux
- [ ] Test mouse wheel scrolling horizontally
- [ ] Verify scroll indicators appear/hide correctly
- [ ] Test with various screen widths
- [ ] Ensure archived prayers option is accessible

### Mobile Testing  
- [ ] Verify touch scrolling still works
- [ ] Confirm scroll indicators are hidden on mobile
- [ ] Test on iOS Safari and Android Chrome

### Edge Cases
- [ ] Very narrow screens with many navigation items
- [ ] Single navigation item (indicators should be hidden)
- [ ] JavaScript disabled fallback behavior

## Success Criteria
- ✅ Desktop users can scroll feed navigation with mouse wheel
- ✅ Visual indicators show scroll availability on desktop
- ✅ Mobile touch scrolling remains unchanged
- ✅ Archived prayers option is discoverable on all screen sizes
- ✅ No visual regressions in existing design

## Alternative Solutions Considered

### Option A: CSS-only with visible scrollbar
- Pros: No JavaScript required
- Cons: Breaks existing hidden scrollbar design

### Option B: Responsive wrapping layout
- Pros: No scrolling needed
- Cons: Takes more vertical space, harder to scan

### Option C: Dropdown menu for overflow items
- Pros: Clean design
- Cons: More complex implementation, discoverability issues

**Selected Solution**: Mouse wheel + visual indicators (best balance of functionality and design)

## Priority: High
This bug affects core navigation functionality and user discovery of archived content.