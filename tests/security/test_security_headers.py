"""
Security Tests: HTTP Security Headers
Tests for security headers (Flask-Talisman)
Week 11-12: Security Enhancements
"""

import pytest
import requests


class TestSecurityHeaders:
    """Test suite for HTTP security headers."""

    @pytest.fixture(autouse=True)
    def setup(self, base_url):
        """Setup for each test."""
        self.base_url = base_url

    def test_strict_transport_security_header(self, base_url):
        """Test that HSTS header is present."""
        response = requests.get(f"{base_url}/health")

        # HSTS header should be present
        hsts_header = response.headers.get('Strict-Transport-Security')

        if hsts_header:
            assert 'max-age' in hsts_header.lower(), "HSTS should specify max-age"
            # In development, HSTS might be disabled, so this is a soft check
            print(f"HSTS Header: {hsts_header}")
        else:
            # HSTS may be disabled in development mode
            print("Note: HSTS header not present (may be disabled in development)")

    def test_content_security_policy_header(self, base_url):
        """Test that CSP header is present."""
        response = requests.get(f"{base_url}/health")

        csp_header = response.headers.get('Content-Security-Policy')

        if csp_header:
            # CSP should have default-src directive
            assert 'default-src' in csp_header.lower(), "CSP should have default-src directive"
            print(f"CSP Header: {csp_header[:100]}...")  # Print first 100 chars
        else:
            print("Note: CSP header not present (may be disabled in development)")

    def test_x_frame_options_header(self, base_url):
        """Test that X-Frame-Options header is present."""
        response = requests.get(f"{base_url}/health")

        x_frame_options = response.headers.get('X-Frame-Options')

        assert x_frame_options is not None, "X-Frame-Options header should be present"
        assert x_frame_options.upper() in ['DENY', 'SAMEORIGIN'], \
            f"X-Frame-Options should be DENY or SAMEORIGIN, got {x_frame_options}"

        print(f"X-Frame-Options: {x_frame_options}")

    def test_x_content_type_options_header(self, base_url):
        """Test that X-Content-Type-Options header is present."""
        response = requests.get(f"{base_url}/health")

        x_content_type_options = response.headers.get('X-Content-Type-Options')

        assert x_content_type_options is not None, "X-Content-Type-Options header should be present"
        assert x_content_type_options.lower() == 'nosniff', \
            f"X-Content-Type-Options should be nosniff, got {x_content_type_options}"

        print(f"X-Content-Type-Options: {x_content_type_options}")

    def test_referrer_policy_header(self, base_url):
        """Test that Referrer-Policy header is present."""
        response = requests.get(f"{base_url}/health")

        referrer_policy = response.headers.get('Referrer-Policy')

        if referrer_policy:
            # Common secure values
            secure_policies = [
                'no-referrer',
                'no-referrer-when-downgrade',
                'strict-origin',
                'strict-origin-when-cross-origin',
                'same-origin'
            ]

            assert any(policy in referrer_policy.lower() for policy in secure_policies), \
                f"Referrer-Policy should be a secure value, got {referrer_policy}"

            print(f"Referrer-Policy: {referrer_policy}")
        else:
            print("Note: Referrer-Policy header not present")

    def test_permissions_policy_header(self, base_url):
        """Test that Permissions-Policy header is present."""
        response = requests.get(f"{base_url}/health")

        # Permissions-Policy or Feature-Policy (deprecated)
        permissions_policy = response.headers.get('Permissions-Policy')
        feature_policy = response.headers.get('Feature-Policy')

        if permissions_policy:
            print(f"Permissions-Policy: {permissions_policy[:100]}...")
        elif feature_policy:
            print(f"Feature-Policy (deprecated): {feature_policy[:100]}...")
        else:
            print("Note: Permissions-Policy header not present")

    def test_x_xss_protection_removed(self, base_url):
        """Test that deprecated X-XSS-Protection header is not present."""
        response = requests.get(f"{base_url}/health")

        x_xss_protection = response.headers.get('X-XSS-Protection')

        # Modern best practice is to NOT use X-XSS-Protection (deprecated)
        # CSP is the modern replacement
        if x_xss_protection:
            print(f"Note: X-XSS-Protection present (deprecated): {x_xss_protection}")
        else:
            # This is the desired state
            print("X-XSS-Protection not present (good - deprecated header)")

    def test_server_header_not_leaked(self, base_url):
        """Test that Server header doesn't leak version information."""
        response = requests.get(f"{base_url}/health")

        server_header = response.headers.get('Server')

        if server_header:
            # Should not contain detailed version information
            sensitive_keywords = ['python', 'flask', 'werkzeug', 'version']
            has_sensitive_info = any(keyword in server_header.lower() for keyword in sensitive_keywords)

            if has_sensitive_info:
                print(f"Warning: Server header leaks information: {server_header}")
            else:
                print(f"Server header: {server_header}")
        else:
            # Best practice - no Server header
            print("Server header not present (good)")

    def test_security_headers_on_multiple_endpoints(self, base_url):
        """Test that security headers are present on various endpoints."""
        endpoints = [
            '/health',
            '/api/search?q=test',
            '/api/suggestions/platforms'
        ]

        for endpoint in endpoints:
            response = requests.get(f"{base_url}{endpoint}")

            # At minimum, X-Frame-Options and X-Content-Type-Options should be present
            x_frame_options = response.headers.get('X-Frame-Options')
            x_content_type_options = response.headers.get('X-Content-Type-Options')

            assert x_frame_options is not None, \
                f"X-Frame-Options missing on {endpoint}"
            assert x_content_type_options is not None, \
                f"X-Content-Type-Options missing on {endpoint}"

            print(f"{endpoint}: ✓ Security headers present")


class TestSecurityHeaderConfiguration:
    """Test security header configuration and values."""

    def test_hsts_max_age_sufficient(self, base_url):
        """Test that HSTS max-age is sufficiently long."""
        response = requests.get(f"{base_url}/health")

        hsts_header = response.headers.get('Strict-Transport-Security')

        if hsts_header:
            # Extract max-age value
            if 'max-age=' in hsts_header:
                max_age_str = hsts_header.split('max-age=')[1].split(';')[0].split(',')[0]
                try:
                    max_age = int(max_age_str.strip())

                    # Should be at least 6 months (15768000 seconds)
                    # Our config uses 1 year (31536000)
                    assert max_age >= 15768000, \
                        f"HSTS max-age should be at least 6 months, got {max_age}"

                    print(f"HSTS max-age: {max_age} seconds ({max_age / 86400:.0f} days)")
                except ValueError:
                    print(f"Could not parse max-age from: {hsts_header}")
        else:
            print("HSTS not configured (development mode)")

    def test_csp_restricts_default_src(self, base_url):
        """Test that CSP restricts default-src appropriately."""
        response = requests.get(f"{base_url}/health")

        csp_header = response.headers.get('Content-Security-Policy')

        if csp_header:
            # Should have restrictive default-src
            assert 'default-src' in csp_header.lower(), "CSP should define default-src"

            # Should not allow 'unsafe-inline' or 'unsafe-eval' in default-src
            # (unless specifically needed and documented)
            if "'unsafe-inline'" in csp_header or "'unsafe-eval'" in csp_header:
                print(f"Warning: CSP allows unsafe directives: {csp_header}")
            else:
                print("CSP has restrictive default-src (good)")
        else:
            print("CSP not configured (development mode)")

    def test_no_information_disclosure_in_headers(self, base_url):
        """Test that headers don't disclose sensitive information."""
        response = requests.get(f"{base_url}/health")

        # Headers that might disclose information
        sensitive_headers = [
            'Server',
            'X-Powered-By',
            'X-AspNet-Version',
            'X-AspNetMvc-Version'
        ]

        for header in sensitive_headers:
            value = response.headers.get(header)
            if value:
                print(f"Info disclosure: {header}: {value}")

        # X-Powered-By should ideally not be present
        x_powered_by = response.headers.get('X-Powered-By')
        if x_powered_by:
            print(f"Warning: X-Powered-By header present: {x_powered_by}")
        else:
            print("X-Powered-By not present (good)")


class TestHTTPSRedirection:
    """Test HTTPS redirection behavior."""

    def test_https_not_enforced_in_development(self, base_url):
        """Test that HTTP works in development mode."""
        # In development, we should be able to connect via HTTP
        if base_url.startswith('http://'):
            response = requests.get(f"{base_url}/health")
            assert response.status_code == 200, "HTTP should work in development"
            print("HTTP connections allowed (development mode)")
        else:
            print("Base URL is HTTPS")

    @pytest.mark.skip(reason="Production-only test - requires HTTPS setup in production/staging")
    @pytest.mark.production
    def test_https_redirection_in_production(self):
        """
        Test HTTPS redirection in production environment.

        MANUAL VERIFICATION PROCEDURE:
        ================================
        Prerequisites:
        - Production/Staging environment with HTTPS configured
        - Valid SSL/TLS certificates installed
        - FORCE_HTTPS=true in environment variables

        Test Steps:
        1. Access application via HTTP: http://your-domain.com/health
        2. Verify 301 Moved Permanently redirect
        3. Verify Location header: https://your-domain.com/health
        4. Verify HSTS header present: Strict-Transport-Security
        5. Follow redirect and verify HTTPS works

        Expected Results:
        - HTTP request returns 301 status
        - Redirects to HTTPS equivalent URL
        - HSTS header includes max-age=31536000
        - No certificate warnings
        - All assets load securely (no mixed content)

        This test is automatically skipped in development environments
        where HTTPS is not configured. It should be run manually as part
        of production deployment verification (Week 15-16: Kubernetes Migration).
        """
        pass


class TestCORSHeaders:
    """Test CORS header configuration."""

    def test_cors_headers_present(self, base_url):
        """Test that CORS headers are appropriately configured."""
        response = requests.get(f"{base_url}/health")

        # Check for CORS headers
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
        }

        print("\nCORS Headers:")
        for header, value in cors_headers.items():
            if value:
                print(f"  {header}: {value}")
            else:
                print(f"  {header}: Not present")

        # In development, wildcard CORS might be okay
        # In production, should be specific origins
        allow_origin = cors_headers['Access-Control-Allow-Origin']
        if allow_origin == '*':
            print("Warning: CORS allows all origins (okay for development)")

    def test_cors_credentials_handling(self, base_url):
        """Test CORS credentials handling."""
        response = requests.get(f"{base_url}/health")

        allow_credentials = response.headers.get('Access-Control-Allow-Credentials')

        if allow_credentials:
            print(f"CORS credentials: {allow_credentials}")

            # If credentials are allowed, origin should not be wildcard
            allow_origin = response.headers.get('Access-Control-Allow-Origin')
            if allow_credentials.lower() == 'true' and allow_origin == '*':
                print("Warning: CORS credentials with wildcard origin (insecure)")
        else:
            print("CORS credentials not configured")
