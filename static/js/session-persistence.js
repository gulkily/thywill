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
    const RELOAD_LOOP_KEY = 'thywill_reload_prevention';
    const RELOAD_LOOP_THRESHOLD = 3; // Max reloads per session
    const RELOAD_COOLDOWN = 30 * 1000; // 30 seconds cooldown
    
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
    
    // Reload loop prevention
    function getReloadCount() {
        try {
            const data = sessionStorage.getItem(RELOAD_LOOP_KEY);
            if (!data) return { count: 0, firstReload: Date.now() };
            
            const parsed = JSON.parse(data);
            
            // Reset counter if cooldown period has passed
            if (Date.now() - parsed.firstReload > RELOAD_COOLDOWN) {
                sessionStorage.removeItem(RELOAD_LOOP_KEY);
                return { count: 0, firstReload: Date.now() };
            }
            
            return parsed;
        } catch (e) {
            return { count: 0, firstReload: Date.now() };
        }
    }
    
    function incrementReloadCount() {
        try {
            const reloads = getReloadCount();
            reloads.count += 1;
            reloads.lastReload = Date.now();
            sessionStorage.setItem(RELOAD_LOOP_KEY, JSON.stringify(reloads));
            return reloads;
        } catch (e) {
            warn('Failed to track reload count:', e);
            return { count: 1, firstReload: Date.now() };
        }
    }
    
    function shouldPreventReload() {
        const reloads = getReloadCount();
        const prevented = reloads.count >= RELOAD_LOOP_THRESHOLD;
        
        if (prevented) {
            log(`Reload loop detected (${reloads.count}/${RELOAD_LOOP_THRESHOLD}), preventing reload`);
        }
        
        return prevented;
    }
    
    function clearReloadTracking() {
        try {
            sessionStorage.removeItem(RELOAD_LOOP_KEY);
            log('Reload tracking cleared');
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
    
    // Check if session exists using server-provided meta tag
    function hasSessionCookie() {
        try {
            const sessionMeta = document.querySelector('meta[name="session-state"]');
            log('Session meta tag found:', sessionMeta ? sessionMeta.content : 'NOT FOUND');
            
            if (sessionMeta) {
                const sessionState = JSON.parse(sessionMeta.content);
                log('Parsed session state:', sessionState);
                
                const hasSession = sessionState.hasValidSession === true && sessionState.isAuthenticated === true;
                log('Has valid session:', hasSession);
                return hasSession;
            }
        } catch (e) {
            warn('Failed to parse session state meta tag:', e);
        }
        
        // Fallback: check for common authenticated indicators
        const fallbackChecks = {
            dataAuthenticated: document.querySelector('[data-authenticated="true"]') !== null,
            profileLink: document.querySelector('a[href="/profile"]') !== null,
            bodyClass: document.body.classList.contains('authenticated')
        };
        
        log('Fallback session checks:', fallbackChecks);
        
        return fallbackChecks.dataAuthenticated || fallbackChecks.profileLink || fallbackChecks.bodyClass;
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
        
        // CRITICAL FIX: Check if we just restored a session recently
        try {
            const recentRestore = sessionStorage.getItem('thywill_session_restored');
            if (recentRestore) {
                const restoreTime = parseInt(recentRestore);
                const timeSinceRestore = Date.now() - restoreTime;
                
                // If we restored within the last 10 seconds, don't try again
                if (timeSinceRestore < 10000) {
                    log('Session was recently restored, skipping restoration attempt');
                    dispatchRestorationComplete(false);
                    return;
                }
                
                // Clear old restoration markers after 10 seconds
                sessionStorage.removeItem('thywill_session_restored');
            }
        } catch (e) {
            // Ignore storage errors
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
            clearReloadTracking(); // Clear reload tracking since session is working
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
    
    // Update page session state without full reload
    function updatePageSessionState(authenticated) {
        try {
            // Update session meta tag
            const sessionMeta = document.querySelector('meta[name="session-state"]');
            if (sessionMeta) {
                const newState = authenticated ? 
                    '{"hasValidSession": true, "isAuthenticated": true}' :
                    '{"hasValidSession": false, "isAuthenticated": false}';
                sessionMeta.setAttribute('content', newState);
                log('Updated session state meta tag');
            }
            
            // Update body class
            if (authenticated) {
                document.body.classList.add('authenticated');
            } else {
                document.body.classList.remove('authenticated');
            }
            
            // Dispatch custom event for other scripts
            window.dispatchEvent(new CustomEvent('sessionStateChanged', {
                detail: { authenticated: authenticated, timestamp: Date.now() }
            }));
            
        } catch (e) {
            warn('Failed to update page session state:', e);
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
                
                // CRITICAL FIX: Check if we actually need to reload
                // If the page is already showing authenticated content, don't reload
                const pageHasAuthContent = document.querySelector('a[href="/profile"]') !== null ||
                                         document.querySelector('[data-authenticated="true"]') !== null ||
                                         document.body.classList.contains('authenticated') ||
                                         document.querySelector('.authenticated') !== null;
                
                if (pageHasAuthContent) {
                    log('Page already shows authenticated content - no reload needed');
                    updatePageSessionState(true);
                    dispatchRestorationComplete(true);
                    return;
                }
                
                // Check for reload loops before reloading
                if (shouldPreventReload()) {
                    warn('Reload loop detected - session restored but not reloading page to prevent infinite loop');
                    // Update page state instead of reloading
                    updatePageSessionState(true);
                    dispatchRestorationComplete(true);
                    return;
                }
                
                // Mark that we've successfully restored a session to prevent immediate re-attempts
                try {
                    sessionStorage.setItem('thywill_session_restored', Date.now().toString());
                } catch (e) {
                    // Ignore storage errors
                }
                
                // Track this reload to prevent loops
                incrementReloadCount();
                log('Reloading page to continue with authenticated state');
                
                // Add a slight delay to ensure cookie is fully set
                setTimeout(() => {
                    window.location.reload();
                }, 100);
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
        
        // Check session status first with detailed logging
        const sessionExists = hasSessionCookie();
        log('Session detection result:', sessionExists);
        
        if (!sessionExists) {
            // Attempt to restore session on page load
            attemptSessionRestore();
        } else {
            log('Valid session detected, skipping restoration');
            // If user is authenticated, backup their session
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
        clearReloads: clearReloadTracking,
        getReloads: getReloadCount,
        isSupported: isSupported,
        hasSession: hasSessionCookie,
        shouldSkip: shouldSkipSessionRestore,
        updateState: updatePageSessionState
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
})();