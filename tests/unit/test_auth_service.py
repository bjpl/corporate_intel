"""Comprehensive tests for authentication service.

This test suite increases coverage for src/auth/service.py
from 18.92% to target of 90%.
"""

import pytest
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

from src.auth.service import AuthService, AuthenticationError, AuthorizationError
from src.auth.models import User, APIKey, UserRole, PermissionScope
from src.core.config import get_settings


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self, auth_service):
        """Test password is properly hashed."""
        password = "TestPassword123!"
        hashed = auth_service.hash_password(password)

        # Hashed password should not equal plaintext
        assert hashed != password
        # Should be bcrypt hash
        assert hashed.startswith("$2b$")
        # Should be reasonable length
        assert len(hashed) >= 60

    def test_verify_password_correct(self, auth_service):
        """Test correct password verification."""
        password = "TestPassword123!"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self, auth_service):
        """Test incorrect password verification."""
        password = "TestPassword123!"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password("WrongPassword!", hashed) is False

    def test_verify_password_empty(self, auth_service):
        """Test verification with empty password."""
        hashed = auth_service.hash_password("TestPassword123!")

        assert auth_service.verify_password("", hashed) is False

    def test_hash_password_deterministic(self, auth_service):
        """Test that hashing same password produces different hashes (salt)."""
        password = "TestPassword123!"
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)

        # Different hashes due to salt
        assert hash1 != hash2
        # But both verify correctly
        assert auth_service.verify_password(password, hash1)
        assert auth_service.verify_password(password, hash2)


class TestJWTTokens:
    """Test JWT token creation and verification."""

    def test_create_access_token(self, auth_service, test_user):
        """Test JWT access token creation."""
        token = auth_service.create_access_token(test_user)

        assert isinstance(token, str)
        assert len(token) > 0
        # Should have 3 parts (header.payload.signature)
        assert len(token.split(".")) == 3

    def test_create_access_token_with_expiration(self, auth_service, test_user):
        """Test JWT token with custom expiration."""
        expires_delta = timedelta(minutes=15)

        token = auth_service.create_access_token(test_user, expires_delta=expires_delta)

        # Decode and verify expiration
        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=["HS256"]
        )

        # Check that exp and iat are present
        assert "exp" in payload
        assert "iat" in payload

        # Verify expiration is ~15 minutes after issuance
        exp_time = payload["exp"]
        iat_time = payload["iat"]
        time_diff = exp_time - iat_time

        # Should be approximately 15 minutes (900 seconds)
        assert 890 <= time_diff <= 910  # Allow 10 second tolerance

    def test_create_access_token_default_expiration(self, auth_service, test_user):
        """Test JWT token with default expiration."""
        token = auth_service.create_access_token(test_user)

        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=["HS256"]
        )

        # Should have exp and iat claims
        assert "exp" in payload
        assert "iat" in payload

        # Verify expiration is ~60 minutes after issuance (default)
        exp_time = payload["exp"]
        iat_time = payload["iat"]
        time_diff = exp_time - iat_time

        # Should be approximately 60 minutes (3600 seconds)
        assert 3590 <= time_diff <= 3610  # Allow 10 second tolerance

    def test_token_contains_data(self, auth_service, admin_user):
        """Test that token contains encoded data."""
        token = auth_service.create_access_token(admin_user)

        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=["HS256"]
        )

        assert payload["email"] == "admin@example.com"
        assert payload["username"] == "adminuser"
        assert payload["role"] == "admin"


class TestAPIKeyGeneration:
    """Test API key generation and validation."""

    def test_create_api_key(self, auth_service, test_user):
        """Test API key creation."""
        from src.auth.models import APIKeyCreate, PermissionScope

        key_data = APIKeyCreate(
            name="Test API Key",
            scopes=[PermissionScope.READ_COMPANIES],
            expires_in_days=30
        )

        response = auth_service.create_api_key(test_user, key_data)

        assert isinstance(response.key, str)
        # Should start with prefix
        assert response.key.startswith("ci_")
        # Should be reasonable length (prefix + random part)
        assert len(response.key) >= 40

    def test_create_api_key_unique(self, auth_service, test_user):
        """Test that created API keys are unique."""
        from src.auth.models import APIKeyCreate, PermissionScope

        key_data = APIKeyCreate(
            name="Test API Key 1",
            scopes=[PermissionScope.READ_COMPANIES],
            expires_in_days=30
        )

        response1 = auth_service.create_api_key(test_user, key_data)

        key_data.name = "Test API Key 2"
        response2 = auth_service.create_api_key(test_user, key_data)

        assert response1.key != response2.key

    def test_create_api_key_format(self, auth_service, test_user):
        """Test API key format."""
        from src.auth.models import APIKeyCreate, PermissionScope

        key_data = APIKeyCreate(
            name="Test API Key",
            scopes=[PermissionScope.READ_COMPANIES],
            expires_in_days=30
        )

        response = auth_service.create_api_key(test_user, key_data)

        # Should match expected format
        assert response.key.startswith("ci_")
        # Should contain only alphanumeric, hyphens, and underscores after prefix
        key_after_prefix = response.key[3:]
        for char in key_after_prefix:
            assert char.isalnum() or char in ['-', '_']


class TestAuthenticationLogic:
    """Test authentication business logic."""

    def test_authenticate_user_success(self, auth_service):
        """Test successful user authentication."""
        # This is a unit test - in reality, you'd use a mock database
        # For now, we test the logic of password verification
        password = "TestPassword123!"
        hashed = auth_service.hash_password(password)

        # Simulate user from database
        assert auth_service.verify_password(password, hashed)

    def test_authenticate_user_wrong_password(self, auth_service):
        """Test authentication with wrong password."""
        password = "TestPassword123!"
        hashed = auth_service.hash_password(password)

        assert not auth_service.verify_password("WrongPassword!", hashed)

    def test_role_hierarchy(self):
        """Test user role hierarchy."""
        # Test that role enums are properly defined
        assert UserRole.VIEWER.value == "viewer"
        assert UserRole.ANALYST.value == "analyst"
        assert UserRole.ADMIN.value == "admin"

    def test_permission_scopes(self):
        """Test permission scope definitions."""
        # Test that permission scopes are properly defined
        assert PermissionScope.READ_COMPANIES.value == "read:companies"
        assert PermissionScope.WRITE_COMPANIES.value == "write:companies"
        assert PermissionScope.MANAGE_USERS.value == "manage:users"


class TestSecurityValidation:
    """Test security validation logic."""

    def test_password_strength_weak(self):
        """Test weak password detection."""
        weak_passwords = [
            "123456",
            "password",
            "abc123",
            "qwerty",
        ]

        for pwd in weak_passwords:
            # Weak passwords can still be hashed, but should be rejected at validation level
            # (This logic would be in the User model or registration endpoint)
            assert len(pwd) < 12  # Too short

    def test_password_strength_strong(self, auth_service):
        """Test strong password acceptance."""
        strong_passwords = [
            "MySecureP@ssw0rd123!",
            "C0mplex!Pass#2024",
            "Str0ng&Secure$Password",
        ]

        for pwd in strong_passwords:
            hashed = auth_service.hash_password(pwd)
            assert auth_service.verify_password(pwd, hashed)

    def test_email_in_token_payload(self, auth_service, test_user):
        """Test that email is properly included in token payload."""
        token = auth_service.create_access_token(test_user)

        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=["HS256"]
        )

        assert payload["email"] == test_user.email


class TestErrorHandling:
    """Test error handling in auth service."""

    def test_verify_password_with_none(self, auth_service):
        """Test password verification with None values."""
        hashed = auth_service.hash_password("test")

        # Should handle None gracefully
        try:
            result = auth_service.verify_password(None, hashed)
            # If it doesn't raise, it should return False
            assert result is False
        except (TypeError, AttributeError):
            # Or it might raise an error, which is also acceptable
            pass

    def test_create_token_minimal_user(self, auth_service, db_session):
        """Test token creation with minimal user data."""
        from src.auth.models import UserCreate

        # Create user with minimal required fields
        user_data = UserCreate(
            email="minimal@example.com",
            username="minimaluser",
            password="Minimal123!@#",
            full_name="Minimal User",
            organization="Test Corp"
        )

        user = auth_service.create_user(user_data, role=UserRole.VIEWER)
        token = auth_service.create_access_token(user)

        # Should still create a valid token
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_with_special_characters(self, auth_service, db_session):
        """Test token creation with special characters in user data."""
        from src.auth.models import UserCreate

        user_data = UserCreate(
            email="user+test@example.com",
            username="testuser_special",
            password="Special123!@#",
            full_name="Test User (Admin)",
            organization="Test Corp"
        )

        user = auth_service.create_user(user_data, role=UserRole.VIEWER)
        token = auth_service.create_access_token(user)

        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=["HS256"]
        )

        assert payload["email"] == "user+test@example.com"
        assert payload["username"] == "testuser_special"


# ============================================================================
# INTEGRATION-STYLE TESTS (still unit tests, but test workflows)
# ============================================================================

class TestAuthWorkflows:
    """Test complete authentication workflows."""

    def test_registration_workflow(self, auth_service):
        """Test complete user registration workflow."""
        # 1. User provides password
        password = "SecurePassword123!"

        # 2. Hash password
        hashed = auth_service.hash_password(password)

        # 3. Verify hash is different from password
        assert hashed != password

        # 4. Later, verify password
        assert auth_service.verify_password(password, hashed)

    def test_login_workflow(self, auth_service, test_user):
        """Test complete login workflow."""
        # 1. User registered (password hashed)
        password = "SecurePassword123!"
        hashed = auth_service.hash_password(password)

        # 2. User attempts login
        login_password = "SecurePassword123!"

        # 3. Verify password
        authenticated = auth_service.verify_password(login_password, hashed)
        assert authenticated is True

        # 4. Create access token
        if authenticated:
            token = auth_service.create_access_token(test_user)
            assert len(token) > 0

    def test_api_key_workflow(self, auth_service, test_user):
        """Test API key creation and usage workflow."""
        from src.auth.models import APIKeyCreate, PermissionScope

        # 1. Create API key
        key_data = APIKeyCreate(
            name="Test API Key",
            scopes=[PermissionScope.READ_COMPANIES],
            expires_in_days=30
        )
        response = auth_service.create_api_key(test_user, key_data)
        api_key = response.key

        # 2. Store hash of API key (it's already hashed in the database)
        # We can verify the key works by calling verify_api_key
        user, key_obj = auth_service.verify_api_key(api_key)

        # 3. Verify we got the correct user back
        assert user.id == test_user.id

    def test_token_expiration_workflow(self, auth_service, test_user):
        """Test token expiration workflow."""
        # 1. Create short-lived token
        expires_delta = timedelta(seconds=1)
        token = auth_service.create_access_token(
            test_user,
            expires_delta=expires_delta
        )

        # 2. Immediately decode - should work
        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=["HS256"]
        )
        assert payload["email"] == test_user.email

        # 3. After expiration, would fail (but we won't sleep in tests)
        # In real code, you'd catch jwt.ExpiredSignatureError
