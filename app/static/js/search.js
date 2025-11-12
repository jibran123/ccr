// Complete search.js with Excel-style Column Filters + Frontend Validation
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
    console.log('Initializing CCR API Manager with validation...');
    initializeApp();
});

function initializeApp() {
    setupEventListeners();
    createPropertiesModal();
    loadAPIs();  // Load initial data
}

function setupEventListeners() {
    // Search form submission with validation
    const searchForm = document.getElementById('searchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            performSearch();
        });
    }
    
    // Real-time validation on search input
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        // Debounce validation to avoid too many checks
        let validationTimeout;
        searchInput.addEventListener('input', function(e) {
            clearTimeout(validationTimeout);
            validationTimeout = setTimeout(() => {
                validateSearchInput(e.target);
            }, 500);
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
    // FILTER ICON CLICKS
    // ==========================
    
    const filterIcons = document.querySelectorAll('.filter-icon');
    filterIcons.forEach(icon => {
        icon.addEventListener('click', function(e) {
            e.stopPropagation();
            const columnName = this.dataset.column;
            toggleFilterDropdown(columnName);
        });
    });
    
    // Add input event listeners for filter search boxes
    const filterSearchApiName = document.getElementById('filterSearchApiName');
    if (filterSearchApiName) {
        filterSearchApiName.addEventListener('input', function() {
            // Validate filter input
            if (window.ValidationLib) {
                const result = window.ValidationLib.validateFilterInput(this.value);
                if (result.valid) {
                    filterDropdownOptions('apiName');
                }
            } else {
                filterDropdownOptions('apiName');
            }
        });
    }
    
    // Click outside to close dropdowns
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
// VALIDATION FUNCTIONS
// ==========================

/**
 * Validate search input field in real-time
 * @param {HTMLInputElement} inputElement - Search input element
 */
function validateSearchInput(inputElement) {
    if (!window.ValidationLib) {
        console.warn('Validation library not loaded');
        return true;
    }
    
    const value = inputElement.value;
    const result = window.ValidationLib.validateSearchQuery(value);
    
    // Visual feedback
    if (!result.valid && value.length > 0) {
        inputElement.style.borderColor = '#dc2626';
        inputElement.style.backgroundColor = '#fef2f2';
    } else {
        inputElement.style.borderColor = '';
        inputElement.style.backgroundColor = '';
    }
    
    return result.valid;
}

/**
 * Sanitize and validate before performing search
 * @returns {boolean} True if validation passed
 */
function validateBeforeSearch() {
    const searchInput = document.getElementById('searchInput');
    const query = searchInput.value;
    
    // If validation library is available, use it
    if (window.ValidationLib) {
        const result = window.ValidationLib.validateSearchQuery(query);
        
        if (!result.valid) {
            // Show error via toast
            if (window.showToast) {
                window.showToast(result.error, 'error', { duration: 5000 });
            } else {
                alert(result.error);
            }
            
            // Visual feedback
            searchInput.style.borderColor = '#dc2626';
            searchInput.style.backgroundColor = '#fef2f2';
            searchInput.focus();
            
            return false;
        }
        
        // Update input with sanitized value
        if (result.sanitized !== query) {
            searchInput.value = result.sanitized;
        }
        
        // Clear visual feedback
        searchInput.style.borderColor = '';
        searchInput.style.backgroundColor = '';
    }
    
    return true;
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
        
        // Use validation library's escapeHtml if available, otherwise use local function
        const escapedValue = window.ValidationLib ? 
            window.ValidationLib.escapeHtml(value) : 
            escapeHtml(value);
        
        const label = document.createElement('label');
        label.className = 'filter-option';
        label.innerHTML = `
            <input type="checkbox" value="${escapedValue}" ${isChecked ? 'checked' : ''}>
            <span>${escapedValue}</span>
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
    let query = searchInput.value.toLowerCase();
    
    // Sanitize filter search input
    if (window.ValidationLib) {
        const result = window.ValidationLib.validateFilterInput(query);
        if (result.valid && result.sanitized) {
            query = result.sanitized.toLowerCase();
        }
    }
    
    const optionsContainer = document.getElementById('filterOptionsApiName');
    const options = optionsContainer.querySelectorAll('.filter-option');
    
    options.forEach(option => {
        const text = option.textContent.toLowerCase();
        option.style.display = text.includes(query) ? '' : 'none';
    });
}

function updateSelectAllCheckbox(columnName) {
    const selectAllCheckbox = document.getElementById(`selectAll${capitalize(columnName)}`);
    const optionsContainer = document.getElementById(`filterOptions${capitalize(columnName)}`);
    
    if (!selectAllCheckbox || !optionsContainer) return;
    
    const checkboxes = optionsContainer.querySelectorAll('input[type="checkbox"]');
    const checkedCount = Array.from(checkboxes).filter(cb => cb.checked).length;
    
    selectAllCheckbox.checked = checkedCount === checkboxes.length;
    selectAllCheckbox.indeterminate = checkedCount > 0 && checkedCount < checkboxes.length;
    
    // Add event listener for Select All
    selectAllCheckbox.onclick = function() {
        const newState = this.checked;
        checkboxes.forEach(cb => cb.checked = newState);
    };
}

function applyColumnFilter(columnName) {
    const optionsContainer = document.getElementById(`filterOptions${capitalize(columnName)}`);
    const checkboxes = optionsContainer.querySelectorAll('input[type="checkbox"]');
    
    // Get selected values
    const selectedValues = Array.from(checkboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.value);
    
    console.log(`${columnName} filter applied:`, selectedValues);
    
    // Update filter state
    columnFilters[columnName] = selectedValues;
    
    // Update icon state
    updateFilterIcon(columnName);
    
    // Close dropdown
    closeFilterDropdown(columnName);
    
    // Apply all filters
    applyFilters();
}

function updateFilterIcon(columnName) {
    const icon = document.getElementById(`filterIcon${capitalize(columnName)}`);
    if (!icon) return;
    
    // Active if some (but not all) values are selected
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
    const searchInput = document.getElementById('searchInput');
    searchInput.value = '';
    searchInput.style.borderColor = '';
    searchInput.style.backgroundColor = '';
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
    // Validate search input before proceeding
    if (!validateBeforeSearch()) {
        return;
    }
    
    const searchInput = document.getElementById('searchInput');
    currentSearchQuery = searchInput.value.trim();
    
    // Sanitize if validation library available
    if (window.ValidationLib) {
        const result = window.ValidationLib.validateSearchQuery(currentSearchQuery);
        if (result.valid && result.sanitized) {
            currentSearchQuery = result.sanitized;
        }
    }
    
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
        
        if (data.status === 'error') {
            throw new Error(data.error?.message || data.message || 'Search failed');
        }
        
        // Store all results for filtering
        allResults = data.data || [];
        filteredResults = allResults;
        
        console.log(`Loaded ${allResults.length} APIs`);
        
        // Extract filter values from results
        extractFilterValues();
        
        // Display results
        displayAPIs(filteredResults);
        updateResultsCount(filteredResults.length);
        updatePagination(data.pagination || {});
        
    } catch (error) {
        console.error('Error loading APIs:', error);
        
        // Show error via toast if available
        if (window.showToast) {
            window.showToast(
                `Failed to load APIs: ${error.message}`,
                'error',
                { duration: 8000 }
            );
        }
        
        // Display error in table
        displayError(`Error loading APIs: ${error.message}`);
    }
}

function displayAPIs(apis) {
    const tbody = document.getElementById('apiTableBody');
    
    if (!tbody) {
        console.error('Table body element not found');
        return;
    }
    
    // Clear existing rows
    tbody.innerHTML = '';
    
    if (!apis || apis.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="no-results">No results found</td></tr>';
        
        // Show toast notification for empty results
        if (currentSearchQuery && window.showToast) {
            window.showToast(
                `No results found for: "${currentSearchQuery}"`,
                'info',
                { duration: 4000 }
            );
        }
        return;
    }
    
    // Populate table
    apis.forEach(api => {
        const tr = document.createElement('tr');
        
        const apiName = api['API Name'] || api.apiName || 'N/A';
        const platform = api.PlatformID || api.platform || 'N/A';
        const environment = api.Environment || api.environment || 'N/A';
        const version = api.Version || api.version || 'N/A';
        const deployDate = api.DeploymentDate || api.deploymentDate || 'N/A';
        const lastUpdated = api.LastUpdated || api.lastUpdated || 'N/A';
        const updatedBy = api.UpdatedBy || api.updatedBy || 'N/A';
        const status = api.Status || api.status || 'UNKNOWN';
        const properties = api.Properties || api.properties || {};
        
        // Use validation library's escapeHtml if available
        const escape = window.ValidationLib ? 
            window.ValidationLib.escapeHtml : 
            escapeHtml;
        
        tr.innerHTML = `
            <td class="api-name">${escape(apiName)}</td>
            <td>${escape(platform)}</td>
            <td>${escape(environment)}</td>
            <td class="api-version">${escape(version)}</td>
            <td>${formatDate(deployDate)}</td>
            <td>${formatDate(lastUpdated)}</td>
            <td>${escape(updatedBy)}</td>
            <td><span class="status-badge ${getStatusClass(status)}">${escape(status)}</span></td>
            <td>
                <button onclick='viewProperties(${JSON.stringify(properties)}, "${escape(apiName)}")' class="btn-view">
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
    const tbody = document.getElementById('apiTableBody');
    if (tbody) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="error-message">
                    <strong>Error:</strong> ${escapeHtml(message)}
                </td>
            </tr>
        `;
    }
}

// ==========================
// PROPERTIES MODAL
// ==========================

function createPropertiesModal() {
    const modal = document.getElementById('propertiesModal');
    if (!modal) return;
    
    // Close modal when clicking X
    const closeBtn = modal.querySelector('.modal-close');
    if (closeBtn) {
        closeBtn.onclick = function() {
            modal.style.display = 'none';
        };
    }
    
    // Close modal when clicking outside
    window.onclick = function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    };
}

function viewProperties(properties, apiName) {
    const modal = document.getElementById('propertiesModal');
    const modalBody = document.getElementById('modalBody');
    
    if (!modal || !modalBody) return;
    
    // Use validation library's escapeHtml if available
    const escape = window.ValidationLib ? 
        window.ValidationLib.escapeHtml : 
        escapeHtml;
    
    // Build properties table
    let html = `<h3>Properties for: ${escape(apiName)}</h3>`;
    
    if (!properties || Object.keys(properties).length === 0) {
        html += '<p>No properties defined.</p>';
    } else {
        html += '<table class="properties-table">';
        html += '<thead><tr><th>Key</th><th>Value</th></tr></thead>';
        html += '<tbody>';
        
        for (const [key, value] of Object.entries(properties)) {
            const displayValue = typeof value === 'object' ? 
                JSON.stringify(value, null, 2) : 
                String(value);
            
            html += `
                <tr>
                    <td><strong>${escape(key)}</strong></td>
                    <td><pre>${escape(displayValue)}</pre></td>
                </tr>
            `;
        }
        
        html += '</tbody></table>';
    }
    
    modalBody.innerHTML = html;
    modal.style.display = 'block';
}

// ==========================
// EXPORT FUNCTIONS
// ==========================

function exportResults(format) {
    const dataToExport = filteredResults.length > 0 ? filteredResults : allResults;
    
    if (dataToExport.length === 0) {
        if (window.showToast) {
            window.showToast('No data to export', 'warning', { duration: 3000 });
        } else {
            alert('No data to export');
        }
        return;
    }
    
    if (format === 'json') {
        exportAsJson(dataToExport);
    } else if (format === 'csv') {
        exportAsCsv(dataToExport);
    }
}

function exportAsJson(data) {
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `ccr-apis-${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    if (window.showToast) {
        window.showToast('Export completed successfully', 'success', { duration: 3000 });
    }
}

function exportAsCsv(data) {
    if (data.length === 0) return;
    
    // CSV headers
    const headers = ['API Name', 'Platform', 'Environment', 'Version', 'Status', 'Updated By', 'Last Updated'];
    let csv = headers.join(',') + '\n';
    
    // CSV rows
    data.forEach(api => {
        const row = [
            api['API Name'] || api.apiName || '',
            api.PlatformID || api.platform || '',
            api.Environment || api.environment || '',
            api.Version || api.version || '',
            api.Status || api.status || '',
            api.UpdatedBy || api.updatedBy || '',
            api.LastUpdated || api.lastUpdated || ''
        ].map(field => `"${String(field).replace(/"/g, '""')}"`);
        
        csv += row.join(',') + '\n';
    });
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `ccr-apis-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    if (window.showToast) {
        window.showToast('Export completed successfully', 'success', { duration: 3000 });
    }
}

// ==========================
// PAGINATION
// ==========================

function updatePagination(pagination) {
    const paginationDiv = document.getElementById('pagination');
    if (!paginationDiv) return;
    
    const page = pagination.page || currentPage;
    const total_pages = pagination.total_pages || 1;
    
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

// ==========================
// UTILITY FUNCTIONS
// ==========================

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

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

console.log('✅ Search.js loaded with validation support');