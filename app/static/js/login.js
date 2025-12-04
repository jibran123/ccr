/**
 * Login Page JavaScript
 * Handles password toggle, form validation, and login interactions
 * Common Configuration Repository (CCR)
 */

(function() {
    'use strict';

    /**
     * Initialize login page functionality
     */
    function initLogin() {
        setupPasswordToggle();
        setupFormValidation();
        setupThemeToggle();
    }

    /**
     * Setup password visibility toggle
     */
    function setupPasswordToggle() {
        const toggleButton = document.getElementById('togglePassword');
        const passwordInput = document.getElementById('password');

        if (toggleButton && passwordInput) {
            toggleButton.addEventListener('click', () => {
                const type = passwordInput.type === 'password' ? 'text' : 'password';
                passwordInput.type = type;

                // Toggle icon
                const icon = toggleButton.querySelector('i');
                if (icon) {
                    icon.classList.toggle('fa-eye');
                    icon.classList.toggle('fa-eye-slash');
                }

                // Update aria-label
                toggleButton.setAttribute('aria-label',
                    type === 'password' ? 'Show password' : 'Hide password'
                );
            });
        }
    }

    /**
     * Setup form validation
     */
    function setupFormValidation() {
        const loginForm = document.getElementById('loginForm');

        if (loginForm) {
            loginForm.addEventListener('submit', (e) => {
                const username = document.getElementById('username').value.trim();
                const password = document.getElementById('password').value;

                // Basic validation
                if (!username) {
                    e.preventDefault();
                    showToast('Please enter your username', 'error');
                    document.getElementById('username').focus();
                    return;
                }

                if (!password) {
                    e.preventDefault();
                    showToast('Please enter your password', 'error');
                    document.getElementById('password').focus();
                    return;
                }

                // If validation passes, show loading state
                const submitButton = loginForm.querySelector('button[type="submit"]');
                if (submitButton) {
                    submitButton.disabled = true;
                    submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Signing In...';
                }
            });
        }
    }

    /**
     * Setup theme toggle button
     */
    function setupThemeToggle() {
        const themeToggle = document.getElementById('themeToggle');

        if (!themeToggle) {
            console.warn('Theme toggle button not found');
            return;
        }

        // Update button based on current theme
        updateThemeToggleButton();

        // Add click listener
        themeToggle.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);

            updateThemeToggleButton();
        });
    }

    /**
     * Update theme toggle button icon and title
     */
    function updateThemeToggleButton() {
        const themeToggle = document.getElementById('themeToggle');
        if (!themeToggle) return;

        const currentTheme = document.documentElement.getAttribute('data-theme');
        const icon = themeToggle.querySelector('i');

        if (currentTheme === 'dark') {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
            themeToggle.setAttribute('title', 'Switch to light mode');
        } else {
            icon.classList.remove('fa-sun');
            icon.classList.add('fa-moon');
            themeToggle.setAttribute('title', 'Switch to dark mode');
        }
    }

    /**
     * Show toast notification
     * (Simplified version for login page)
     */
    function showToast(message, type = 'info') {
        // Use toast.js if available
        if (window.showToast) {
            window.showToast(message, type);
            return;
        }

        // Fallback: Simple alert
        alert(message);
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initLogin);
    } else {
        initLogin();
    }

})();
