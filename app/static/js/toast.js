/**
 * Toast Notification System
 * 
 * Features:
 * - Auto-dismissing toasts with customizable duration
 * - Stack multiple toasts (top-right corner)
 * - Color-coded by severity (success, error, warning, info)
 * - Progress bar showing time remaining
 * - Click to dismiss manually
 * - Smooth animations
 */

// Toast Configuration
const TOAST_CONFIG = {
    defaultDuration: 6000, // 6 seconds
    animationDuration: 300, // Animation time in ms
    maxToasts: 5, // Maximum number of visible toasts
    positions: {
        'top-right': { top: '20px', right: '20px', left: 'auto', bottom: 'auto' },
        'top-left': { top: '20px', left: '20px', right: 'auto', bottom: 'auto' },
        'bottom-right': { bottom: '20px', right: '20px', left: 'auto', top: 'auto' },
        'bottom-left': { bottom: '20px', left: '20px', right: 'auto', top: 'auto' }
    },
    currentPosition: 'top-right'
};

// Toast tracking
let toastCounter = 0;
let activeToasts = [];

/**
 * Initialize toast container
 * Called automatically when script loads
 */
function initToastContainer() {
    // Check if container already exists
    let container = document.querySelector('.toast-container');
    
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    return container;
}

/**
 * Create and show a toast notification
 * 
 * @param {string} message - Main message text
 * @param {string} type - Toast type: 'success', 'error', 'warning', 'info'
 * @param {object} options - Additional options
 * @param {string} options.title - Optional title (defaults based on type)
 * @param {number} options.duration - Duration in ms (0 = no auto-dismiss)
 * @param {boolean} options.dismissible - Whether user can dismiss (default: true)
 * @returns {object} Toast object with dismiss() method
 */
function showToast(message, type = 'info', options = {}) {
    // Get or create container
    const container = initToastContainer();
    
    // Remove oldest toast if we've hit the limit
    if (activeToasts.length >= TOAST_CONFIG.maxToasts) {
        const oldestToast = activeToasts[0];
        if (oldestToast && oldestToast.dismiss) {
            oldestToast.dismiss();
        }
    }
    
    // Default options
    const defaults = {
        title: getDefaultTitle(type),
        duration: TOAST_CONFIG.defaultDuration,
        dismissible: true
    };
    
    const config = { ...defaults, ...options };
    
    // Create toast element
    const toastId = `toast-${++toastCounter}`;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.id = toastId;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'polite');
    
    // Build toast HTML
    toast.innerHTML = `
        <div class="toast-icon">${getIcon(type)}</div>
        <div class="toast-content">
            ${config.title ? `<div class="toast-title">${escapeHtml(config.title)}</div>` : ''}
            <div class="toast-message">${escapeHtml(message)}</div>
        </div>
        ${config.dismissible ? '<div class="toast-close">×</div>' : ''}
        ${config.duration > 0 ? '<div class="toast-progress"></div>' : ''}
    `;
    
    // Add to container
    container.appendChild(toast);
    
    // Setup dismiss functionality
    let timeoutId = null;
    let progressAnimation = null;
    
    const toastObject = {
        element: toast,
        id: toastId,
        dismiss: function() {
            if (!toast.classList.contains('removing')) {
                toast.classList.add('removing');
                
                // Clear timeout and animation
                if (timeoutId) clearTimeout(timeoutId);
                if (progressAnimation) progressAnimation.cancel();
                
                // Remove from active toasts
                const index = activeToasts.indexOf(toastObject);
                if (index > -1) {
                    activeToasts.splice(index, 1);
                }
                
                // Remove element after animation
                setTimeout(() => {
                    if (toast.parentNode) {
                        toast.parentNode.removeChild(toast);
                    }
                }, TOAST_CONFIG.animationDuration);
            }
        }
    };
    
    // Add to active toasts
    activeToasts.push(toastObject);
    
    // Click to dismiss
    if (config.dismissible) {
        toast.addEventListener('click', () => toastObject.dismiss());
    }
    
    // Auto-dismiss with progress bar
    if (config.duration > 0) {
        const progressBar = toast.querySelector('.toast-progress');
        
        if (progressBar) {
            // Animate progress bar
            progressAnimation = progressBar.animate([
                { transform: 'scaleX(1)' },
                { transform: 'scaleX(0)' }
            ], {
                duration: config.duration,
                easing: 'linear',
                fill: 'forwards'
            });
        }
        
        // Set timeout for auto-dismiss
        timeoutId = setTimeout(() => {
            toastObject.dismiss();
        }, config.duration);
    }
    
    return toastObject;
}

/**
 * Show success toast
 * @param {string} message - Success message
 * @param {object} options - Additional options
 */
function showSuccess(message, options = {}) {
    return showToast(message, 'success', {
        title: 'Success',
        duration: 5000,
        ...options
    });
}

/**
 * Show error toast
 * @param {string} message - Error message
 * @param {object} options - Additional options
 */
function showError(message, options = {}) {
    return showToast(message, 'error', {
        title: 'Error',
        duration: 8000, // Errors stay longer
        ...options
    });
}

/**
 * Show warning toast
 * @param {string} message - Warning message
 * @param {object} options - Additional options
 */
function showWarning(message, options = {}) {
    return showToast(message, 'warning', {
        title: 'Warning',
        duration: 6000,
        ...options
    });
}

/**
 * Show info toast
 * @param {string} message - Info message
 * @param {object} options - Additional options
 */
function showInfo(message, options = {}) {
    return showToast(message, 'info', {
        title: 'Info',
        duration: 5000,
        ...options
    });
}

/**
 * Clear all active toasts
 */
function clearAllToasts() {
    // Make a copy since dismiss() modifies the array
    const toastsCopy = [...activeToasts];
    toastsCopy.forEach(toast => {
        if (toast.dismiss) {
            toast.dismiss();
        }
    });
}

/**
 * Get default title based on toast type
 * @private
 */
function getDefaultTitle(type) {
    const titles = {
        success: 'Success',
        error: 'Error',
        warning: 'Warning',
        info: 'Information'
    };
    return titles[type] || 'Notification';
}

/**
 * Get icon HTML for toast type
 * @private
 */
function getIcon(type) {
    const icons = {
        success: '✓',
        error: '✕',
        warning: '⚠',
        info: 'ℹ'
    };
    return icons[type] || 'ℹ';
}

/**
 * Escape HTML to prevent XSS
 * @private
 */
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

/**
 * Legacy compatibility - wrapper for old displayError function
 * This allows existing code to work without changes
 */
function displayError(message) {
    showError(message);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initToastContainer);
} else {
    initToastContainer();
}

// Export functions for use in other scripts
window.showToast = showToast;
window.showSuccess = showSuccess;
window.showError = showError;
window.showWarning = showWarning;
window.showInfo = showInfo;
window.clearAllToasts = clearAllToasts;
window.displayError = displayError; // Backward compatibility