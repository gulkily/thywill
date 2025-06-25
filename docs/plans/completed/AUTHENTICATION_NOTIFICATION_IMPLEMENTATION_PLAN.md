# Authentication Notification System Implementation Plan

## Overview

This specification outlines the implementation of a notification system that alerts fully authenticated users when new authentication requests are created for their username from other devices. This enables users to quickly approve their own login attempts from additional devices.

## Current System Analysis

### Existing Authentication Flow
1. User attempts login with existing username
2. `AuthenticationRequest` is created with verification code
3. Half-authenticated session is created for the waiting user
4. Fully authenticated users can approve requests via `/auth/pending`
5. Self-approval is possible if user has another fully authenticated session

### Key Components
- **AuthenticationRequest model** - Contains user_id, device_info, verification_code
- **Session model** - Tracks fully/half authenticated sessions
- **Auth helpers** - `get_pending_requests_for_approval()` function
- **Templates** - `/auth/pending` shows all requests, `/auth/status` shows waiting status

## Notification System Requirements

### Functional Requirements

1. **Real-time Notifications**
   - Notify users immediately when new auth requests are created for their username
   - Display notifications prominently in the UI for fully authenticated users
   - **Prominently display verification codes with high visual priority**
   - Include contextual device information and timing

2. **Notification Visibility**
   - Show notification count/badge in navigation
   - **Large, readable verification codes (minimum 24px font size)**
   - **Mobile-optimized modal interface for small screens**
   - Highlight own authentication requests vs others
   - **Clear visual hierarchy: verification code → device → actions**

3. **Secure Verification Workflow**
   - **Mandatory verification code confirmation before approval**
   - **Server-side verification code validation**
   - **Similar code detection and disambiguation**
   - **Auto-formatting of verification input (123-456 format)**
   - Copy-to-clipboard functionality for verification codes
   - Rate limiting on verification attempts

4. **Enhanced User Experience**
   - **Responsive design for mobile and desktop**
   - **Accessibility features for screen readers**
   - **Keyboard navigation support**
   - Multiple simultaneous request handling
   - Clear error messaging for verification failures

5. **Notification Management**
   - Mark notifications as read/unread
   - Auto-dismiss when request is approved/rejected/expired
   - Persistence across sessions
   - **Audit logging of all verification attempts**

### Technical Requirements

1. **Backend Data Model**
   - Track notification state (read/unread)
   - Efficient queries for user's own auth requests
   - Real-time updates via HTMX or WebSocket

2. **Frontend Components**
   - Notification badge in header/menu
   - Notification dropdown/modal
   - Integration with existing auth pages

3. **Performance**
   - Minimal database queries
   - Efficient notification checking
   - Background cleanup of expired notifications

## Implementation Plan

### Phase 1: Data Model Enhancement

#### 1.1 Add Notification Tracking
```sql
-- New table for notification state
CREATE TABLE notification_state (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    auth_request_id TEXT NOT NULL,
    notification_type TEXT DEFAULT 'auth_request',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES user (id),
    FOREIGN KEY (auth_request_id) REFERENCES authenticationrequest (id)
);

-- Index for efficient querying
CREATE INDEX idx_notification_user_unread ON notification_state (user_id, is_read);
```

#### 1.2 Helper Functions
Add to `auth_helpers.py`:

```python
def create_auth_notification(user_id: str, auth_request_id: str) -> str:
    """Create notification when auth request is created for user"""
    
def get_unread_auth_notifications(user_id: str) -> list:
    """Get unread authentication notifications for user"""
    
def mark_notification_read(notification_id: str, user_id: str) -> bool:
    """Mark notification as read"""
    
def validate_verification_code(notification_id: str, user_id: str, input_code: str) -> dict:
    """Validate verification code with comprehensive error handling"""
    
def detect_similar_verification_codes(user_id: str, input_code: str) -> list:
    """Detect similar verification codes to prevent confusion"""
    
def cleanup_expired_notifications() -> int:
    """Remove notifications for expired auth requests"""
```

### Phase 2: Backend Logic Integration

#### 2.1 Modify Authentication Request Creation
Update `create_auth_request()` in `auth_helpers.py`:

```python
def create_auth_request(user_id: str, device_info: str = None, ip_address: str = None) -> str:
    """Create auth request and notification"""
    request_id = uuid.uuid4().hex
    verification_code = f"{random.randint(100000, 999999):06d}"
    
    with Session(engine) as db:
        # Create auth request (existing logic)
        auth_req = AuthenticationRequest(...)
        db.add(auth_req)
        
        # Create notification for other devices of same user
        create_auth_notification(user_id, request_id)
        
        db.commit()
    return request_id
```

#### 2.2 Add Notification API Endpoints
Add to `auth_routes.py`:

```python
@router.get("/auth/notifications")
def get_notifications(user_session: tuple = Depends(require_full_auth)):
    """Get unread notifications for current user"""
    
@router.post("/auth/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str, user_session: tuple = Depends(require_full_auth)):
    """Mark notification as read"""

@router.post("/auth/notifications/{notification_id}/verify")
def verify_notification_code(
    notification_id: str, 
    verification_code: str = Form(...),
    user_session: tuple = Depends(require_full_auth)
):
    """Validate verification code before approval"""
    
@router.post("/auth/notifications/{notification_id}/approve")
def approve_from_notification(
    notification_id: str, 
    verification_code: str = Form(...),
    user_session: tuple = Depends(require_full_auth)
):
    """Approve auth request with mandatory verification code validation"""
```

### Phase 3: Frontend Implementation

#### 3.1 Enhanced Notification Badge Component
Create `templates/components/notification_badge.html`:

```html
<div class="relative" 
     hx-get="/auth/notifications" 
     hx-trigger="every 10s"
     hx-target="#notification-content"
     hx-swap="innerHTML">
  
  <!-- Bell icon with badge -->
  <button onclick="toggleNotifications()" 
          class="relative p-2 focus:outline-none focus:ring-2 focus:ring-purple-500 rounded"
          aria-label="Authentication notifications">
    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" 
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
    </svg>
    
    <!-- Enhanced notification badge with pulsing animation -->
    {% if notification_count > 0 %}
    <span class="absolute -top-1 -right-1 bg-red-500 text-white rounded-full text-xs w-6 h-6 flex items-center justify-center animate-pulse">
      {{ notification_count }}
    </span>
    {% endif %}
  </button>
  
  <!-- Desktop Dropdown (hidden by default) -->
  <div id="notification-dropdown" 
       class="hidden absolute right-0 mt-2 w-96 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-50 max-h-96 overflow-y-auto">
    <div id="notification-content">
      <!-- Notifications loaded via HTMX -->
    </div>
  </div>
</div>

<!-- Mobile Modal (hidden by default) -->
<div id="mobile-notification-modal" 
     class="fixed inset-0 bg-black bg-opacity-50 z-50 hidden">
  <div class="fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-800 rounded-t-xl max-h-[80vh] overflow-y-auto">
    <div class="sticky top-0 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-4">
      <div class="flex items-center justify-between">
        <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
          Authentication Requests
        </h3>
        <button onclick="closeMobileNotifications()" 
                class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
          </svg>
        </button>
      </div>
    </div>
    <div id="mobile-notification-content" class="p-4">
      <!-- Mobile notifications loaded here -->
    </div>
  </div>
</div>
```

#### 3.2 Enhanced Notification Content with Verification Workflow
Create `templates/components/notification_dropdown.html`:

```html
{% if notifications %}
<div class="p-4">
  <div class="flex items-center justify-between mb-4">
    <h3 class="font-semibold text-gray-900 dark:text-gray-100">
      Authentication Requests
    </h3>
    <span class="text-xs text-gray-500 dark:text-gray-400">
      {{ notifications|length }} pending
    </span>
  </div>
  
  {% for notification in notifications %}
  <div class="border border-gray-200 dark:border-gray-700 rounded-lg p-4 mb-3 last:mb-0">
    <!-- Device Information Header -->
    <div class="flex items-start justify-between mb-3">
      <div class="flex-1">
        <p class="font-medium text-gray-900 dark:text-gray-100 text-sm">
          Login Request
        </p>
        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
          From {{ notification.auth_request.device_info }} • {{ notification.created_at.strftime('%I:%M %p') }}
        </p>
      </div>
      
      <!-- Dismiss button -->
      <button hx-post="/auth/notifications/{{ notification.id }}/read"
              hx-target="#notification-content"
              hx-swap="innerHTML"
              class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 p-1"
              aria-label="Dismiss notification">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    </div>
    
    <!-- PRIMARY: Verification Code Display -->
    <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-4 mb-4">
      <div class="text-center">
        <p class="text-xs font-medium text-blue-700 dark:text-blue-300 mb-2">
          Verification Code
        </p>
        <div class="text-3xl font-mono font-bold text-blue-800 dark:text-blue-200 tracking-widest mb-2"
             id="code-display-{{ notification.id }}">
          {{ notification.auth_request.verification_code }}
        </div>
        <button onclick="copyVerificationCode('{{ notification.auth_request.verification_code }}', '{{ notification.id }}')"
                class="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 flex items-center justify-center mx-auto">
          <svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
          </svg>
          Copy Code
        </button>
      </div>
    </div>
    
    <!-- Verification Input Section -->
    <div class="verification-section" id="verify-section-{{ notification.id }}">
      <div class="mb-3">
        <label class="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
          Enter the code shown on your other device to confirm:
        </label>
        <input type="text" 
               class="w-full text-center text-xl font-mono border border-gray-300 dark:border-gray-600 rounded-lg p-3 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
               placeholder="123456"
               maxlength="6"
               pattern="[0-9]{6}"
               id="code-input-{{ notification.id }}"
               oninput="formatVerificationCode(this)"
               onkeydown="handleVerificationKeydown(event, '{{ notification.id }}')"
               autocomplete="off"
               aria-label="Enter verification code">
      </div>
      
      <div class="verification-actions">
        <button onclick="verifyAndApprove('{{ notification.id }}')"
                class="w-full bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-medium py-3 px-4 rounded-lg transition duration-200 focus:outline-none focus:ring-2 focus:ring-green-500"
                id="verify-btn-{{ notification.id }}"
                disabled>
          <span class="verify-text">Enter Code to Approve</span>
          <span class="loading-text hidden">Verifying...</span>
        </button>
        
        <!-- Error display -->
        <div id="verification-error-{{ notification.id }}" 
             class="mt-2 text-sm text-red-600 dark:text-red-400 text-center hidden"
             role="alert">
        </div>
        
        <!-- Success display -->
        <div id="verification-success-{{ notification.id }}" 
             class="mt-2 text-sm text-green-600 dark:text-green-400 text-center hidden"
             role="status">
        </div>
      </div>
    </div>
    
    <!-- Alternative Actions -->
    <div class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
      <div class="flex justify-between text-xs">
        <a href="/auth/pending" 
           class="text-purple-600 hover:text-purple-700 dark:text-purple-400 dark:hover:text-purple-300">
          View Full Details
        </a>
        <span class="text-gray-500 dark:text-gray-400">
          Expires {{ notification.auth_request.expires_at.strftime('%m/%d') }}
        </span>
      </div>
    </div>
  </div>
  {% endfor %}
  
  <!-- Footer -->
  <div class="mt-4 pt-3 border-t border-gray-200 dark:border-gray-700 text-center">
    <a href="/auth/pending" 
       class="text-sm text-purple-600 hover:text-purple-700 dark:text-purple-400 dark:hover:text-purple-300 font-medium">
      Manage All Authentication Requests →
    </a>
  </div>
</div>

{% else %}
<div class="p-6 text-center">
  <div class="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center mx-auto mb-3">
    <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
    </svg>
  </div>
  <h4 class="font-medium text-gray-900 dark:text-gray-100 mb-1">All Caught Up!</h4>
  <p class="text-sm text-gray-500 dark:text-gray-400">No authentication requests waiting for approval.</p>
</div>
{% endif %}
```

#### 3.3 Enhanced JavaScript for Verification Workflow
Create `static/js/notification-verification.js`:

```javascript
// Verification code formatting and validation
function formatVerificationCode(input) {
    // Remove non-digits and limit to 6 characters
    let value = input.value.replace(/\D/g, '').substring(0, 6);
    
    // Auto-format as 123-456 if desired
    if (value.length > 3) {
        value = value.substring(0, 3) + '-' + value.substring(3);
    }
    
    input.value = value;
    
    // Enable/disable verify button based on input
    const notificationId = input.id.split('-').pop();
    const verifyBtn = document.getElementById(`verify-btn-${notificationId}`);
    const cleanValue = value.replace('-', '');
    
    if (cleanValue.length === 6) {
        verifyBtn.disabled = false;
        verifyBtn.querySelector('.verify-text').textContent = 'Verify & Approve';
        verifyBtn.classList.remove('bg-gray-400');
        verifyBtn.classList.add('bg-green-600', 'hover:bg-green-700');
    } else {
        verifyBtn.disabled = true;
        verifyBtn.querySelector('.verify-text').textContent = `Enter ${6 - cleanValue.length} more digits`;
        verifyBtn.classList.add('bg-gray-400');
        verifyBtn.classList.remove('bg-green-600', 'hover:bg-green-700');
    }
    
    // Clear previous errors
    hideVerificationError(notificationId);
}

// Handle keyboard shortcuts
function handleVerificationKeydown(event, notificationId) {
    if (event.key === 'Enter') {
        event.preventDefault();
        verifyAndApprove(notificationId);
    } else if (event.key === 'Escape') {
        event.preventDefault();
        clearVerificationInput(notificationId);
    }
}

// Copy verification code to clipboard
async function copyVerificationCode(code, notificationId) {
    try {
        await navigator.clipboard.writeText(code);
        showTemporaryMessage(`code-display-${notificationId}`, 'Copied!', 2000);
    } catch (err) {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = code;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showTemporaryMessage(`code-display-${notificationId}`, 'Copied!', 2000);
    }
}

// Main verification and approval function
async function verifyAndApprove(notificationId) {
    const input = document.getElementById(`code-input-${notificationId}`);
    const verifyBtn = document.getElementById(`verify-btn-${notificationId}`);
    const verificationCode = input.value.replace(/\D/g, ''); // Remove non-digits
    
    if (verificationCode.length !== 6) {
        showVerificationError(notificationId, 'Please enter a complete 6-digit code');
        return;
    }
    
    // Show loading state
    setVerificationLoading(notificationId, true);
    
    try {
        const response = await fetch(`/auth/notifications/${notificationId}/approve`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `verification_code=${verificationCode}`
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            showVerificationSuccess(notificationId, 'Authentication approved successfully!');
            
            // Refresh notifications after 1 second
            setTimeout(() => {
                htmx.trigger('#notification-content', 'refresh');
            }, 1000);
            
        } else {
            // Handle specific error cases
            if (result.error_type === 'invalid_code') {
                showVerificationError(notificationId, 'Invalid verification code. Please check and try again.');
                // Highlight the correct code for comparison
                highlightCorrectCode(notificationId);
            } else if (result.error_type === 'similar_codes') {
                showSimilarCodesWarning(notificationId, result.similar_codes);
            } else {
                showVerificationError(notificationId, result.message || 'Verification failed. Please try again.');
            }
        }
        
    } catch (error) {
        showVerificationError(notificationId, 'Network error. Please check your connection and try again.');
    } finally {
        setVerificationLoading(notificationId, false);
    }
}

// UI helper functions
function setVerificationLoading(notificationId, loading) {
    const verifyBtn = document.getElementById(`verify-btn-${notificationId}`);
    const verifyText = verifyBtn.querySelector('.verify-text');
    const loadingText = verifyBtn.querySelector('.loading-text');
    
    if (loading) {
        verifyBtn.disabled = true;
        verifyText.classList.add('hidden');
        loadingText.classList.remove('hidden');
    } else {
        verifyText.classList.remove('hidden');
        loadingText.classList.add('hidden');
        // Re-enable based on input state
        const input = document.getElementById(`code-input-${notificationId}`);
        formatVerificationCode(input); // This will set the correct button state
    }
}

function showVerificationError(notificationId, message) {
    const errorDiv = document.getElementById(`verification-error-${notificationId}`);
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
    
    // Shake animation for input
    const input = document.getElementById(`code-input-${notificationId}`);
    input.classList.add('animate-shake');
    setTimeout(() => input.classList.remove('animate-shake'), 600);
}

function hideVerificationError(notificationId) {
    const errorDiv = document.getElementById(`verification-error-${notificationId}`);
    errorDiv.classList.add('hidden');
}

function showVerificationSuccess(notificationId, message) {
    const successDiv = document.getElementById(`verification-success-${notificationId}`);
    successDiv.textContent = message;
    successDiv.classList.remove('hidden');
    
    // Hide error if showing
    hideVerificationError(notificationId);
}

function showSimilarCodesWarning(notificationId, similarCodes) {
    const errorDiv = document.getElementById(`verification-error-${notificationId}`);
    errorDiv.innerHTML = `
        <div class="text-left">
            <p class="font-medium mb-1">Multiple similar codes found:</p>
            <ul class="text-xs space-y-1">
                ${similarCodes.map(code => `<li class="font-mono">${code}</li>`).join('')}
            </ul>
            <p class="mt-1">Please enter the exact 6-digit code.</p>
        </div>
    `;
    errorDiv.classList.remove('hidden');
}

function highlightCorrectCode(notificationId) {
    const codeDisplay = document.getElementById(`code-display-${notificationId}`);
    codeDisplay.classList.add('animate-pulse', 'bg-blue-200', 'dark:bg-blue-800');
    setTimeout(() => {
        codeDisplay.classList.remove('animate-pulse', 'bg-blue-200', 'dark:bg-blue-800');
    }, 2000);
}

function clearVerificationInput(notificationId) {
    const input = document.getElementById(`code-input-${notificationId}`);
    input.value = '';
    formatVerificationCode(input);
    hideVerificationError(notificationId);
}

function showTemporaryMessage(elementId, message, duration) {
    const element = document.getElementById(elementId);
    const originalText = element.textContent;
    element.textContent = message;
    setTimeout(() => {
        element.textContent = originalText;
    }, duration);
}

// Mobile notification handling
function toggleNotifications() {
    const dropdown = document.getElementById('notification-dropdown');
    const mobileModal = document.getElementById('mobile-notification-modal');
    
    if (window.innerWidth < 640) { // Mobile
        mobileModal.classList.remove('hidden');
        // Copy content to mobile view
        const desktopContent = document.getElementById('notification-content').innerHTML;
        document.getElementById('mobile-notification-content').innerHTML = desktopContent;
    } else { // Desktop
        dropdown.classList.toggle('hidden');
    }
}

function closeMobileNotifications() {
    document.getElementById('mobile-notification-modal').classList.add('hidden');
}

// Auto-resize on window resize
window.addEventListener('resize', () => {
    const dropdown = document.getElementById('notification-dropdown');
    const mobileModal = document.getElementById('mobile-notification-modal');
    
    if (window.innerWidth >= 640 && !mobileModal.classList.contains('hidden')) {
        // Switching to desktop view
        mobileModal.classList.add('hidden');
        dropdown.classList.remove('hidden');
    }
});

// Close notifications when clicking outside
document.addEventListener('click', (event) => {
    const dropdown = document.getElementById('notification-dropdown');
    const button = event.target.closest('[onclick="toggleNotifications()"]');
    const dropdownContent = event.target.closest('#notification-dropdown');
    
    if (!button && !dropdownContent && !dropdown.classList.contains('hidden')) {
        dropdown.classList.add('hidden');
    }
});
```

#### 3.4 Backend Verification Implementation
Add to `auth_helpers.py`:

```python
def validate_verification_code(notification_id: str, user_id: str, input_code: str) -> dict:
    """Comprehensive verification code validation with error handling"""
    with Session(engine) as db:
        # Get notification and validate ownership
        notification = db.get(NotificationState, notification_id)
        if not notification or notification.user_id != user_id:
            return {"success": False, "error_type": "unauthorized", "message": "Not authorized"}
        
        # Get auth request
        auth_req = db.get(AuthenticationRequest, notification.auth_request_id)
        if not auth_req:
            return {"success": False, "error_type": "not_found", "message": "Authentication request not found"}
        
        # Check if already processed
        if auth_req.status != "pending":
            return {"success": False, "error_type": "already_processed", "message": "Request already processed"}
        
        # Check if expired
        if auth_req.expires_at < datetime.utcnow():
            return {"success": False, "error_type": "expired", "message": "Authentication request has expired"}
        
        # Validate verification code
        if auth_req.verification_code != input_code:
            # Check for similar codes
            similar_codes = detect_similar_verification_codes(user_id, input_code)
            if len(similar_codes) > 1:
                return {
                    "success": False, 
                    "error_type": "similar_codes", 
                    "message": "Multiple similar codes found",
                    "similar_codes": similar_codes
                }
            
            # Log failed verification attempt
            log_auth_action(
                auth_request_id=auth_req.id,
                action="verification_failed",
                actor_user_id=user_id,
                actor_type="self",
                details=f"Invalid verification code entered: {input_code}",
                db_session=db
            )
            
            return {"success": False, "error_type": "invalid_code", "message": "Invalid verification code"}
        
        return {"success": True, "auth_request": auth_req}

def detect_similar_verification_codes(user_id: str, input_code: str) -> list:
    """Detect similar verification codes to prevent confusion"""
    with Session(engine) as db:
        # Get all pending requests for this user
        pending_requests = db.exec(
            select(AuthenticationRequest)
            .where(AuthenticationRequest.user_id == user_id)
            .where(AuthenticationRequest.status == "pending")
            .where(AuthenticationRequest.expires_at > datetime.utcnow())
        ).all()
        
        similar_codes = []
        for req in pending_requests:
            code = req.verification_code
            # Check for similarity (same first 3 digits, etc.)
            if code[:3] == input_code[:3] or code[-3:] == input_code[-3:]:
                similar_codes.append(code)
        
        return similar_codes
```

#### 3.5 Integration Points

**Header/Menu Integration:**
- Add notification badge to `templates/base.html` navigation
- Only show for fully authenticated users
- Include JavaScript files and responsive behavior
- ARIA labels and keyboard navigation support

**Enhanced Mobile Experience:**
- Full-screen modal on mobile devices
- Touch-friendly verification input
- Swipe gestures for dismissing notifications
- Haptic feedback on verification success/failure

**Existing Page Enhancement:**
- Update `/auth/pending` to highlight user's own requests
- Add notification state tracking and badge integration
- Cross-page notification consistency
- Auto-refresh when notifications change

### Phase 4: Real-time Updates

#### 4.1 HTMX Polling
- Poll `/auth/notifications` every 10 seconds for fully authenticated users
- Update notification badge and dropdown content
- Efficient backend queries with caching

#### 4.2 Background Cleanup
Add scheduled task or cron job:
```python
def cleanup_auth_notifications():
    """Remove notifications for expired/completed auth requests"""
    with Session(engine) as db:
        # Remove notifications for expired requests
        expired_requests = db.exec(
            select(AuthenticationRequest.id)
            .where(AuthenticationRequest.expires_at < datetime.utcnow())
        ).all()
        
        # Remove notifications for approved/rejected requests
        completed_requests = db.exec(
            select(AuthenticationRequest.id)
            .where(AuthenticationRequest.status.in_(["approved", "rejected"]))
        ).all()
        
        # Delete associated notifications
        db.exec(
            delete(NotificationState)
            .where(NotificationState.auth_request_id.in_(expired_requests + completed_requests))
        )
        db.commit()
```

### Phase 5: User Experience Enhancements

#### 5.1 Smart Notifications
- Only notify for auth requests from different IP addresses
- Group multiple requests from same device
- Show approximate location if available

#### 5.2 Notification Preferences
- Allow users to enable/disable auth notifications
- Email notifications for critical security events
- Configurable notification frequency

#### 5.3 Mobile Optimization
- Touch-friendly notification interface
- Push notifications for mobile web browsers
- Responsive notification dropdown

## Database Schema Changes

### New Tables
```sql
-- Notification state tracking
CREATE TABLE notification_state (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
    user_id TEXT NOT NULL,
    auth_request_id TEXT NOT NULL,
    notification_type TEXT DEFAULT 'auth_request',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE,
    FOREIGN KEY (auth_request_id) REFERENCES authenticationrequest (id) ON DELETE CASCADE
);

CREATE INDEX idx_notification_user_unread ON notification_state (user_id, is_read, created_at);
CREATE INDEX idx_notification_auth_request ON notification_state (auth_request_id);
```

## API Endpoints

### GET /auth/notifications
- Returns unread notifications for current user
- Includes auth request details and verification codes
- Supports HTMX partial updates

### POST /auth/notifications/{id}/read
- Marks notification as read
- Returns updated notification count
- Validates user ownership

### POST /auth/notifications/{id}/approve
- Approves associated auth request
- Marks notification as read
- Returns success/error status

## Security Considerations

1. **Authorization**
   - Only show notifications for user's own auth requests
   - Validate notification ownership before actions
   - Rate limit notification API calls

2. **Information Disclosure**
   - Limit device info shown in notifications
   - Don't expose sensitive session data
   - Sanitize user agent strings

3. **Performance**
   - Cache notification counts
   - Limit notification history
   - Efficient database queries

## Testing Strategy

### Unit Tests
- Notification creation and retrieval
- Notification state transitions
- Authorization and ownership validation

### Integration Tests
- End-to-end auth request notification flow
- HTMX polling and updates
- Notification cleanup processes

### User Testing
- Notification visibility and clarity
- Quick approval workflow
- Mobile responsiveness

## Migration Plan

### Phase 1: Database Migration
1. Create notification_state table
2. Add indexes for performance
3. Migrate existing auth requests (optional)

### Phase 2: Backend Implementation
1. Add notification helper functions
2. Integrate with auth request creation
3. Create notification API endpoints

### Phase 3: Frontend Implementation
1. Add notification badge component
2. Create dropdown interface
3. Integrate with existing templates

### Phase 4: Testing and Optimization
1. Load testing with notification polling
2. User experience testing
3. Performance optimization

## Success Metrics

1. **User Engagement**
   - Notification click-through rate
   - Time to approve own auth requests
   - User adoption of notification feature

2. **Technical Performance**
   - Notification delivery latency
   - Database query performance
   - Frontend rendering speed

3. **Security Impact**
   - Reduction in unauthorized approvals
   - Faster detection of suspicious requests
   - User awareness of authentication activity

## Future Enhancements

1. **Advanced Notifications**
   - Email/SMS notifications for security events
   - Browser push notifications
   - Webhook integrations

2. **Analytics Dashboard**
   - Authentication request patterns
   - Device usage statistics
   - Security event monitoring

3. **Enhanced Security**
   - Geolocation-based notifications
   - Risk scoring for auth requests
   - Automated blocking of suspicious requests

## Implementation Timeline

- **Week 1-2**: Database schema and backend helpers
- **Week 3-4**: API endpoints and notification logic
- **Week 5-6**: Frontend components and integration
- **Week 7**: Testing and optimization
- **Week 8**: Deployment and monitoring

## Key Improvements in Enhanced Specification

### **Critical Security Enhancements**

1. **Mandatory Verification Code Validation**
   - Server-side verification code validation for all approvals
   - No one-click approvals without code confirmation
   - Comprehensive error handling for invalid codes

2. **Similar Code Detection**
   - Detects and warns about similar verification codes (123456 vs 123465)
   - Prevents accidental approval of wrong requests
   - Shows all similar codes for user comparison

3. **Enhanced Audit Logging**
   - Logs all verification attempts (successful and failed)
   - Tracks verification code mismatches for security monitoring
   - Complete audit trail for authentication flows

### **Superior User Experience**

1. **Prominent Verification Code Display**
   - 3xl font size (minimum 24px) for verification codes
   - High contrast colors and visual hierarchy
   - Copy-to-clipboard functionality with feedback

2. **Mobile-First Design**
   - Full-screen modal on mobile devices
   - Touch-friendly verification inputs
   - Responsive design that adapts to screen size

3. **Progressive Enhancement**
   - Works without JavaScript (fallback to full page)
   - Keyboard navigation and accessibility support
   - Screen reader friendly with proper ARIA labels

4. **Real-time Feedback**
   - Auto-formatting of verification input (123-456)
   - Dynamic button states based on input completion
   - Immediate error/success feedback with animations

### **Robust Error Handling**

1. **Comprehensive Validation**
   - Input length validation with progress indicators
   - Network error handling with retry suggestions
   - Expired request detection and user notification

2. **User-Friendly Error Messages**
   - Specific error types with clear next steps
   - Visual highlighting of correct codes for comparison
   - Progressive assistance (showing remaining digits needed)

3. **Edge Case Management**
   - Multiple simultaneous requests handling
   - Browser compatibility fallbacks
   - Offline/online state management

### **Performance Optimizations**

1. **Efficient Database Queries**
   - Indexed notification lookups
   - Batch operations for notification cleanup
   - Minimal polling frequency with smart caching

2. **Frontend Performance**
   - Lazy loading of notification content
   - Debounced input validation
   - Optimized re-rendering with HTMX

3. **Scalable Architecture**
   - Notification state separation from auth requests
   - Background cleanup processes
   - Rate limiting and abuse prevention

### **Implementation Phases Summary**

- **Phase 1**: Enhanced data model with notification tracking
- **Phase 2**: Server-side verification validation and APIs
- **Phase 3**: Rich frontend with verification workflow
- **Phase 4**: Real-time updates and performance optimization
- **Phase 5**: User experience polish and accessibility

This enhanced implementation ensures verification codes serve their intended security purpose while providing an excellent user experience across all devices and use cases.