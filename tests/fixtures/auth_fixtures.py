"""
Authentication Test Fixtures

Provides reusable fixtures for authentication testing including users,
tokens, and mock dependencies.
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, List
from unittest.mock import Mock, AsyncMock
from jose import jwt

from models.user import User, UserRole, APIKey
from core.auth import get_password_hash, create_access_token, create_refresh_token
from core.config import get_settings

settings = get_settings()


# User Fixtures
@pytest.fixture
def test_users_data() -> List[Dict]:
    """Provide test user data for bulk creation."""
    return [
        {
            "email": "admin1@example.com",
            "username": "admin1",
            "role": UserRole.ADMIN,
            "is_active": True,
            "is_verified": True
        },
        {
            "email": "admin2@example.com",
            "username": "admin2",
            "role": UserRole.ADMIN,
            "is_active": True,
            "is_verified": True
        },
        {
            "email": "analyst1@example.com",
            "username": "analyst1",
            "role": UserRole.ANALYST,
            "is_active": True,
            "is_verified": True
        },
        {
            "email": "analyst2@example.com",
            "username": "analyst2",
            "role": UserRole.ANALYST,
            "is_active": True,
            "is_verified": True
        },
        {
            "email": "viewer1@example.com",
            "username": "viewer1",
            "role": UserRole.VIEWER,
            "is_active": True,
            "is_verified": True
        },
        {
            "email": "viewer2@example.com",
            "username": "viewer2",
            "role": UserRole.VIEWER,
            "is_active": True,
            "is_verified": True
        }
    ]


@pytest.fixture
def bulk_test_users(db_session, hashed_password, test_users_data):
    """Create multiple test users for bulk operations testing."""
    users = []
    for user_data in test_users_data:
        user = User(
            email=user_data["email"],
            username=user_data["username"],
            hashed_password=hashed_password,
            role=user_data["role"],
            is_active=user_data["is_active"],
            is_verified=user_data["is_verified"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(user)
        users.append(user)

    db_session.commit()
    for user in users:
        db_session.refresh(user)

    return users


# Token Fixtures
@pytest.fixture
def token_payload_admin() -> Dict:
    """Standard admin token payload."""
    return {
        "sub": "1",
        "email": "admin@example.com",
        "role": UserRole.ADMIN.value,
        "username": "admin"
    }


@pytest.fixture
def token_payload_analyst() -> Dict:
    """Standard analyst token payload."""
    return {
        "sub": "2",
        "email": "analyst@example.com",
        "role": UserRole.ANALYST.value,
        "username": "analyst"
    }


@pytest.fixture
def token_payload_viewer() -> Dict:
    """Standard viewer token payload."""
    return {
        "sub": "3",
        "email": "viewer@example.com",
        "role": UserRole.VIEWER.value,
        "username": "viewer"
    }


@pytest.fixture
def custom_token(token_payload_admin):
    """Factory for creating custom tokens."""
    def _create_token(
        payload: Dict = None,
        expires_delta: timedelta = None,
        secret: str = None
    ) -> str:
        """Create a custom token with specified parameters."""
        if payload is None:
            payload = token_payload_admin.copy()

        if expires_delta is None:
            expires_delta = timedelta(minutes=30)

        if secret is None:
            secret = settings.SECRET_KEY

        expire = datetime.utcnow() + expires_delta
        to_encode = {**payload, "exp": expire}

        return jwt.encode(to_encode, secret, algorithm=settings.ALGORITHM)

    return _create_token


@pytest.fixture
def malformed_tokens() -> List[str]:
    """Collection of malformed tokens for testing."""
    return [
        "",  # Empty
        "not.a.token",  # Invalid format
        "invalid",  # Single part
        "two.parts",  # Two parts
        "header.payload.signature.extra",  # Four parts
        "header..signature",  # Empty payload
        ".payload.signature",  # Empty header
        "header.payload.",  # Empty signature
    ]


# API Key Fixtures
@pytest.fixture
def test_api_key(admin_user, db_session):
    """Create a test API key."""
    from core.auth import generate_api_key, hash_api_key

    key_value = generate_api_key()
    api_key = APIKey(
        user_id=admin_user.id,
        key_hash=hash_api_key(key_value),
        name="Test API Key",
        is_active=True,
        created_at=datetime.utcnow(),
        last_used_at=None
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)

    # Return both the key object and the plain key value
    return {"api_key": api_key, "key_value": key_value}


@pytest.fixture
def expired_api_key(admin_user, db_session):
    """Create an expired API key."""
    from core.auth import generate_api_key, hash_api_key

    key_value = generate_api_key()
    api_key = APIKey(
        user_id=admin_user.id,
        key_hash=hash_api_key(key_value),
        name="Expired API Key",
        is_active=True,
        expires_at=datetime.utcnow() - timedelta(days=1),
        created_at=datetime.utcnow() - timedelta(days=30),
        last_used_at=None
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)

    return {"api_key": api_key, "key_value": key_value}


@pytest.fixture
def inactive_api_key(admin_user, db_session):
    """Create an inactive API key."""
    from core.auth import generate_api_key, hash_api_key

    key_value = generate_api_key()
    api_key = APIKey(
        user_id=admin_user.id,
        key_hash=hash_api_key(key_value),
        name="Inactive API Key",
        is_active=False,
        created_at=datetime.utcnow(),
        last_used_at=None
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)

    return {"api_key": api_key, "key_value": key_value}


# Mock Fixtures
@pytest.fixture
def mock_email_service():
    """Mock email service for testing."""
    mock = Mock()
    mock.send_verification_email = AsyncMock(return_value=True)
    mock.send_password_reset_email = AsyncMock(return_value=True)
    mock.send_welcome_email = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter for testing."""
    mock = Mock()
    mock.check_rate_limit = AsyncMock(return_value=True)
    mock.increment_counter = AsyncMock()
    mock.reset_counter = AsyncMock()
    return mock


@pytest.fixture
def mock_session_store():
    """Mock session store for testing."""
    mock = Mock()
    mock.create_session = AsyncMock(return_value="session-id-123")
    mock.get_session = AsyncMock(return_value={"user_id": 1})
    mock.delete_session = AsyncMock()
    mock.update_session = AsyncMock()
    return mock


# Auth Header Fixtures
@pytest.fixture
def auth_headers_factory(custom_token):
    """Factory for creating authorization headers."""
    def _create_headers(
        user_id: str = "1",
        role: str = UserRole.ADMIN.value,
        expires_delta: timedelta = None
    ) -> Dict[str, str]:
        """Create authorization headers with custom parameters."""
        payload = {
            "sub": user_id,
            "email": f"user{user_id}@example.com",
            "role": role
        }
        token = custom_token(payload=payload, expires_delta=expires_delta)
        return {"Authorization": f"Bearer {token}"}

    return _create_headers


@pytest.fixture
def invalid_auth_headers() -> List[Dict[str, str]]:
    """Collection of invalid authorization headers."""
    return [
        {},  # Missing header
        {"Authorization": ""},  # Empty value
        {"Authorization": "Bearer"},  # Missing token
        {"Authorization": "InvalidScheme token"},  # Wrong scheme
        {"Authorization": "Bearer invalid.token"},  # Invalid token
        {"Auth": "Bearer token"},  # Wrong header name
    ]


# Password Fixtures
@pytest.fixture
def weak_passwords() -> List[str]:
    """Collection of weak passwords for testing."""
    return [
        "123456",
        "password",
        "abc123",
        "qwerty",
        "pass",
        "12345678",
        "admin",
        "letmein",
        "welcome",
        "monkey"
    ]


@pytest.fixture
def strong_passwords() -> List[str]:
    """Collection of strong passwords for testing."""
    return [
        "P@ssw0rd123!Strong",
        "MySecure#Pass2024",
        "C0mpl3x$Password!",
        "Str0ng&P@ssw0rd#123",
        "S3cur3*Passphrase!2024"
    ]


# Permission Testing Fixtures
@pytest.fixture
def permission_test_cases():
    """Test cases for permission checking."""
    return [
        # (role, permission, expected_result)
        (UserRole.ADMIN, "read", True),
        (UserRole.ADMIN, "write", True),
        (UserRole.ADMIN, "delete", True),
        (UserRole.ADMIN, "admin", True),
        (UserRole.ANALYST, "read", True),
        (UserRole.ANALYST, "write", True),
        (UserRole.ANALYST, "delete", False),
        (UserRole.ANALYST, "admin", False),
        (UserRole.VIEWER, "read", True),
        (UserRole.VIEWER, "write", False),
        (UserRole.VIEWER, "delete", False),
        (UserRole.VIEWER, "admin", False),
    ]


# OAuth Fixtures (for future OAuth integration)
@pytest.fixture
def mock_oauth_provider():
    """Mock OAuth provider for testing."""
    mock = Mock()
    mock.authorize = AsyncMock(return_value={"code": "auth-code-123"})
    mock.get_token = AsyncMock(return_value={
        "access_token": "oauth-token-123",
        "refresh_token": "oauth-refresh-123",
        "expires_in": 3600
    })
    mock.get_user_info = AsyncMock(return_value={
        "email": "oauth-user@example.com",
        "name": "OAuth User",
        "sub": "oauth-user-id-123"
    })
    return mock


# Rate Limiting Fixtures
@pytest.fixture
def rate_limit_scenarios():
    """Scenarios for rate limiting tests."""
    return [
        {
            "name": "Login attempts",
            "endpoint": "/api/v1/auth/login",
            "limit": 5,
            "window": 300,  # 5 minutes
            "requests": 10  # Try 10 times
        },
        {
            "name": "Password reset requests",
            "endpoint": "/api/v1/auth/password-reset/request",
            "limit": 3,
            "window": 3600,  # 1 hour
            "requests": 5
        },
        {
            "name": "API key generation",
            "endpoint": "/api/v1/auth/api-keys",
            "limit": 10,
            "window": 86400,  # 24 hours
            "requests": 15
        }
    ]


# Session Management Fixtures
@pytest.fixture
def session_scenarios():
    """Test scenarios for session management."""
    return [
        {
            "name": "Short session",
            "duration": timedelta(minutes=15),
            "refresh_enabled": False
        },
        {
            "name": "Standard session",
            "duration": timedelta(hours=1),
            "refresh_enabled": True
        },
        {
            "name": "Extended session",
            "duration": timedelta(days=7),
            "refresh_enabled": True
        },
        {
            "name": "Permanent session",
            "duration": timedelta(days=30),
            "refresh_enabled": True
        }
    ]
