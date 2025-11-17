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

@bp.route('/audit')
def audit_page():
    """Serve the audit log viewer page."""
    return render_template('audit.html')
