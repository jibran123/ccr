"""
Security Tests: Token Refresh Mechanism
Tests for JWT token refresh, revocation, and blacklist functionality
Week 11-12: Security Enhancements
"""

import pytest
import requests
import time
import jwt


class TestTokenGeneration:
    """Test token generation functionality."""

    def test_generate_token_success(self, base_url, admin_headers):
        """Test successful token generation."""
        response = requests.post(
            f"{base_url}/api/auth/token",
            headers=admin_headers,
            json={"username": "test_user", "role": "user"}
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

        data = response.json()
        assert data['status'] == 'success'
        assert 'access_token' in data['data']
        assert 'refresh_token' in data['data']
        assert 'expires_at' in data['data']
        assert 'refresh_expires_at' in data['data']

        print(f"✓ Token generated successfully for test_user")

    def test_generate_token_without_admin_key(self, base_url):
        """Test that token generation requires admin key."""
        response = requests.post(
            f"{base_url}/api/auth/token",
            json={"username": "test_user", "role": "user"}
        )

        assert response.status_code == 401, "Should require admin key"

        data = response.json()
        assert data['status'] == 'error'

        print("✓ Token generation properly requires admin key")

    def test_generate_token_with_invalid_admin_key(self, base_url):
        """Test that invalid admin key is rejected."""
        response = requests.post(
            f"{base_url}/api/auth/token",
            headers={
                "X-Admin-Key": "invalid-key",
                "Content-Type": "application/json"
            },
            json={"username": "test_user", "role": "user"}
        )

        assert response.status_code == 401, "Invalid admin key should be rejected"

        print("✓ Invalid admin key properly rejected")

    def test_generate_admin_token(self, base_url, admin_headers):
        """Test generation of admin role token."""
        response = requests.post(
            f"{base_url}/api/auth/token",
            headers=admin_headers,
            json={"username": "admin_user", "role": "admin"}
        )

        assert response.status_code == 200

        data = response.json()
        assert data['data']['role'] == 'admin'

        print("✓ Admin token generated successfully")


class TestTokenRefresh:
    """Test token refresh functionality."""

    def test_refresh_token_success(self, base_url, admin_headers):
        """Test successful token refresh."""
        # Generate initial token
        gen_response = requests.post(
            f"{base_url}/api/auth/token",
            headers=admin_headers,
            json={"username": "refresh_test_user", "role": "user"}
        )

        assert gen_response.status_code == 200

        tokens = gen_response.json()['data']
        refresh_token = tokens['refresh_token']

        # Wait a moment
        time.sleep(1)

        # Refresh the token
        refresh_response = requests.post(
            f"{base_url}/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert refresh_response.status_code == 200, \
            f"Token refresh should succeed, got {refresh_response.status_code}"

        new_tokens = refresh_response.json()['data']
        assert 'access_token' in new_tokens
        assert 'refresh_token' in new_tokens

        # New tokens should be different from old ones
        assert new_tokens['access_token'] != tokens['access_token'], \
            "New access token should be different"
        assert new_tokens['refresh_token'] != refresh_token, \
            "Refresh token should be rotated"

        print("✓ Token refresh successful with rotation")

    def test_refresh_with_invalid_token(self, base_url):
        """Test that invalid refresh token is rejected."""
        response = requests.post(
            f"{base_url}/api/auth/refresh",
            json={"refresh_token": "invalid.refresh.token"}
        )

        assert response.status_code == 401, "Invalid refresh token should be rejected"

        print("✓ Invalid refresh token properly rejected")

    def test_refresh_token_reuse_prevented(self, base_url, admin_headers):
        """Test that refresh token cannot be reused (rotation)."""
        # Generate initial token
        gen_response = requests.post(
            f"{base_url}/api/auth/token",
            headers=admin_headers,
            json={"username": "reuse_test_user", "role": "user"}
        )

        refresh_token = gen_response.json()['data']['refresh_token']

        # Use refresh token once
        first_refresh = requests.post(
            f"{base_url}/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert first_refresh.status_code == 200, "First refresh should succeed"

        time.sleep(1)

        # Try to reuse the same refresh token
        second_refresh = requests.post(
            f"{base_url}/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        # Old refresh token should be invalid after being used
        assert second_refresh.status_code == 401, \
            "Reused refresh token should be rejected (rotation)"

        print("✓ Refresh token rotation prevents reuse")


class TestTokenRevocation:
    """Test token revocation functionality."""

    def test_revoke_refresh_token(self, base_url, admin_headers):
        """Test revoking a refresh token."""
        # Generate token
        gen_response = requests.post(
            f"{base_url}/api/auth/token",
            headers=admin_headers,
            json={"username": "revoke_test_user", "role": "user"}
        )

        tokens = gen_response.json()['data']
        access_token = tokens['access_token']
        refresh_token = tokens['refresh_token']

        # Revoke the refresh token
        revoke_response = requests.post(
            f"{base_url}/api/auth/revoke",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"refresh_token": refresh_token}
        )

        assert revoke_response.status_code == 200, \
            f"Revocation should succeed, got {revoke_response.status_code}"

        print("✓ Refresh token revoked successfully")

        # Try to use revoked refresh token
        time.sleep(1)
        refresh_response = requests.post(
            f"{base_url}/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert refresh_response.status_code == 401, \
            "Revoked refresh token should not work"

        print("✓ Revoked refresh token cannot be used")

    def test_revoke_without_authentication(self, base_url):
        """Test that revocation requires authentication."""
        response = requests.post(
            f"{base_url}/api/auth/revoke",
            json={"refresh_token": "some.refresh.token"}
        )

        assert response.status_code == 401, \
            "Revocation should require authentication"

        print("✓ Revocation requires authentication")


class TestTokenLogout:
    """Test logout functionality."""

    def test_logout_success(self, base_url, admin_headers):
        """Test successful logout."""
        # Generate token
        gen_response = requests.post(
            f"{base_url}/api/auth/token",
            headers=admin_headers,
            json={"username": "logout_test_user", "role": "user"}
        )

        tokens = gen_response.json()['data']
        access_token = tokens['access_token']
        refresh_token = tokens['refresh_token']

        # Logout
        logout_response = requests.post(
            f"{base_url}/api/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"refresh_token": refresh_token}
        )

        assert logout_response.status_code == 200, \
            f"Logout should succeed, got {logout_response.status_code}"

        print("✓ Logout successful")

        # Try to use access token after logout
        time.sleep(1)
        protected_response = requests.get(
            f"{base_url}/api/admin/scheduler/jobs",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        # Access token should be blacklisted
        assert protected_response.status_code == 401, \
            "Blacklisted access token should not work"

        print("✓ Access token blacklisted after logout")

        # Try to use refresh token after logout
        refresh_response = requests.post(
            f"{base_url}/api/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert refresh_response.status_code == 401, \
            "Refresh token should not work after logout"

        print("✓ Refresh token revoked after logout")


class TestTokenBlacklist:
    """Test token blacklist functionality."""

    def test_blacklisted_token_rejected(self, base_url, admin_headers):
        """Test that blacklisted tokens are rejected."""
        # Generate token
        gen_response = requests.post(
            f"{base_url}/api/auth/token",
            headers=admin_headers,
            json={"username": "blacklist_test_user", "role": "user"}
        )

        tokens = gen_response.json()['data']
        access_token = tokens['access_token']

        # Use token successfully first
        protected_response = requests.get(
            f"{base_url}/api/admin/scheduler/jobs",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert protected_response.status_code == 200, \
            "Token should work before logout"

        # Logout (blacklists access token)
        logout_response = requests.post(
            f"{base_url}/api/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"refresh_token": tokens['refresh_token']}
        )

        assert logout_response.status_code == 200

        # Try to use blacklisted token
        time.sleep(1)
        blacklisted_response = requests.get(
            f"{base_url}/api/admin/scheduler/jobs",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert blacklisted_response.status_code == 401, \
            "Blacklisted token should be rejected"

        data = blacklisted_response.json()
        assert 'revoked' in data['message'].lower(), \
            "Error message should indicate token was revoked"

        print("✓ Blacklisted token properly rejected")


class TestTokenExpiration:
    """Test token expiration behavior."""

    def test_token_contains_expiration(self, base_url, admin_headers):
        """Test that generated tokens contain expiration claims."""
        gen_response = requests.post(
            f"{base_url}/api/auth/token",
            headers=admin_headers,
            json={"username": "expiry_test_user", "role": "user"}
        )

        tokens = gen_response.json()['data']
        access_token = tokens['access_token']

        # Decode token without verification to inspect claims
        payload = jwt.decode(access_token, options={"verify_signature": False})

        assert 'exp' in payload, "Token should have expiration claim"
        assert 'iat' in payload, "Token should have issued-at claim"
        assert 'jti' in payload, "Access token should have JTI (JWT ID)"

        print(f"✓ Token has expiration: {payload.get('exp')}")
        print(f"  Issued at: {payload.get('iat')}")
        print(f"  JTI: {payload.get('jti', 'N/A')[:10]}...")

    def test_refresh_token_longer_expiry(self, base_url, admin_headers):
        """Test that refresh tokens have longer expiry than access tokens."""
        gen_response = requests.post(
            f"{base_url}/api/auth/token",
            headers=admin_headers,
            json={"username": "expiry_comparison_user", "role": "user"}
        )

        data = gen_response.json()['data']

        # Parse expiration times
        from datetime import datetime
        access_expires = datetime.fromisoformat(data['expires_at'].replace('Z', '+00:00'))
        refresh_expires = datetime.fromisoformat(data['refresh_expires_at'].replace('Z', '+00:00'))

        # Refresh token should expire later than access token
        assert refresh_expires > access_expires, \
            "Refresh token should have longer expiry than access token"

        time_diff = refresh_expires - access_expires
        print(f"✓ Refresh token expires {time_diff.days} days after access token")


class TestTokenPermissions:
    """Test that tokens properly enforce permissions."""

    def test_user_token_cannot_access_admin_endpoint(self, base_url, admin_headers):
        """Test that user role token cannot access admin endpoints."""
        # Generate user token
        gen_response = requests.post(
            f"{base_url}/api/auth/token",
            headers=admin_headers,
            json={"username": "regular_user", "role": "user"}
        )

        access_token = gen_response.json()['data']['access_token']

        # Try to access admin endpoint
        admin_response = requests.post(
            f"{base_url}/api/admin/audit/cleanup",
            headers={"Authorization": f"Bearer {access_token}"},
            json={"days": 180}
        )

        # Should be forbidden (403) or unauthorized (401) depending on implementation
        assert admin_response.status_code in [401, 403], \
            f"User token should not access admin endpoint, got {admin_response.status_code}"

        print("✓ User token cannot access admin endpoints")

    def test_admin_token_can_access_admin_endpoint(self, base_url, admin_headers):
        """Test that admin token can access admin endpoints."""
        # Generate admin token
        gen_response = requests.post(
            f"{base_url}/api/auth/token",
            headers=admin_headers,
            json={"username": "admin_user", "role": "admin"}
        )

        access_token = gen_response.json()['data']['access_token']

        # Access admin endpoint
        admin_response = requests.get(
            f"{base_url}/api/admin/scheduler/jobs",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert admin_response.status_code == 200, \
            "Admin token should access admin endpoints"

        print("✓ Admin token can access admin endpoints")
