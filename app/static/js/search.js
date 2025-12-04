// Complete search.js with Excel-style Column Filters + Frontend Validation + Sortable Columns
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

// Sort state
let currentSort = {
    column: null,
    direction: null  // null, 'asc', 'desc'
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing Common Configuration Repository (CCR) with validation...');
    initializeApp();
});

function initializeApp() {
    // Setup offline/online detection
    if (window.setupOfflineDetection) {
        window.setupOfflineDetection();
    }

    // Check for search parameter in URL
    const urlParams = new URLSearchParams(window.location.search);
    const searchParam = urlParams.get('search');
    if (searchParam) {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.value = decodeURIComponent(searchParam);
            currentSearchQuery = searchInput.value.trim();
        }
    }

    setupEventListeners();
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
    // SEARCH HELP MODAL
    // ==========================
    setupSearchHelpModal();

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

    // ==========================
    // SORTABLE COLUMN CLICKS
    // ==========================

    const sortableHeaders = document.querySelectorAll('.sortable');
    sortableHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const column = this.dataset.column;
            sortByColumn(column);
        });
    });

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
    const tableContainer = document.querySelector('.table-container');

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

        // Expand table container when dropdown opens (Excel behavior)
        if (tableContainer) {
            tableContainer.style.maxHeight = 'none';
            tableContainer.style.overflow = 'visible';
        }
    } else {
        dropdown.style.display = 'none';

        // Restore table container size when dropdown closes
        if (tableContainer) {
            tableContainer.style.maxHeight = '600px';
            tableContainer.style.overflow = 'auto';
        }
    }
}

function closeFilterDropdown(columnName) {
    const dropdown = document.getElementById(`filterDropdown${capitalize(columnName)}`);
    const tableContainer = document.querySelector('.table-container');

    if (dropdown) {
        dropdown.style.display = 'none';
    }

    // Restore table container size
    if (tableContainer) {
        tableContainer.style.maxHeight = '600px';
        tableContainer.style.overflow = 'auto';
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

    // Clear sort state
    currentSort = {
        column: null,
        direction: null
    };
    updateSortIcons();

    // Reload data
    currentPage = 1;
    loadAPIs();
}

// ==========================
// SORTABLE COLUMN FUNCTIONS
// ==========================

function sortByColumn(column) {
    console.log('Sorting by:', column);

    // Determine new sort direction: null → asc → desc → null
    if (currentSort.column === column) {
        if (currentSort.direction === null) {
            currentSort.direction = 'asc';
        } else if (currentSort.direction === 'asc') {
            currentSort.direction = 'desc';
        } else {
            currentSort.direction = null;
            currentSort.column = null;
        }
    } else {
        currentSort.column = column;
        currentSort.direction = 'asc';
    }

    // Update header icons
    updateSortIcons();

    // Sort the filtered results
    if (currentSort.direction === null) {
        // Reset to original order
        applyFilters();
    } else {
        sortFilteredResults();
        displayAPIs(filteredResults);
    }
}

function sortFilteredResults() {
    if (!currentSort.column || !currentSort.direction) {
        return;
    }

    const column = currentSort.column;
    const direction = currentSort.direction;

    filteredResults.sort((a, b) => {
        let aVal, bVal;

        // Map column names to data keys
        switch(column) {
            case 'version':
                aVal = a.Version || a.version || '';
                bVal = b.Version || b.version || '';
                break;
            case 'deploymentDate':
                aVal = a.DeploymentDate || a.deploymentDate || '';
                bVal = b.DeploymentDate || b.deploymentDate || '';
                // Convert to Date for proper comparison
                aVal = aVal ? new Date(aVal).getTime() : 0;
                bVal = bVal ? new Date(bVal).getTime() : 0;
                break;
            case 'lastUpdated':
                aVal = a.LastUpdated || a.lastUpdated || '';
                bVal = b.LastUpdated || b.lastUpdated || '';
                // Convert to Date for proper comparison
                aVal = aVal ? new Date(aVal).getTime() : 0;
                bVal = bVal ? new Date(bVal).getTime() : 0;
                break;
            case 'updatedBy':
                aVal = a.UpdatedBy || a.updatedBy || '';
                bVal = b.UpdatedBy || b.updatedBy || '';
                break;
            case 'status':
                aVal = a.Status || a.status || '';
                bVal = b.Status || b.status || '';
                break;
            default:
                return 0;
        }

        // Handle string comparison (case insensitive)
        if (typeof aVal === 'string' && typeof bVal === 'string') {
            aVal = aVal.toLowerCase();
            bVal = bVal.toLowerCase();
        }

        // Compare
        let comparison = 0;
        if (aVal < bVal) comparison = -1;
        if (aVal > bVal) comparison = 1;

        // Apply direction
        return direction === 'asc' ? comparison : -comparison;
    });
}

function updateSortIcons() {
    // Remove all sort classes
    document.querySelectorAll('.sortable').forEach(header => {
        header.classList.remove('sort-asc', 'sort-desc');
    });

    // Add class to current sorted column
    if (currentSort.column && currentSort.direction) {
        const header = document.querySelector(`.sortable[data-column="${currentSort.column}"]`);
        if (header) {
            header.classList.add(`sort-${currentSort.direction}`);
        }
    }
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
            // Parse error response
            const errorData = await response.json().catch(() => ({}));
            const error = new Error(errorData.error?.message || `HTTP ${response.status}`);
            error.status = response.status;
            error.error = errorData.error;
            throw error;
        }

        const data = await response.json();

        if (data.status === 'error') {
            const error = new Error(data.error?.message || data.message || 'Search failed');
            error.error = data.error;
            throw error;
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

        // Use enhanced error handling with retry
        if (window.showApiError) {
            window.showApiError(error, 'Search', () => loadAPIs());
        } else if (window.showToast) {
            // Fallback if showApiError not available
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
        
        // Prepare row data for drawer
        const rowData = {
            apiName: apiName,
            platform: platform,
            environment: environment,
            version: version,
            status: status,
            lastUpdated: lastUpdated,
            deploymentDate: deployDate,
            updatedBy: updatedBy,
            properties: properties
        };

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
                <button class="btn-view" title="View details">
                    <i class="fas fa-eye"></i> View
                </button>
            </td>
        `;

        // Add click handler to View button
        const viewBtn = tr.querySelector('.btn-view');
        if (viewBtn) {
            viewBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (window.openApiDetails) {
                    window.openApiDetails(rowData);
                }
            });
        }

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
// PROPERTIES MODAL - REMOVED (Replaced by API Details Drawer)
// ==========================
// The old properties modal has been replaced by a comprehensive API details drawer
// See api-details.js for the new implementation

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

// ==========================
// SEARCH HELP MODAL
// ==========================

function setupSearchHelpModal() {
    const modal = document.getElementById('searchHelpModal');
    const helpBtn = document.getElementById('searchHelpBtn');

    if (!modal || !helpBtn) {
        console.warn('Search help modal or button not found');
        return;
    }

    const closeBtn = modal.querySelector('.modal-close');

    // Open modal
    helpBtn.addEventListener('click', function(e) {
        e.preventDefault();
        modal.style.display = 'block';
    });

    // Close modal
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            modal.style.display = 'none';
        });
    }

    // Click outside to close
    window.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });

    // ESC key to close
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.style.display === 'block') {
            modal.style.display = 'none';
        }
    });

    // Tab switching
    const tabBtns = modal.querySelectorAll('.tab-btn');
    const tabContents = modal.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const tabName = this.dataset.tab;

            // Remove active class from all
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            // Add active class to clicked tab
            this.classList.add('active');
            document.getElementById(`tab-${tabName}`).classList.add('active');
        });
    });

    // Example box click to populate search
    const exampleBoxes = modal.querySelectorAll('.example-box');
    exampleBoxes.forEach(box => {
        box.addEventListener('click', function() {
            const query = this.dataset.query;
            const searchInput = document.getElementById('searchInput');
            searchInput.value = query;
            searchInput.focus();
            modal.style.display = 'none';

            // Show toast
            if (window.showToast) {
                window.showToast('Search query populated! Click SEARCH to execute.', 'info', { duration: 3000 });
            }
        });
    });

    console.log('✅ Search help modal initialized');
}

console.log('✅ Search.js loaded with validation support + sortable columns');