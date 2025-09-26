// Complete search.js file - Updated for Platform array structure
// app/static/js/search.js

let currentPage = 1;
let currentPerPage = 100;
let currentSearchQuery = '';
let currentCaseSensitive = false;
let currentRegexMode = false;
let allResults = [];
let searchTimeout = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing API Search...');
    initializeApp();
});

function initializeApp() {
    loadAPIs();
    setupEventListeners();
    setupKeyboardShortcuts();
    updateSearchHelp();
    loadUserPreferences();
}

function setupEventListeners() {
    // Search form submission
    const searchForm = document.getElementById('searchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            performSearch();
        });
    }
    
    // Search input with debounce
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                if (this.value !== currentSearchQuery) {
                    performSearch();
                }
            }, 500); // 500ms debounce
        });
        
        // Focus on page load
        searchInput.focus();
    }
    
    // Clear button
    const clearBtn = document.getElementById('clearBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            clearSearch();
        });
    }
    
    // Regex mode checkbox
    const regexMode = document.getElementById('regexMode');
    if (regexMode) {
        regexMode.addEventListener('change', function() {
            currentRegexMode = this.checked;
            saveUserPreferences();
            if (currentSearchQuery) {
                performSearch();
            }
        });
    }
    
    // Case sensitive checkbox
    const caseSensitive = document.getElementById('caseSensitive');
    if (caseSensitive) {
        caseSensitive.addEventListener('change', function() {
            currentCaseSensitive = this.checked;
            saveUserPreferences();
            if (currentSearchQuery) {
                performSearch();
            }
        });
    }
    
    // Per page selector
    const perPageSelector = document.getElementById('perPageSelector');
    if (perPageSelector) {
        perPageSelector.addEventListener('change', function() {
            currentPerPage = parseInt(this.value);
            currentPage = 1;
            saveUserPreferences();
            loadAPIs();
        });
    }
    
    // Export buttons
    const exportJsonBtn = document.getElementById('exportJsonBtn');
    if (exportJsonBtn) {
        exportJsonBtn.addEventListener('click', () => exportResults('json'));
    }
    
    const exportCsvBtn = document.getElementById('exportCsvBtn');
    if (exportCsvBtn) {
        exportCsvBtn.addEventListener('click', () => exportResults('csv'));
    }
    
    // Refresh button
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            loadAPIs();
        });
    }
    
    // Property search form
    const propSearchForm = document.getElementById('propSearchForm');
    if (propSearchForm) {
        propSearchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            searchByProperty();
        });
    }
}

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + K to focus search
        if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
            e.preventDefault();
            const searchInput = document.getElementById('searchInput');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
        
        // Escape to clear search
        if (e.key === 'Escape') {
            const searchInput = document.getElementById('searchInput');
            if (searchInput && searchInput === document.activeElement) {
                clearSearch();
            }
        }
        
        // Ctrl/Cmd + E to export
        if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
            e.preventDefault();
            exportResults('json');
        }
    });
}

function updateSearchHelp() {
    const helpToggle = document.querySelector('.help-toggle');
    if (helpToggle) {
        helpToggle.addEventListener('click', function() {
            const helpContent = document.querySelector('.help-content');
            if (helpContent) {
                const isVisible = helpContent.style.display === 'block';
                helpContent.style.display = isVisible ? 'none' : 'block';
                this.innerHTML = isVisible ? 
                    '<i class="fas fa-question-circle"></i> Search Help & Examples' : 
                    '<i class="fas fa-times-circle"></i> Hide Help';
            }
        });
    }
}

function loadUserPreferences() {
    // Load from localStorage
    const prefs = localStorage.getItem('apiSearchPreferences');
    if (prefs) {
        try {
            const parsed = JSON.parse(prefs);
            currentPerPage = parsed.perPage || 100;
            currentCaseSensitive = parsed.caseSensitive || false;
            currentRegexMode = parsed.regexMode || false;
            
            // Update UI
            const perPageSelector = document.getElementById('perPageSelector');
            if (perPageSelector) perPageSelector.value = currentPerPage;
            
            const caseSensitive = document.getElementById('caseSensitive');
            if (caseSensitive) caseSensitive.checked = currentCaseSensitive;
            
            const regexMode = document.getElementById('regexMode');
            if (regexMode) regexMode.checked = currentRegexMode;
        } catch (e) {
            console.error('Failed to load preferences:', e);
        }
    }
}

function saveUserPreferences() {
    const prefs = {
        perPage: currentPerPage,
        caseSensitive: currentCaseSensitive,
        regexMode: currentRegexMode
    };
    localStorage.setItem('apiSearchPreferences', JSON.stringify(prefs));
}

function clearSearch() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.value = '';
        searchInput.focus();
    }
    currentSearchQuery = '';
    currentPage = 1;
    loadAPIs();
}

function performSearch() {
    const searchInput = document.getElementById('searchInput');
    currentSearchQuery = searchInput ? searchInput.value : '';
    currentPage = 1;
    loadAPIs();
}

async function loadAPIs() {
    try {
        // Show loading state
        showLoadingState();
        
        // Build query parameters
        const params = new URLSearchParams({
            q: currentSearchQuery,
            case_sensitive: currentCaseSensitive,
            regex: currentRegexMode,
            page: currentPage,
            per_page: currentPerPage
        });
        
        const response = await fetch(`/api/apis?${params}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // Store all results - these are already flattened from backend
        allResults = data.apis || [];
        
        // Display results
        displayAPIs(allResults);
        updateResultsCount(allResults.length, false);
        updatePagination(data);
        
    } catch (error) {
        console.error('Error loading APIs:', error);
        displayError('Failed to load APIs: ' + error.message);
    }
}

async function searchByProperty() {
    const propKey = document.getElementById('propKey');
    const propValue = document.getElementById('propValue');
    
    if (!propKey || !propValue) return;
    
    const key = propKey.value.trim();
    const value = propValue.value.trim();
    
    if (!key || !value) {
        alert('Please enter both property key and value');
        return;
    }
    
    try {
        showLoadingState();
        
        const params = new URLSearchParams({
            key: key,
            value: value
        });
        
        const response = await fetch(`/api/apis/search/properties?${params}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        allResults = data.apis || [];
        displayAPIs(allResults);
        updateResultsCount(allResults.length, false);
        
        // Clear pagination for property search
        const paginationElement = document.getElementById('pagination');
        if (paginationElement) {
            paginationElement.innerHTML = '';
        }
        
    } catch (error) {
        console.error('Error searching by property:', error);
        displayError('Failed to search by property: ' + error.message);
    }
}

function showLoadingState() {
    updateResultsCount(0, true);
    const tbody = document.getElementById('apiTableBody');
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="loading-cell">
                    <div class="loading-spinner">
                        <i class="fas fa-spinner fa-spin fa-2x"></i>
                        <p>Loading APIs...</p>
                    </div>
                </td>
            </tr>
        `;
    }
}

function displayAPIs(apis) {
    const tbody = document.getElementById('apiTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    if (!apis || apis.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="no-results">
                    <div class="empty-state">
                        <i class="fas fa-search fa-3x"></i>
                        <p>No APIs found</p>
                        ${currentSearchQuery ? '<p class="text-sm">Try adjusting your search criteria</p>' : ''}
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    // Display each row (already flattened from backend)
    apis.forEach((api, index) => {
        const row = createAPIRow(api, index);
        tbody.appendChild(row);
    });
    
    // Add hover effects
    addRowHoverEffects();
}

function createAPIRow(api, index) {
    const tr = document.createElement('tr');
    tr.className = 'api-row';
    tr.dataset.apiId = api._id;
    tr.dataset.index = index;
    
    // Determine status badge color
    const statusClass = getStatusClass(api.status);
    
    // Handle properties - ensure it's properly escaped
    const propertiesStr = JSON.stringify(api.properties || {});
    const escapedProperties = escapeHtml(propertiesStr).replace(/'/g, "\\'");
    
    tr.innerHTML = `
        <td class="api-name-cell">
            <div class="api-name">${escapeHtml(api.apiName)}</div>
        </td>
        <td class="platform-cell">
            <div class="platform-info">
                <span class="platform-name">${escapeHtml(api.platform)}</span>
                <span class="platform-id">${escapeHtml(api.platformId)}</span>
            </div>
        </td>
        <td class="environment-cell">
            <div class="environment-info">
                <span class="environment-name">${escapeHtml(api.environment)}</span>
                <span class="environment-id">${escapeHtml(api.environmentId)}</span>
            </div>
        </td>
        <td class="date-cell">
            <span title="${escapeHtml(api.deploymentDate)}">${formatDate(api.deploymentDate)}</span>
        </td>
        <td class="date-cell">
            <span title="${escapeHtml(api.lastUpdated)}">${formatDate(api.lastUpdated)}</span>
        </td>
        <td class="user-cell">${escapeHtml(api.updatedBy)}</td>
        <td class="status-cell">
            <span class="status-badge ${statusClass}">
                ${getStatusIcon(api.status)} ${escapeHtml(api.status)}
            </span>
        </td>
        <td class="actions-cell">
            <button onclick="viewProperties('${escapedProperties}')" 
                    class="btn-view" 
                    title="View Properties">
                <i class="fas fa-eye"></i> View
            </button>
        </td>
    `;
    
    return tr;
}

function getStatusClass(status) {
    const statusMap = {
        'RUNNING': 'status-running',
        'STOPPED': 'status-stopped',
        'PENDING': 'status-pending',
        'UNKNOWN': 'status-unknown',
        'FAILED': 'status-failed',
        'DEPLOYING': 'status-deploying',
        'DEPLOYED': 'status-running',
        'ERROR': 'status-failed'
    };
    return statusMap[status] || 'status-unknown';
}

function getStatusIcon(status) {
    const iconMap = {
        'RUNNING': '<i class="fas fa-check-circle"></i>',
        'STOPPED': '<i class="fas fa-stop-circle"></i>',
        'PENDING': '<i class="fas fa-clock"></i>',
        'UNKNOWN': '<i class="fas fa-question-circle"></i>',
        'FAILED': '<i class="fas fa-times-circle"></i>',
        'DEPLOYING': '<i class="fas fa-spinner fa-spin"></i>',
        'DEPLOYED': '<i class="fas fa-check-circle"></i>',
        'ERROR': '<i class="fas fa-exclamation-circle"></i>'
    };
    return iconMap[status] || '<i class="fas fa-question-circle"></i>';
}

function formatDate(dateStr) {
    if (!dateStr || dateStr === 'N/A') return 'N/A';
    
    try {
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) return dateStr;
        
        // Format as YYYY-MM-DD HH:mm
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        
        return `${year}-${month}-${day} ${hours}:${minutes}`;
    } catch (e) {
        return dateStr;
    }
}

function addRowHoverEffects() {
    const rows = document.querySelectorAll('.api-row');
    rows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.backgroundColor = '#f7fafc';
        });
        row.addEventListener('mouseleave', function() {
            this.style.backgroundColor = '';
        });
    });
}

function viewProperties(propertiesJson) {
    try {
        const properties = JSON.parse(propertiesJson);
        
        // Create modal or detailed view
        showPropertiesModal(properties);
        
    } catch (error) {
        console.error('Error parsing properties:', error);
        showErrorModal('Failed to parse properties');
    }
}

function showPropertiesModal(properties) {
    // Check if modal exists, if not create it
    let modal = document.getElementById('propertiesModal');
    if (!modal) {
        modal = createPropertiesModal();
        document.body.appendChild(modal);
    }
    
    // Build properties content
    const modalBody = modal.querySelector('.modal-body');
    if (!modalBody) {
        // Fallback to alert if modal structure is broken
        alert(formatPropertiesForAlert(properties));
        return;
    }
    
    if (Object.keys(properties).length === 0) {
        modalBody.innerHTML = '<p class="no-properties">No properties available</p>';
    } else {
        let content = '<div class="properties-list">';
        for (const [key, value] of Object.entries(properties)) {
            content += `
                <div class="property-item">
                    <span class="property-key">${escapeHtml(key)}:</span>
                    <span class="property-value">${escapeHtml(String(value))}</span>
                </div>
            `;
        }
        content += '</div>';
        modalBody.innerHTML = content;
    }
    
    // Show modal
    modal.style.display = 'block';
    
    // Add close handlers
    const closeBtn = modal.querySelector('.close-modal');
    const cancelBtn = modal.querySelector('.btn-cancel');
    
    if (closeBtn) {
        closeBtn.onclick = () => modal.style.display = 'none';
    }
    if (cancelBtn) {
        cancelBtn.onclick = () => modal.style.display = 'none';
    }
    
    // Close on outside click
    window.onclick = function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    };
    
    // Close on Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.style.display === 'block') {
            modal.style.display = 'none';
        }
    });
}

function createPropertiesModal() {
    const modal = document.createElement('div');
    modal.id = 'propertiesModal';
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>API Properties</h3>
                <span class="close-modal">&times;</span>
            </div>
            <div class="modal-body">
                <!-- Properties will be inserted here -->
            </div>
            <div class="modal-footer">
                <button class="btn-cancel">Close</button>
            </div>
        </div>
    `;
    return modal;
}

function formatPropertiesForAlert(properties) {
    if (Object.keys(properties).length === 0) {
        return 'No properties available';
    }
    
    let result = 'Properties:\n\n';
    for (const [key, value] of Object.entries(properties)) {
        result += `${key}: ${value}\n`;
    }
    return result;
}

function showErrorModal(message) {
    alert('Error: ' + message);
}

function updateResultsCount(count, loading = false) {
    const countElement = document.getElementById('resultCount');
    if (!countElement) return;
    
    if (loading) {
        countElement.innerHTML = `
            <span class="loading-text">
                <i class="fas fa-spinner fa-spin"></i> Loading...
            </span>
        `;
    } else {
        const apiText = count === 1 ? 'API deployment' : 'API deployments';
        countElement.innerHTML = `
            <span class="results-text">
                <i class="fas fa-chart-bar"></i> 
                Search Results 
                <strong>(${count} ${apiText} found)</strong>
            </span>
        `;
    }
}

function updatePagination(data) {
    const paginationElement = document.getElementById('pagination');
    if (!paginationElement) return;
    
    const totalPages = data.total_pages || 1;
    const total = data.total || 0;
    
    if (totalPages <= 1) {
        paginationElement.innerHTML = '';
        return;
    }
    
    let paginationHTML = '<div class="pagination-controls">';
    
    // Page info
    paginationHTML += `
        <span class="page-info">
            Page ${currentPage} of ${totalPages} (Total: ${total} APIs)
        </span>
    `;
    
    paginationHTML += '<div class="pagination-buttons">';
    
    // First page button
    if (currentPage > 2) {
        paginationHTML += `
            <button onclick="changePage(1)" class="pagination-btn" title="First Page">
                <i class="fas fa-angle-double-left"></i>
            </button>
        `;
    }
    
    // Previous button
    if (currentPage > 1) {
        paginationHTML += `
            <button onclick="changePage(${currentPage - 1})" class="pagination-btn" title="Previous Page">
                <i class="fas fa-angle-left"></i> Previous
            </button>
        `;
    }
    
    // Page numbers
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, startPage + 4);
    
    for (let i = startPage; i <= endPage; i++) {
        const activeClass = i === currentPage ? 'active' : '';
        paginationHTML += `
            <button onclick="changePage(${i})" 
                    class="pagination-btn pagination-number ${activeClass}"
                    ${i === currentPage ? 'disabled' : ''}>
                ${i}
            </button>
        `;
    }
    
    // Next button
    if (currentPage < totalPages) {
        paginationHTML += `
            <button onclick="changePage(${currentPage + 1})" class="pagination-btn" title="Next Page">
                Next <i class="fas fa-angle-right"></i>
            </button>
        `;
    }
    
    // Last page button
    if (currentPage < totalPages - 1) {
        paginationHTML += `
            <button onclick="changePage(${totalPages})" class="pagination-btn" title="Last Page">
                <i class="fas fa-angle-double-right"></i>
            </button>
        `;
    }
    
    paginationHTML += '</div></div>';
    
    paginationElement.innerHTML = paginationHTML;
}

function changePage(page) {
    currentPage = page;
    loadAPIs();
    
    // Scroll to top of results
    const resultsSection = document.querySelector('.results-section');
    if (resultsSection) {
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function displayError(message) {
    const tbody = document.getElementById('apiTableBody');
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="error-cell">
                    <div class="error-message">
                        <i class="fas fa-exclamation-triangle fa-2x"></i>
                        <p>${escapeHtml(message)}</p>
                        <button onclick="loadAPIs()" class="btn-retry">
                            <i class="fas fa-redo"></i> Retry
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }
    updateResultsCount(0, false);
}

function escapeHtml(unsafe) {
    if (unsafe == null || unsafe === undefined) return 'N/A';
    return String(unsafe)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Export functions
function exportResults(format) {
    if (!allResults || allResults.length === 0) {
        alert('No data to export');
        return;
    }
    
    if (format === 'json') {
        exportAsJSON();
    } else if (format === 'csv') {
        exportAsCSV();
    }
}

function exportAsJSON() {
    const exportData = allResults.map(api => ({
        apiName: api.apiName,
        platform: api.platform,
        platformId: api.platformId,
        environment: api.environment,
        environmentId: api.environmentId,
        deploymentDate: api.deploymentDate,
        lastUpdated: api.lastUpdated,
        updatedBy: api.updatedBy,
        status: api.status,
        properties: api.properties
    }));
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], 
                          { type: 'application/json' });
    downloadBlob(blob, `api_deployments_${getTimestamp()}.json`);
}

function exportAsCSV() {
    const headers = ['API Name', 'Platform', 'Platform ID', 'Environment', 
                    'Environment ID', 'Deployment Date', 'Last Updated', 
                    'Updated By', 'Status', 'Properties'];
    
    const rows = allResults.map(api => [
        api.apiName,
        api.platform,
        api.platformId,
        api.environment,
        api.environmentId,
        api.deploymentDate,
        api.lastUpdated,
        api.updatedBy,
        api.status,
        JSON.stringify(api.properties || {})
    ]);
    
    const csvContent = [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    downloadBlob(blob, `api_deployments_${getTimestamp()}.csv`);
}

function downloadBlob(blob, filename) {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

function getTimestamp() {
    const now = new Date();
    return now.toISOString().replace(/[:.]/g, '-').slice(0, -5);
}

// Public API
window.apiSearch = {
    refresh: loadAPIs,
    search: performSearch,
    clearSearch: clearSearch,
    exportResults: exportResults,
    changePage: changePage,
    viewProperties: viewProperties
};

// Log initialization complete
console.log('API Search initialized successfully');