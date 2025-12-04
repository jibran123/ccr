/**
 * Utility functions for the application
 */

// API base URL
const API_BASE_URL = window.location.origin;

/**
 * Make an API request
 * @param {string} endpoint - API endpoint
 * @param {object} options - Request options
 * @returns {Promise} Response data
 */
async function apiRequest(endpoint, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...options.headers,
        },
    };

    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, mergedOptions);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || `HTTP ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

/**
 * Debounce function to limit rate of function calls
 * @param {function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Format date string
 * @param {string} dateStr - Date string
 * @returns {string} Formatted date
 */
function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    
    try {
        const date = new Date(dateStr);
        return date.toLocaleString();
    } catch {
        return dateStr;
    }
}

/**
 * Escape HTML to prevent XSS
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

/**
 * Show loading spinner
 * @param {string} containerId - Container element ID
 */
function showLoading(containerId) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
            </div>
        `;
    }
}

/**
 * Show error message
 * @param {string} containerId - Container element ID
 * @param {string} message - Error message
 */
function showError(containerId, message) {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="error-message">
                <strong>Error:</strong> ${escapeHtml(message)}
            </div>
        `;
    }
}

/**
 * Show success message
 * @param {string} containerId - Container element ID
 * @param {string} message - Success message
 */
function showSuccess(containerId, message) {
    const container = document.getElementById(containerId);
    if (container) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'success-message';
        messageDiv.innerHTML = `<strong>Success:</strong> ${escapeHtml(message)}`;
        container.insertBefore(messageDiv, container.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            messageDiv.remove();
        }, 5000);
    }
}

/**
 * Download data as file
 * @param {string} data - Data to download
 * @param {string} filename - Filename
 * @param {string} type - MIME type
 */
function downloadFile(data, filename, type = 'application/json') {
    const blob = new Blob([data], { type });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

/**
 * Parse query parameters from URL
 * @returns {object} Query parameters
 */
function getQueryParams() {
    const params = new URLSearchParams(window.location.search);
    const result = {};
    for (const [key, value] of params) {
        result[key] = value;
    }
    return result;
}

/**
 * Update URL query parameters without reload
 * @param {object} params - Parameters to update
 */
function updateQueryParams(params) {
    const url = new URL(window.location);
    Object.keys(params).forEach(key => {
        if (params[key] === null || params[key] === '') {
            url.searchParams.delete(key);
        } else {
            url.searchParams.set(key, params[key]);
        }
    });
    window.history.pushState({}, '', url);
}

/**
 * Enhanced error handler for API requests
 * Provides user-friendly messages based on error type
 * @param {Error|Response} error - The error object
 * @param {string} context - Context of the operation (e.g., "search", "deploy")
 * @returns {object} {message: string, action: string, canRetry: boolean}
 */
function handleApiError(error, context = "operation") {
    console.error(`${context} error:`, error);

    // Check if offline
    if (!navigator.onLine) {
        return {
            message: 'No internet connection.',
            action: 'Please check your network and try again.',
            canRetry: true,
            errorType: 'network'
        };
    }

    // Handle fetch/network errors
    if (error instanceof TypeError || error.name === 'NetworkError' || error.name === 'TypeError') {
        return {
            message: 'Unable to reach server.',
            action: 'Please check your connection and try again.',
            canRetry: true,
            errorType: 'network'
        };
    }

    // Handle timeout errors
    if (error.name === 'TimeoutError' || (error.message && error.message.includes('timeout'))) {
        return {
            message: 'Request timed out.',
            action: 'The server is taking too long to respond. Please try again.',
            canRetry: true,
            errorType: 'timeout'
        };
    }

    // Handle response with error object
    if (error.error) {
        const apiError = error.error;

        // Use API-provided message if available
        if (apiError.message) {
            return {
                message: apiError.message,
                action: error.help || 'Please try again.',
                canRetry: apiError.error_code !== 'VALIDATION_ERROR',
                errorType: apiError.type || 'api_error',
                errorCode: apiError.error_code
            };
        }
    }

    // Handle HTTP status codes from response
    if (error.status) {
        switch (error.status) {
            case 400:
                return {
                    message: error.message || 'Invalid request.',
                    action: 'Please check your input and try again.',
                    canRetry: false,
                    errorType: 'validation'
                };
            case 401:
                return {
                    message: 'Authentication required.',
                    action: 'Please log in and try again.',
                    canRetry: false,
                    errorType: 'auth'
                };
            case 403:
                return {
                    message: 'Access denied.',
                    action: 'You don\'t have permission to perform this action.',
                    canRetry: false,
                    errorType: 'permission'
                };
            case 404:
                return {
                    message: 'Resource not found.',
                    action: 'The requested item doesn\'t exist or has been deleted.',
                    canRetry: false,
                    errorType: 'not_found'
                };
            case 413:
                return {
                    message: 'Request too large.',
                    action: 'Please try with less data or smaller file size.',
                    canRetry: false,
                    errorType: 'too_large'
                };
            case 429:
                return {
                    message: 'Too many requests.',
                    action: 'Please wait a moment before trying again.',
                    canRetry: true,
                    errorType: 'rate_limit'
                };
            case 500:
                return {
                    message: 'Server error.',
                    action: 'Please try again in a moment. Contact support if this persists.',
                    canRetry: true,
                    errorType: 'server_error'
                };
            case 503:
                return {
                    message: 'Service unavailable.',
                    action: 'The server is temporarily down. Please try again shortly.',
                    canRetry: true,
                    errorType: 'service_unavailable'
                };
            case 507:
                return {
                    message: 'Insufficient storage.',
                    action: 'Please contact support to free up space.',
                    canRetry: false,
                    errorType: 'storage_full'
                };
            default:
                return {
                    message: `Server responded with error code ${error.status}.`,
                    action: 'Please try again or contact support.',
                    canRetry: true,
                    errorType: 'http_error'
                };
        }
    }

    // Generic error fallback
    return {
        message: `${context} failed.`,
        action: 'Please try again. Contact support if the problem persists.',
        canRetry: true,
        errorType: 'unknown'
    };
}

/**
 * Display error using toast notification
 * @param {Error|Response} error - The error object
 * @param {string} context - Context of the operation
 * @param {function} retryCallback - Optional callback to retry the operation
 */
function showApiError(error, context = "Operation", retryCallback = null) {
    const errorInfo = handleApiError(error, context);
    const fullMessage = `${errorInfo.message} ${errorInfo.action}`;

    // Show toast with retry option if available
    const toastOptions = { duration: 6000 };

    if (errorInfo.canRetry && retryCallback) {
        toastOptions.action = {
            text: 'Retry',
            callback: retryCallback
        };
    }

    showToast(fullMessage, 'error', toastOptions);

    return errorInfo;
}

/**
 * Check if user is online
 * @returns {boolean} True if online
 */
function isOnline() {
    return navigator.onLine;
}

/**
 * Setup offline/online detection
 */
function setupOfflineDetection() {
    window.addEventListener('offline', () => {
        showToast('You are offline. Some features may not work.', 'warning', { duration: 0 });
    });

    window.addEventListener('online', () => {
        showToast('Connection restored.', 'success');
    });
}

// Export functions to window object
window.setupOfflineDetection = setupOfflineDetection;
window.isOnline = isOnline;
window.showApiError = showApiError;
window.handleApiError = handleApiError;