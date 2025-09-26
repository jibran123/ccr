# Update all files
cd ~/rws/ccr/ccr

# Create main_routes.py
cat > app/routes/main_routes.py << 'ENDFILE'
"""Main routes for serving the web interface."""
from flask import Blueprint, render_template

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')

@bp.route('/search')
def search_page():
    """Serve the search page (same as index for now)."""
    return render_template('index.html')
ENDFILE

# Update app/__init__.py
cat > app/__init__.py << 'ENDFILE'
"""Flask application factory."""
import logging
from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.services.database import DatabaseService
from app.utils.exceptions import register_error_handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app(config_class=Config):
    """Create and configure the Flask application.
    
    Args:
        config_class: Configuration class to use
        
    Returns:
        Flask: Configured Flask application
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize CORS
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['*']))
    
    # Initialize database
    app.db_service = DatabaseService(app.config['MONGO_URI'])
    
    # Register blueprints - imports MUST be inside function to avoid circular imports
    from app.routes import api_routes, health_routes, main_routes
    app.register_blueprint(main_routes.bp)
    app.register_blueprint(api_routes.bp)
    app.register_blueprint(health_routes.bp)
    
    # Register error handlers
    register_error_handlers(app)
    
    logger.info("Application initialized successfully")
    
    return app
ENDFILE

# Update index.html
cat > app/templates/index.html << 'ENDFILE'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CCR API Manager</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
</head>
<body>
    <nav class="navbar">
        <div class="nav-container">
            <h1 class="nav-title">CCR API Manager</h1>
            <div class="nav-links">
                <a href="/" class="nav-link active">Search</a>
                <a href="/health" class="nav-link">Health</a>
            </div>
        </div>
    </nav>

    <main class="container">
        <section class="search-section">
            <h2>API Search</h2>
            
            <details class="search-help">
                <summary>▶ Search Help & Examples</summary>
                <div class="help-content">
                    <p><strong>Search Examples:</strong></p>
                    <ul>
                        <li>Search by name: <code>analytics</code></li>
                        <li>Search by platform: <code>IP4</code></li>
                        <li>Search by environment: <code>production</code></li>
                        <li>Use regex: <code>api-.*-blue</code> (check Regex Mode)</li>
                    </ul>
                </div>
            </details>

            <form id="searchForm" class="search-form">
                <div class="search-input-group">
                    <input 
                        type="text" 
                        id="searchInput" 
                        class="search-input" 
                        placeholder="Enter search query..."
                        autocomplete="off"
                    >
                    <button type="submit" class="btn btn-primary">Search</button>
                    <button type="button" class="btn btn-secondary clear-btn">Clear</button>
                </div>
                
                <div class="search-options">
                    <label class="checkbox-label">
                        <input type="checkbox" id="regexMode">
                        Regex Mode
                    </label>
                    <label class="checkbox-label">
                        <input type="checkbox" id="caseSensitive">
                        Case Sensitive
                    </label>
                    <select id="resultsPerPage" class="select-input">
                        <option value="10">10 per page</option>
                        <option value="25">25 per page</option>
                        <option value="50">50 per page</option>
                        <option value="100" selected>100 per page</option>
                    </select>
                </div>
            </form>

            <div id="errorContainer" class="error-message" style="display: none;"></div>
        </section>

        <section id="resultsContainer" class="results-section">
            <!-- Results will be inserted here by JavaScript -->
        </section>
    </main>

    <!-- JSON Viewer Modal -->
    <div id="jsonModal" class="modal" style="display: none;">
        <div class="modal-content">
            <div class="modal-header">
                <h3>API Details</h3>
                <span class="modal-close">&times;</span>
            </div>
            <div class="modal-body">
                <pre id="jsonContent"></pre>
            </div>
        </div>
    </div>

    <script src="{{ url_for('static', filename='js/search.js') }}"></script>
    <script src="{{ url_for('static', filename='js/json-viewer.js') }}"></script>
</body>
</html>
ENDFILE

# Update main.css
cat > app/static/css/main.css << 'ENDFILE'
/* Reset and Base Styles */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    background-color: #f5f5f5;
    color: #333;
    line-height: 1.6;
}

/* Navigation */
.navbar {
    background-color: #fff;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    padding: 1rem 0;
}

.nav-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.nav-title {
    color: #2563eb;
    font-size: 1.5rem;
}

.nav-links {
    display: flex;
    gap: 2rem;
}

.nav-link {
    color: #6b7280;
    text-decoration: none;
    font-weight: 500;
    transition: color 0.2s;
}

.nav-link:hover,
.nav-link.active {
    color: #2563eb;
}

/* Container */
.container {
    max-width: 1200px;
    margin: 2rem auto;
    padding: 0 2rem;
}

/* Search Section */
.search-section {
    background-color: #fff;
    border-radius: 8px;
    padding: 2rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    margin-bottom: 2rem;
}

.search-section h2 {
    color: #1f2937;
    margin-bottom: 1rem;
}

/* Search Help */
.search-help {
    background-color: #eff6ff;
    border: 1px solid #dbeafe;
    border-radius: 6px;
    padding: 0.75rem;
    margin-bottom: 1.5rem;
}

.search-help summary {
    cursor: pointer;
    font-weight: 500;
    color: #1e40af;
    user-select: none;
}

.help-content {
    margin-top: 1rem;
    padding-left: 1rem;
}

.help-content code {
    background-color: #f3f4f6;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: monospace;
}

/* Search Form */
.search-form {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.search-input-group {
    display: flex;
    gap: 0.5rem;
}

.search-input {
    flex: 1;
    padding: 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    font-size: 1rem;
}

.search-input:focus {
    outline: none;
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

/* Buttons */
.btn {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 6px;
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
}

.btn-primary {
    background-color: #2563eb;
    color: white;
}

.btn-primary:hover {
    background-color: #1d4ed8;
}

.btn-secondary {
    background-color: #6b7280;
    color: white;
}

.btn-secondary:hover {
    background-color: #4b5563;
}

/* Search Options */
.search-options {
    display: flex;
    gap: 2rem;
    align-items: center;
}

.checkbox-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
}

.select-input {
    padding: 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    background-color: white;
}

/* Error Message */
.error-message {
    background-color: #fee2e2;
    color: #dc2626;
    padding: 1rem;
    border-radius: 6px;
    margin-top: 1rem;
    border: 1px solid #fca5a5;
}

/* Results Section */
.results-section {
    background-color: #fff;
    border-radius: 8px;
    padding: 2rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.no-results {
    text-align: center;
    color: #6b7280;
    padding: 3rem 1rem;
}

.results-header {
    margin-bottom: 1.5rem;
}

.results-header h3 {
    color: #1f2937;
}

/* Results Table */
.results-table {
    width: 100%;
    border-collapse: collapse;
}

.results-table th {
    background-color: #f9fafb;
    padding: 0.75rem;
    text-align: left;
    font-weight: 600;
    color: #4b5563;
    border-bottom: 2px solid #e5e7eb;
}

.results-table td {
    padding: 0.75rem;
    border-bottom: 1px solid #e5e7eb;
}

.results-table tr:hover {
    background-color: #f9fafb;
}

.api-name {
    font-weight: 500;
    color: #1f2937;
}

.status-badge {
    display: inline-block;
    padding: 0.25rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.875rem;
    font-weight: 500;
}

.status-running {
    background-color: #d1fae5;
    color: #059669;
}

.status-stopped {
    background-color: #fee2e2;
    color: #dc2626;
}

.status-active {
    background-color: #d1fae5;
    color: #059669;
}

.view-btn {
    padding: 0.375rem 0.75rem;
    background-color: #2563eb;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.875rem;
}

.view-btn:hover {
    background-color: #1d4ed8;
}

/* Modal */
.modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    z-index: 1000;
}

.modal-content {
    position: relative;
    background-color: white;
    margin: 5% auto;
    padding: 0;
    width: 80%;
    max-width: 800px;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.modal-header {
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #e5e7eb;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.modal-close {
    font-size: 1.5rem;
    cursor: pointer;
    color: #6b7280;
}

.modal-close:hover {
    color: #1f2937;
}

.modal-body {
    padding: 1.5rem;
    max-height: 60vh;
    overflow-y: auto;
}

#jsonContent {
    background-color: #f9fafb;
    padding: 1rem;
    border-radius: 4px;
    overflow-x: auto;
    font-family: 'Courier New', monospace;
    font-size: 0.875rem;
}
ENDFILE

# Create json-viewer.js
cat > app/static/js/json-viewer.js << 'ENDFILE'
// JSON Viewer functionality
window.showJsonViewer = function(data) {
    const modal = document.getElementById('jsonModal');
    const jsonContent = document.getElementById('jsonContent');
    const closeBtn = document.querySelector('.modal-close');
    
    if (modal && jsonContent) {
        // Format JSON with syntax highlighting
        jsonContent.textContent = JSON.stringify(data, null, 2);
        modal.style.display = 'block';
        
        // Close modal when clicking X
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
};
ENDFILE

# Rebuild and restart
podman-compose down
podman-compose build --no-cache flask-app
podman-compose up -d

# Check logs
podman logs -f flask-app