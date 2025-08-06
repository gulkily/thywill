/**
 * Session Persistence - LocalStorage backup for session cookies
 * 
 * Automatically backs up and restores session data to survive cookie clearing.
 * Works transparently with minimal backend changes.
 */

(function() {
    'use strict';
    
    // Constants
    const STORAGE_KEY = 'thywill_session_backup';
    const SESSION_COOKIE_NAME = 'sid';
    const STORAGE_VERSION = 1;
    const RESTORE_ATTEMPT_KEY = 'thywill_restore_attempt';
    const RESTORE_ATTEMPT_EXPIRY = 5 * 60 * 1000; // 5 minutes
    const MAX_RESTORE_ATTEMPTS = 3; // Max attempts per session
    
    // Utility functions
    function log(message, ...args) {
        if (console && console.log) {
            console.log('[SessionPersistence]', message, ...args);
        }
    }
    
    function warn(message, ...args) {
        if (console && console.warn) {
            console.warn('[SessionPersistence]', message, ...args);
        }
    }
    
    function error(message, ...args) {
        if (console && console.error) {
            console.error('[SessionPersistence]', message, ...args);
        }
    }
    
    // Check browser support
    function isSupported() {
        try {
            return typeof Storage !== 'undefined' && 
                   typeof localStorage !== 'undefined' &&
                   typeof sessionStorage !== 'undefined' &&
                   typeof crypto !== 'undefined' &&
                   typeof crypto.getRandomValues === 'function';
        } catch (e) {
            return false;
        }
    }
    
    // Restoration attempt tracking
    function getRestoreAttempts() {
        try {
            const data = sessionStorage.getItem(RESTORE_ATTEMPT_KEY);
            if (!data) return { count: 0, firstAttempt: Date.now() };
            
            const parsed = JSON.parse(data);
            
            // Check if attempts have expired
            if (Date.now() - parsed.firstAttempt > RESTORE_ATTEMPT_EXPIRY) {
                sessionStorage.removeItem(RESTORE_ATTEMPT_KEY);
                return { count: 0, firstAttempt: Date.now() };
            }
            
            return parsed;
        } catch (e) {
            return { count: 0, firstAttempt: Date.now() };
        }
    }
    
    function incrementRestoreAttempts() {
        try {
            const attempts = getRestoreAttempts();
            attempts.count += 1;
            attempts.lastAttempt = Date.now();
            sessionStorage.setItem(RESTORE_ATTEMPT_KEY, JSON.stringify(attempts));
            return attempts;
        } catch (e) {
            warn('Failed to track restore attempts:', e);
            return { count: 1, firstAttempt: Date.now() };
        }
    }
    
    function shouldAllowRestoreAttempt() {
        const attempts = getRestoreAttempts();
        const allowed = attempts.count < MAX_RESTORE_ATTEMPTS;
        
        if (!allowed) {
            log(`Restore attempts exceeded (${attempts.count}/${MAX_RESTORE_ATTEMPTS}), blocking restore`);
        }
        
        return allowed;
    }
    
    function clearRestoreAttempts() {
        try {
            sessionStorage.removeItem(RESTORE_ATTEMPT_KEY);
            log('Restore attempt tracking cleared');
        } catch (e) {
            // Ignore errors
        }
    }
    
    // Simple encryption using browser's crypto API
    function encryptData(data) {
        try {
            // Simple base64 encoding for now - can enhance later
            return btoa(JSON.stringify(data));
        } catch (e) {
            warn('Failed to encrypt session data:', e);
            return null;
        }
    }
    
    function decryptData(encryptedData) {
        try {
            return JSON.parse(atob(encryptedData));
        } catch (e) {
            warn('Failed to decrypt session data:', e);
            return null;
        }
    }
    
    // Get session info from backend (since cookie is httpOnly)
    async function getSessionInfo() {
        try {
            const response = await fetch('/api/session/info');
            if (response.ok) {
                return await response.json();
            }
        } catch (e) {
            // Session not available or other error
        }
        return null;
    }
    
    // Check if session cookie exists (indirect method)
    function hasSessionCookie() {
        // We can't directly check httpOnly cookies, but we can check if we're authenticated
        // by looking for authenticated user indicators in the DOM
        return document.querySelector('[data-authenticated="true"]') !== null ||
               document.querySelector('a[href="/profile"]') !== null ||
               document.body.classList.contains('authenticated');
    }
    
    // Backup session data to LocalStorage
    async function backupSessionData(sessionInfo) {
        if (!isSupported()) {
            log('LocalStorage not supported, skipping backup');
            return false;
        }
        
        try {
            const backupData = {
                version: STORAGE_VERSION,
                sessionId: sessionInfo.sessionId,
                userId: sessionInfo.userId,
                displayName: sessionInfo.displayName,
                expiresAt: sessionInfo.expiresAt,
                isFullyAuthenticated: sessionInfo.isFullyAuthenticated,
                timestamp: Date.now(),
                userAgent: navigator.userAgent.substring(0, 100) // Basic fingerprinting
            };
            
            const encrypted = encryptData(backupData);
            if (encrypted) {
                localStorage.setItem(STORAGE_KEY, encrypted);
                log('Session backed up to LocalStorage for user:', sessionInfo.displayName);
                broadcastStorageUpdate('backup', sessionInfo.sessionId);
                
                // Notify backend of successful backup
                try {
                    await fetch('/api/session/backup', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({userData: {displayName: sessionInfo.displayName}})
                    });
                } catch (e) {
                    // Backup notification failed, but local backup succeeded
                    warn('Failed to notify backend of backup:', e);
                }
                
                return true;
            }
        } catch (e) {
            error('Failed to backup session:', e);
        }
        
        return false;
    }
    
    // Restore session from LocalStorage
    function restoreSessionFromStorage() {
        if (!isSupported()) {
            return null;
        }
        
        try {
            const encrypted = localStorage.getItem(STORAGE_KEY);
            if (!encrypted) {
                log('No session backup found');
                return null;
            }
            
            const backupData = decryptData(encrypted);
            if (!backupData || backupData.version !== STORAGE_VERSION) {
                warn('Invalid or outdated session backup');
                clearSessionData();
                return null;
            }
            
            // Check expiration
            if (Date.now() > backupData.expires) {
                log('Session backup expired');
                clearSessionData();
                return null;
            }
            
            // Basic validation
            if (!backupData.sessionId || !backupData.userId) {
                warn('Invalid session backup data');
                clearSessionData();
                return null;
            }
            
            log('Found valid session backup');
            return backupData;
            
        } catch (e) {
            error('Failed to restore session:', e);
            clearSessionData();
        }
        
        return null;
    }
    
    // Clear session data from LocalStorage
    function clearSessionData() {
        if (!isSupported()) {
            return;
        }
        
        try {
            localStorage.removeItem(STORAGE_KEY);
            log('Session data cleared from LocalStorage');
            broadcastStorageUpdate('clear', null);
        } catch (e) {
            error('Failed to clear session data:', e);
        }
    }
    
    // Cross-tab communication via storage events
    function broadcastStorageUpdate(action, sessionId) {
        try {
            // Storage events are automatically broadcast to other tabs
            // We can add custom data if needed
            window.dispatchEvent(new CustomEvent('sessionPersistenceUpdate', {
                detail: { action, sessionId, timestamp: Date.now() }
            }));
        } catch (e) {
            // Ignore errors in event dispatching
        }
    }
    
    // Listen for storage changes from other tabs
    function setupCrossTabSync() {
        if (!isSupported()) {
            return;
        }
        
        window.addEventListener('storage', function(e) {
            if (e.key === STORAGE_KEY) {
                log('Session storage updated in another tab');
                // Could trigger UI updates or re-validation here
            }
        });
        
        // Listen for custom session events
        window.addEventListener('sessionPersistenceUpdate', function(e) {
            log('Session persistence event:', e.detail);
        });
    }
    
    // Backup current session if authenticated
    async function attemptSessionBackup() {
        try {
            const sessionInfo = await getSessionInfo();
            if (sessionInfo) {
                log('Found active session, backing up to LocalStorage');
                await backupSessionData(sessionInfo);
            } else {
                log('No active session found for backup');
            }
        } catch (e) {
            warn('Failed to backup session:', e);
        }
    }
    
    // Smart page detection for appropriate session restoration
    function shouldSkipSessionRestore() {
        // Check manual disable marker
        if (document.body.hasAttribute('data-disable-session-restore') || 
            document.querySelector('[data-disable-session-restore]')) {
            log('Session restoration manually disabled for this page');
            return true;
        }
        
        // Check URL patterns that should not restore sessions
        const pathname = window.location.pathname;
        const skipPatterns = [
            /^\/claim\/[a-f0-9]+/,        // Invite claim links
            /^\/auth\/status/,            // Authentication pending
            /^\/login/,                   // Login page
            /^\/auth\/login/,             // Alt login page
            /^\/auth\/requests/,          // Auth requests page
        ];
        
        for (const pattern of skipPatterns) {
            if (pattern.test(pathname)) {
                log(`Skipping session restore for URL pattern: ${pathname}`);
                return true;
            }
        }
        
        // Check for page elements that indicate session restoration shouldn't happen
        const skipIndicators = [
            '[data-page-type="auth"]',           // Auth pages
            '[data-page-type="claim"]',          // Claim pages  
            '[data-page-type="pending"]',        // Pending pages
            'form[action*="/login"]',            // Login forms
            'form[action*="/claim"]',            // Claim forms
            '.auth-pending-page',                // Auth pending content
            '.claim-invite-page'                 // Claim invite content
        ];
        
        for (const selector of skipIndicators) {
            if (document.querySelector(selector)) {
                log(`Skipping session restore due to page indicator: ${selector}`);
                return true;
            }
        }
        
        return false;
    }
    
    // Restore session on page load if needed
    function attemptSessionRestore() {
        // Smart detection of pages that shouldn't restore sessions
        if (shouldSkipSessionRestore()) {
            dispatchRestorationComplete(false);
            return;
        }
        
        // Check restore attempt limits
        if (!shouldAllowRestoreAttempt()) {
            dispatchRestorationComplete(false);
            return;
        }
        
        // Only attempt restore if we don't currently have a session
        if (hasSessionCookie()) {
            log('Session cookie present, no restore needed');
            clearRestoreAttempts(); // Clear tracking since we have a valid session
            dispatchRestorationComplete(false);
            return;
        }
        
        log('No session cookie found, attempting restore from LocalStorage');
        const backupData = restoreSessionFromStorage();
        
        if (backupData) {
            // Send the session data to the backend to restore the cookie
            restoreSessionCookie(backupData);
        } else {
            log('No valid session backup available');
            dispatchRestorationComplete(false);
        }
    }
    
    // Dispatch completion event for UI updates
    function dispatchRestorationComplete(restored) {
        try {
            window.dispatchEvent(new CustomEvent('sessionPersistenceComplete', {
                detail: { restored: restored, timestamp: Date.now() }
            }));
        } catch (e) {
            // Ignore event dispatch errors
        }
    }
    
    // Send session restore request to backend
    function restoreSessionCookie(backupData) {
        log('Attempting to restore session cookie for user:', backupData.displayName);
        
        // Track this restoration attempt
        const attempts = incrementRestoreAttempts();
        log(`Session restore attempt ${attempts.count}/${MAX_RESTORE_ATTEMPTS}`);
        
        // Make request to backend to restore the session cookie
        fetch('/api/session/restore', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                sessionId: backupData.sessionId,
                userData: {
                    userId: backupData.userId,
                    displayName: backupData.displayName
                }
            })
        })
        .then(response => {
            if (response.ok) {
                log('Session cookie restored successfully for user:', backupData.displayName);
                clearRestoreAttempts(); // Clear attempts on success
                // Reload the page to continue with authenticated state
                window.location.reload();
            } else {
                warn(`Failed to restore session cookie (${response.status}), attempt ${attempts.count}/${MAX_RESTORE_ATTEMPTS}`);
                
                // If we've exhausted attempts, clear data and stop trying
                if (attempts.count >= MAX_RESTORE_ATTEMPTS) {
                    log('Maximum restore attempts reached, clearing session data');
                    clearSessionData();
                }
                
                dispatchRestorationComplete(false);
            }
        })
        .catch(error => {
            error(`Error restoring session cookie (attempt ${attempts.count}/${MAX_RESTORE_ATTEMPTS}):`, error);
            
            // If we've exhausted attempts, clear data and stop trying
            if (attempts.count >= MAX_RESTORE_ATTEMPTS) {
                log('Maximum restore attempts reached due to errors, clearing session data');
                clearSessionData();
            }
            
            dispatchRestorationComplete(false);
        });
    }
    
    // Setup logout detection and cleanup handlers
    function setupLogoutHandlers() {
        log('Setting up logout detection handlers');
        
        // Handle logout form submissions
        document.addEventListener('submit', function(e) {
            const form = e.target;
            if (form && form.action && form.action.includes('/logout')) {
                log('Logout form submission detected, clearing session data');
                clearSessionData();
            }
        });
        
        // Handle logout button clicks (for direct links)
        document.addEventListener('click', function(e) {
            const target = e.target.closest('[href*="/logout"], [onclick*="logout"]');
            if (target) {
                log('Logout button clicked, clearing session data');
                clearSessionData();
            }
        });
        
        // Listen for beforeunload when session has been cleared (logout redirect)
        window.addEventListener('beforeunload', function() {
            // If we're navigating away and no session cookie exists,
            // it might be due to logout, so don't try to restore
            if (!hasSessionCookie()) {
                try {
                    const backupData = localStorage.getItem(STORAGE_KEY);
                    if (backupData) {
                        log('Page unloading without session - potential logout detected');
                    }
                } catch (e) {
                    // Ignore storage errors
                }
            }
        });
    }
    
    // Initialize session persistence
    function init() {
        if (!isSupported()) {
            log('Session persistence not supported in this browser');
            return;
        }
        
        log('Initializing session persistence with smart detection');
        
        // Set up cross-tab synchronization
        setupCrossTabSync();
        
        // Attempt to restore session on page load
        attemptSessionRestore();
        
        // If user is authenticated, backup their session
        if (hasSessionCookie()) {
            attemptSessionBackup();
        }
        
        // Add logout handler to clear data
        setupLogoutHandlers();
    }
    
    // Public API
    window.SessionPersistence = {
        backup: backupSessionData,
        restore: restoreSessionFromStorage,
        clear: clearSessionData,
        clearAttempts: clearRestoreAttempts,
        getAttempts: getRestoreAttempts,
        isSupported: isSupported,
        hasSession: hasSessionCookie,
        shouldSkip: shouldSkipSessionRestore
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
})();