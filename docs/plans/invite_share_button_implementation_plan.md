# Invite Dialog Share Button Implementation Plan

## Overview
Add a native share button to the existing invite dialog that triggers platform-specific sharing mechanisms on 
iOS/Android and provides fallback functionality on desktop platforms.

## Current State Analysis
- **Invite Dialog**: Located in `templates/invite_modal.html`
- **Route Handler**: `app_helpers/routes/invite_routes.py` - `new_invite()` function
- **JavaScript**: Share-related functions in `templates/components/feed_scripts.html`
- **Current Actions**: Copy Link, Close modal
- **Integration**: HTMX-powered modal with QR code and invite link display

## Implementation Options

### Option 1: Web Share API (Recommended)
Use the modern Web Share API with graceful fallbacks.

**Pros:**
- Native platform integration on mobile
- Simple implementation
- Progressive enhancement approach
- Standardized web API

**Cons:**
- Limited browser support on desktop
- Requires HTTPS in production
- Not available in all browsers

### Option 2: Platform Detection + Custom Fallbacks
Detect platform and provide different share mechanisms.

**Pros:**
- More control over experience
- Can provide rich desktop fallbacks
- Better cross-platform consistency

**Cons:**
- More complex implementation
- Requires user agent detection
- More maintenance overhead

### Option 3: Hybrid Approach (Recommended)
Combine Web Share API with intelligent fallbacks based on capability detection.

**Pros:**
- Best of both approaches
- Progressive enhancement
- Graceful degradation
- Future-proof

**Cons:**
- Slightly more complex than Option 1

## Recommended Implementation: Option 3 (Hybrid)

### Phase 1: Frontend JavaScript Enhancement

#### 1.1 Add Share Function
**File**: `templates/components/feed_scripts.html`

```javascript
async function shareInviteLink(url, title = "Join ThyWill Prayer Community") {
    // Check if Web Share API is available
    if (navigator.share) {
        try {
            await navigator.share({
                title: title,
                text: "You're invited to join our prayer community. Click the link to create your account.",
                url: url
            });
            return true;
        } catch (error) {
            // User cancelled or error occurred
            if (error.name !== 'AbortError') {
                console.warn('Web Share API failed:', error);
                return false;
            }
            return true; // User cancelled, treat as success
        }
    }
    
    // Fallback for desktop/unsupported browsers
    return shareInviteLinkFallback(url, title);
}

function shareInviteLinkFallback(url, title) {
    // Desktop fallback options
    const fallbackOptions = [
        { name: 'Copy Link', action: () => copyInviteLink(url) },
        { name: 'Email', action: () => openEmailShare(url, title) },
        { name: 'SMS', action: () => openSMSShare(url, title) }
    ];
    
    // For now, just copy the link as fallback
    // Could be enhanced with a dropdown menu of options
    copyInviteLink(url);
    return true;
}

function openEmailShare(url, title) {
    const subject = encodeURIComponent(title);
    const body = encodeURIComponent(`You're invited to join our prayer community!\n\n${url}\n\nClick the link above to create your account and start sharing in our faith journey together.`);
    window.open(`mailto:?subject=${subject}&body=${body}`, '_self');
}

function openSMSShare(url, title) {
    const text = encodeURIComponent(`${title}\n${url}`);
    // iOS uses sms:, Android uses sms:
    window.open(`sms:?body=${text}`, '_self');
}
```

#### 1.2 Feature Detection Helper
```javascript
function getShareCapabilities() {
    return {
        hasWebShare: !!navigator.share,
        hasClipboard: !!navigator.clipboard,
        isMobile: /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent),
        isIOS: /iPad|iPhone|iPod/.test(navigator.userAgent),
        isAndroid: /Android/.test(navigator.userAgent)
    };
}
```

### Phase 2: Template Updates

#### 2.1 Update Invite Modal Template
**File**: `templates/invite_modal.html`

Add share button to the action buttons section:

```html
<!-- Existing content remains the same until action buttons -->
<div class="flex flex-col sm:flex-row gap-3 mt-6">
    <!-- Share Button (conditional rendering based on capability) -->
    <button onclick="shareInviteLink('{{ invite_url }}')"
            id="shareInviteBtn"
            class="flex-1 bg-blue-600 hover:bg-blue-700 dark:bg-blue-800 dark:hover:bg-blue-900 text-white px-4 py-2 rounded-lg font-medium transition-colors duration-200 flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400">
        <span id="shareIcon">📤</span>
        <span id="shareText">Share</span>
    </button>
    
    <!-- Existing Copy Link Button -->
    <button onclick="copyInviteLink('{{ invite_url }}')"
            class="flex-1 bg-green-600 hover:bg-green-700 dark:bg-green-800 dark:hover:bg-green-900 text-white px-4 py-2 rounded-lg font-medium transition-colors duration-200 flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-green-500 dark:focus:ring-green-400">
        <span>📋</span>
        <span>Copy Link</span>
    </button>
    
    <!-- Existing Close Button -->
    <button onclick="closeInviteModal()"
            class="bg-gray-500 hover:bg-gray-600 dark:bg-gray-700 dark:hover:bg-gray-600 text-white px-4 py-2 rounded-lg font-medium transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-gray-500 dark:focus:ring-gray-400">
        Close
    </button>
</div>

<!-- Add script to customize share button based on capabilities -->
<script>
document.addEventListener('DOMContentLoaded', function() {
    const capabilities = getShareCapabilities();
    const shareBtn = document.getElementById('shareInviteBtn');
    const shareIcon = document.getElementById('shareIcon');
    const shareText = document.getElementById('shareText');
    
    if (capabilities.hasWebShare) {
        // Native share available
        shareIcon.textContent = '📤';
        shareText.textContent = 'Share';
    } else if (capabilities.isMobile) {
        // Mobile without native share
        shareIcon.textContent = '📱';
        shareText.textContent = 'Share';
    } else {
        // Desktop fallback
        shareIcon.textContent = '📧';
        shareText.textContent = 'Email';
    }
});
</script>
```

### Phase 3: Enhanced Fallback Options (Optional)

#### 3.1 Desktop Share Menu
For enhanced desktop experience, create a dropdown with multiple share options:

```html
<!-- Desktop share dropdown (hidden by default) -->
<div id="shareDropdown" class="hidden absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg z-10 border border-gray-200 dark:border-gray-700">
    <button onclick="openEmailShare('{{ invite_url }}', 'Join ThyWill Prayer Community')" 
            class="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2">
        <span>📧</span> Email
    </button>
    <button onclick="openSMSShare('{{ invite_url }}', 'Join ThyWill Prayer Community')" 
            class="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2">
        <span>💬</span> SMS
    </button>
    <button onclick="copyInviteLink('{{ invite_url }}')" 
            class="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2">
        <span>📋</span> Copy Link
    </button>
</div>
```

### Phase 4: Backend Considerations (Optional)

#### 4.1 Share Analytics
**File**: `app_helpers/routes/invite_routes.py`

Add optional share tracking:

```python
# Add to new_invite function if analytics desired
def track_invite_share_method(invite_token: str, share_method: str):
    """Track how invites are being shared for analytics"""
    # Implementation depends on whether you want this data
    pass
```

## Testing Strategy

### Cross-Platform Testing
1. **iOS Safari**: Test Web Share API integration
2. **Android Chrome**: Test Web Share API integration  
3. **Desktop Chrome**: Test fallback functionality
4. **Desktop Firefox**: Test fallback functionality
5. **Desktop Safari**: Test fallback functionality

### Test Cases
1. **Share button visibility**: Button appears in modal
2. **Native share trigger**: Web Share API launches on supported platforms
3. **Fallback behavior**: Email/SMS links work on unsupported platforms
4. **Accessibility**: Button is keyboard accessible
5. **Error handling**: Graceful handling of share cancellation/errors

## Implementation Timeline

### Phase 1 (Core Implementation) - 2-4 hours
- Add share JavaScript functions
- Update invite modal template
- Test basic functionality

### Phase 2 (Enhancement) - 1-2 hours  
- Add platform detection
- Customize button text/icons
- Improve fallback experience

### Phase 3 (Polish) - 1-2 hours
- Add share dropdown for desktop
- Implement share analytics (if desired)
- Cross-platform testing

## Security Considerations

1. **URL Validation**: Ensure invite URLs are properly formatted
2. **XSS Prevention**: Sanitize any user-provided share content
3. **Rate Limiting**: Existing invite rate limiting covers share functionality
4. **Privacy**: Web Share API doesn't expose recipient information

## Accessibility Considerations

1. **Keyboard Navigation**: Share button is focusable and activatable
2. **Screen Readers**: Proper ARIA labels and descriptions
3. **High Contrast**: Button styling works in high contrast mode
4. **Touch Targets**: Minimum 44px touch target size on mobile

## Future Enhancements

1. **Social Media Integration**: Direct sharing to social platforms
2. **QR Code Sharing**: Share QR code image along with link
3. **Custom Messages**: Allow users to customize share message
4. **Share Analytics**: Track which share methods are most effective
5. **Rich Previews**: Implement Open Graph tags for better link previews

## Browser Support Matrix

| Browser | Web Share API | Email Share | SMS Share | Copy Link |
|---------|---------------|-------------|-----------|-----------|
| iOS Safari | ✅ | ✅ | ✅ | ✅ |
| Android Chrome | ✅ | ✅ | ✅ | ✅ |
| Desktop Chrome | ❌ | ✅ | ❌ | ✅ |
| Desktop Firefox | ❌ | ✅ | ❌ | ✅ |
| Desktop Safari | ❌ | ✅ | ❌ | ✅ |

## Conclusion

The hybrid approach provides the best user experience across all platforms while maintaining simplicity and leveraging modern web APIs where available. The implementation is progressive, starting with basic functionality and allowing for future enhancements based on user feedback and analytics.