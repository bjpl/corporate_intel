"""
Integration Tests for Authentication API

Tests complete authentication flows including registration, login, token refresh,
and protected endpoint access.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from models.user import User, UserRole
from core.auth import create_access_token, create_refresh_token


class TestUserRegistration:
    """Test user registration endpoint."""

    def test_register_new_user_success(self, client: TestClient, db_session: Session):
        """Test successful user registration."""
        registration_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "SecurePassword123!",
            "full_name": "New User"
        }

        response = client.post("/api/v1/auth/register", json=registration_data)

        assert response.status_code == 201
        data = response.json()

        assert data["email"] == registration_data["email"]
        assert data["username"] == registration_data["username"]
        assert "id" in data
        assert "hashed_password" not in data  # Should not expose password

        # Verify user exists in database
        user = db_session.query(User).filter_by(email=registration_data["email"]).first()
        assert user is not None
        assert user.username == registration_data["username"]

    def test_register_duplicate_email(self, client: TestClient, admin_user: User):
        """Test registration fails with duplicate email."""
        registration_data = {
            "email": admin_user.email,
            "username": "different_username",
            "password": "SecurePassword123!"
        }

        response = client.post("/api/v1/auth/register", json=registration_data)

        assert response.status_code == 400
        assert "email" in response.json()["detail"].lower()

    def test_register_duplicate_username(self, client: TestClient, admin_user: User):
        """Test registration fails with duplicate username."""
        registration_data = {
            "email": "different@example.com",
            "username": admin_user.username,
            "password": "SecurePassword123!"
        }

        response = client.post("/api/v1/auth/register", json=registration_data)

        assert response.status_code == 400
        assert "username" in response.json()["detail"].lower()

    def test_register_weak_password(self, client: TestClient):
        """Test registration fails with weak password."""
        registration_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "weak"
        }

        response = client.post("/api/v1/auth/register", json=registration_data)

        assert response.status_code == 422

    def test_register_invalid_email(self, client: TestClient):
        """Test registration fails with invalid email format."""
        registration_data = {
            "email": "not-an-email",
            "username": "newuser",
            "password": "SecurePassword123!"
        }

        response = client.post("/api/v1/auth/register", json=registration_data)

        assert response.status_code == 422

    def test_register_missing_required_fields(self, client: TestClient):
        """Test registration fails when required fields are missing."""
        response = client.post("/api/v1/auth/register", json={})

        assert response.status_code == 422


class TestUserLogin:
    """Test user login endpoint."""

    def test_login_success(self, client: TestClient, admin_user: User, test_password: str):
        """Test successful login."""
        login_data = {
            "username": admin_user.email,
            "password": test_password
        }

        response = client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 0

    def test_login_with_username(self, client: TestClient, admin_user: User, test_password: str):
        """Test login with username instead of email."""
        login_data = {
            "username": admin_user.username,
            "password": test_password
        }

        response = client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_incorrect_password(self, client: TestClient, admin_user: User):
        """Test login fails with incorrect password."""
        login_data = {
            "username": admin_user.email,
            "password": "WrongPassword123!"
        }

        response = client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login fails for nonexistent user."""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "SomePassword123!"
        }

        response = client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 401

    def test_login_inactive_user(self, client: TestClient, inactive_user: User, test_password: str):
        """Test login fails for inactive user."""
        login_data = {
            "username": inactive_user.email,
            "password": test_password
        }

        response = client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower()

    def test_login_unverified_user(self, client: TestClient, unverified_user: User, test_password: str):
        """Test login behavior for unverified user."""
        login_data = {
            "username": unverified_user.email,
            "password": test_password
        }

        response = client.post("/api/v1/auth/login", data=login_data)

        # Depending on requirements, may allow login but restrict access
        # or deny login entirely
        assert response.status_code in [200, 403]


class TestTokenRefresh:
    """Test token refresh endpoint."""

    def test_refresh_token_success(self, client: TestClient, admin_user: User):
        """Test successful token refresh."""
        refresh_token = create_refresh_token(data={"sub": str(admin_user.id)})

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_refresh_with_expired_token(self, client: TestClient, admin_user: User):
        """Test refresh fails with expired token."""
        expired_refresh_token = create_refresh_token(
            data={"sub": str(admin_user.id)},
            expires_delta=timedelta(seconds=-1)
        )

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": expired_refresh_token}
        )

        assert response.status_code == 401

    def test_refresh_with_invalid_token(self, client: TestClient):
        """Test refresh fails with invalid token."""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )

        assert response.status_code == 401

    def test_refresh_with_access_token(self, client: TestClient, admin_user: User):
        """Test refresh fails when using access token instead of refresh token."""
        access_token = create_access_token(data={"sub": str(admin_user.id)})

        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token}
        )

        # Should fail or warn about token type mismatch
        assert response.status_code in [400, 401]


class TestPasswordReset:
    """Test password reset flow."""

    def test_request_password_reset(self, client: TestClient, admin_user: User):
        """Test requesting password reset."""
        response = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": admin_user.email}
        )

        assert response.status_code == 200
        assert "sent" in response.json()["message"].lower()

    def test_request_password_reset_nonexistent_email(self, client: TestClient):
        """Test password reset request for nonexistent email."""
        response = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "nonexistent@example.com"}
        )

        # Should return success to prevent email enumeration
        assert response.status_code == 200

    def test_reset_password_with_valid_token(self, client: TestClient, admin_user: User):
        """Test resetting password with valid token."""
        # First request reset to get token
        reset_token = create_access_token(
            data={"sub": str(admin_user.id), "type": "password_reset"},
            expires_delta=timedelta(hours=1)
        )

        new_password = "NewSecurePassword123!"
        response = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": reset_token,
                "new_password": new_password
            }
        )

        assert response.status_code == 200

        # Verify can login with new password
        login_response = client.post(
            "/api/v1/auth/login",
            data={"username": admin_user.email, "password": new_password}
        )
        assert login_response.status_code == 200

    def test_reset_password_with_expired_token(self, client: TestClient, admin_user: User):
        """Test password reset fails with expired token."""
        expired_token = create_access_token(
            data={"sub": str(admin_user.id), "type": "password_reset"},
            expires_delta=timedelta(seconds=-1)
        )

        response = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "token": expired_token,
                "new_password": "NewPassword123!"
            }
        )

        assert response.status_code == 401


class TestProtectedEndpoints:
    """Test access to protected endpoints."""

    def test_access_protected_endpoint_with_valid_token(
        self,
        client: TestClient,
        auth_headers: dict
    ):
        """Test accessing protected endpoint with valid token."""
        response = client.get("/api/v1/users/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "role" in data

    def test_access_protected_endpoint_without_token(self, client: TestClient):
        """Test accessing protected endpoint without token."""
        response = client.get("/api/v1/users/me")

        assert response.status_code == 401

    def test_access_protected_endpoint_with_expired_token(
        self,
        client: TestClient,
        expired_token: str
    ):
        """Test accessing protected endpoint with expired token."""
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/v1/users/me", headers=headers)

        assert response.status_code == 401

    def test_access_protected_endpoint_with_invalid_token(
        self,
        client: TestClient,
        invalid_token: str
    ):
        """Test accessing protected endpoint with invalid token."""
        headers = {"Authorization": f"Bearer {invalid_token}"}
        response = client.get("/api/v1/users/me", headers=headers)

        assert response.status_code == 401

    def test_access_protected_endpoint_with_malformed_header(self, client: TestClient):
        """Test accessing protected endpoint with malformed auth header."""
        headers = {"Authorization": "InvalidFormat token"}
        response = client.get("/api/v1/users/me", headers=headers)

        assert response.status_code == 401


class TestRoleBasedAccess:
    """Test role-based access control (RBAC)."""

    def test_admin_can_access_admin_endpoint(
        self,
        client: TestClient,
        valid_token: str
    ):
        """Test admin can access admin-only endpoints."""
        headers = {"Authorization": f"Bearer {valid_token}"}
        response = client.get("/api/v1/admin/users", headers=headers)

        assert response.status_code == 200

    def test_analyst_cannot_access_admin_endpoint(
        self,
        client: TestClient,
        analyst_token: str
    ):
        """Test analyst cannot access admin-only endpoints."""
        headers = {"Authorization": f"Bearer {analyst_token}"}
        response = client.get("/api/v1/admin/users", headers=headers)

        assert response.status_code == 403

    def test_viewer_cannot_access_write_endpoint(
        self,
        client: TestClient,
        viewer_token: str
    ):
        """Test viewer cannot access write endpoints."""
        headers = {"Authorization": f"Bearer {viewer_token}"}
        response = client.post(
            "/api/v1/reports",
            headers=headers,
            json={"title": "Test Report", "content": "Test content"}
        )

        assert response.status_code == 403

    def test_viewer_can_access_read_endpoint(
        self,
        client: TestClient,
        viewer_token: str
    ):
        """Test viewer can access read-only endpoints."""
        headers = {"Authorization": f"Bearer {viewer_token}"}
        response = client.get("/api/v1/reports", headers=headers)

        assert response.status_code == 200

    def test_analyst_can_access_write_endpoint(
        self,
        client: TestClient,
        analyst_token: str
    ):
        """Test analyst can access write endpoints."""
        headers = {"Authorization": f"Bearer {analyst_token}"}
        response = client.post(
            "/api/v1/reports",
            headers=headers,
            json={"title": "Test Report", "content": "Test content"}
        )

        assert response.status_code in [200, 201]


class TestConcurrentSessions:
    """Test concurrent session handling."""

    def test_multiple_valid_tokens_same_user(
        self,
        client: TestClient,
        admin_user: User
    ):
        """Test multiple valid tokens work for same user."""
        token1 = create_access_token(data={"sub": str(admin_user.id)})
        token2 = create_access_token(data={"sub": str(admin_user.id)})

        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}

        response1 = client.get("/api/v1/users/me", headers=headers1)
        response2 = client.get("/api/v1/users/me", headers=headers2)

        assert response1.status_code == 200
        assert response2.status_code == 200

    def test_login_from_multiple_devices(
        self,
        client: TestClient,
        admin_user: User,
        test_password: str
    ):
        """Test user can login from multiple devices."""
        login_data = {
            "username": admin_user.email,
            "password": test_password
        }

        # Simulate multiple device logins
        response1 = client.post("/api/v1/auth/login", data=login_data)
        response2 = client.post("/api/v1/auth/login", data=login_data)

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Both tokens should work
        token1 = response1.json()["access_token"]
        token2 = response2.json()["access_token"]

        assert token1 != token2  # Different tokens

        headers1 = {"Authorization": f"Bearer {token1}"}
        headers2 = {"Authorization": f"Bearer {token2}"}

        me1 = client.get("/api/v1/users/me", headers=headers1)
        me2 = client.get("/api/v1/users/me", headers=headers2)

        assert me1.status_code == 200
        assert me2.status_code == 200


class TestSecurityHeaders:
    """Test security-related headers in responses."""

    def test_login_response_has_security_headers(
        self,
        client: TestClient,
        admin_user: User,
        test_password: str
    ):
        """Test login response includes security headers."""
        response = client.post(
            "/api/v1/auth/login",
            data={"username": admin_user.email, "password": test_password}
        )

        # Check for security headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_cors_headers_on_auth_endpoints(self, client: TestClient):
        """Test CORS headers are properly set on auth endpoints."""
        response = client.options("/api/v1/auth/login")

        # Should have CORS headers
        assert "Access-Control-Allow-Origin" in response.headers
