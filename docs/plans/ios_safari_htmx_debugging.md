# iOS Safari HTMX Button Issue - Debugging Documentation

## Issue Summary

The "Invite Someone" button stopped working specifically on iOS Safari after implementing share functionality, while continuing to work on iOS Firefox and other browsers.

## Root Cause Analysis

### Timeline
1. **Share functionality added** in commit `63e11d6` - "Add native share functionality for invite links"
2. **Inline script added** to `templates/invite_modal.html` (lines 82-112)
3. **iOS Safari invite button** stopped responding to taps

### Technical Root Cause

The issue was caused by an **inline script** added to the invite modal that runs when HTMX injects the modal HTML:

```html
<script>
(function() {
    // Wait for DOM to be ready and functions to be available
    setTimeout(function() {
        if (typeof getShareCapabilities === 'function') {
            const capabilities = getShareCapabilities();
            // ... customize share button based on capabilities
        }
    }, 100);
})();
</script>
```

**iOS Safari's strict behavior:**
- Stricter **Content Security Policy** enforcement for dynamically injected scripts
- Different **script execution timing** compared to other browsers
- **Silent failures** when inline scripts in HTMX-injected content don't execute properly
- This caused the entire HTMX modal injection to fail, breaking the invite button

### Browser Differences
- **iOS Safari**: Strict CSP, restrictive about dynamically injected scripts
- **iOS Firefox**: Same WebKit engine but different CSP handling, more permissive
- **Desktop browsers**: Generally more permissive with dynamic script execution

## Resolution

### Immediate Fix
Added Safari-specific fallback to the invite button:

**File: `templates/feed.html`**
```html
<button id="invite-btn"
        hx-post="/invites"
        hx-target="body"
        hx-swap="beforeend"
        onclick="handleInviteClick(this)"
        class="...">
  📧 Invite Someone
</button>
```

**File: `templates/components/feed_scripts.html`**
```javascript
function handleInviteClick(button) {
    // Only use fallback on Safari where HTMX events may fail
    const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
    
    if (!isSafari) {
        // Let HTMX handle it on other browsers
        return;
    }
    
    // Safari fallback using fetch()
    // ... manual implementation
}
```

### Strategy
1. **Safari detection** using user agent
2. **Graceful degradation** - HTMX for other browsers, fetch() for Safari
3. **Preserved functionality** - same end result across all browsers

## Key Learnings

### HTMX + iOS Safari Gotchas
1. **Avoid inline scripts** in HTMX-injected content on iOS Safari
2. **Move JavaScript logic** to the main page rather than injected modals
3. **Test on actual iOS Safari** - iOS Firefox behavior differs significantly
4. **Consider CSP implications** when dynamically injecting content

### Debugging Approach
1. **Cross-browser testing** revealed Safari-specific issue
2. **Git history analysis** identified the breaking change
3. **Incremental fixes** - tried removing `defer` first, then added fallback
4. **Targeted solution** - Safari-specific rather than universal changes

### Prevention
- **Test on iOS Safari** specifically, not just iOS Firefox
- **Avoid inline scripts** in HTMX-injected content
- **Use progressive enhancement** patterns for better compatibility
- **Consider CSP implications** early in feature design

## Files Modified

1. `templates/base.html` - Removed `defer` from HTMX script (partial fix)
2. `templates/feed.html` - Added `onclick` handler and ID to invite button
3. `templates/components/feed_scripts.html` - Added Safari fallback function

## Related Commits

- `63e11d6` - Original share functionality (introduced the issue)
- `bfe8b34` - Removed defer from HTMX (partial fix attempt)
- [Current] - Added Safari-specific fallback (full resolution)

## Testing Notes

- **Works**: iOS Firefox, Android Chrome, Desktop browsers
- **Fixed**: iOS Safari (was broken, now works with fallback)
- **Behavior**: HTMX on compatible browsers, fetch() fallback on Safari
- **User experience**: Identical across all browsers

---

*This issue demonstrates the importance of iOS Safari-specific testing and the need for graceful degradation when using HTMX with dynamically injected content.*