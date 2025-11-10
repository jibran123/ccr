// Complete search.js with Excel-style Column Filters
let currentPage = 1;
let currentPerPage = 100;
let currentSearchQuery = '';
let allResults = [];
let filteredResults = [];

// Column filter state
let columnFilters = {
    apiName: [],
    platform: [],
    environment: []
};

// Available filter values
let availableValues = {
    apiName: [],
    platform: [],
    environment: []
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing CCR API Manager with Excel-style Column Filters...');
    initializeApp();
});

function initializeApp() {
    setupEventListeners();
    createPropertiesModal();
    loadAPIs();  // Load initial data
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
    
    // Clear ALL button - clears search AND filters
    const clearBtn = document.getElementById('clearBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearAllFiltersAndSearch);
    }
    
    // Results per page
    const resultsPerPage = document.getElementById('resultsPerPage');
    if (resultsPerPage) {
        resultsPerPage.addEventListener('change', function() {
            currentPerPage = parseInt(this.value);
            currentPage = 1;
            applyFilters();
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
    
    // ==========================
    // FILTER ICON CLICK HANDLERS
    // ==========================
    
    // API Name filter icon
    const apiNameIcon = document.getElementById('filterIconApiName');
    if (apiNameIcon) {
        apiNameIcon.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleFilterDropdown('apiName');
        });
    }
    
    // Platform filter icon
    const platformIcon = document.getElementById('filterIconPlatform');
    if (platformIcon) {
        platformIcon.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleFilterDropdown('platform');
        });
    }
    
    // Environment filter icon
    const environmentIcon = document.getElementById('filterIconEnvironment');
    if (environmentIcon) {
        environmentIcon.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleFilterDropdown('environment');
        });
    }
    
    // Search within API Name dropdown
    const apiNameSearch = document.getElementById('filterSearchApiName');
    if (apiNameSearch) {
        apiNameSearch.addEventListener('input', () => filterDropdownOptions('apiName'));
    }
    
    // Select All checkboxes
    const selectAllApiName = document.getElementById('selectAllApiName');
    if (selectAllApiName) {
        selectAllApiName.addEventListener('change', () => toggleSelectAll('apiName'));
    }
    
    const selectAllPlatform = document.getElementById('selectAllPlatform');
    if (selectAllPlatform) {
        selectAllPlatform.addEventListener('change', () => toggleSelectAll('platform'));
    }
    
    const selectAllEnvironment = document.getElementById('selectAllEnvironment');
    if (selectAllEnvironment) {
        selectAllEnvironment.addEventListener('change', () => toggleSelectAll('environment'));
    }
    
    // Close dropdowns when clicking outside
    document.addEventListener('click', function(e) {
        const dropdowns = document.querySelectorAll('.filter-dropdown');
        dropdowns.forEach(dropdown => {
            if (!dropdown.contains(e.target) && !e.target.classList.contains('filter-icon')) {
                dropdown.style.display = 'none';
            }
        });
    });
}

// ==========================
// EXCEL-STYLE FILTER FUNCTIONS
// ==========================

function toggleFilterDropdown(columnName) {
    const dropdown = document.getElementById(`filterDropdown${capitalize(columnName)}`);
    
    // Close all other dropdowns
    document.querySelectorAll('.filter-dropdown').forEach(d => {
        if (d.id !== dropdown.id) {
            d.style.display = 'none';
        }
    });
    
    // Toggle this dropdown
    if (dropdown.style.display === 'none' || dropdown.style.display === '') {
        populateFilterDropdown(columnName);
        dropdown.style.display = 'block';
    } else {
        dropdown.style.display = 'none';
    }
}

function closeFilterDropdown(columnName) {
    const dropdown = document.getElementById(`filterDropdown${capitalize(columnName)}`);
    if (dropdown) {
        dropdown.style.display = 'none';
    }
}

function populateFilterDropdown(columnName) {
    const optionsContainer = document.getElementById(`filterOptions${capitalize(columnName)}`);
    if (!optionsContainer) return;
    
    // Get available values for this column
    const values = availableValues[columnName] || [];
    
    console.log(`Populating ${columnName} dropdown with ${values.length} values`);
    
    // Clear existing options
    optionsContainer.innerHTML = '';
    
    // Create checkbox for each value
    values.forEach(value => {
        const isChecked = columnFilters[columnName].length === 0 || columnFilters[columnName].includes(value);
        
        const label = document.createElement('label');
        label.className = 'filter-option';
        label.innerHTML = `
            <input type="checkbox" value="${escapeHtml(value)}" ${isChecked ? 'checked' : ''}>
            <span>${escapeHtml(value)}</span>
        `;
        
        optionsContainer.appendChild(label);
    });
    
    // Update Select All checkbox
    updateSelectAllCheckbox(columnName);
}

function filterDropdownOptions(columnName) {
    // Only for API Name dropdown with search
    if (columnName !== 'apiName') return;
    
    const searchInput = document.getElementById('filterSearchApiName');
    const query = searchInput.value.toLowerCase();
    
    const optionsContainer = document.getElementById('filterOptionsApiName');
    const options = optionsContainer.querySelectorAll('.filter-option');
    
    options.forEach(option => {
        const text = option.textContent.toLowerCase();
        option.style.display = text.includes(query) ? 'flex' : 'none';
    });
}

function toggleSelectAll(columnName) {
    const selectAllCheckbox = document.getElementById(`selectAll${capitalize(columnName)}`);
    const optionsContainer = document.getElementById(`filterOptions${capitalize(columnName)}`);
    const checkboxes = optionsContainer.querySelectorAll('input[type="checkbox"]');
    
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAllCheckbox.checked;
    });
}

function updateSelectAllCheckbox(columnName) {
    const selectAllCheckbox = document.getElementById(`selectAll${capitalize(columnName)}`);
    const optionsContainer = document.getElementById(`filterOptions${capitalize(columnName)}`);
    const checkboxes = optionsContainer.querySelectorAll('input[type="checkbox"]');
    
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    const noneChecked = Array.from(checkboxes).every(cb => !cb.checked);
    
    selectAllCheckbox.checked = allChecked;
    selectAllCheckbox.indeterminate = !allChecked && !noneChecked;
}

function applyColumnFilter(columnName) {
    const optionsContainer = document.getElementById(`filterOptions${capitalize(columnName)}`);
    const checkboxes = optionsContainer.querySelectorAll('input[type="checkbox"]:checked');
    
    // Get selected values
    const selectedValues = Array.from(checkboxes).map(cb => cb.value);
    
    console.log(`Applying filter for ${columnName}:`, selectedValues);
    
    // Update filter state
    columnFilters[columnName] = selectedValues;
    
    // Update filter icon to show active state
    updateFilterIcon(columnName);
    
    // Close dropdown
    closeFilterDropdown(columnName);
    
    // Apply all filters
    applyFilters();
}

function updateFilterIcon(columnName) {
    const icon = document.getElementById(`filterIcon${capitalize(columnName)}`);
    if (!icon) return;
    
    // Check if filter is active (not all values selected)
    const allValues = availableValues[columnName] || [];
    const selectedValues = columnFilters[columnName] || [];
    
    const isActive = selectedValues.length > 0 && selectedValues.length < allValues.length;
    
    if (isActive) {
        icon.classList.add('active');
    } else {
        icon.classList.remove('active');
    }
}

function extractFilterValues() {
    // Extract unique values from all results
    const apiNames = [...new Set(allResults.map(api => api['API Name'] || api.apiName).filter(Boolean))].sort();
    const platforms = [...new Set(allResults.map(api => api.PlatformID || api.platform).filter(Boolean))].sort();
    const environments = [...new Set(allResults.map(api => api.Environment || api.environment).filter(Boolean))].sort();
    
    availableValues = {
        apiName: apiNames,
        platform: platforms,
        environment: environments
    };
    
    console.log('Extracted filter values:', {
        apiName: availableValues.apiName.length,
        platform: availableValues.platform.length,
        environment: availableValues.environment.length
    });
}

function applyFilters() {
    console.log('Applying filters:', columnFilters);
    
    // Start with all results
    filteredResults = allResults;
    
    // Apply API Name filter
    if (columnFilters.apiName.length > 0) {
        filteredResults = filteredResults.filter(api => {
            const apiName = api['API Name'] || api.apiName;
            return columnFilters.apiName.includes(apiName);
        });
    }
    
    // Apply Platform filter
    if (columnFilters.platform.length > 0) {
        filteredResults = filteredResults.filter(api => {
            const platform = api.PlatformID || api.platform;
            return columnFilters.platform.includes(platform);
        });
    }
    
    // Apply Environment filter
    if (columnFilters.environment.length > 0) {
        filteredResults = filteredResults.filter(api => {
            const environment = api.Environment || api.environment;
            return columnFilters.environment.includes(environment);
        });
    }
    
    console.log(`Filtered ${filteredResults.length} from ${allResults.length} results`);
    
    // Display filtered results
    displayAPIs(filteredResults);
    updateResultsCount(filteredResults.length);
}

function clearAllFiltersAndSearch() {
    console.log('Clearing ALL filters and search');
    
    // Clear search input
    document.getElementById('searchInput').value = '';
    currentSearchQuery = '';
    
    // Clear all column filters
    columnFilters = {
        apiName: [],
        platform: [],
        environment: []
    };
    
    // Update all filter icons to inactive
    ['apiName', 'platform', 'environment'].forEach(col => {
        updateFilterIcon(col);
    });
    
    // Reload data
    currentPage = 1;
    loadAPIs();
}

// ==========================
// SEARCH & DATA LOADING
// ==========================

function performSearch() {
    const searchInput = document.getElementById('searchInput');
    currentSearchQuery = searchInput.value.trim();
    currentPage = 1;
    
    console.log('Performing search:', currentSearchQuery);
    
    // Clear filters when performing new search
    columnFilters = {
        apiName: [],
        platform: [],
        environment: []
    };
    
    loadAPIs();
}

async function loadAPIs() {
    try {
        const params = new URLSearchParams({
            q: currentSearchQuery,
            page: currentPage,
            page_size: currentPerPage
        });
        
        console.log('Loading APIs with params:', params.toString());
        
        const response = await fetch(`/api/search?${params}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Response data:', data);
        
        // Extract results from response
        if (data.status === 'success' && data.data) {
            allResults = data.data;
        } else if (data.apis) {
            allResults = data.apis;
        } else if (Array.isArray(data)) {
            allResults = data;
        } else {
            allResults = [];
        }
        
        console.log('Number of results:', allResults.length);
        
        // Extract available filter values
        extractFilterValues();
        
        // Apply any existing filters
        applyFilters();
        
        // Update pagination if metadata exists
        if (data.metadata) {
            updatePagination(data.metadata);
        }
        
    } catch (error) {
        console.error('Error loading APIs:', error);
        displayError('Failed to load APIs: ' + error.message);
    }
}

// ==========================
// DISPLAY FUNCTIONS
// ==========================

function displayAPIs(apis) {
    const tbody = document.getElementById('apiTableBody');
    
    if (!tbody) {
        console.error('Table body element not found!');
        return;
    }
    
    tbody.innerHTML = '';
    
    if (!apis || apis.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="no-results">No APIs found</td></tr>';
        return;
    }
    
    // Display each row with REORDERED COLUMNS
    apis.forEach((api) => {
        const tr = document.createElement('tr');
        
        // Handle field names from backend
        const apiName = api['API Name'] || api.apiName || 'N/A';
        const platform = api.PlatformID || api.platform || 'N/A';
        const environment = api.Environment || api.environment || 'N/A';
        const version = api.Version || api.version || 'N/A';
        const deploymentDate = api.DeploymentDate || api.deploymentDate || 'N/A';
        const lastUpdated = api.LastUpdated || api.lastUpdated || 'N/A';
        const updatedBy = api.UpdatedBy || api.updatedBy || 'N/A';
        const status = api.Status || api.status || 'UNKNOWN';
        const properties = api.Properties || api.properties || {};
        
        const statusClass = getStatusClass(status);
        
        // NEW COLUMN ORDER: API Name, Platform, Environment, Version, Deployment Date, Last Updated, Updated By, Status, Properties
        tr.innerHTML = `
            <td class="api-name">${escapeHtml(apiName)}</td>
            <td>${escapeHtml(platform)}</td>
            <td>${escapeHtml(environment)}</td>
            <td class="api-version">${escapeHtml(version)}</td>
            <td>${escapeHtml(deploymentDate)}</td>
            <td>${escapeHtml(lastUpdated)}</td>
            <td>${escapeHtml(updatedBy)}</td>
            <td><span class="status-badge ${statusClass}">${escapeHtml(status)}</span></td>
            <td>
                <button onclick='viewProperties(${JSON.stringify(properties)}, "${escapeHtml(apiName)}")' class="btn-view">
                    <i class="fas fa-eye"></i> View
                </button>
            </td>
        `;
        
        tbody.appendChild(tr);
    });
}

function getStatusClass(status) {
    // Convert status to uppercase for comparison
    const normalizedStatus = status.toUpperCase();
    
    const statusMap = {
        // Green statuses
        'RUNNING': 'status-running',
        'ACTIVE': 'status-active',
        'DEPLOYED': 'status-deployed',
        'STARTED': 'status-running',
        
        // Red statuses
        'STOPPED': 'status-stopped',
        'FAILED': 'status-failed',
        'ERROR': 'status-error',
        
        // Yellow/Orange statuses
        'DEPLOYING': 'status-deploying',
        'PENDING': 'status-pending',
        
        // Gray statuses
        'UNKNOWN': 'status-unknown',
        'MAINTENANCE': 'status-maintenance'
    };
    
    return statusMap[normalizedStatus] || 'status-unknown';
}

function updateResultsCount(count) {
    const resultCount = document.getElementById('resultCount');
    if (resultCount) {
        resultCount.innerHTML = `<i class="fas fa-chart-bar"></i> Search Results (${count})`;
    }
}

function displayError(message) {
    const errorContainer = document.getElementById('errorContainer');
    if (errorContainer) {
        errorContainer.textContent = message;
        errorContainer.style.display = 'block';
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            errorContainer.style.display = 'none';
        }, 5000);
    }
}

// ==========================
// PROPERTIES MODAL
// ==========================

function createPropertiesModal() {
    // Modal already exists in HTML, just set up close handler
    const modal = document.getElementById('propertiesModal');
    if (!modal) return;
    
    const closeBtn = modal.querySelector('.modal-close');
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            modal.classList.remove('active');
            modal.style.display = 'none';
        });
    }
    
    // Close on outside click
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.classList.remove('active');
            modal.style.display = 'none';
        }
    });
}

function viewProperties(properties, apiName) {
    const modal = document.getElementById('propertiesModal');
    const modalBody = document.getElementById('modalBody');
    
    if (!modal || !modalBody) {
        alert('Modal not available');
        return;
    }
    
    // Update modal header
    const modalHeader = modal.querySelector('.modal-header h2');
    if (modalHeader && apiName) {
        modalHeader.textContent = `Properties - ${apiName}`;
    }
    
    // Build properties HTML
    if (!properties || Object.keys(properties).length === 0) {
        modalBody.innerHTML = '<div class="no-properties">No properties available</div>';
    } else {
        let propertiesHtml = '<table class="properties-table"><thead><tr><th>Key</th><th>Value</th></tr></thead><tbody>';
        
        Object.entries(properties).forEach(([key, value]) => {
            const displayValue = typeof value === 'object' ? JSON.stringify(value, null, 2) : value;
            propertiesHtml += `
                <tr>
                    <td class="property-key">${escapeHtml(key)}</td>
                    <td class="property-value">${escapeHtml(String(displayValue))}</td>
                </tr>
            `;
        });
        
        propertiesHtml += '</tbody></table>';
        modalBody.innerHTML = propertiesHtml;
    }
    
    // Show modal
    modal.style.display = 'flex';
    modal.classList.add('active');
}

// ==========================
// EXPORT FUNCTIONS
// ==========================

function exportResults(format) {
    const dataToExport = filteredResults.length > 0 ? filteredResults : allResults;
    
    if (dataToExport.length === 0) {
        alert('No data to export');
        return;
    }
    
    if (format === 'json') {
        exportJSON(dataToExport);
    } else if (format === 'csv') {
        exportCSV(dataToExport);
    }
}

function exportJSON(data) {
    const jsonString = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ccr-api-export-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

function exportCSV(data) {
    // CSV headers
    const headers = ['API Name', 'Platform', 'Environment', 'Version', 'Deployment Date', 'Last Updated', 'Updated By', 'Status'];
    
    // Build CSV content
    let csvContent = headers.join(',') + '\n';
    
    data.forEach(api => {
        const row = [
            api['API Name'] || api.apiName || '',
            api.PlatformID || api.platform || '',
            api.Environment || api.environment || '',
            api.Version || api.version || '',
            api.DeploymentDate || api.deploymentDate || '',
            api.LastUpdated || api.lastUpdated || '',
            api.UpdatedBy || api.updatedBy || '',
            api.Status || api.status || ''
        ].map(field => `"${String(field).replace(/"/g, '""')}"`);
        
        csvContent += row.join(',') + '\n';
    });
    
    // Download
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `ccr-api-export-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
}

// ==========================
// UTILITY FUNCTIONS
// ==========================

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function updatePagination(metadata) {
    const paginationDiv = document.getElementById('pagination');
    if (!paginationDiv) return;
    
    const { page, total_pages } = metadata;
    
    if (total_pages <= 1) {
        paginationDiv.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // Previous button
    html += `<button ${page <= 1 ? 'disabled' : ''} onclick="changePage(${page - 1})">Previous</button>`;
    
    // Page info
    html += `<span>Page ${page} of ${total_pages}</span>`;
    
    // Next button
    html += `<button ${page >= total_pages ? 'disabled' : ''} onclick="changePage(${page + 1})">Next</button>`;
    
    paginationDiv.innerHTML = html;
}

function changePage(page) {
    currentPage = page;
    loadAPIs();
}