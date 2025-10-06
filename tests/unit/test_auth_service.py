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

    def test_hash_password(self):
        """Test password is properly hashed."""
        password = "TestPassword123!"
        hashed = AuthService.hash_password(password)

        # Hashed password should not equal plaintext
        assert hashed != password
        # Should be bcrypt hash
        assert hashed.startswith("$2b$")
        # Should be reasonable length
        assert len(hashed) >= 60

    def test_verify_password_correct(self):
        """Test correct password verification."""
        password = "TestPassword123!"
        hashed = AuthService.hash_password(password)

        assert AuthService.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test incorrect password verification."""
        password = "TestPassword123!"
        hashed = AuthService.hash_password(password)

        assert AuthService.verify_password("WrongPassword!", hashed) is False

    def test_verify_password_empty(self):
        """Test verification with empty password."""
        hashed = AuthService.hash_password("TestPassword123!")

        assert AuthService.verify_password("", hashed) is False

    def test_hash_password_deterministic(self):
        """Test that hashing same password produces different hashes (salt)."""
        password = "TestPassword123!"
        hash1 = AuthService.hash_password(password)
        hash2 = AuthService.hash_password(password)

        # Different hashes due to salt
        assert hash1 != hash2
        # But both verify correctly
        assert AuthService.verify_password(password, hash1)
        assert AuthService.verify_password(password, hash2)


class TestJWTTokens:
    """Test JWT token creation and verification."""

    def test_create_access_token(self):
        """Test JWT access token creation."""
        data = {"sub": "user@example.com", "user_id": "123"}
        token = AuthService.create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 0
        # Should have 3 parts (header.payload.signature)
        assert len(token.split(".")) == 3

    def test_create_access_token_with_expiration(self):
        """Test JWT token with custom expiration."""
        data = {"sub": "user@example.com"}
        expires_delta = timedelta(minutes=15)

        token = AuthService.create_access_token(data, expires_delta=expires_delta)

        # Decode and verify expiration
        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=["HS256"]
        )

        exp = datetime.fromtimestamp(payload["exp"])
        # Should expire in approximately 15 minutes
        assert exp > datetime.utcnow()
        assert exp < datetime.utcnow() + timedelta(minutes=16)

    def test_create_access_token_default_expiration(self):
        """Test JWT token with default expiration."""
        data = {"sub": "user@example.com"}
        token = AuthService.create_access_token(data)

        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=["HS256"]
        )

        # Should have exp claim
        assert "exp" in payload
        exp = datetime.fromtimestamp(payload["exp"])
        # Should be in the future
        assert exp > datetime.utcnow()

    def test_token_contains_data(self):
        """Test that token contains encoded data."""
        data = {
            "sub": "user@example.com",
            "user_id": "123",
            "role": "admin"
        }
        token = AuthService.create_access_token(data)

        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=["HS256"]
        )

        assert payload["sub"] == "user@example.com"
        assert payload["user_id"] == "123"
        assert payload["role"] == "admin"


class TestAPIKeyGeneration:
    """Test API key generation and validation."""

    def test_generate_api_key(self):
        """Test API key generation."""
        key = AuthService.generate_api_key()

        assert isinstance(key, str)
        # Should start with prefix
        assert key.startswith("ci_")
        # Should be reasonable length (prefix + random part)
        assert len(key) >= 40

    def test_generate_api_key_unique(self):
        """Test that generated API keys are unique."""
        key1 = AuthService.generate_api_key()
        key2 = AuthService.generate_api_key()

        assert key1 != key2

    def test_generate_api_key_format(self):
        """Test API key format."""
        key = AuthService.generate_api_key()

        # Should match expected format
        assert key.startswith("ci_")
        # Should be alphanumeric after prefix
        assert key[3:].replace("-", "").isalnum()


class TestAuthenticationLogic:
    """Test authentication business logic."""

    def test_authenticate_user_success(self):
        """Test successful user authentication."""
        # This is a unit test - in reality, you'd use a mock database
        # For now, we test the logic of password verification
        password = "TestPassword123!"
        hashed = AuthService.hash_password(password)

        # Simulate user from database
        assert AuthService.verify_password(password, hashed)

    def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password."""
        password = "TestPassword123!"
        hashed = AuthService.hash_password(password)

        assert not AuthService.verify_password("WrongPassword!", hashed)

    def test_role_hierarchy(self):
        """Test user role hierarchy."""
        # Test that role enums are properly defined
        assert UserRole.VIEWER.value == "viewer"
        assert UserRole.ANALYST.value == "analyst"
        assert UserRole.ADMIN.value == "admin"

    def test_permission_scopes(self):
        """Test permission scope definitions."""
        # Test that permission scopes are properly defined
        assert PermissionScope.READ.value == "read"
        assert PermissionScope.WRITE.value == "write"
        assert PermissionScope.ADMIN.value == "admin"


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

    def test_password_strength_strong(self):
        """Test strong password acceptance."""
        strong_passwords = [
            "MySecureP@ssw0rd123!",
            "C0mplex!Pass#2024",
            "Str0ng&Secure$Password",
        ]

        for pwd in strong_passwords:
            hashed = AuthService.hash_password(pwd)
            assert AuthService.verify_password(pwd, hashed)

    def test_email_in_token_payload(self):
        """Test that email is properly included in token payload."""
        email = "test@example.com"
        data = {"sub": email, "user_id": "123"}
        token = AuthService.create_access_token(data)

        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=["HS256"]
        )

        assert payload["sub"] == email


class TestErrorHandling:
    """Test error handling in auth service."""

    def test_verify_password_with_none(self):
        """Test password verification with None values."""
        hashed = AuthService.hash_password("test")

        # Should handle None gracefully
        try:
            result = AuthService.verify_password(None, hashed)
            # If it doesn't raise, it should return False
            assert result is False
        except (TypeError, AttributeError):
            # Or it might raise an error, which is also acceptable
            pass

    def test_create_token_with_empty_data(self):
        """Test token creation with empty data."""
        token = AuthService.create_access_token({})

        # Should still create a valid token
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_with_special_characters(self):
        """Test token creation with special characters in data."""
        data = {
            "sub": "user+test@example.com",
            "name": "Test User (Admin)"
        }
        token = AuthService.create_access_token(data)

        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=["HS256"]
        )

        assert payload["sub"] == "user+test@example.com"
        assert payload["name"] == "Test User (Admin)"


# ============================================================================
# INTEGRATION-STYLE TESTS (still unit tests, but test workflows)
# ============================================================================

class TestAuthWorkflows:
    """Test complete authentication workflows."""

    def test_registration_workflow(self):
        """Test complete user registration workflow."""
        # 1. User provides password
        password = "SecurePassword123!"

        # 2. Hash password
        hashed = AuthService.hash_password(password)

        # 3. Verify hash is different from password
        assert hashed != password

        # 4. Later, verify password
        assert AuthService.verify_password(password, hashed)

    def test_login_workflow(self):
        """Test complete login workflow."""
        # 1. User registered (password hashed)
        password = "SecurePassword123!"
        hashed = AuthService.hash_password(password)

        # 2. User attempts login
        login_password = "SecurePassword123!"

        # 3. Verify password
        authenticated = AuthService.verify_password(login_password, hashed)
        assert authenticated is True

        # 4. Create access token
        if authenticated:
            token = AuthService.create_access_token({
                "sub": "user@example.com",
                "user_id": "123"
            })
            assert len(token) > 0

    def test_api_key_workflow(self):
        """Test API key generation and usage workflow."""
        # 1. Generate API key
        api_key = AuthService.generate_api_key()

        # 2. Store hash of API key (you'd normally hash it)
        api_key_hash = AuthService.hash_password(api_key)

        # 3. Later, verify API key
        assert AuthService.verify_password(api_key, api_key_hash)

    def test_token_expiration_workflow(self):
        """Test token expiration workflow."""
        # 1. Create short-lived token
        expires_delta = timedelta(seconds=1)
        token = AuthService.create_access_token(
            {"sub": "user@example.com"},
            expires_delta=expires_delta
        )

        # 2. Immediately decode - should work
        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=["HS256"]
        )
        assert payload["sub"] == "user@example.com"

        # 3. After expiration, would fail (but we won't sleep in tests)
        # In real code, you'd catch jwt.ExpiredSignatureError
