/**
 * Dashboard & Analytics
 * Handles data fetching, Chart.js rendering, and interactivity
 * Common Configuration Repository (CCR)
 */

(function() {
    'use strict';

    // State
    let currentPeriod = 'all';
    let charts = {
        platform: null,
        environment: null,
        status: null
    };

    /**
     * Initialize dashboard on page load
     */
    function initDashboard() {
        // Check if Chart.js is loaded
        if (typeof Chart === 'undefined') {
            console.error('Chart.js library failed to load');
            if (window.showToast) {
                window.showToast('Chart library failed to load. Please check your internet connection.', 'error', { duration: 5000 });
            }
            // Still setup filter and try to load data (for KPI cards)
        }

        setupTimePeriodFilter();
        loadDashboardData();
    }

    /**
     * Setup time period filter buttons
     */
    function setupTimePeriodFilter() {
        const filterButtons = document.querySelectorAll('.filter-btn');

        filterButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                // Update active state
                filterButtons.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                // Update current period and reload data
                currentPeriod = btn.dataset.period;
                loadDashboardData();
            });
        });
    }

    /**
     * Load dashboard data from API
     */
    async function loadDashboardData() {
        try {
            const response = await fetch(`/api/dashboard/summary?time_period=${currentPeriod}`);

            if (!response.ok) {
                throw new Error('Failed to load dashboard data');
            }

            const result = await response.json();

            if (result.status === 'success' && result.data) {
                // Update UI
                updateSummaryCards(result.data.summary);
                renderPlatformChart(result.data.platform_distribution);
                renderEnvironmentChart(result.data.environment_distribution);
                renderStatusChart(result.data.status_distribution);
                renderRecentActivity(result.data.recent_activity);
            } else {
                throw new Error(result.message || 'Invalid response format');
            }

        } catch (error) {
            console.error('Error loading dashboard:', error);
            if (window.showToast) {
                window.showToast('Failed to load dashboard data', 'error');
            }
        }
    }

    /**
     * Update summary cards with data
     */
    function updateSummaryCards(summary) {
        document.getElementById('totalApis').textContent = summary.total_apis.toLocaleString();
        document.getElementById('totalDeployments').textContent = summary.total_deployments.toLocaleString();
        document.getElementById('activeDeployments').textContent = summary.active_deployments.toLocaleString();
        document.getElementById('recentChanges').textContent = summary.recent_changes.toLocaleString();
    }

    /**
     * Get theme-aware colors
     */
    function getThemeColor(cssVar) {
        return getComputedStyle(document.documentElement).getPropertyValue(cssVar).trim();
    }

    /**
     * Render platform distribution donut chart
     */
    function renderPlatformChart(data) {
        // Check if Chart.js is available
        if (typeof Chart === 'undefined') {
            console.warn('Cannot render platform chart: Chart.js not loaded');
            return;
        }

        const ctx = document.getElementById('platformChart');

        // Destroy existing chart
        if (charts.platform) {
            charts.platform.destroy();
        }

        // Platform colors
        const colors = {
            'IP2': '#667eea',
            'IP3': '#764ba2',
            'IP4': '#f093fb',
            'IP5': '#4facfe',
            'IP6': '#43e97b',
            'IP7': '#fa709a',
            'OpenShift': '#fee140',
            'AWS': '#30cfd0',
            'Azure': '#a8edea'
        };

        const labels = Object.keys(data);
        const values = Object.values(data);
        const backgroundColors = labels.map(label => colors[label] || '#cccccc');

        charts.platform = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: backgroundColors,
                    borderWidth: 2,
                    borderColor: getThemeColor('--bg-primary')
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: getThemeColor('--text-primary'),
                            padding: 15,
                            font: { size: 12 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                },
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const platform = labels[index];
                        navigateToAPIs(`Platform = ${platform}`);
                    }
                }
            }
        });
    }

    /**
     * Render environment distribution bar chart
     */
    function renderEnvironmentChart(data) {
        // Check if Chart.js is available
        if (typeof Chart === 'undefined') {
            console.warn('Cannot render environment chart: Chart.js not loaded');
            return;
        }

        const ctx = document.getElementById('environmentChart');

        // Destroy existing chart
        if (charts.environment) {
            charts.environment.destroy();
        }

        // Environment colors
        const colors = {
            'dev': '#43e97b',
            'tst': '#4facfe',
            'acc': '#fa709a',
            'prd': '#f44336'
        };

        const labels = Object.keys(data);
        const values = Object.values(data);
        const backgroundColors = labels.map(label => colors[label] || '#cccccc');

        charts.environment = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels.map(l => l.toUpperCase()),
                datasets: [{
                    label: 'Deployments',
                    data: values,
                    backgroundColor: backgroundColors,
                    borderWidth: 0
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Deployments: ${context.parsed.x}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        ticks: {
                            color: getThemeColor('--text-secondary')
                        },
                        grid: {
                            color: getThemeColor('--border-color')
                        }
                    },
                    y: {
                        ticks: {
                            color: getThemeColor('--text-secondary')
                        },
                        grid: {
                            display: false
                        }
                    }
                },
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const environment = labels[index];
                        navigateToAPIs(`Environment = ${environment}`);
                    }
                }
            }
        });
    }

    /**
     * Render status overview pie chart
     */
    function renderStatusChart(data) {
        // Check if Chart.js is available
        if (typeof Chart === 'undefined') {
            console.warn('Cannot render status chart: Chart.js not loaded');
            return;
        }

        const ctx = document.getElementById('statusChart');

        // Destroy existing chart
        if (charts.status) {
            charts.status.destroy();
        }

        // Status colors
        const colors = {
            'RUNNING': '#43e97b',
            'DEPLOYING': '#4facfe',
            'STOPPED': '#fa709a',
            'FAILED': '#f44336',
            'PENDING': '#fee140'
        };

        const labels = Object.keys(data);
        const values = Object.values(data);
        const backgroundColors = labels.map(label => colors[label] || '#cccccc');

        charts.status = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: backgroundColors,
                    borderWidth: 2,
                    borderColor: getThemeColor('--bg-primary')
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: getThemeColor('--text-primary'),
                            padding: 15,
                            font: { size: 12 }
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${label}: ${value} (${percentage}%)`;
                            }
                        }
                    }
                },
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const status = labels[index];
                        navigateToAPIs(`Status = ${status}`);
                    }
                }
            }
        });
    }

    /**
     * Render recent activity timeline
     */
    function renderRecentActivity(activities) {
        const container = document.getElementById('recentActivity');

        if (!activities || activities.length === 0) {
            container.innerHTML = `
                <div class="timeline-empty">
                    <i class="fas fa-inbox"></i>
                    <p>No recent activity</p>
                </div>
            `;
            return;
        }

        container.innerHTML = activities.map(activity => {
            const timestamp = formatRelativeTime(activity.timestamp);
            const actionIcon = getActionIcon(activity.action);

            return `
                <div class="timeline-item action-${activity.action}"
                     data-api="${activity.api_name || ''}"
                     data-platform="${activity.platform_id || ''}"
                     data-environment="${activity.environment_id || ''}"
                     onclick="openActivityDetails(this)">
                    <div class="timeline-timestamp">
                        <i class="fas fa-clock"></i> ${timestamp}
                    </div>
                    <div class="timeline-action">
                        <i class="${actionIcon}"></i> ${activity.action}: ${activity.api_name || 'Unknown API'}
                    </div>
                    <div class="timeline-details">
                        ${activity.platform_id ? `${activity.platform_id} / ` : ''}${activity.environment_id || 'All environments'}
                    </div>
                    <div class="timeline-user">
                        <i class="fas fa-user"></i> ${activity.username || 'System'}
                    </div>
                </div>
            `;
        }).join('');
    }

    /**
     * Format timestamp as relative time
     */
    function formatRelativeTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;

        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);
        const days = Math.floor(hours / 24);

        if (days > 1) {
            return date.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: 'numeric',
                minute: '2-digit'
            });
        } else if (days === 1) {
            return `Yesterday at ${date.toLocaleTimeString('en-US', {
                hour: 'numeric',
                minute: '2-digit'
            })}`;
        } else if (hours > 0) {
            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        } else if (minutes > 0) {
            return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        } else {
            return 'Just now';
        }
    }

    /**
     * Get Font Awesome icon for action type
     */
    function getActionIcon(action) {
        const icons = {
            'CREATE': 'fas fa-plus-circle',
            'UPDATE': 'fas fa-edit',
            'DELETE': 'fas fa-trash-alt'
        };
        return icons[action] || 'fas fa-info-circle';
    }

    /**
     * Navigate to APIs page with search query
     */
    function navigateToAPIs(searchQuery) {
        const encodedQuery = encodeURIComponent(searchQuery);
        window.location.href = `/apis?search=${encodedQuery}`;
    }

    /**
     * Open API details for timeline item
     * Global function to be called from onclick
     */
    window.openActivityDetails = function(element) {
        const apiName = element.dataset.api;
        const platform = element.dataset.platform;
        const environment = element.dataset.environment;

        // Build filter based on available data
        let filter = '';
        if (apiName) {
            filter = `API Name = ${apiName}`;
            if (platform) {
                filter += ` AND Platform = ${platform}`;
                if (environment) {
                    filter += ` AND Environment = ${environment}`;
                }
            }
        }

        if (filter) {
            navigateToAPIs(filter);
        }
    };

    /**
     * Update charts when theme changes
     */
    document.addEventListener('themeChanged', () => {
        // Re-render all charts with new theme colors
        if (charts.platform) {
            loadDashboardData();
        }
    });

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDashboard);
    } else {
        initDashboard();
    }

})();
