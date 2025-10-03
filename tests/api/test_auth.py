"""Tests for authentication API endpoints."""

import pytest
from datetime import datetime, timedelta
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.auth.models import User, UserRole


class TestRegisterEndpoint:
    """Test suite for POST /auth/register endpoint."""

    def test_register_user_success(self, api_client: TestClient):
        """Test successful user registration."""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "SecurePass123!@#",
            "full_name": "New User",
            "organization": "Test Org"
        }

        response = api_client.post("/auth/register", json=user_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert "message" in data
        assert "user" in data
        assert data["user"]["email"] == user_data["email"]
        assert data["user"]["username"] == user_data["username"]
        assert data["user"]["role"] == UserRole.VIEWER.value

    def test_register_duplicate_email(
        self, api_client: TestClient, test_user: User
    ):
        """Test registration with duplicate email returns 400."""
        user_data = {
            "email": test_user.email,
            "username": "differentuser",
            "password": "SecurePass123!@#"
        }

        response = api_client.post("/auth/register", json=user_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_username(
        self, api_client: TestClient, test_user: User
    ):
        """Test registration with duplicate username returns 400."""
        user_data = {
            "email": "different@example.com",
            "username": test_user.username,
            "password": "SecurePass123!@#"
        }

        response = api_client.post("/auth/register", json=user_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_weak_password(self, api_client: TestClient):
        """Test registration with weak password returns 400."""
        user_data = {
            "email": "weak@example.com",
            "username": "weakuser",
            "password": "weak"
        }

        response = api_client.post("/auth/register", json=user_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_invalid_email(self, api_client: TestClient):
        """Test registration with invalid email returns 422."""
        user_data = {
            "email": "invalid-email",
            "username": "testuser",
            "password": "SecurePass123!@#"
        }

        response = api_client.post("/auth/register", json=user_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_missing_required_fields(self, api_client: TestClient):
        """Test registration with missing fields returns 422."""
        user_data = {
            "email": "test@example.com"
            # Missing username and password
        }

        response = api_client.post("/auth/register", json=user_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestLoginEndpoint:
    """Test suite for POST /auth/login endpoint."""

    def test_login_success(
        self, api_client: TestClient, test_user: User
    ):
        """Test successful login with email."""
        login_data = {
            "identifier": test_user.email,
            "password": "Test123!@#"
        }

        response = api_client.post("/auth/login", json=login_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

    def test_login_with_username(
        self, api_client: TestClient, test_user: User
    ):
        """Test successful login with username."""
        login_data = {
            "identifier": test_user.username,
            "password": "Test123!@#"
        }

        response = api_client.post("/auth/login", json=login_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "access_token" in data

    def test_login_wrong_password(
        self, api_client: TestClient, test_user: User
    ):
        """Test login with wrong password returns 401."""
        login_data = {
            "identifier": test_user.email,
            "password": "WrongPassword123!"
        }

        response = api_client.post("/auth/login", json=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client: TestClient):
        """Test login with non-existent user returns 401."""
        login_data = {
            "identifier": "nonexistent@example.com",
            "password": "Password123!"
        }

        response = api_client.post("/auth/login", json=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_sets_refresh_token_cookie(
        self, api_client: TestClient, test_user: User
    ):
        """Test login sets refresh token as secure cookie."""
        login_data = {
            "identifier": test_user.email,
            "password": "Test123!@#"
        }

        response = api_client.post("/auth/login", json=login_data)

        # Check for Set-Cookie header
        assert "set-cookie" in [h.lower() for h in response.headers.keys()]


class TestRefreshTokenEndpoint:
    """Test suite for POST /auth/refresh endpoint."""

    def test_refresh_token_success(
        self, api_client: TestClient, test_user: User, auth_service
    ):
        """Test refreshing access token with valid refresh token."""
        # Get initial tokens
        tokens = auth_service.create_tokens(test_user)

        # Refresh the token
        response = api_client.post(
            "/auth/refresh",
            json={"refresh_token": tokens.refresh_token}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_with_invalid_token(self, api_client: TestClient):
        """Test refresh with invalid token returns 401."""
        response = api_client.post(
            "/auth/refresh",
            json={"refresh_token": "invalid.token.here"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_without_token(self, api_client: TestClient):
        """Test refresh without token returns 400."""
        response = api_client.post("/auth/refresh", json={})

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestLogoutEndpoint:
    """Test suite for POST /auth/logout endpoint."""

    def test_logout_success(
        self, api_client: TestClient, auth_headers: dict
    ):
        """Test successful logout."""
        response = api_client.post("/auth/logout", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "message" in data

    def test_logout_requires_auth(self, api_client: TestClient):
        """Test logout requires authentication."""
        response = api_client.post("/auth/logout")

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_logout_clears_cookie(
        self, api_client: TestClient, auth_headers: dict
    ):
        """Test logout clears refresh token cookie."""
        response = api_client.post("/auth/logout", headers=auth_headers)

        # Check for cookie deletion
        cookies = response.headers.get("set-cookie", "")
        assert "refresh_token" in cookies.lower()


class TestCurrentUserEndpoint:
    """Test suite for GET /auth/me endpoint."""

    def test_get_current_user_success(
        self, api_client: TestClient, auth_headers: dict, test_user: User
    ):
        """Test getting current user information."""
        response = api_client.get("/auth/me", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == str(test_user.id)
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username
        assert "role" in data
        assert "permissions" in data

    def test_get_current_user_requires_auth(self, api_client: TestClient):
        """Test /me endpoint requires authentication."""
        response = api_client.get("/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_invalid_token(
        self, api_client: TestClient, invalid_token_headers: dict
    ):
        """Test /me endpoint with invalid token returns 401."""
        response = api_client.get("/auth/me", headers=invalid_token_headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_includes_rate_limit(
        self, api_client: TestClient, auth_headers: dict
    ):
        """Test current user response includes rate limit info."""
        response = api_client.get("/auth/me", headers=auth_headers)

        data = response.json()
        assert "rate_limit" in data
        assert "used" in data["rate_limit"]
        assert "limit" in data["rate_limit"]


class TestUpdateCurrentUserEndpoint:
    """Test suite for PUT /auth/me endpoint."""

    def test_update_current_user_success(
        self, api_client: TestClient, auth_headers: dict
    ):
        """Test updating current user information."""
        update_data = {
            "full_name": "Updated Name",
            "organization": "New Organization"
        }

        response = api_client.put(
            "/auth/me",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["user"]["full_name"] == "Updated Name"
        assert data["user"]["organization"] == "New Organization"

    def test_update_current_user_requires_auth(self, api_client: TestClient):
        """Test updating user requires authentication."""
        update_data = {"full_name": "New Name"}

        response = api_client.put("/auth/me", json=update_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_current_user_invalid_fields(
        self, api_client: TestClient, auth_headers: dict
    ):
        """Test updating invalid fields is ignored."""
        update_data = {
            "email": "newemail@example.com",  # Should be ignored
            "role": "ADMIN"  # Should be ignored
        }

        response = api_client.put(
            "/auth/me",
            json=update_data,
            headers=auth_headers
        )

        # Should succeed but ignore invalid fields
        assert response.status_code == status.HTTP_200_OK


class TestAPIKeyEndpoints:
    """Test suite for API key management endpoints."""

    def test_create_api_key_success(
        self, api_client: TestClient, auth_headers: dict
    ):
        """Test creating a new API key."""
        key_data = {
            "name": "Test API Key",
            "scopes": ["read:companies", "read:metrics"],
            "expires_in_days": 30
        }

        response = api_client.post(
            "/auth/api-keys",
            json=key_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "key" in data
        assert "id" in data
        assert "name" in data
        assert data["name"] == key_data["name"]

    def test_create_api_key_requires_auth(self, api_client: TestClient):
        """Test creating API key requires authentication."""
        key_data = {"name": "Test Key"}

        response = api_client.post("/auth/api-keys", json=key_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_api_keys(
        self, api_client: TestClient, auth_headers: dict, api_key
    ):
        """Test listing user's API keys."""
        response = api_client.get("/auth/api-keys", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)

    def test_revoke_api_key_success(
        self, api_client: TestClient, auth_headers: dict, api_key
    ):
        """Test revoking an API key."""
        key_value, key_obj = api_key

        response = api_client.delete(
            f"/auth/api-keys/{key_obj.id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK

    def test_revoke_nonexistent_api_key(
        self, api_client: TestClient, auth_headers: dict
    ):
        """Test revoking non-existent API key returns 404."""
        from uuid import uuid4

        response = api_client.delete(
            f"/auth/api-keys/{uuid4()}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestAdminEndpoints:
    """Test suite for admin-only endpoints."""

    def test_list_users_as_admin(
        self, api_client: TestClient, admin_headers: dict
    ):
        """Test admin can list all users."""
        response = api_client.get("/auth/users", headers=admin_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)

    def test_list_users_as_viewer_forbidden(
        self, api_client: TestClient, auth_headers: dict
    ):
        """Test viewer cannot list users."""
        response = api_client.get("/auth/users", headers=auth_headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_user_role_as_admin(
        self, api_client: TestClient, admin_headers: dict, test_user: User
    ):
        """Test admin can update user role."""
        response = api_client.put(
            f"/auth/users/{test_user.id}/role",
            params={"role": UserRole.ANALYST.value},
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_200_OK

    def test_update_user_status_as_admin(
        self, api_client: TestClient, admin_headers: dict, test_user: User
    ):
        """Test admin can update user status."""
        response = api_client.put(
            f"/auth/users/{test_user.id}/status",
            params={"is_active": False},
            headers=admin_headers
        )

        assert response.status_code == status.HTTP_200_OK


class TestAuthenticationErrors:
    """Test suite for authentication error handling."""

    def test_missing_authorization_header(self, api_client: TestClient):
        """Test request without Authorization header returns 401."""
        response = api_client.get("/api/v1/companies/watchlist")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_malformed_authorization_header(self, api_client: TestClient):
        """Test malformed Authorization header returns 401."""
        headers = {"Authorization": "InvalidFormat"}

        response = api_client.get(
            "/api/v1/companies/watchlist",
            headers=headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_expired_token(
        self, api_client: TestClient, expired_token_headers: dict
    ):
        """Test expired token returns 401."""
        response = api_client.get(
            "/auth/me",
            headers=expired_token_headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_inactive_user_forbidden(
        self, api_client: TestClient, db_session: Session, test_user: User, auth_service
    ):
        """Test inactive user cannot access protected endpoints."""
        # Deactivate user
        test_user.is_active = False
        db_session.commit()

        # Create token for inactive user
        token = auth_service.create_access_token(test_user)
        headers = {"Authorization": f"Bearer {token}"}

        response = api_client.get("/auth/me", headers=headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN
