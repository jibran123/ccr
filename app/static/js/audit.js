/**
 * Audit Log Viewer JavaScript
 *
 * Provides functionality for:
 * - Audit log filtering and search
 * - Timeline view for API changes
 * - Statistics dashboard with charts
 * - User activity tracking
 * - Export functionality (CSV, JSON)
 */

// Global state
let currentAuditLogs = [];
let currentFilters = {};
let currentPage = 1;
let resultsPerPage = 50;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initializeTabs();
    initializeFilters();
    initializeExport();
    loadActionTypes();

    // Auto-load recent logs on page load
    loadRecentAuditLogs();
});

/**
 * Tab Navigation
 */
function initializeTabs() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');

            // Remove active class from all tabs and contents
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            // Add active class to clicked tab and corresponding content
            this.classList.add('active');
            document.getElementById(`tab-${targetTab}`).classList.add('active');

            // Load data for specific tabs
            if (targetTab === 'statistics') {
                loadStatistics();
            }
        });
    });
}

/**
 * Initialize Filter Handlers
 */
function initializeFilters() {
    // Date range selector
    const dateRangeSelect = document.getElementById('filterDateRange');
    const customDateRange = document.getElementById('customDateRange');

    dateRangeSelect.addEventListener('change', function() {
        if (this.value === 'custom') {
            customDateRange.style.display = 'block';
        } else {
            customDateRange.style.display = 'none';
        }
    });

    // Filter form submission
    const filterForm = document.getElementById('auditFilterForm');
    filterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        applyFilters();
    });

    // Clear filters button
    const clearBtn = document.getElementById('clearFiltersBtn');
    clearBtn.addEventListener('click', function() {
        filterForm.reset();
        customDateRange.style.display = 'none';
        currentFilters = {};
        loadRecentAuditLogs();
    });

    // Results per page
    const resultsSelect = document.getElementById('auditResultsPerPage');
    resultsSelect.addEventListener('change', function() {
        resultsPerPage = parseInt(this.value);
        currentPage = 1;
        applyFilters();
    });

    // Timeline load button
    const loadTimelineBtn = document.getElementById('loadTimelineBtn');
    loadTimelineBtn.addEventListener('click', loadTimeline);

    // Activity load button
    const loadActivityBtn = document.getElementById('loadActivityBtn');
    loadActivityBtn.addEventListener('click', loadUserActivity);

    // Refresh statistics button
    const refreshStatsBtn = document.getElementById('refreshStatsBtn');
    refreshStatsBtn.addEventListener('click', loadStatistics);
}

/**
 * Load Available Action Types
 */
async function loadActionTypes() {
    try {
        const response = await fetch('/api/audit/actions');
        const data = await response.json();

        if (data.status === 'success') {
            const select = document.getElementById('filterAction');
            data.data.actions.forEach(action => {
                const option = document.createElement('option');
                option.value = action;
                option.textContent = formatActionName(action);
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Failed to load action types:', error);
    }
}

/**
 * Load Recent Audit Logs (default: last 24 hours)
 */
async function loadRecentAuditLogs() {
    try {
        showLoading();

        const response = await fetch('/api/audit/recent?hours=24&limit=100');
        const data = await response.json();

        if (data.status === 'success') {
            currentAuditLogs = data.data.logs;
            displayAuditLogs(currentAuditLogs);
            showToast('Loaded recent audit logs (last 24 hours)', 'success');
        } else {
            showToast('Failed to load audit logs', 'error');
        }
    } catch (error) {
        console.error('Failed to load recent logs:', error);
        showToast('Error loading audit logs', 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Apply Filters and Load Audit Logs
 */
async function applyFilters() {
    try {
        showLoading();

        // Build query parameters
        const params = new URLSearchParams();

        const apiName = document.getElementById('filterApiName').value.trim();
        const user = document.getElementById('filterUser').value.trim();
        const action = document.getElementById('filterAction').value;
        const platform = document.getElementById('filterPlatform').value;
        const environment = document.getElementById('filterEnvironment').value;
        const dateRange = document.getElementById('filterDateRange').value;

        if (apiName) params.append('api_name', apiName);
        if (user) params.append('changed_by', user);
        if (action) params.append('action', action);

        // Handle date range
        if (dateRange === 'custom') {
            const startDate = document.getElementById('filterStartDate').value;
            const endDate = document.getElementById('filterEndDate').value;

            if (startDate) params.append('start_date', new Date(startDate).toISOString());
            if (endDate) params.append('end_date', new Date(endDate).toISOString());
        }

        params.append('limit', resultsPerPage);
        params.append('skip', (currentPage - 1) * resultsPerPage);

        // Store filters for export
        currentFilters = {
            api_name: apiName,
            changed_by: user,
            action: action,
            platform: platform,
            environment: environment
        };

        const response = await fetch(`/api/audit/logs?${params.toString()}`);
        const data = await response.json();

        if (data.status === 'success') {
            let logs = data.data.logs;

            // Client-side filtering for platform and environment (not supported by API)
            if (platform) {
                logs = logs.filter(log => log.platform_id === platform);
            }
            if (environment) {
                logs = logs.filter(log => log.environment_id === environment);
            }

            currentAuditLogs = logs;
            displayAuditLogs(logs);

            if (logs.length === 0) {
                showToast('No audit logs found matching your filters', 'info');
            } else {
                showToast(`Found ${logs.length} audit log(s)`, 'success');
            }
        } else {
            showToast(data.error?.message || 'Failed to load audit logs', 'error');
        }
    } catch (error) {
        console.error('Failed to apply filters:', error);
        showToast('Error applying filters', 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Display Audit Logs in Table
 */
function displayAuditLogs(logs) {
    const tbody = document.getElementById('auditTableBody');
    const countSpan = document.getElementById('auditCount');

    countSpan.textContent = `(${logs.length})`;

    if (logs.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="no-data">
                    <i class="fas fa-search"></i> No audit logs found matching your criteria.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = logs.map(log => {
        const timestamp = formatTimestamp(log.timestamp);
        const action = formatActionBadge(log.action);

        return `
            <tr>
                <td>${timestamp}</td>
                <td>${action}</td>
                <td>${escapeHtml(log.api_name || '-')}</td>
                <td>${escapeHtml(log.platform_id || '-')}</td>
                <td>${escapeHtml(log.environment_id || '-')}</td>
                <td>${escapeHtml(log.changed_by || 'System')}</td>
                <td>
                    <button class="details-btn" onclick='showAuditDetails(${JSON.stringify(log).replace(/'/g, "&apos;")})'>
                        <i class="fas fa-info-circle"></i> Details
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

/**
 * Show Audit Log Details in Modal
 */
function showAuditDetails(log) {
    const modal = document.getElementById('auditDetailsModal');
    const modalBody = document.getElementById('auditModalBody');

    let html = `
        <div class="detail-group">
            <h4>Basic Information</h4>
            <div class="detail-row">
                <span class="detail-label">Audit ID:</span>
                <span class="detail-value">${escapeHtml(log.audit_id)}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Timestamp:</span>
                <span class="detail-value">${formatTimestamp(log.timestamp)}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Action:</span>
                <span class="detail-value">${formatActionBadge(log.action)}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Changed By:</span>
                <span class="detail-value">${escapeHtml(log.changed_by || 'System')}</span>
            </div>
        </div>

        <div class="detail-group">
            <h4>Resource Information</h4>
            <div class="detail-row">
                <span class="detail-label">API Name:</span>
                <span class="detail-value">${escapeHtml(log.api_name || '-')}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Platform:</span>
                <span class="detail-value">${escapeHtml(log.platform_id || '-')}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Environment:</span>
                <span class="detail-value">${escapeHtml(log.environment_id || '-')}</span>
            </div>
        </div>
    `;

    // Show changes if present
    if (log.changes && Object.keys(log.changes).length > 0) {
        html += `
            <div class="detail-group">
                <h4>Changes</h4>
                <div class="detail-value">
                    <pre>${JSON.stringify(log.changes, null, 2)}</pre>
                </div>
            </div>
        `;
    }

    // Show old state if present
    if (log.old_state) {
        html += `
            <div class="detail-group">
                <h4>Old State</h4>
                <div class="detail-value">
                    <pre>${JSON.stringify(log.old_state, null, 2)}</pre>
                </div>
            </div>
        `;
    }

    // Show new state if present
    if (log.new_state) {
        html += `
            <div class="detail-group">
                <h4>New State</h4>
                <div class="detail-value">
                    <pre>${JSON.stringify(log.new_state, null, 2)}</pre>
                </div>
            </div>
        `;
    }

    modalBody.innerHTML = html;
    modal.classList.add('active');
}

/**
 * Load Timeline for Specific API
 */
async function loadTimeline() {
    const apiName = document.getElementById('timelineApiName').value.trim();

    if (!apiName) {
        showToast('Please enter an API name', 'warning');
        return;
    }

    try {
        showLoading();

        const response = await fetch(`/api/audit/logs/${encodeURIComponent(apiName)}?limit=100`);
        const data = await response.json();

        if (data.status === 'success') {
            displayTimeline(data.data.logs, apiName);

            if (data.data.logs.length === 0) {
                showToast(`No audit logs found for API: ${apiName}`, 'info');
            } else {
                showToast(`Loaded ${data.data.logs.length} events for ${apiName}`, 'success');
            }
        } else {
            showToast(data.error?.message || 'Failed to load timeline', 'error');
        }
    } catch (error) {
        console.error('Failed to load timeline:', error);
        showToast('Error loading timeline', 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Display Timeline View
 */
function displayTimeline(logs, apiName) {
    const container = document.getElementById('timelineContainer');

    if (logs.length === 0) {
        container.innerHTML = `
            <div class="no-data">
                <i class="fas fa-info-circle"></i>
                No history found for API: ${escapeHtml(apiName)}
            </div>
        `;
        return;
    }

    container.innerHTML = logs.map(log => {
        const timestamp = formatTimestamp(log.timestamp);
        const action = formatActionName(log.action);

        let description = `<strong>${escapeHtml(log.changed_by || 'System')}</strong> performed <strong>${action}</strong>`;

        // Add specific details based on action type
        if (log.changes && Object.keys(log.changes).length > 0) {
            const changes = Object.keys(log.changes).map(key => {
                const change = log.changes[key];
                return `${key}: ${change.old} → ${change.new}`;
            }).join(', ');
            description += `<br>Changes: ${changes}`;
        }

        if (log.platform_id) {
            description += `<br>Platform: ${escapeHtml(log.platform_id)}`;
        }

        if (log.environment_id) {
            description += `, Environment: ${escapeHtml(log.environment_id)}`;
        }

        return `
            <div class="timeline-item">
                <div class="timeline-dot"></div>
                <div class="timeline-content">
                    <div class="timeline-header">
                        ${formatActionBadge(log.action)}
                        <span class="timeline-time">${timestamp}</span>
                    </div>
                    <div class="timeline-body">
                        ${description}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Load Statistics
 */
async function loadStatistics() {
    try {
        showLoading();

        const response = await fetch('/api/audit/stats');
        const data = await response.json();

        if (data.status === 'success') {
            displayStatistics(data.data);
            showToast('Statistics refreshed', 'success');
        } else {
            showToast('Failed to load statistics', 'error');
        }
    } catch (error) {
        console.error('Failed to load statistics:', error);
        showToast('Error loading statistics', 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Display Statistics
 */
function displayStatistics(stats) {
    // Update stat cards
    document.getElementById('statTotalLogs').textContent = stats.total_logs || 0;
    document.getElementById('statRecent24h').textContent = stats.recent_24h || 0;
    document.getElementById('statRetentionDays').textContent = stats.retention_days || 180;
    document.getElementById('statActiveUsers').textContent = stats.top_users?.length || 0;

    // Display action type chart
    if (stats.by_action) {
        displayActionTypeChart(stats.by_action);
    }

    // Display top users chart
    if (stats.top_users) {
        displayTopUsersChart(stats.top_users);
    }
}

/**
 * Display Action Type Chart
 */
function displayActionTypeChart(actionData) {
    const container = document.getElementById('actionTypeChart');

    const total = Object.values(actionData).reduce((sum, val) => sum + val, 0);

    container.innerHTML = Object.entries(actionData).map(([action, count]) => {
        const percentage = total > 0 ? (count / total * 100) : 0;

        return `
            <div class="chart-bar">
                <div class="chart-label">${formatActionName(action)}</div>
                <div class="chart-bar-fill" style="width: ${percentage}%">
                    ${count} (${percentage.toFixed(1)}%)
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Display Top Users Chart
 */
function displayTopUsersChart(userData) {
    const container = document.getElementById('topUsersChart');

    const maxCount = Math.max(...userData.map(u => u.changes));

    container.innerHTML = userData.slice(0, 10).map(user => {
        const percentage = maxCount > 0 ? (user.changes / maxCount * 100) : 0;

        return `
            <div class="chart-bar">
                <div class="chart-label">${escapeHtml(user.user)}</div>
                <div class="chart-bar-fill" style="width: ${percentage}%">
                    ${user.changes} change${user.changes !== 1 ? 's' : ''}
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Load User Activity
 */
async function loadUserActivity() {
    const username = document.getElementById('activityUsername').value.trim();
    const limit = document.getElementById('activityLimit').value;

    if (!username) {
        showToast('Please enter a username', 'warning');
        return;
    }

    try {
        showLoading();

        const response = await fetch(`/api/audit/users/${encodeURIComponent(username)}/activity?limit=${limit}`);
        const data = await response.json();

        if (data.status === 'success') {
            displayUserActivity(data.data.logs, username);

            if (data.data.logs.length === 0) {
                showToast(`No activity found for user: ${username}`, 'info');
            } else {
                showToast(`Loaded ${data.data.logs.length} activities for ${username}`, 'success');
            }
        } else {
            showToast(data.error?.message || 'Failed to load user activity', 'error');
        }
    } catch (error) {
        console.error('Failed to load user activity:', error);
        showToast('Error loading user activity', 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Display User Activity
 */
function displayUserActivity(logs, username) {
    const container = document.getElementById('activityResults');

    if (logs.length === 0) {
        container.innerHTML = `
            <div class="no-data">
                <i class="fas fa-info-circle"></i>
                No activity found for user: ${escapeHtml(username)}
            </div>
        `;
        return;
    }

    container.innerHTML = logs.map(log => {
        const timestamp = formatTimestamp(log.timestamp);
        const action = formatActionName(log.action);

        let description = `${action} on <strong>${escapeHtml(log.api_name || 'Unknown API')}</strong>`;

        if (log.platform_id && log.environment_id) {
            description += ` (${escapeHtml(log.platform_id)}/${escapeHtml(log.environment_id)})`;
        }

        return `
            <div class="activity-item">
                <div class="activity-header">
                    ${formatActionBadge(log.action)}
                    <span class="activity-time">${timestamp}</span>
                </div>
                <div class="activity-body">
                    ${description}
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Initialize Export Functionality
 */
function initializeExport() {
    const exportBtn = document.getElementById('exportAuditBtn');
    const exportModal = document.getElementById('exportModal');
    const jsonBtn = document.getElementById('exportJsonFormat');
    const csvBtn = document.getElementById('exportCsvFormat');

    exportBtn.addEventListener('click', function() {
        if (currentAuditLogs.length === 0) {
            showToast('No audit logs to export. Please apply filters first.', 'warning');
            return;
        }
        exportModal.classList.add('active');
    });

    jsonBtn.addEventListener('click', function() {
        exportToJSON();
        exportModal.classList.remove('active');
    });

    csvBtn.addEventListener('click', function() {
        exportToCSV();
        exportModal.classList.remove('active');
    });

    // Close modals
    const modalCloses = document.querySelectorAll('.modal-close');
    modalCloses.forEach(close => {
        close.addEventListener('click', function() {
            this.closest('.modal').classList.remove('active');
        });
    });

    // Close on outside click
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        modal.addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.remove('active');
            }
        });
    });
}

/**
 * Export to JSON
 */
function exportToJSON() {
    const dataStr = JSON.stringify(currentAuditLogs, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `audit-logs-${new Date().toISOString().split('T')[0]}.json`;
    link.click();
    URL.revokeObjectURL(url);

    showToast('Audit logs exported as JSON', 'success');
}

/**
 * Export to CSV
 */
function exportToCSV() {
    const headers = ['Timestamp', 'Action', 'API Name', 'Platform', 'Environment', 'Changed By', 'Audit ID'];
    const rows = currentAuditLogs.map(log => [
        log.timestamp,
        log.action,
        log.api_name || '',
        log.platform_id || '',
        log.environment_id || '',
        log.changed_by || 'System',
        log.audit_id
    ]);

    const csvContent = [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n');

    const dataBlob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    URL.revokeObjectURL(url);

    showToast('Audit logs exported as CSV', 'success');
}

/**
 * Utility Functions
 */

function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function formatActionName(action) {
    return action.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function formatActionBadge(action) {
    let className = 'action-badge';

    if (action.includes('CREATE')) {
        className += ' create';
    } else if (action.includes('DELETE')) {
        className += ' delete';
    } else if (action.includes('UPDATE') || action.includes('STATUS')) {
        className += ' status';
    } else {
        className += ' update';
    }

    return `<span class="${className}">${formatActionName(action)}</span>`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showLoading() {
    // Use existing toast system if available
    if (typeof showToast === 'function') {
        // showToast('Loading...', 'info');
    }
}

function hideLoading() {
    // Clear loading state
}

// Make functions globally accessible
window.showAuditDetails = showAuditDetails;
