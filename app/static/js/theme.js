/**
 * Theme Manager for CCR
 * Handles dark/light mode toggle and persistence
 * Desktop-only implementation for internal corporate tool
 */

(function() {
    'use strict';

    // Theme constants
    const THEME_KEY = 'ccr-theme';
    const THEME_DARK = 'dark';
    const THEME_LIGHT = 'light';

    /**
     * Get current theme from localStorage or default to light
     */
    function getCurrentTheme() {
        return localStorage.getItem(THEME_KEY) || THEME_LIGHT;
    }

    /**
     * Set theme on document
     */
    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(THEME_KEY, theme);
        updateToggleButton(theme);
    }

    /**
     * Update toggle button icon based on current theme
     */
    function updateToggleButton(theme) {
        const toggleBtn = document.getElementById('themeToggle');
        if (!toggleBtn) return;

        const icon = toggleBtn.querySelector('i');
        if (!icon) return;

        if (theme === THEME_DARK) {
            // Show sun icon (to switch back to light)
            icon.className = 'fas fa-sun';
            toggleBtn.setAttribute('title', 'Switch to light mode');
        } else {
            // Show moon icon (to switch to dark)
            icon.className = 'fas fa-moon';
            toggleBtn.setAttribute('title', 'Switch to dark mode');
        }
    }

    /**
     * Toggle between light and dark theme
     */
    function toggleTheme() {
        const currentTheme = getCurrentTheme();
        const newTheme = currentTheme === THEME_DARK ? THEME_LIGHT : THEME_DARK;
        setTheme(newTheme);

        // Show toast notification
        if (window.showToast) {
            const message = newTheme === THEME_DARK ?
                '🌙 Dark mode enabled' :
                '☀️ Light mode enabled';
            window.showToast(message, 'success', { duration: 2000 });
        }
    }

    /**
     * Initialize theme on page load
     * IMPORTANT: This runs immediately to prevent flash of wrong theme
     */
    function initTheme() {
        const savedTheme = getCurrentTheme();
        setTheme(savedTheme);
    }

    /**
     * Setup theme toggle button listener
     */
    function setupThemeToggle() {
        const toggleBtn = document.getElementById('themeToggle');
        if (toggleBtn) {
            toggleBtn.addEventListener('click', toggleTheme);
        }
    }

    // Initialize theme IMMEDIATELY (before DOM ready to prevent flash)
    initTheme();

    // Setup toggle button when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupThemeToggle);
    } else {
        setupThemeToggle();
    }

})();
