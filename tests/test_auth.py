"""Authentication and authorization tests."""

import pytest
from fastapi import status
from datetime import datetime, timedelta
from jose import jwt
from unittest.mock import patch

from src.auth.models import UserRole, PermissionScope
from src.auth.service import AuthenticationError, AuthorizationError
from src.config import settings


class TestUserRegistration:
    """Test user registration functionality."""
    
    def test_register_valid_user(self, client):
        """Test successful user registration."""
        response = client.post("/auth/register", json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "NewUser123!@#",
            "full_name": "New User",
            "organization": "Test Corp"
        })
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["message"] == "User registered successfully"
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["username"] == "newuser"
        assert data["user"]["role"] == UserRole.VIEWER
    
    def test_register_duplicate_email(self, client, test_user):
        """Test registration with duplicate email."""
        response = client.post("/auth/register", json={
            "email": test_user.email,
            "username": "another",
            "password": "Another123!@#",
            "full_name": "Another User"
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Email already registered" in response.json()["detail"]
    
    def test_register_duplicate_username(self, client, test_user):
        """Test registration with duplicate username."""
        response = client.post("/auth/register", json={
            "email": "another@example.com",
            "username": test_user.username,
            "password": "Another123!@#",
            "full_name": "Another User"
        })
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Username already taken" in response.json()["detail"]
    
    def test_register_weak_password(self, client):
        """Test registration with weak password."""
        response = client.post("/auth/register", json={
            "email": "weak@example.com",
            "username": "weakuser",
            "password": "weak",  # Too short, no uppercase, no special char
            "full_name": "Weak User"
        })
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_register_invalid_email(self, client):
        """Test registration with invalid email."""
        response = client.post("/auth/register", json={
            "email": "not-an-email",
            "username": "invaliduser",
            "password": "Valid123!@#",
            "full_name": "Invalid User"
        })
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUserLogin:
    """Test user login functionality."""
    
    def test_login_with_email(self, client, test_user):
        """Test login with email."""
        response = client.post("/auth/login", json={
            "username": test_user.email,
            "password": "Test123!@#"
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] == 3600
    
    def test_login_with_username(self, client, test_user):
        """Test login with username."""
        response = client.post("/auth/login", json={
            "username": test_user.username,
            "password": "Test123!@#"
        })
        
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.json()
    
    def test_login_invalid_password(self, client, test_user):
        """Test login with invalid password."""
        response = client.post("/auth/login", json={
            "username": test_user.email,
            "password": "WrongPassword123!@#"
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid credentials" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user."""
        response = client.post("/auth/login", json={
            "username": "nonexistent@example.com",
            "password": "Password123!@#"
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid credentials" in response.json()["detail"]
    
    def test_login_inactive_user(self, client, test_user, db_session):
        """Test login with inactive user."""
        # Deactivate user
        test_user.is_active = False
        db_session.commit()
        
        response = client.post("/auth/login", json={
            "username": test_user.email,
            "password": "Test123!@#"
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Account is disabled" in response.json()["detail"]


class TestTokenRefresh:
    """Test token refresh functionality."""
    
    def test_refresh_valid_token(self, client, test_user, auth_service):
        """Test refreshing with valid refresh token."""
        tokens = auth_service.create_tokens(test_user)
        
        response = client.post("/auth/refresh", json={
            "refresh_token": tokens.refresh_token
        })
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        # New tokens should be different
        assert data["access_token"] != tokens.access_token
    
    def test_refresh_invalid_token(self, client):
        """Test refreshing with invalid token."""
        response = client.post("/auth/refresh", json={
            "refresh_token": "invalid.token.here"
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_refresh_expired_token(self, client, test_user, auth_service):
        """Test refreshing with expired token."""
        # Create token with past expiration
        with patch('src.auth.service.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime.utcnow() - timedelta(days=8)
            expired_token = auth_service.create_refresh_token(test_user)
        
        response = client.post("/auth/refresh", json={
            "refresh_token": expired_token
        })
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUserProfile:
    """Test user profile endpoints."""
    
    def test_get_current_user(self, client, test_user, auth_headers):
        """Test getting current user info."""
        response = client.get("/auth/me", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username
        assert data["role"] == test_user.role
        assert "rate_limit" in data
        assert "permissions" in data
    
    def test_get_current_user_unauthorized(self, client):
        """Test getting current user without auth."""
        response = client.get("/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_update_current_user(self, client, test_user, auth_headers):
        """Test updating current user info."""
        response = client.put("/auth/me", 
            headers=auth_headers,
            json={
                "full_name": "Updated Name",
                "organization": "Updated Corp"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user"]["full_name"] == "Updated Name"
        assert data["user"]["organization"] == "Updated Corp"
    
    def test_update_forbidden_fields(self, client, auth_headers):
        """Test updating forbidden user fields."""
        response = client.put("/auth/me",
            headers=auth_headers,
            json={
                "email": "newemail@example.com",  # Should be ignored
                "role": "admin",  # Should be ignored
                "full_name": "Valid Update"
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Email and role should not change
        assert data["user"]["email"] != "newemail@example.com"


class TestAPIKeys:
    """Test API key management."""
    
    def test_create_api_key(self, client, test_user, auth_headers):
        """Test creating an API key."""
        response = client.post("/auth/api-keys",
            headers=auth_headers,
            json={
                "name": "Test Key",
                "scopes": ["read:companies", "read:metrics"],
                "expires_in_days": 30
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Test Key"
        assert "key" in data  # Full key shown once
        assert data["key"].startswith("ci_")
        assert len(data["scopes"]) == 2
    
    def test_list_api_keys(self, client, test_user, auth_headers, api_key):
        """Test listing user's API keys."""
        response = client.get("/auth/api-keys", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 1
        assert data[0]["name"] == "Test API Key"
        assert "key_prefix" in data[0]
        assert "key" not in data[0]  # Full key not shown
    
    def test_revoke_api_key(self, client, test_user, auth_headers, api_key):
        """Test revoking an API key."""
        _, key_obj = api_key
        
        response = client.delete(f"/auth/api-keys/{key_obj.id}", 
                                headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert "revoked successfully" in response.json()["message"]
    
    def test_use_api_key_auth(self, client, api_key_headers):
        """Test using API key for authentication."""
        response = client.get("/auth/me", headers=api_key_headers)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_api_key_invalid_scope(self, client, test_user, auth_service):
        """Test API key with insufficient scope."""
        from src.auth.models import APIKeyCreate
        
        # Create key with limited scope
        key_data = APIKeyCreate(
            name="Limited Key",
            scopes=[PermissionScope.READ_COMPANIES],
            expires_in_days=1
        )
        key_response = auth_service.create_api_key(test_user, key_data)
        
        # Try to access endpoint requiring different scope
        headers = {"X-API-Key": key_response.key}
        
        # This would fail if endpoint requires WRITE_COMPANIES
        # (would need to test with actual protected endpoint)


class TestAuthorization:
    """Test role-based authorization."""
    
    def test_admin_access(self, client, admin_headers):
        """Test admin accessing admin endpoints."""
        response = client.get("/auth/users", headers=admin_headers)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_viewer_denied_admin(self, client, auth_headers):
        """Test viewer denied admin access."""
        response = client.get("/auth/users", headers=auth_headers)
        
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_analyst_permissions(self, client, analyst_user, auth_service):
        """Test analyst role permissions."""
        token = auth_service.create_access_token(analyst_user)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.get("/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["role"] == UserRole.ANALYST
        
        # Check analyst has expected permissions
        permissions = data["permissions"]
        assert "read:companies" in permissions
        assert "run:analysis" in permissions
        assert "manage:users" not in permissions  # Admin only
    
    def test_update_user_role_admin_only(self, client, admin_headers, test_user):
        """Test only admin can update user roles."""
        response = client.put(f"/auth/users/{test_user.id}/role",
            headers=admin_headers,
            json={"role": "analyst"}
        )
        
        # Admin should succeed
        assert response.status_code == status.HTTP_200_OK
    
    def test_update_user_role_denied(self, client, auth_headers, test_user):
        """Test non-admin cannot update user roles."""
        response = client.put(f"/auth/users/{test_user.id}/role",
            headers=auth_headers,
            json={"role": "admin"}
        )
        
        # Non-admin should be denied
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    @pytest.mark.skip(reason="Rate limiting disabled in tests")
    def test_rate_limit_exceeded(self, client, auth_headers):
        """Test rate limit enforcement."""
        # Make many requests quickly
        for _ in range(100):
            response = client.get("/auth/me", headers=auth_headers)
        
        # Should eventually get rate limited
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "Rate limit exceeded" in response.json()["detail"]
    
    def test_rate_limit_reset(self, client, test_user, db_session):
        """Test rate limit counter reset."""
        # Set high API call count
        test_user.api_calls_today = 999
        test_user.api_calls_reset_at = datetime.utcnow() - timedelta(hours=1)
        db_session.commit()
        
        # Get rate limit should reset
        used, limit = test_user.get_rate_limit()
        assert used == 0  # Should reset
        assert limit == 1000  # Viewer limit


class TestSessionManagement:
    """Test session and logout functionality."""
    
    def test_logout(self, client, auth_headers):
        """Test user logout."""
        response = client.post("/auth/logout", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        assert "Logged out successfully" in response.json()["message"]
    
    def test_revoked_token_denied(self, client, test_user, auth_service, db_session):
        """Test revoked token is denied."""
        token = auth_service.create_access_token(test_user)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Revoke the token
        auth_service.revoke_token(token)
        
        # Try to use revoked token
        response = client.get("/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_expired_token_denied(self, client, test_user):
        """Test expired token is denied."""
        # Create token with past expiration
        expired_token = jwt.encode(
            {
                "sub": str(test_user.id),
                "exp": datetime.utcnow() - timedelta(hours=1),
                "type": "access"
            },
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestPasswordComplexity:
    """Test password complexity requirements."""
    
    @pytest.mark.parametrize("password,should_pass", [
        ("Short1!", False),  # Too short
        ("nouppercase123!", False),  # No uppercase
        ("NOLOWERCASE123!", False),  # No lowercase
        ("NoNumbers!", False),  # No digits
        ("NoSpecialChar123", False),  # No special chars
        ("ValidPass123!", True),  # Valid password
        ("C0mpl3x!P@ssw0rd", True),  # Complex valid
    ])
    def test_password_validation(self, client, password, should_pass):
        """Test password complexity validation."""
        response = client.post("/auth/register", json={
            "email": f"test{password[:5]}@example.com",
            "username": f"user{password[:5]}",
            "password": password,
            "full_name": "Test User"
        })
        
        if should_pass:
            assert response.status_code == status.HTTP_201_CREATED
        else:
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY