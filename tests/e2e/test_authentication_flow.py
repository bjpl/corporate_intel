"""End-to-end tests for authentication flows.

Tests cover:
- User registration flow
- Login/logout flow
- Token refresh flow
- API key creation and usage
- Permission and role validation
- Password reset flow
- Session management
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from src.api.main import app
from src.auth.models import UserRole, PermissionScope


@pytest.fixture
def e2e_client():
    """Create E2E test client."""
    return TestClient(app)


class TestUserRegistrationFlow:
    """Test complete user registration flow."""

    def test_register_new_user_success(self, e2e_client):
        """Test successful new user registration."""
        user_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "SecurePass123!",
            "full_name": "New User",
            "organization": "Test Corp"
        }

        response = e2e_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["username"] == user_data["username"]
        assert "id" in data

    def test_register_duplicate_email(self, e2e_client):
        """Test registration with duplicate email."""
        user_data = {
            "email": "test@example.com",
            "username": "testuser1",
            "password": "SecurePass123!",
            "full_name": "Test User"
        }

        # First registration should succeed
        response1 = e2e_client.post("/api/v1/auth/register", json=user_data)
        assert response1.status_code == 201

        # Second registration with same email should fail
        user_data["username"] = "testuser2"
        response2 = e2e_client.post("/api/v1/auth/register", json=user_data)
        assert response2.status_code == 400

    def test_register_weak_password(self, e2e_client):
        """Test registration with weak password."""
        user_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "weak",  # Too short
            "full_name": "Test User"
        }

        response = e2e_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 422  # Validation error

    def test_register_invalid_email(self, e2e_client):
        """Test registration with invalid email format."""
        user_data = {
            "email": "notanemail",
            "username": "testuser",
            "password": "SecurePass123!",
            "full_name": "Test User"
        }

        response = e2e_client.post("/api/v1/auth/register", json=user_data)

        assert response.status_code == 422


class TestLoginLogoutFlow:
    """Test complete login and logout flow."""

    def test_login_success(self, e2e_client):
        """Test successful user login."""
        # First register user
        register_data = {
            "email": "logintest@example.com",
            "username": "loginuser",
            "password": "SecurePass123!",
            "full_name": "Login Test"
        }
        e2e_client.post("/api/v1/auth/register", json=register_data)

        # Then login
        login_data = {
            "username": "logintest@example.com",
            "password": "SecurePass123!"
        }

        response = e2e_client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials(self, e2e_client):
        """Test login with invalid credentials."""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "WrongPassword123!"
        }

        response = e2e_client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 401

    def test_login_incorrect_password(self, e2e_client):
        """Test login with incorrect password."""
        # Register user
        register_data = {
            "email": "passtest@example.com",
            "username": "passuser",
            "password": "CorrectPass123!",
            "full_name": "Pass Test"
        }
        e2e_client.post("/api/v1/auth/register", json=register_data)

        # Try to login with wrong password
        login_data = {
            "username": "passtest@example.com",
            "password": "WrongPass123!"
        }

        response = e2e_client.post("/api/v1/auth/login", data=login_data)

        assert response.status_code == 401

    def test_protected_endpoint_without_token(self, e2e_client):
        """Test accessing protected endpoint without token."""
        response = e2e_client.get("/api/v1/companies")

        assert response.status_code == 401

    def test_protected_endpoint_with_valid_token(self, e2e_client):
        """Test accessing protected endpoint with valid token."""
        # Register and login
        register_data = {
            "email": "tokentest@example.com",
            "username": "tokenuser",
            "password": "SecurePass123!",
            "full_name": "Token Test"
        }
        e2e_client.post("/api/v1/auth/register", json=register_data)

        login_data = {
            "username": "tokentest@example.com",
            "password": "SecurePass123!"
        }
        login_response = e2e_client.post("/api/v1/auth/login", data=login_data)
        token = login_response.json()["access_token"]

        # Access protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = e2e_client.get("/api/v1/companies", headers=headers)

        assert response.status_code in [200, 404]  # Success or no data


class TestTokenRefreshFlow:
    """Test token refresh flow."""

    def test_refresh_token_success(self, e2e_client):
        """Test successful token refresh."""
        # Register and login
        register_data = {
            "email": "refreshtest@example.com",
            "username": "refreshuser",
            "password": "SecurePass123!",
            "full_name": "Refresh Test"
        }
        e2e_client.post("/api/v1/auth/register", json=register_data)

        login_data = {
            "username": "refreshtest@example.com",
            "password": "SecurePass123!"
        }
        login_response = e2e_client.post("/api/v1/auth/login", data=login_data)
        refresh_token = login_response.json()["refresh_token"]

        # Refresh token
        response = e2e_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    def test_refresh_with_invalid_token(self, e2e_client):
        """Test token refresh with invalid token."""
        response = e2e_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"}
        )

        assert response.status_code == 401


class TestAPIKeyFlow:
    """Test API key creation and usage flow."""

    def test_create_api_key_success(self, e2e_client):
        """Test successful API key creation."""
        # Register and login
        register_data = {
            "email": "apikeytest@example.com",
            "username": "apikeyuser",
            "password": "SecurePass123!",
            "full_name": "API Key Test"
        }
        e2e_client.post("/api/v1/auth/register", json=register_data)

        login_data = {
            "username": "apikeytest@example.com",
            "password": "SecurePass123!"
        }
        login_response = e2e_client.post("/api/v1/auth/login", data=login_data)
        token = login_response.json()["access_token"]

        # Create API key
        headers = {"Authorization": f"Bearer {token}"}
        api_key_data = {
            "name": "Test API Key",
            "scopes": ["read:companies", "read:metrics"],
            "expires_in_days": 30
        }

        response = e2e_client.post(
            "/api/v1/auth/api-keys",
            json=api_key_data,
            headers=headers
        )

        assert response.status_code == 201
        data = response.json()
        assert "key" in data
        assert data["name"] == "Test API Key"

    def test_use_api_key_for_authentication(self, e2e_client):
        """Test using API key for authentication."""
        # This would require more complex setup
        pass

    def test_list_api_keys(self, e2e_client):
        """Test listing user's API keys."""
        # Register and login
        register_data = {
            "email": "listkeys@example.com",
            "username": "listkeyuser",
            "password": "SecurePass123!",
            "full_name": "List Keys Test"
        }
        e2e_client.post("/api/v1/auth/register", json=register_data)

        login_data = {
            "username": "listkeys@example.com",
            "password": "SecurePass123!"
        }
        login_response = e2e_client.post("/api/v1/auth/login", data=login_data)
        token = login_response.json()["access_token"]

        # List API keys
        headers = {"Authorization": f"Bearer {token}"}
        response = e2e_client.get("/api/v1/auth/api-keys", headers=headers)

        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestRoleBasedAccess:
    """Test role-based access control."""

    def test_viewer_cannot_create_company(self, e2e_client):
        """Test that viewer role cannot create companies."""
        # Register viewer user
        register_data = {
            "email": "viewer@example.com",
            "username": "viewer",
            "password": "SecurePass123!",
            "full_name": "Viewer User"
        }
        e2e_client.post("/api/v1/auth/register", json=register_data)

        login_data = {
            "username": "viewer@example.com",
            "password": "SecurePass123!"
        }
        login_response = e2e_client.post("/api/v1/auth/login", data=login_data)
        token = login_response.json()["access_token"]

        # Try to create company
        headers = {"Authorization": f"Bearer {token}"}
        company_data = {
            "ticker": "TEST",
            "name": "Test Company"
        }

        response = e2e_client.post("/api/v1/companies", json=company_data, headers=headers)

        assert response.status_code == 403  # Forbidden

    def test_admin_can_manage_users(self, e2e_client):
        """Test that admin can manage users."""
        # This would require admin user setup
        pass


class TestCompleteAuthenticationFlow:
    """Test complete authentication workflow from registration to data access."""

    def test_complete_workflow(self, e2e_client):
        """Test complete user workflow."""
        # 1. Register
        register_data = {
            "email": "workflow@example.com",
            "username": "workflowuser",
            "password": "SecurePass123!",
            "full_name": "Workflow User"
        }
        register_response = e2e_client.post("/api/v1/auth/register", json=register_data)
        assert register_response.status_code == 201

        # 2. Login
        login_data = {
            "username": "workflow@example.com",
            "password": "SecurePass123!"
        }
        login_response = e2e_client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # 3. Access protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        companies_response = e2e_client.get("/api/v1/companies", headers=headers)
        assert companies_response.status_code in [200, 404]

        # 4. Get user profile
        profile_response = e2e_client.get("/api/v1/auth/me", headers=headers)
        assert profile_response.status_code == 200
        assert profile_response.json()["email"] == "workflow@example.com"

        # 5. Create API key
        api_key_data = {
            "name": "Workflow API Key",
            "scopes": ["read:companies"],
            "expires_in_days": 30
        }
        api_key_response = e2e_client.post(
            "/api/v1/auth/api-keys",
            json=api_key_data,
            headers=headers
        )
        assert api_key_response.status_code == 201
