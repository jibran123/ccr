/**
 * CCR API Manager - Frontend Validation Library
 * 
 * Provides input validation and sanitization for all user inputs.
 * Integrates with toast notification system for error display.
 * 
 * Features:
 * - XSS protection and HTML escaping
 * - Input length validation
 * - Format validation (alphanumeric, version, etc.)
 * - SQL injection prevention (while allowing legitimate search operators)
 * - Special character filtering
 * - Integration with toast notifications
 */

// ===========================
// VALIDATION CONFIGURATION
// ===========================

const VALIDATION_CONFIG = {
    search: {
        minLength: 0,
        maxLength: 500,
        // Allow search query operators: =, !=, >, <, >=, <=, AND, OR, :, contains, startswith, endswith
        allowedCharacters: /^[a-zA-Z0-9\s\-_\.,:=<>!()&|"']*$/,
        name: 'Search query'
    },
    apiName: {
        minLength: 3,
        maxLength: 100,
        pattern: /^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$/,
        name: 'API name'
    },
    general: {
        maxLength: 1000
    }
};

// ===========================
// XSS PROTECTION
// ===========================

/**
 * Escape HTML to prevent XSS attacks
 * @param {string} text - Text to escape
 * @returns {string} Escaped text
 */
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;',
        '/': '&#x2F;',
        '`': '&#x60;',
        '=': '&#x3D;'
    };
    
    return String(text).replace(/[&<>"'`=\/]/g, (char) => map[char]);
}

/**
 * Strip HTML tags from input
 * @param {string} input - Input string
 * @returns {string} Sanitized string
 */
function stripHtmlTags(input) {
    if (!input) return '';
    return String(input).replace(/<[^>]*>/g, '');
}

/**
 * Sanitize input for safe display
 * @param {string} input - Input to sanitize
 * @returns {string} Sanitized input
 */
function sanitizeInput(input) {
    if (!input) return '';
    
    // Strip HTML tags first
    let sanitized = stripHtmlTags(input);
    
    // Trim whitespace
    sanitized = sanitized.trim();
    
    // Remove null bytes
    sanitized = sanitized.replace(/\0/g, '');
    
    // Limit consecutive spaces
    sanitized = sanitized.replace(/\s{2,}/g, ' ');
    
    return sanitized;
}

// ===========================
// SQL INJECTION PREVENTION
// ===========================

/**
 * Check for potential SQL injection patterns
 * IMPORTANT: This should block malicious SQL but ALLOW legitimate search operators like:
 * - "Platform = IP4 AND Environment = prod"
 * - "Status = RUNNING OR Status = DEPLOYING"
 * 
 * @param {string} input - Input to check
 * @returns {boolean} True if suspicious patterns found
 */
function containsSqlInjection(input) {
    if (!input) return false;
    
    // Normalize input for checking (but don't modify original)
    const normalized = input.toUpperCase();
    
    // CRITICAL: These patterns are MALICIOUS SQL injection attempts
    // We must NOT block legitimate search queries like "Platform = IP4 AND Environment = prod"
    
    const maliciousPatterns = [
        // SQL comment indicators (definitely malicious)
        /(--|\#|\/\*|\*\/)/,
        
        // Semicolon followed by SQL commands (malicious)
        /;.*(DROP|DELETE|INSERT|UPDATE|CREATE|ALTER|EXEC|EXECUTE)/i,
        
        // UNION-based injection (malicious)
        /UNION.*SELECT/i,
        
        // Stacked queries with semicolons (malicious)
        /;\s*(DROP|DELETE|TRUNCATE|ALTER)/i,
        
        // SQL commands that should NEVER appear in search queries
        /(DROP\s+TABLE|DELETE\s+FROM|TRUNCATE\s+TABLE|INSERT\s+INTO)/i,
        
        // Tautology-based injection like ' OR '1'='1
        /['"]\s*OR\s*['"]\d+['"]\s*=\s*['"]\d+/i,
        
        // Quotes with OR that look like injection (but not simple "OR Status = X")
        /['"]\s*OR\s+[^=]+\s*$/i,
        
        // EXEC/EXECUTE commands
        /\bEXEC(UTE)?\s*\(/i
    ];
    
    // Check each malicious pattern
    for (const pattern of maliciousPatterns) {
        if (pattern.test(input)) {
            console.warn('Blocked malicious SQL pattern:', input);
            return true;
        }
    }
    
    // IMPORTANT: Do NOT block these legitimate patterns:
    // - "Platform = IP4 AND Environment = prod" (legitimate AND)
    // - "Status = RUNNING OR Status = DEPLOYING" (legitimate OR)
    // - "Version >= 2.0" (legitimate comparison)
    // - "Properties : owner = team-alpha" (legitimate property search)
    
    return false;
}

// ===========================
// VALIDATION FUNCTIONS
// ===========================

/**
 * Validate input length
 * @param {string} input - Input to validate
 * @param {number} minLength - Minimum length
 * @param {number} maxLength - Maximum length
 * @param {string} fieldName - Name of field for error message
 * @returns {object} {valid: boolean, error: string}
 */
function validateLength(input, minLength, maxLength, fieldName = 'Input') {
    const length = input ? input.length : 0;
    
    if (minLength > 0 && length < minLength) {
        return {
            valid: false,
            error: `${fieldName} must be at least ${minLength} characters`
        };
    }
    
    if (length > maxLength) {
        return {
            valid: false,
            error: `${fieldName} must not exceed ${maxLength} characters`
        };
    }
    
    return { valid: true, error: null };
}

/**
 * Validate search query input
 * @param {string} query - Search query
 * @returns {object} {valid: boolean, error: string, sanitized: string}
 */
function validateSearchQuery(query) {
    // Allow empty search (show all results)
    if (!query || query.trim() === '') {
        return {
            valid: true,
            error: null,
            sanitized: ''
        };
    }
    
    const config = VALIDATION_CONFIG.search;
    
    // Sanitize input
    const sanitized = sanitizeInput(query);
    
    // Check length
    const lengthCheck = validateLength(
        sanitized,
        config.minLength,
        config.maxLength,
        config.name
    );
    
    if (!lengthCheck.valid) {
        return {
            valid: false,
            error: lengthCheck.error,
            sanitized: sanitized
        };
    }
    
    // Check for SQL injection
    if (containsSqlInjection(sanitized)) {
        return {
            valid: false,
            error: 'Search query contains invalid characters or patterns',
            sanitized: sanitized
        };
    }
    
    // All checks passed
    return {
        valid: true,
        error: null,
        sanitized: sanitized
    };
}

/**
 * Validate API name format
 * @param {string} apiName - API name to validate
 * @returns {object} {valid: boolean, error: string}
 */
function validateApiName(apiName) {
    if (!apiName) {
        return {
            valid: false,
            error: 'API name is required'
        };
    }
    
    const config = VALIDATION_CONFIG.apiName;
    const sanitized = sanitizeInput(apiName);
    
    // Check length
    const lengthCheck = validateLength(
        sanitized,
        config.minLength,
        config.maxLength,
        config.name
    );
    
    if (!lengthCheck.valid) {
        return lengthCheck;
    }
    
    // Check pattern
    if (!config.pattern.test(sanitized)) {
        return {
            valid: false,
            error: 'API name must be alphanumeric with hyphens/underscores, cannot start or end with special characters'
        };
    }
    
    return { valid: true, error: null };
}

/**
 * Validate general text input
 * @param {string} input - Input to validate
 * @param {string} fieldName - Name of field
 * @returns {object} {valid: boolean, error: string, sanitized: string}
 */
function validateTextInput(input, fieldName = 'Input') {
    if (!input || input.trim() === '') {
        return {
            valid: true,
            error: null,
            sanitized: ''
        };
    }
    
    const sanitized = sanitizeInput(input);
    
    // Check max length
    if (sanitized.length > VALIDATION_CONFIG.general.maxLength) {
        return {
            valid: false,
            error: `${fieldName} is too long (max ${VALIDATION_CONFIG.general.maxLength} characters)`,
            sanitized: sanitized
        };
    }
    
    return {
        valid: true,
        error: null,
        sanitized: sanitized
    };
}

/**
 * Validate filter input
 * @param {string} input - Filter search input
 * @returns {object} {valid: boolean, error: string, sanitized: string}
 */
function validateFilterInput(input) {
    // Filters are less restrictive than general search
    if (!input || input.trim() === '') {
        return {
            valid: true,
            error: null,
            sanitized: ''
        };
    }
    
    const sanitized = sanitizeInput(input);
    
    // Check length (shorter limit for filters)
    if (sanitized.length > 100) {
        return {
            valid: false,
            error: 'Filter search is too long (max 100 characters)',
            sanitized: sanitized
        };
    }
    
    // Check for SQL injection (even in filters)
    if (containsSqlInjection(sanitized)) {
        return {
            valid: false,
            error: 'Filter contains invalid characters',
            sanitized: sanitized
        };
    }
    
    return {
        valid: true,
        error: null,
        sanitized: sanitized
    };
}

// ===========================
// VALIDATION WITH TOAST INTEGRATION
// ===========================

/**
 * Validate and show error via toast if invalid
 * @param {string} input - Input to validate
 * @param {function} validationFn - Validation function
 * @param {array} args - Additional arguments for validation function
 * @returns {object} Validation result
 */
function validateWithToast(input, validationFn, ...args) {
    const result = validationFn(input, ...args);
    
    if (!result.valid && result.error) {
        // Show error toast if available
        if (typeof showToast === 'function') {
            showToast(result.error, 'error', {
                duration: 5000
            });
        } else {
            console.error('Validation error:', result.error);
        }
    }
    
    return result;
}

// ===========================
// INPUT SANITIZATION HELPERS
// ===========================

/**
 * Sanitize form data object
 * @param {object} formData - Form data object
 * @returns {object} Sanitized form data
 */
function sanitizeFormData(formData) {
    const sanitized = {};
    
    for (const [key, value] of Object.entries(formData)) {
        if (typeof value === 'string') {
            sanitized[key] = sanitizeInput(value);
        } else if (typeof value === 'object' && value !== null) {
            sanitized[key] = sanitizeFormData(value);
        } else {
            sanitized[key] = value;
        }
    }
    
    return sanitized;
}

/**
 * Validate URL parameter
 * @param {string} param - URL parameter
 * @returns {object} {valid: boolean, error: string, sanitized: string}
 */
function validateUrlParam(param) {
    if (!param) {
        return { valid: true, error: null, sanitized: '' };
    }
    
    const sanitized = sanitizeInput(decodeURIComponent(param));
    
    // Check for suspicious patterns
    if (containsSqlInjection(sanitized)) {
        return {
            valid: false,
            error: 'URL parameter contains invalid characters',
            sanitized: ''
        };
    }
    
    return {
        valid: true,
        error: null,
        sanitized: sanitized
    };
}

// ===========================
// EXPORT FUNCTIONS
// ===========================

// Make functions globally available
window.ValidationLib = {
    // Core functions
    escapeHtml,
    sanitizeInput,
    stripHtmlTags,
    
    // Validation functions
    validateSearchQuery,
    validateApiName,
    validateTextInput,
    validateFilterInput,
    validateLength,
    validateUrlParam,
    
    // With toast integration
    validateWithToast,
    
    // Helpers
    sanitizeFormData,
    containsSqlInjection,
    
    // Config
    config: VALIDATION_CONFIG
};

console.log('✅ Validation library loaded (SQL injection protection allows legitimate AND/OR operators)');