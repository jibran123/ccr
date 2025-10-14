// Complete search.js - Simplified without checkboxes
let currentPage = 1;
let currentPerPage = 100;
let currentSearchQuery = '';
let allResults = [];

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing API Search...');
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
    
    // Clear button
    const clearBtn = document.getElementById('clearBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', function() {
            document.getElementById('searchInput').value = '';
            currentSearchQuery = '';
            currentPage = 1;
            loadAPIs();
        });
    }
    
    // Results per page
    const resultsPerPage = document.getElementById('resultsPerPage');
    if (resultsPerPage) {
        resultsPerPage.addEventListener('change', function() {
            currentPerPage = parseInt(this.value);
            currentPage = 1;
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
}

function createPropertiesModal() {
    // Check if modal already exists
    if (document.getElementById('propertiesModal')) {
        return;
    }
    
    // Create modal HTML
    const modalHtml = `
        <div id="propertiesModal" class="modal">
            <div class="modal-content">
                <div class="modal-header">
                    <h2>API Properties</h2>
                    <span class="modal-close">&times;</span>
                </div>
                <div class="modal-body" id="modalBody">
                    <!-- Properties will be inserted here -->
                </div>
                <div class="modal-footer">
                    <button class="btn-copy" onclick="copyProperties()">Copy to Clipboard</button>
                    <button class="btn-close-modal">Close</button>
                </div>
            </div>
        </div>
    `;
    
    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHtml);
    
    // Setup modal event listeners
    const modal = document.getElementById('propertiesModal');
    const closeBtn = modal.querySelector('.modal-close');
    const closeModalBtn = modal.querySelector('.btn-close-modal');
    
    closeBtn.onclick = function() {
        modal.style.display = 'none';
    };
    
    closeModalBtn.onclick = function() {
        modal.style.display = 'none';
    };
    
    window.onclick = function(event) {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    };
}

function performSearch() {
    const searchInput = document.getElementById('searchInput');
    currentSearchQuery = searchInput ? searchInput.value : '';
    currentPage = 1;
    loadAPIs();
}

async function loadAPIs() {
    try {
        console.log('Loading APIs...');
        
        // Show loading state
        const tbody = document.getElementById('apiTableBody');
        if (tbody) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align: center;"><div class="loading"><div class="spinner"></div><p>Loading APIs...</p></div></td></tr>';
        }
        
        // Build query parameters
        const params = new URLSearchParams({
            q: currentSearchQuery,
            page: currentPage,
            page_size: currentPerPage
        });
        
        const url = `/api/search?${params}`;
        console.log('Fetching from:', url);
        
        const response = await fetch(url);
        
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
        
        // Display results
        displayAPIs(allResults);
        updateResultsCount(allResults.length);
        
        // Update pagination if metadata exists
        if (data.metadata) {
            updatePagination(data.metadata);
        }
        
    } catch (error) {
        console.error('Error loading APIs:', error);
        displayError('Failed to load APIs: ' + error.message);
    }
}

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
    
    // Display each row
    apis.forEach((api) => {
        const tr = document.createElement('tr');
        
        // Handle field names from backend
        const apiName = api['API Name'] || api.apiName || 'N/A';
        const platform = api.PlatformID || api.platform || 'N/A';
        const environment = api.Environment || api.environment || 'N/A';
        const deploymentDate = api.DeploymentDate || api.deploymentDate || 'N/A';
        const lastUpdated = api.LastUpdated || api.lastUpdated || 'N/A';
        const updatedBy = api.UpdatedBy || api.updatedBy || 'N/A';
        const status = api.Status || api.status || 'UNKNOWN';
        const version = api.Version || api.version || 'N/A';
        const properties = api.Properties || api.properties || {};
        
        const statusClass = getStatusClass(status);
        
        tr.innerHTML = `
            <td class="api-name">${escapeHtml(apiName)}</td>
            <td class="api-version">${escapeHtml(version)}</td>
            <td>${escapeHtml(platform)}</td>
            <td>${escapeHtml(environment)}</td>
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

function viewProperties(properties, apiName) {
    const modal = document.getElementById('propertiesModal');
    const modalBody = document.getElementById('modalBody');
    
    if (!modal || !modalBody) {
        alert('Modal not available');
        return;
    }
    
    // Store properties for copy function
    window.currentProperties = properties;
    
    // Update modal header
    const modalHeader = modal.querySelector('.modal-header h2');
    if (modalHeader && apiName) {
        modalHeader.textContent = `Properties - ${apiName}`;
    }
    
    // Build properties HTML
    if (!properties || Object.keys(properties).length === 0) {
        modalBody.innerHTML = '<div class="no-properties">No properties available</div>';
    } else {
        let propertiesHtml = '<div class="properties-container">';
        
        // Sort properties alphabetically
        const sortedKeys = Object.keys(properties).sort();
        
        for (const key of sortedKeys) {
            const value = properties[key];
            let valueClass = 'property-value';
            let displayValue = String(value);
            
            // Special handling for different value types
            if (value === 'true') {
                valueClass += ' property-value-boolean-true';
            } else if (value === 'false') {
                valueClass += ' property-value-boolean-false';
            }
            
            // Format the key for better display
            const formattedKey = key.replace(/\./g, '.<wbr>').replace(/_/g, '_<wbr>');
            
            propertiesHtml += `
                <div class="property-item">
                    <div class="property-key">${formattedKey}:</div>
                    <div class="${valueClass}">${escapeHtml(displayValue)}</div>
                </div>
            `;
        }
        
        propertiesHtml += '</div>';
        modalBody.innerHTML = propertiesHtml;
    }
    
    // Show modal
    modal.style.display = 'flex';
}

function copyProperties() {
    if (!window.currentProperties) {
        return;
    }
    
    // Format properties as text
    let text = '';
    for (const [key, value] of Object.entries(window.currentProperties)) {
        text += `${key}: ${value}\n`;
    }
    
    // Copy to clipboard
    navigator.clipboard.writeText(text).then(function() {
        const copyBtn = document.querySelector('.btn-copy');
        const originalText = copyBtn.textContent;
        copyBtn.textContent = 'Copied!';
        copyBtn.style.background = '#28a745';
        
        setTimeout(() => {
            copyBtn.textContent = originalText;
            copyBtn.style.background = '';
        }, 2000);
    }).catch(function(err) {
        alert('Failed to copy to clipboard');
    });
}

function updateResultsCount(count) {
    const countElement = document.getElementById('resultCount');
    if (countElement) {
        countElement.innerHTML = `<i class="fas fa-chart-bar"></i> Search Results (${count} found)`;
    }
}

function updatePagination(metadata) {
    const paginationElement = document.getElementById('pagination');
    if (!paginationElement) return;
    
    const totalPages = metadata.total_pages || 1;
    
    if (totalPages <= 1) {
        paginationElement.innerHTML = '';
        return;
    }
    
    let html = '';
    
    // Previous button
    if (currentPage > 1) {
        html += `<button onclick="changePage(${currentPage - 1})" class="page-btn">Previous</button>`;
    }
    
    // Page numbers
    for (let i = 1; i <= Math.min(totalPages, 10); i++) {
        const activeClass = i === currentPage ? 'active' : '';
        html += `<button onclick="changePage(${i})" class="page-btn ${activeClass}">${i}</button>`;
    }
    
    // Next button
    if (currentPage < totalPages) {
        html += `<button onclick="changePage(${currentPage + 1})" class="page-btn">Next</button>`;
    }
    
    paginationElement.innerHTML = html;
}

function changePage(page) {
    currentPage = page;
    loadAPIs();
}

function displayError(message) {
    const tbody = document.getElementById('apiTableBody');
    if (tbody) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: red;"><i class="fas fa-exclamation-triangle"></i> ${escapeHtml(message)}</td></tr>`;
    }
    updateResultsCount(0);
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

function exportResults(format) {
    if (!allResults || allResults.length === 0) {
        alert('No data to export');
        return;
    }
    
    if (format === 'json') {
        const blob = new Blob([JSON.stringify(allResults, null, 2)], 
                            { type: 'application/json' });
        downloadBlob(blob, 'api_export.json');
    } else if (format === 'csv') {
        const csv = convertToCSV(allResults);
        const blob = new Blob([csv], { type: 'text/csv' });
        downloadBlob(blob, 'api_export.csv');
    }
}

function convertToCSV(data) {
    if (!data || data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    const rows = data.map(obj => headers.map(h => obj[h] || ''));
    
    return [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
    ].join('\n');
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

// Make functions globally available
window.changePage = changePage;
window.viewProperties = viewProperties;
window.copyProperties = copyProperties;

console.log('Search.js loaded successfully');