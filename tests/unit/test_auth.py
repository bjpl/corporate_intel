"""
Unit Tests for Authentication Module

Tests password hashing, JWT tokens, permissions, and session management.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from jose import jwt, JWTError

from core.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
    has_permission,
    generate_api_key,
    hash_api_key
)
from core.config import get_settings
from models.user import UserRole
from core.exceptions import AuthenticationError, AuthorizationError


settings = get_settings()


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_password_hash_is_different_from_plain_text(self):
        """Test that hashed password differs from plain text."""
        password = "MySecurePassword123!"
        hashed = get_password_hash(password)

        assert hashed != password
        assert len(hashed) > 0

    def test_same_password_produces_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "MySecurePassword123!"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        assert hash1 != hash2

    def test_verify_correct_password(self):
        """Test verification of correct password."""
        password = "MySecurePassword123!"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Test verification fails for incorrect password."""
        password = "MySecurePassword123!"
        wrong_password = "WrongPassword456!"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_empty_password_handling(self):
        """Test handling of empty passwords."""
        with pytest.raises(ValueError):
            get_password_hash("")

    def test_very_long_password(self):
        """Test handling of very long passwords."""
        long_password = "A" * 1000
        hashed = get_password_hash(long_password)

        assert verify_password(long_password, hashed) is True

    def test_unicode_password(self):
        """Test handling of unicode characters in passwords."""
        unicode_password = "Pass123!@#$%äöüñ中文"
        hashed = get_password_hash(unicode_password)

        assert verify_password(unicode_password, hashed) is True


class TestJWTTokenGeneration:
    """Test JWT token creation and validation."""

    def test_create_access_token_with_user_id(self):
        """Test creating access token with user ID."""
        user_id = 123
        token = create_access_token(
            data={"sub": str(user_id)},
            expires_delta=timedelta(minutes=30)
        )

        assert isinstance(token, str)
        assert len(token) > 0

        # Decode and verify
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        assert payload["sub"] == str(user_id)
        assert "exp" in payload

    def test_create_access_token_with_custom_data(self):
        """Test creating token with custom claims."""
        data = {
            "sub": "user123",
            "email": "test@example.com",
            "role": "admin"
        }
        token = create_access_token(data)

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "admin"

    def test_create_access_token_default_expiration(self):
        """Test token uses default expiration when not specified."""
        token = create_access_token(data={"sub": "123"})

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        exp_time = datetime.fromtimestamp(payload["exp"])
        now = datetime.utcnow()
        time_diff = (exp_time - now).total_seconds() / 60

        # Should be close to default (15 minutes)
        assert 14 <= time_diff <= 16

    def test_create_access_token_custom_expiration(self):
        """Test token with custom expiration time."""
        expires_delta = timedelta(hours=2)
        token = create_access_token(
            data={"sub": "123"},
            expires_delta=expires_delta
        )

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        exp_time = datetime.fromtimestamp(payload["exp"])
        now = datetime.utcnow()
        time_diff = (exp_time - now).total_seconds() / 3600

        # Should be close to 2 hours
        assert 1.9 <= time_diff <= 2.1

    def test_create_refresh_token(self):
        """Test creating refresh token."""
        user_id = 123
        token = create_refresh_token(data={"sub": str(user_id)})

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        assert payload["sub"] == str(user_id)

        # Refresh token should have longer expiration
        exp_time = datetime.fromtimestamp(payload["exp"])
        now = datetime.utcnow()
        time_diff = (exp_time - now).total_seconds() / 86400  # days

        assert time_diff >= 6  # At least 6 days


class TestTokenVerification:
    """Test JWT token verification."""

    def test_verify_valid_token(self):
        """Test verification of valid token."""
        data = {"sub": "123", "email": "test@example.com"}
        token = create_access_token(data)

        payload = verify_token(token)

        assert payload["sub"] == "123"
        assert payload["email"] == "test@example.com"

    def test_verify_expired_token(self):
        """Test verification fails for expired token."""
        data = {"sub": "123"}
        token = create_access_token(
            data,
            expires_delta=timedelta(seconds=-1)  # Already expired
        )

        with pytest.raises(AuthenticationError) as exc_info:
            verify_token(token)

        assert "expired" in str(exc_info.value).lower()

    def test_verify_invalid_signature(self):
        """Test verification fails for invalid signature."""
        # Create token with wrong secret
        data = {"sub": "123"}
        token = jwt.encode(
            {**data, "exp": datetime.utcnow() + timedelta(minutes=30)},
            "wrong-secret-key",
            algorithm=settings.ALGORITHM
        )

        with pytest.raises(AuthenticationError):
            verify_token(token)

    def test_verify_malformed_token(self):
        """Test verification fails for malformed token."""
        with pytest.raises(AuthenticationError):
            verify_token("not.a.valid.jwt.token")

    def test_verify_empty_token(self):
        """Test verification fails for empty token."""
        with pytest.raises(AuthenticationError):
            verify_token("")

    def test_verify_token_missing_required_claims(self):
        """Test verification fails when required claims are missing."""
        # Token without 'sub' claim
        token = jwt.encode(
            {"email": "test@example.com", "exp": datetime.utcnow() + timedelta(minutes=30)},
            settings.SECRET_KEY,
            algorithm=settings.ALGORITHM
        )

        with pytest.raises(AuthenticationError):
            verify_token(token)


class TestPermissionChecking:
    """Test permission and authorization logic."""

    def test_admin_has_all_permissions(self):
        """Test admin role has all permissions."""
        assert has_permission(UserRole.ADMIN, "read") is True
        assert has_permission(UserRole.ADMIN, "write") is True
        assert has_permission(UserRole.ADMIN, "delete") is True
        assert has_permission(UserRole.ADMIN, "admin") is True

    def test_analyst_has_read_write_permissions(self):
        """Test analyst role has read and write permissions."""
        assert has_permission(UserRole.ANALYST, "read") is True
        assert has_permission(UserRole.ANALYST, "write") is True
        assert has_permission(UserRole.ANALYST, "delete") is False
        assert has_permission(UserRole.ANALYST, "admin") is False

    def test_viewer_has_only_read_permission(self):
        """Test viewer role has only read permission."""
        assert has_permission(UserRole.VIEWER, "read") is True
        assert has_permission(UserRole.VIEWER, "write") is False
        assert has_permission(UserRole.VIEWER, "delete") is False
        assert has_permission(UserRole.VIEWER, "admin") is False

    def test_invalid_permission_raises_error(self):
        """Test that invalid permission raises error."""
        with pytest.raises(ValueError):
            has_permission(UserRole.VIEWER, "invalid_permission")

    def test_permission_hierarchy(self):
        """Test permission hierarchy is respected."""
        # Admin > Analyst > Viewer
        admin_perms = sum([
            has_permission(UserRole.ADMIN, p)
            for p in ["read", "write", "delete", "admin"]
        ])
        analyst_perms = sum([
            has_permission(UserRole.ANALYST, p)
            for p in ["read", "write", "delete", "admin"]
        ])
        viewer_perms = sum([
            has_permission(UserRole.VIEWER, p)
            for p in ["read", "write", "delete", "admin"]
        ])

        assert admin_perms > analyst_perms > viewer_perms


class TestAPIKeyGeneration:
    """Test API key generation and hashing."""

    def test_generate_api_key_format(self):
        """Test generated API key has correct format."""
        api_key = generate_api_key()

        # Should be a string
        assert isinstance(api_key, str)

        # Should have reasonable length (typically 32+ chars)
        assert len(api_key) >= 32

        # Should be alphanumeric
        assert api_key.isalnum()

    def test_generate_unique_api_keys(self):
        """Test that generated API keys are unique."""
        keys = [generate_api_key() for _ in range(100)]

        # All keys should be unique
        assert len(keys) == len(set(keys))

    def test_hash_api_key(self):
        """Test API key hashing."""
        api_key = generate_api_key()
        hashed = hash_api_key(api_key)

        # Hash should be different from original
        assert hashed != api_key

        # Hash should be consistent
        assert hash_api_key(api_key) == hashed

    def test_api_key_hash_is_deterministic(self):
        """Test that same API key produces same hash."""
        api_key = "test_api_key_12345"
        hash1 = hash_api_key(api_key)
        hash2 = hash_api_key(api_key)

        assert hash1 == hash2

    def test_different_api_keys_produce_different_hashes(self):
        """Test that different API keys produce different hashes."""
        key1 = generate_api_key()
        key2 = generate_api_key()

        hash1 = hash_api_key(key1)
        hash2 = hash_api_key(key2)

        assert hash1 != hash2


class TestSessionManagement:
    """Test session management and token lifecycle."""

    def test_token_contains_expiration(self):
        """Test that tokens contain expiration claim."""
        token = create_access_token(data={"sub": "123"})
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        assert "exp" in payload
        assert isinstance(payload["exp"], int)

    def test_token_expiration_time_calculation(self):
        """Test token expiration time is calculated correctly."""
        minutes = 30
        expires_delta = timedelta(minutes=minutes)
        token = create_access_token(
            data={"sub": "123"},
            expires_delta=expires_delta
        )

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        exp_time = datetime.fromtimestamp(payload["exp"])
        expected_exp = datetime.utcnow() + expires_delta

        # Allow 5 second tolerance for test execution time
        time_diff = abs((exp_time - expected_exp).total_seconds())
        assert time_diff < 5

    def test_refresh_token_longer_expiration(self):
        """Test refresh token has longer expiration than access token."""
        access_token = create_access_token(data={"sub": "123"})
        refresh_token = create_refresh_token(data={"sub": "123"})

        access_payload = jwt.decode(
            access_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        refresh_payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )

        assert refresh_payload["exp"] > access_payload["exp"]


class TestSecurityEdgeCases:
    """Test security edge cases and attack scenarios."""

    def test_sql_injection_in_password(self):
        """Test SQL injection attempts in password are safely handled."""
        malicious_password = "' OR '1'='1'; DROP TABLE users; --"
        hashed = get_password_hash(malicious_password)

        # Should hash successfully without executing SQL
        assert verify_password(malicious_password, hashed) is True

    def test_xss_in_token_data(self):
        """Test XSS attempts in token data are safely encoded."""
        xss_data = {
            "sub": "123",
            "email": "<script>alert('XSS')</script>@example.com"
        }
        token = create_access_token(data=xss_data)

        # Should create token and preserve data as-is (encoding happens at render time)
        payload = verify_token(token)
        assert payload["email"] == xss_data["email"]

    def test_token_tampering_detection(self):
        """Test that tampered tokens are rejected."""
        token = create_access_token(data={"sub": "123", "role": "viewer"})

        # Tamper with token by changing role
        parts = token.split(".")
        # Decode payload, modify, re-encode
        import base64
        import json

        payload = json.loads(
            base64.urlsafe_b64decode(parts[1] + "=" * (4 - len(parts[1]) % 4))
        )
        payload["role"] = "admin"  # Escalate privileges

        tampered_payload = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip("=")

        tampered_token = f"{parts[0]}.{tampered_payload}.{parts[2]}"

        # Should fail verification due to invalid signature
        with pytest.raises(AuthenticationError):
            verify_token(tampered_token)

    def test_null_byte_in_password(self):
        """Test null bytes in passwords are handled correctly."""
        password_with_null = "password\x00injection"
        hashed = get_password_hash(password_with_null)

        assert verify_password(password_with_null, hashed) is True

    def test_timing_attack_resistance(self):
        """Test password verification is resistant to timing attacks."""
        import time

        password = "SecurePassword123!"
        hashed = get_password_hash(password)

        # Time correct password verification
        start = time.perf_counter()
        verify_password(password, hashed)
        correct_time = time.perf_counter() - start

        # Time incorrect password verification
        start = time.perf_counter()
        verify_password("WrongPassword", hashed)
        incorrect_time = time.perf_counter() - start

        # Times should be similar (within 50% to account for system variance)
        # This is a basic check; real timing attack tests need more samples
        time_ratio = max(correct_time, incorrect_time) / min(correct_time, incorrect_time)
        assert time_ratio < 2.0  # Shouldn't differ by more than 2x
