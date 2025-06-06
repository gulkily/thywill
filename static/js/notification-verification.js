// Enhanced JavaScript for Verification Workflow
// Handles verification code formatting, validation, and approval process

// Verification code formatting and validation
function formatVerificationCode(input) {
    // Remove non-digits and limit to 6 characters
    let value = input.value.replace(/\D/g, '').substring(0, 6);
    
    // Auto-format as 123-456 if desired (optional)
    // if (value.length > 3) {
    //     value = value.substring(0, 3) + '-' + value.substring(3);
    // }
    
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

// Auto-approval function for Standard Mode (code is pre-filled)
async function autoApprove(notificationId, verificationCode) {
    const approveBtn = document.getElementById(`approve-btn-${notificationId}`);
    
    // Show loading state
    setApprovalLoading(notificationId, true);
    
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
                htmx.trigger(document.querySelector('[hx-get="/auth/notifications"]'), 'refresh');
            }, 1000);
            
        } else {
            showVerificationError(notificationId, result.message || 'Approval failed. Please try again.');
        }
        
    } catch (error) {
        showVerificationError(notificationId, 'Network error. Please check your connection and try again.');
    } finally {
        setApprovalLoading(notificationId, false);
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
                htmx.trigger(document.querySelector('[hx-get="/auth/notifications"]'), 'refresh');
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
function setApprovalLoading(notificationId, loading) {
    const approveBtn = document.getElementById(`approve-btn-${notificationId}`);
    const approveText = approveBtn.querySelector('.approve-text');
    const loadingText = approveBtn.querySelector('.loading-text');
    
    if (loading) {
        approveBtn.disabled = true;
        approveText.classList.add('hidden');
        loadingText.classList.remove('hidden');
    } else {
        approveBtn.disabled = false;
        approveText.classList.remove('hidden');
        loadingText.classList.add('hidden');
    }
}

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
    if (!element) return;
    
    const originalText = element.textContent;
    element.textContent = message;
    setTimeout(() => {
        element.textContent = originalText;
    }, duration);
}

// Add CSS for shake animation if not already present
if (!document.getElementById('notification-verification-styles')) {
    const style = document.createElement('style');
    style.id = 'notification-verification-styles';
    style.textContent = `
        @keyframes shake {
            0% { transform: translateX(0); }
            25% { transform: translateX(-5px); }
            50% { transform: translateX(5px); }
            75% { transform: translateX(-5px); }
            100% { transform: translateX(0); }
        }
        
        .animate-shake {
            animation: shake 0.6s ease-in-out;
        }
    `;
    document.head.appendChild(style);
}

console.log('Notification verification system loaded successfully');