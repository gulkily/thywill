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
                   typeof crypto !== 'undefined' &&
                   typeof crypto.getRandomValues === 'function';
        } catch (e) {
            return false;
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
    
    // Restore session on page load if needed
    function attemptSessionRestore() {
        // Check if session restoration is disabled for this page
        if (document.body.hasAttribute('data-disable-session-restore') || 
            document.querySelector('[data-disable-session-restore]')) {
            log('Session restoration disabled for this page');
            dispatchRestorationComplete(false);
            return;
        }
        
        // Only attempt restore if we don't currently have a session
        if (hasSessionCookie()) {
            log('Session cookie present, no restore needed');
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
                // Reload the page to continue with authenticated state
                window.location.reload();
            } else {
                warn('Failed to restore session cookie:', response.status);
                // Clear invalid backup data
                clearSessionData();
                dispatchRestorationComplete(false);
            }
        })
        .catch(error => {
            error('Error restoring session cookie:', error);
            clearSessionData();
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
        
        log('Initializing session persistence');
        
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
        isSupported: isSupported,
        hasSession: hasSessionCookie
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
})();