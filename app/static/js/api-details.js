/**
 * API Details Drawer for CCR
 * Shows comprehensive information about an API deployment
 *
 * Features:
 * - Slide-out drawer from right
 * - 4 tabs: Overview, Properties, Related, History
 * - Quick actions: copy, export, view audit
 * - Dark mode compatible
 */

(function() {
    'use strict';

    let currentApiData = null;
    let allSearchResults = []; // Store all search results for Related tab

    /**
     * Initialize API details drawer
     */
    function initApiDetailsDrawer() {
        console.log('Initializing API details drawer...');
        setupDrawerListeners();
        setupTabSwitching();
    }

    /**
     * Setup drawer event listeners
     */
    function setupDrawerListeners() {
        // Close button
        const closeBtn = document.querySelector('.drawer-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', closeDrawer);
        }

        // Overlay click
        const overlay = document.querySelector('.drawer-overlay');
        if (overlay) {
            overlay.addEventListener('click', closeDrawer);
        }

        // ESC key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                const drawer = document.getElementById('apiDetailsDrawer');
                if (drawer && drawer.classList.contains('open')) {
                    closeDrawer();
                }
            }
        });
    }

    /**
     * Setup tab switching
     */
    function setupTabSwitching() {
        const tabButtons = document.querySelectorAll('.drawer-tab');

        tabButtons.forEach(button => {
            button.addEventListener('click', function() {
                const tabName = this.dataset.tab;
                switchTab(tabName);
            });
        });
    }

    /**
     * Switch drawer tab
     */
    function switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.drawer-tab').forEach(btn => {
            btn.classList.remove('active');
        });
        const activeBtn = document.querySelector(`.drawer-tab[data-tab="${tabName}"]`);
        if (activeBtn) {
            activeBtn.classList.add('active');
        }

        // Update tab content
        document.querySelectorAll('.drawer-tab-content').forEach(content => {
            content.classList.remove('active');
        });
        const activeContent = document.getElementById(`tab-${tabName}`);
        if (activeContent) {
            activeContent.classList.add('active');
        }
    }

    /**
     * Open drawer with API data
     * @param {Object} apiData - API deployment data
     */
    function openDrawer(apiData) {
        console.log('Opening drawer with data:', apiData);
        currentApiData = apiData;

        // Populate all tabs
        populateOverview(apiData);
        populateProperties(apiData);
        populateRelated(apiData);
        populateHistory(apiData);

        // Reset to Overview tab
        switchTab('overview');

        // Show drawer
        const drawer = document.getElementById('apiDetailsDrawer');
        if (drawer) {
            drawer.classList.add('open');
            document.body.style.overflow = 'hidden'; // Prevent background scroll
        }
    }

    /**
     * Close drawer
     */
    function closeDrawer() {
        const drawer = document.getElementById('apiDetailsDrawer');
        if (drawer) {
            drawer.classList.remove('open');
            document.body.style.overflow = ''; // Restore scroll
        }
        currentApiData = null;
    }

    /**
     * Populate overview tab
     */
    function populateOverview(data) {
        const escape = window.ValidationLib ? window.ValidationLib.escapeHtml : escapeHtml;

        // API Name
        const apiNameEl = document.getElementById('detail-api-name');
        if (apiNameEl) {
            apiNameEl.textContent = data.apiName || 'N/A';
        }

        // Platform
        const platformEl = document.getElementById('detail-platform');
        if (platformEl) {
            platformEl.innerHTML = `<span class="badge badge-platform">${escape(data.platform || 'N/A')}</span>`;
        }

        // Environment
        const environmentEl = document.getElementById('detail-environment');
        if (environmentEl) {
            environmentEl.innerHTML = `<span class="badge badge-environment">${escape(data.environment || 'N/A')}</span>`;
        }

        // Version
        const versionEl = document.getElementById('detail-version');
        if (versionEl) {
            versionEl.textContent = data.version || 'N/A';
        }

        // Status
        const statusEl = document.getElementById('detail-status');
        if (statusEl) {
            const statusClass = getStatusBadgeClass(data.status);
            statusEl.innerHTML = `<span class="badge ${statusClass}">${escape(data.status || 'UNKNOWN')}</span>`;
        }

        // Last Updated
        const lastUpdatedEl = document.getElementById('detail-last-updated');
        if (lastUpdatedEl) {
            lastUpdatedEl.textContent = formatDate(data.lastUpdated) || 'N/A';
        }

        // Updated By
        const updatedByEl = document.getElementById('detail-updated-by');
        if (updatedByEl) {
            updatedByEl.textContent = data.updatedBy || 'N/A';
        }

        // Deployment Date
        const deploymentDateEl = document.getElementById('detail-deployment-date');
        if (deploymentDateEl) {
            deploymentDateEl.textContent = formatDate(data.deploymentDate) || 'N/A';
        }
    }

    /**
     * Populate properties tab
     */
    function populateProperties(data) {
        const properties = data.properties || {};
        const propertyCount = Object.keys(properties).length;

        // Update count
        const countEl = document.querySelector('.property-count');
        if (countEl) {
            countEl.textContent = `${propertyCount} ${propertyCount === 1 ? 'property' : 'properties'}`;
        }

        // Update JSON viewer
        const jsonViewer = document.querySelector('.json-viewer code');
        if (jsonViewer) {
            if (propertyCount === 0) {
                jsonViewer.textContent = '{}';
            } else {
                jsonViewer.textContent = JSON.stringify(properties, null, 2);
            }
        }
    }

    /**
     * Populate related deployments tab
     */
    function populateRelated(data) {
        const relatedList = document.querySelector('.related-list');
        if (!relatedList) return;

        const escape = window.ValidationLib ? window.ValidationLib.escapeHtml : escapeHtml;

        // Get all search results from search.js
        const searchResults = window.filteredResults || window.allResults || [];

        // Filter for same API name but different platform/environment
        const related = searchResults.filter(api => {
            const apiName = api['API Name'] || api.apiName;
            const platform = api.PlatformID || api.platform;
            const environment = api.Environment || api.environment;

            return apiName === data.apiName &&
                   !(platform === data.platform && environment === data.environment);
        });

        if (related.length === 0) {
            relatedList.innerHTML = `
                <div class="no-related">
                    <p>No other deployments found for this API.</p>
                </div>
            `;
            return;
        }

        // Build related items
        let html = '';
        related.forEach(api => {
            const platform = api.PlatformID || api.platform;
            const environment = api.Environment || api.environment;
            const version = api.Version || api.version;
            const status = api.Status || api.status;
            const statusClass = getStatusBadgeClass(status);

            html += `
                <div class="related-item">
                    <div class="related-info">
                        <span class="badge badge-platform">${escape(platform)}</span>
                        <span class="badge badge-environment">${escape(environment)}</span>
                        <span class="related-version">v${escape(version)}</span>
                        <span class="badge ${statusClass}">${escape(status)}</span>
                    </div>
                    <button class="view-btn" onclick="window.viewRelatedDetails('${escape(data.apiName)}', '${escape(platform)}', '${escape(environment)}')">
                        View <i class="fas fa-arrow-right"></i>
                    </button>
                </div>
            `;
        });

        relatedList.innerHTML = html;
    }

    /**
     * Populate history tab
     */
    function populateHistory(data) {
        const historyTimeline = document.querySelector('.history-timeline');
        if (!historyTimeline) return;

        // For now, show placeholder
        // TODO: Integrate with audit logs API in future
        historyTimeline.innerHTML = `
            <div class="history-placeholder">
                <div class="placeholder-icon">
                    <i class="fas fa-clock"></i>
                </div>
                <h4>Deployment History Coming Soon</h4>
                <p>This feature will display the complete deployment history from audit logs.</p>
                <p><strong>API:</strong> ${escapeHtml(data.apiName)}</p>
                <p><strong>Platform:</strong> ${escapeHtml(data.platform)}</p>
                <p><strong>Environment:</strong> ${escapeHtml(data.environment)}</p>
                <button class="action-btn" onclick="window.viewInAudit()">
                    <i class="fas fa-clipboard-list"></i> View in Audit Logs
                </button>
            </div>
        `;
    }

    /**
     * View related deployment details
     */
    function viewRelatedDetails(apiName, platform, environment) {
        const searchResults = window.filteredResults || window.allResults || [];

        // Find the matching deployment
        const deployment = searchResults.find(api => {
            const name = api['API Name'] || api.apiName;
            const plat = api.PlatformID || api.platform;
            const env = api.Environment || api.environment;
            return name === apiName && plat === platform && env === environment;
        });

        if (deployment) {
            // Map to expected format
            const mappedData = {
                apiName: deployment['API Name'] || deployment.apiName,
                platform: deployment.PlatformID || deployment.platform,
                environment: deployment.Environment || deployment.environment,
                version: deployment.Version || deployment.version,
                status: deployment.Status || deployment.status,
                lastUpdated: deployment.LastUpdated || deployment.lastUpdated,
                deploymentDate: deployment.DeploymentDate || deployment.deploymentDate,
                updatedBy: deployment.UpdatedBy || deployment.updatedBy,
                properties: deployment.Properties || deployment.properties || {}
            };

            openDrawer(mappedData);
        }
    }

    /**
     * Copy API name to clipboard
     */
    function copyApiName() {
        if (!currentApiData) return;

        const apiName = currentApiData.apiName;
        copyToClipboard(apiName, 'API name copied to clipboard!');
    }

    /**
     * Copy full configuration to clipboard
     */
    function copyFullConfig() {
        if (!currentApiData) return;

        const config = JSON.stringify(currentApiData, null, 2);
        copyToClipboard(config, 'Configuration copied to clipboard!');
    }

    /**
     * Copy properties to clipboard
     */
    function copyProperties() {
        if (!currentApiData) return;

        const properties = currentApiData.properties || {};
        const json = JSON.stringify(properties, null, 2);
        copyToClipboard(json, 'Properties copied to clipboard!');
    }

    /**
     * Export configuration as JSON file
     */
    function exportAsJSON() {
        if (!currentApiData) return;

        const json = JSON.stringify(currentApiData, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);

        const filename = `${currentApiData.apiName}-${currentApiData.platform}-${currentApiData.environment}.json`;

        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        if (window.showToast) {
            window.showToast('Configuration exported successfully', 'success', { duration: 3000 });
        }
    }

    /**
     * View in audit logs
     */
    function viewInAudit() {
        if (!currentApiData) return;

        // Navigate to audit page with API name filter
        const apiName = currentApiData.apiName;
        window.location.href = `/audit?api=${encodeURIComponent(apiName)}`;
    }

    /**
     * Copy text to clipboard
     */
    function copyToClipboard(text, successMessage) {
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(() => {
                if (window.showToast) {
                    window.showToast(successMessage, 'success', { duration: 3000 });
                }
            }).catch(err => {
                console.error('Failed to copy:', err);
                if (window.showToast) {
                    window.showToast('Failed to copy to clipboard', 'error', { duration: 3000 });
                }
            });
        } else {
            // Fallback for older browsers
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            document.body.appendChild(textarea);
            textarea.select();
            try {
                document.execCommand('copy');
                if (window.showToast) {
                    window.showToast(successMessage, 'success', { duration: 3000 });
                }
            } catch (err) {
                console.error('Failed to copy:', err);
                if (window.showToast) {
                    window.showToast('Failed to copy to clipboard', 'error', { duration: 3000 });
                }
            }
            document.body.removeChild(textarea);
        }
    }

    /**
     * Get status badge class
     */
    function getStatusBadgeClass(status) {
        if (!status) return 'badge-status-unknown';

        const normalizedStatus = status.toUpperCase();

        const statusMap = {
            'RUNNING': 'badge-status-running',
            'ACTIVE': 'badge-status-running',
            'DEPLOYED': 'badge-status-running',
            'STARTED': 'badge-status-running',
            'STOPPED': 'badge-status-stopped',
            'FAILED': 'badge-status-stopped',
            'ERROR': 'badge-status-stopped',
            'DEPLOYING': 'badge-status-deploying',
            'PENDING': 'badge-status-deploying',
            'UNKNOWN': 'badge-status-unknown',
            'MAINTENANCE': 'badge-status-unknown'
        };

        return statusMap[normalizedStatus] || 'badge-status-unknown';
    }

    /**
     * Format date string
     */
    function formatDate(dateStr) {
        if (!dateStr || dateStr === 'N/A') return 'N/A';

        try {
            const date = new Date(dateStr);
            if (isNaN(date.getTime())) return dateStr;
            return date.toLocaleString();
        } catch {
            return dateStr;
        }
    }

    /**
     * Escape HTML to prevent XSS
     */
    function escapeHtml(text) {
        if (text === null || text === undefined) return '';

        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };

        return String(text).replace(/[&<>"']/g, m => map[m]);
    }

    // Export functions to global scope
    window.openApiDetails = openDrawer;
    window.closeApiDetails = closeDrawer;
    window.viewRelatedDetails = viewRelatedDetails;
    window.copyApiName = copyApiName;
    window.copyFullConfig = copyFullConfig;
    window.copyProperties = copyProperties;
    window.exportAsJSON = exportAsJSON;
    window.viewInAudit = viewInAudit;

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initApiDetailsDrawer);
    } else {
        initApiDetailsDrawer();
    }

    console.log('✅ API Details Drawer loaded');

})();
