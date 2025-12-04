"""
Unit Tests: Custom Exceptions and Error Handlers
Tests for custom exceptions and Flask error handlers
Week 13-14: Testing & Quality Assurance - Phase 1
"""

import pytest
import json
from flask import Flask

from app.utils.exceptions import (
    ValidationError,
    DatabaseError,
    AuthenticationError,
    register_error_handlers
)


class TestCustomExceptions:
    """Test custom exception classes."""

    def test_validation_error_instantiation(self):
        """Test ValidationError can be instantiated."""
        error = ValidationError("Invalid input")
        assert isinstance(error, Exception)
        assert str(error) == "Invalid input"

    def test_validation_error_with_empty_message(self):
        """Test ValidationError with empty message."""
        error = ValidationError("")
        assert str(error) == ""

    def test_validation_error_with_complex_message(self):
        """Test ValidationError with complex message."""
        message = "Field 'email' must be valid: user@example.com expected"
        error = ValidationError(message)
        assert str(error) == message

    def test_database_error_instantiation(self):
        """Test DatabaseError can be instantiated."""
        error = DatabaseError("Connection failed")
        assert isinstance(error, Exception)
        assert str(error) == "Connection failed"

    def test_database_error_with_detailed_message(self):
        """Test DatabaseError with detailed message."""
        message = "MongoDB connection timeout: Could not connect to localhost:27017"
        error = DatabaseError(message)
        assert str(error) == message

    def test_authentication_error_instantiation(self):
        """Test AuthenticationError can be instantiated."""
        error = AuthenticationError("Invalid credentials")
        assert isinstance(error, Exception)
        assert str(error) == "Invalid credentials"

    def test_authentication_error_with_token_message(self):
        """Test AuthenticationError with token-related message."""
        message = "JWT token expired at 2024-01-01T10:00:00Z"
        error = AuthenticationError(message)
        assert str(error) == message

    def test_exceptions_can_be_raised(self):
        """Test that custom exceptions can be raised and caught."""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Test validation error")
        assert str(exc_info.value) == "Test validation error"

        with pytest.raises(DatabaseError) as exc_info:
            raise DatabaseError("Test database error")
        assert str(exc_info.value) == "Test database error"

        with pytest.raises(AuthenticationError) as exc_info:
            raise AuthenticationError("Test auth error")
        assert str(exc_info.value) == "Test auth error"

    def test_exception_inheritance(self):
        """Test that custom exceptions inherit from Exception."""
        assert issubclass(ValidationError, Exception)
        assert issubclass(DatabaseError, Exception)
        assert issubclass(AuthenticationError, Exception)


class TestErrorHandlerRegistration:
    """Test error handler registration."""

    def test_register_error_handlers_function_exists(self):
        """Test that register_error_handlers function exists."""
        assert callable(register_error_handlers)

    def test_register_error_handlers_with_flask_app(self):
        """Test registering error handlers with Flask app."""
        app = Flask(__name__)
        app.config['TESTING'] = True

        # Should not raise any errors
        register_error_handlers(app)

        # Verify error handlers are registered by checking they actually work
        # Simpler approach: just verify the function doesn't error and handlers exist
        assert len(app.error_handler_spec) > 0
        # The structure is complex, so just verify registration succeeded
        # The functional tests below verify they actually work


class TestValidationErrorHandler:
    """Test ValidationError handler."""

    @pytest.fixture
    def app(self):
        """Create Flask app with error handlers."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        register_error_handlers(app)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_validation_error_handler_returns_400(self, app, client):
        """Test ValidationError handler returns 400 status."""
        @app.route('/test-validation-error')
        def test_route():
            raise ValidationError("Invalid input data")

        response = client.get('/test-validation-error')
        assert response.status_code == 400

    def test_validation_error_handler_returns_json(self, app, client):
        """Test ValidationError handler returns JSON response."""
        @app.route('/test-validation-error')
        def test_route():
            raise ValidationError("Invalid input data")

        response = client.get('/test-validation-error')
        data = json.loads(response.data)

        assert data['status'] == 'error'
        assert data['message'] == 'Invalid input data'

    def test_validation_error_handler_with_long_message(self, app, client):
        """Test ValidationError handler with long error message."""
        long_message = "Validation failed: " + "error " * 50

        @app.route('/test-long-error')
        def test_route():
            raise ValidationError(long_message)

        response = client.get('/test-long-error')
        data = json.loads(response.data)

        assert response.status_code == 400
        assert data['message'] == long_message


class TestDatabaseErrorHandler:
    """Test DatabaseError handler."""

    @pytest.fixture
    def app(self):
        """Create Flask app with error handlers."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        register_error_handlers(app)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_database_error_handler_returns_500(self, app, client):
        """Test DatabaseError handler returns 500 status."""
        @app.route('/test-database-error')
        def test_route():
            raise DatabaseError("Connection timeout")

        response = client.get('/test-database-error')
        assert response.status_code == 500

    def test_database_error_handler_returns_json(self, app, client):
        """Test DatabaseError handler returns JSON response."""
        @app.route('/test-database-error')
        def test_route():
            raise DatabaseError("Connection timeout")

        response = client.get('/test-database-error')
        data = json.loads(response.data)

        assert data['status'] == 'error'
        # Should return generic message, not internal details
        assert data['message'] == 'Database operation failed'

    def test_database_error_hides_internal_details(self, app, client):
        """Test DatabaseError handler hides internal database details."""
        @app.route('/test-database-error')
        def test_route():
            raise DatabaseError("Connection failed: password=secret123")

        response = client.get('/test-database-error')
        data = json.loads(response.data)

        # Should not expose internal error details
        assert 'password' not in data['message']
        assert 'secret123' not in data['message']
        assert data['message'] == 'Database operation failed'


class TestAuthenticationErrorHandler:
    """Test AuthenticationError handler."""

    @pytest.fixture
    def app(self):
        """Create Flask app with error handlers."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        register_error_handlers(app)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_authentication_error_handler_returns_401(self, app, client):
        """Test AuthenticationError handler returns 401 status."""
        @app.route('/test-auth-error')
        def test_route():
            raise AuthenticationError("Invalid token")

        response = client.get('/test-auth-error')
        assert response.status_code == 401

    def test_authentication_error_handler_returns_json(self, app, client):
        """Test AuthenticationError handler returns JSON response."""
        @app.route('/test-auth-error')
        def test_route():
            raise AuthenticationError("Invalid token")

        response = client.get('/test-auth-error')
        data = json.loads(response.data)

        assert data['status'] == 'error'
        # Should return generic message
        assert data['message'] == 'Authentication failed'

    def test_authentication_error_hides_details(self, app, client):
        """Test AuthenticationError handler hides auth details."""
        @app.route('/test-auth-error')
        def test_route():
            raise AuthenticationError("Token validation failed: secret_key mismatch")

        response = client.get('/test-auth-error')
        data = json.loads(response.data)

        # Should not expose internal auth details
        assert 'secret_key' not in data['message']
        assert data['message'] == 'Authentication failed'


class TestHTTPErrorHandlers:
    """Test HTTP error handlers (404, 500)."""

    @pytest.fixture
    def app(self):
        """Create Flask app with error handlers."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        register_error_handlers(app)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_404_error_handler(self, client):
        """Test 404 error handler for non-existent route."""
        response = client.get('/non-existent-route')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert data['message'] == 'Resource not found'

    def test_500_error_handler(self, app, client):
        """Test 500 error handler for internal errors."""
        # Need to set PROPAGATE_EXCEPTIONS to False for Flask to use error handlers
        app.config['PROPAGATE_EXCEPTIONS'] = False

        @app.route('/test-500-error')
        def test_route():
            # Simulate internal server error
            1 / 0  # ZeroDivisionError will be caught as 500

        response = client.get('/test-500-error')
        assert response.status_code == 500

        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert data['message'] == 'Internal server error'


class TestErrorHandlerEdgeCases:
    """Test error handler edge cases."""

    @pytest.fixture
    def app(self):
        """Create Flask app with error handlers."""
        app = Flask(__name__)
        app.config['TESTING'] = True
        register_error_handlers(app)
        return app

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()

    def test_error_with_none_message(self, app, client):
        """Test error handler with None message."""
        @app.route('/test-none-error')
        def test_route():
            raise ValidationError(None)

        response = client.get('/test-none-error')
        data = json.loads(response.data)

        assert response.status_code == 400
        assert 'message' in data

    def test_error_with_unicode_message(self, app, client):
        """Test error handler with Unicode characters."""
        @app.route('/test-unicode-error')
        def test_route():
            raise ValidationError("エラーが発生しました")

        response = client.get('/test-unicode-error')
        data = json.loads(response.data)

        assert response.status_code == 400
        assert data['message'] == "エラーが発生しました"

    def test_multiple_errors_in_sequence(self, app, client):
        """Test handling multiple errors in sequence."""
        @app.route('/test-error-1')
        def test_route_1():
            raise ValidationError("Error 1")

        @app.route('/test-error-2')
        def test_route_2():
            raise DatabaseError("Error 2")

        @app.route('/test-error-3')
        def test_route_3():
            raise AuthenticationError("Error 3")

        response1 = client.get('/test-error-1')
        response2 = client.get('/test-error-2')
        response3 = client.get('/test-error-3')

        assert response1.status_code == 400
        assert response2.status_code == 500
        assert response3.status_code == 401

    def test_error_response_content_type(self, app, client):
        """Test error response has correct content type."""
        @app.route('/test-content-type')
        def test_route():
            raise ValidationError("Test error")

        response = client.get('/test-content-type')
        assert 'application/json' in response.content_type
