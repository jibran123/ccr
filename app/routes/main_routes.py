"""Main routes for serving the web interface."""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
import logging

bp = Blueprint('main', __name__)
logger = logging.getLogger(__name__)

# Hardcoded credentials (for initial implementation)
# TODO: Replace with proper database/LDAP authentication in production
VALID_USERNAME = "omdadmin"
VALID_PASSWORD = "M0elijk!!"

def login_required(f):
    """
    Decorator to require login for protected routes.
    Redirects to login page if user is not authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session.get('logged_in'):
            logger.warning(f"Unauthorized access attempt to {request.path}")
            return redirect(url_for('main.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login (both GET and POST).

    GET: Display login form
    POST: Process login credentials
    """
    # If already logged in, redirect to dashboard
    if session.get('logged_in'):
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Validate credentials
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            # Set session variables
            session['logged_in'] = True
            session['username'] = username
            session.permanent = True  # Use permanent session (configurable lifetime)

            logger.info(f"User '{username}' logged in successfully from IP {request.remote_addr}")

            # Redirect to original destination or dashboard
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('main.dashboard'))
        else:
            logger.warning(f"Failed login attempt for username '{username}' from IP {request.remote_addr}")
            return render_template('login.html', error='Invalid username or password')

    # GET request: Show login form
    return render_template('login.html')


@bp.route('/logout')
def logout():
    """
    Handle user logout.
    Clears session and redirects to login page.
    """
    username = session.get('username', 'unknown')
    session.clear()
    logger.info(f"User '{username}' logged out")
    return redirect(url_for('main.login'))


@bp.route('/')
@login_required
def dashboard():
    """Serve the dashboard landing page."""
    return render_template('dashboard.html', active_tab='dashboard')


@bp.route('/apis')
@login_required
def apis_list():
    """Serve the APIs search and table page."""
    return render_template('index.html', active_tab='apis')


@bp.route('/search')
@login_required
def search_page():
    """Serve the search page (same as APIs page for now)."""
    return render_template('index.html', active_tab='apis')


@bp.route('/audit')
@login_required
def audit_page():
    """Serve the audit log viewer page."""
    return render_template('audit.html', active_tab='audit')
