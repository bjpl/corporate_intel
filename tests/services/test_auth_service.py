"""Comprehensive tests for AuthService - JWT, API keys, permissions, rate limiting."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from src.auth.service import AuthService, AuthenticationError, AuthorizationError
from src.auth.models import (
    User, APIKey, UserSession, Permission,
    UserRole, PermissionScope, UserCreate, UserLogin, APIKeyCreate
)


@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = MagicMock(spec=Session)
    db.query.return_value.filter.return_value.first.return_value = None
    return db


@pytest.fixture
def auth_service(mock_db):
    """Create AuthService instance with mocked database."""
    return AuthService(mock_db)


@pytest.fixture
def sample_user():
    """Create sample user for testing."""
    user = User(
        id="test-uuid-123",
        email="test@example.com",
        username="testuser",
        hashed_password="$2b$12$hashedpassword",
        full_name="Test User",
        organization="Test Org",
        role=UserRole.VIEWER,
        is_active=True,
        api_calls_today=0,
        api_calls_reset_at=datetime.utcnow() + timedelta(days=1)
    )
    user.permissions = []
    return user


class TestPasswordUtilities:
    """Tests for password hashing and verification."""

    def test_hash_password(self, auth_service):
        """Test password hashing."""
        password = "secure_password_123"
        hashed = auth_service.hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2b$")
        assert len(hashed) > 50

    def test_verify_password_correct(self, auth_service):
        """Test password verification with correct password."""
        password = "secure_password_123"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self, auth_service):
        """Test password verification with incorrect password."""
        password = "secure_password_123"
        wrong_password = "wrong_password"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password(wrong_password, hashed) is False

    def test_different_passwords_different_hashes(self, auth_service):
        """Test that same password creates different hashes (salt)."""
        password = "secure_password_123"
        hash1 = auth_service.hash_password(password)
        hash2 = auth_service.hash_password(password)

        assert hash1 != hash2
        assert auth_service.verify_password(password, hash1)
        assert auth_service.verify_password(password, hash2)


class TestUserCreation:
    """Tests for user creation and management."""

    def test_create_user_success(self, auth_service, mock_db):
        """Test successful user creation."""
        # Mock no existing user
        mock_db.query.return_value.filter.return_value.first.return_value = None

        user_data = UserCreate(
            email="newuser@example.com",
            username="newuser",
            password="secure_password_123",
            full_name="New User",
            organization="Test Org"
        )

        # Mock user creation
        created_user = User(
            id="new-uuid",
            email=user_data.email,
            username=user_data.username,
            hashed_password="hashed",
            full_name=user_data.full_name,
            organization=user_data.organization,
            role=UserRole.VIEWER
        )
        created_user.permissions = []

        mock_db.add = MagicMock()
        mock_db.commit = MagicMock()
        mock_db.refresh = MagicMock(side_effect=lambda u: setattr(u, 'id', 'new-uuid'))

        with patch.object(auth_service, '_assign_role_permissions'):
            # Execute
            result = auth_service.create_user(user_data)

            # Verify
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called()

    def test_create_user_duplicate_email(self, auth_service, mock_db):
        """Test user creation fails with duplicate email."""
        # Mock existing user with same email
        existing_user = User(
            email="existing@example.com",
            username="other_user"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user

        user_data = UserCreate(
            email="existing@example.com",
            username="newuser",
            password="password",
            full_name="Test"
        )

        with pytest.raises(ValueError, match="Email already registered"):
            auth_service.create_user(user_data)

    def test_create_user_duplicate_username(self, auth_service, mock_db):
        """Test user creation fails with duplicate username."""
        existing_user = User(
            email="other@example.com",
            username="existinguser"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = existing_user

        user_data = UserCreate(
            email="new@example.com",
            username="existinguser",
            password="password",
            full_name="Test"
        )

        with pytest.raises(ValueError, match="Username already taken"):
            auth_service.create_user(user_data)

    def test_assign_role_permissions_viewer(self, auth_service, mock_db, sample_user):
        """Test that viewer role gets appropriate permissions."""
        sample_user.role = UserRole.VIEWER

        # Mock permission query
        mock_permission = Permission(
            scope=PermissionScope.READ_COMPANIES.value,
            description="Read companies"
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_permission

        auth_service._assign_role_permissions(sample_user)

        assert mock_db.commit.called


class TestAuthentication:
    """Tests for user authentication."""

    def test_authenticate_user_success(self, auth_service, mock_db, sample_user):
        """Test successful user authentication."""
        # Mock user lookup
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        login_data = UserLogin(
            username="testuser",
            password="correct_password"
        )

        # Mock password verification
        with patch.object(auth_service, 'verify_password', return_value=True):
            result = auth_service.authenticate_user(login_data)

            assert result == sample_user
            assert sample_user.last_login_at is not None
            mock_db.commit.assert_called_once()

    def test_authenticate_user_not_found(self, auth_service, mock_db):
        """Test authentication fails with non-existent user."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        login_data = UserLogin(username="nonexistent", password="password")

        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            auth_service.authenticate_user(login_data)

    def test_authenticate_user_wrong_password(self, auth_service, mock_db, sample_user):
        """Test authentication fails with wrong password."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        login_data = UserLogin(username="testuser", password="wrong_password")

        with patch.object(auth_service, 'verify_password', return_value=False):
            with pytest.raises(AuthenticationError, match="Invalid credentials"):
                auth_service.authenticate_user(login_data)

    def test_authenticate_user_inactive(self, auth_service, mock_db, sample_user):
        """Test authentication fails for inactive user."""
        sample_user.is_active = False
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        login_data = UserLogin(username="testuser", password="password")

        with patch.object(auth_service, 'verify_password', return_value=True):
            with pytest.raises(AuthenticationError, match="Account is disabled"):
                auth_service.authenticate_user(login_data)

    def test_authenticate_with_email(self, auth_service, mock_db, sample_user):
        """Test authentication works with email instead of username."""
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        login_data = UserLogin(username="test@example.com", password="password")

        with patch.object(auth_service, 'verify_password', return_value=True):
            result = auth_service.authenticate_user(login_data)
            assert result == sample_user


class TestJWTTokens:
    """Tests for JWT token management."""

    def test_create_access_token(self, auth_service, mock_db, sample_user):
        """Test access token creation."""
        token = auth_service.create_access_token(sample_user)

        assert isinstance(token, str)
        assert len(token) > 100
        assert mock_db.add.called
        assert mock_db.commit.called

    def test_create_access_token_custom_expiry(self, auth_service, mock_db, sample_user):
        """Test access token with custom expiry."""
        custom_delta = timedelta(minutes=30)
        token = auth_service.create_access_token(sample_user, expires_delta=custom_delta)

        assert isinstance(token, str)

    def test_create_refresh_token(self, auth_service, sample_user):
        """Test refresh token creation."""
        token = auth_service.create_refresh_token(sample_user)

        assert isinstance(token, str)
        assert len(token) > 100

    def test_create_tokens(self, auth_service, mock_db, sample_user):
        """Test creating both access and refresh tokens."""
        tokens = auth_service.create_tokens(sample_user)

        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.expires_in > 0

    def test_verify_token_valid(self, auth_service, mock_db, sample_user):
        """Test verifying valid access token."""
        # Create token first
        token = auth_service.create_access_token(sample_user)

        # Mock active session
        mock_session = UserSession(
            user_id=sample_user.id,
            token_jti="some-jti",
            is_active=True
        )
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        # Verify
        payload = auth_service.verify_token(token)

        assert payload["sub"] == str(sample_user.id)
        assert payload["type"] == "access"

    def test_verify_token_wrong_type(self, auth_service, mock_db, sample_user):
        """Test verifying token with wrong type."""
        refresh_token = auth_service.create_refresh_token(sample_user)

        with pytest.raises(AuthenticationError, match="Invalid token type"):
            auth_service.verify_token(refresh_token, token_type="access")

    def test_verify_token_session_inactive(self, auth_service, mock_db, sample_user):
        """Test verifying token with inactive session."""
        token = auth_service.create_access_token(sample_user)

        # Mock inactive session
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(AuthenticationError, match="Session expired or revoked"):
            auth_service.verify_token(token)

    def test_get_current_user(self, auth_service, mock_db, sample_user):
        """Test getting current user from token."""
        token = auth_service.create_access_token(sample_user)

        # Mock session and user lookup
        mock_session = UserSession(user_id=sample_user.id, is_active=True)
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_session,  # For session lookup
            sample_user     # For user lookup
        ]

        with patch.object(auth_service, 'verify_token', return_value={"sub": sample_user.id}):
            result = auth_service.get_current_user(token)
            assert result == sample_user

    def test_refresh_access_token(self, auth_service, mock_db, sample_user):
        """Test refreshing access token."""
        refresh_token = auth_service.create_refresh_token(sample_user)

        # Mock user lookup
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user

        with patch.object(auth_service, 'verify_token', return_value={"sub": sample_user.id}):
            new_tokens = auth_service.refresh_access_token(refresh_token)

            assert new_tokens.access_token is not None
            assert new_tokens.refresh_token is not None

    def test_revoke_token(self, auth_service, mock_db, sample_user):
        """Test token revocation (logout)."""
        token = auth_service.create_access_token(sample_user)

        # Mock session lookup
        mock_session = UserSession(token_jti="test-jti", is_active=True)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_session

        with patch.object(auth_service, 'verify_token', return_value={"jti": "test-jti"}):
            auth_service.revoke_token(token)

            assert mock_session.is_active is False
            assert mock_session.revoked_at is not None


class TestAPIKeys:
    """Tests for API key management."""

    def test_create_api_key(self, auth_service, mock_db, sample_user):
        """Test creating API key."""
        key_data = APIKeyCreate(
            name="Test API Key",
            scopes=[PermissionScope.READ_COMPANIES],
            expires_in_days=30
        )

        # Mock API key creation
        with patch.object(APIKey, 'generate_key', return_value=("ci_test_key_123", "hash123")):
            response = auth_service.create_api_key(sample_user, key_data)

            assert response.name == "Test API Key"
            assert response.key.startswith("ci_")
            assert PermissionScope.READ_COMPANIES.value in response.scopes
            mock_db.add.assert_called_once()

    def test_create_api_key_no_expiry(self, auth_service, mock_db, sample_user):
        """Test creating API key without expiry."""
        key_data = APIKeyCreate(
            name="Permanent Key",
            scopes=[PermissionScope.READ_COMPANIES]
        )

        with patch.object(APIKey, 'generate_key', return_value=("ci_key", "hash")):
            response = auth_service.create_api_key(sample_user, key_data)

            assert response.expires_at is None

    def test_verify_api_key_success(self, auth_service, mock_db, sample_user):
        """Test verifying valid API key."""
        # Mock API key lookup
        api_key = APIKey(
            id="key-uuid",
            user_id=sample_user.id,
            name="Test Key",
            key_hash="correct_hash",
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        api_key.user = sample_user

        mock_db.query.return_value.filter.return_value.first.return_value = api_key

        with patch('hashlib.sha256') as mock_sha:
            mock_sha.return_value.hexdigest.return_value = "correct_hash"

            user, key = auth_service.verify_api_key("ci_test_key")

            assert user == sample_user
            assert key == api_key
            assert api_key.last_used_at is not None

    def test_verify_api_key_invalid(self, auth_service, mock_db):
        """Test verifying invalid API key."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(AuthenticationError, match="Invalid API key"):
            auth_service.verify_api_key("ci_invalid_key")

    def test_verify_api_key_expired(self, auth_service, mock_db, sample_user):
        """Test verifying expired API key."""
        api_key = APIKey(
            user_id=sample_user.id,
            key_hash="hash",
            is_active=True,
            expires_at=datetime.utcnow() - timedelta(days=1)  # Expired
        )
        api_key.user = sample_user

        mock_db.query.return_value.filter.return_value.first.return_value = api_key

        with patch('hashlib.sha256') as mock_sha:
            mock_sha.return_value.hexdigest.return_value = "hash"

            with pytest.raises(AuthenticationError, match="API key expired"):
                auth_service.verify_api_key("ci_key")

    def test_verify_api_key_inactive_user(self, auth_service, mock_db, sample_user):
        """Test verifying API key with inactive user."""
        sample_user.is_active = False
        api_key = APIKey(
            user_id=sample_user.id,
            key_hash="hash",
            is_active=True,
            expires_at=None
        )
        api_key.user = sample_user

        mock_db.query.return_value.filter.return_value.first.return_value = api_key

        with patch('hashlib.sha256') as mock_sha:
            mock_sha.return_value.hexdigest.return_value = "hash"

            with pytest.raises(AuthenticationError, match="User account is inactive"):
                auth_service.verify_api_key("ci_key")

    def test_revoke_api_key(self, auth_service, mock_db, sample_user):
        """Test revoking API key."""
        api_key = APIKey(
            id="key-uuid",
            user_id=sample_user.id,
            is_active=True
        )

        mock_db.query.return_value.filter.return_value.first.return_value = api_key

        auth_service.revoke_api_key(sample_user, "key-uuid")

        assert api_key.is_active is False
        assert api_key.revoked_at is not None

    def test_revoke_api_key_not_found(self, auth_service, mock_db, sample_user):
        """Test revoking non-existent API key."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ValueError, match="API key not found"):
            auth_service.revoke_api_key(sample_user, "nonexistent")


class TestAuthorization:
    """Tests for permission checking and authorization."""

    def test_check_permission_has_permission(self, auth_service, sample_user):
        """Test checking permission when user has it."""
        with patch.object(sample_user, 'has_permission', return_value=True):
            result = auth_service.check_permission(sample_user, PermissionScope.READ_COMPANIES)
            assert result is True

    def test_check_permission_no_permission(self, auth_service, sample_user):
        """Test checking permission when user lacks it."""
        with patch.object(sample_user, 'has_permission', return_value=False):
            result = auth_service.check_permission(sample_user, PermissionScope.WRITE_COMPANIES)
            assert result is False

    def test_require_permission_success(self, auth_service, sample_user):
        """Test requiring permission when user has it."""
        with patch.object(sample_user, 'has_permission', return_value=True):
            # Should not raise
            auth_service.require_permission(sample_user, PermissionScope.READ_COMPANIES)

    def test_require_permission_fails(self, auth_service, sample_user):
        """Test requiring permission when user lacks it."""
        with patch.object(sample_user, 'has_permission', return_value=False):
            with pytest.raises(AuthorizationError, match="Missing permission"):
                auth_service.require_permission(sample_user, PermissionScope.WRITE_COMPANIES)


class TestRateLimiting:
    """Tests for rate limiting functionality."""

    def test_check_rate_limit_allowed(self, auth_service, mock_db, sample_user):
        """Test rate limit check when under limit."""
        with patch.object(sample_user, 'get_rate_limit', return_value=(50, 100)):
            is_allowed, used, limit = auth_service.check_rate_limit(sample_user)

            assert is_allowed is True
            assert used == 51
            assert limit == 100
            assert sample_user.api_calls_today == 1

    def test_check_rate_limit_exceeded(self, auth_service, mock_db, sample_user):
        """Test rate limit check when limit exceeded."""
        with patch.object(sample_user, 'get_rate_limit', return_value=(100, 100)):
            is_allowed, used, limit = auth_service.check_rate_limit(sample_user)

            assert is_allowed is False
            assert used == 100
            assert limit == 100

    @pytest.mark.asyncio
    async def test_check_api_key_rate_limit_allowed(self, auth_service):
        """Test API key rate limit when under limit."""
        api_key = APIKey(id="key-uuid", rate_limit_per_hour=100)

        # Mock Redis
        with patch('src.core.cache.get_redis_client') as mock_redis:
            mock_client = MagicMock()
            mock_client.incr.return_value = 50
            mock_redis.return_value = mock_client

            is_allowed, current, limit = await auth_service.check_api_key_rate_limit(api_key)

            assert is_allowed is True
            assert current == 50
            assert limit == 100

    @pytest.mark.asyncio
    async def test_check_api_key_rate_limit_exceeded(self, auth_service):
        """Test API key rate limit when exceeded."""
        api_key = APIKey(id="key-uuid", rate_limit_per_hour=100)

        with patch('src.core.cache.get_redis_client') as mock_redis:
            mock_client = MagicMock()
            mock_client.incr.return_value = 101
            mock_redis.return_value = mock_client

            is_allowed, current, limit = await auth_service.check_api_key_rate_limit(api_key)

            assert is_allowed is False
            assert current == 101

    @pytest.mark.asyncio
    async def test_check_api_key_rate_limit_redis_failure(self, auth_service):
        """Test API key rate limit fails open on Redis error."""
        api_key = APIKey(id="key-uuid", rate_limit_per_hour=100)

        with patch('src.core.cache.get_redis_client', side_effect=Exception("Redis down")):
            is_allowed, current, limit = await auth_service.check_api_key_rate_limit(api_key)

            # Should fail open (allow request)
            assert is_allowed is True
