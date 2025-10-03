"""Comprehensive unit tests for authentication models."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
import hashlib
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.exc import IntegrityError

from src.auth.models import (
    User, UserRole, Permission, PermissionScope, APIKey, UserSession,
    UserCreate, UserLogin, APIKeyCreate, APIKeyResponse, TokenResponse,
    ROLE_PERMISSIONS, user_permissions
)
from src.db.base import Base


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def session(engine):
    """Create database session for testing."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_user(session):
    """Create a sample user for testing."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password_123",
        full_name="Test User",
        organization="Test Corp",
        role=UserRole.VIEWER,
        is_active=True,
        is_verified=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def sample_admin_user(session):
    """Create a sample admin user."""
    admin = User(
        email="admin@example.com",
        username="adminuser",
        hashed_password="hashed_password_456",
        full_name="Admin User",
        role=UserRole.ADMIN,
        is_active=True
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return admin


# ============================================================================
# USER MODEL TESTS
# ============================================================================

class TestUserModel:
    """Test User model functionality."""

    def test_user_creation_minimal(self, session):
        """Test creating user with minimal required fields."""
        user = User(
            email="user@test.com",
            username="newuser",
            hashed_password="hashed_pwd"
        )
        session.add(user)
        session.commit()

        assert user.id is not None
        assert user.role == UserRole.VIEWER  # Default role
        assert user.is_active is True
        assert user.is_verified is False

    def test_user_email_unique_constraint(self, session, sample_user):
        """Test that email must be unique."""
        duplicate_user = User(
            email=sample_user.email,
            username="different_username",
            hashed_password="password"
        )
        session.add(duplicate_user)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_user_username_unique_constraint(self, session, sample_user):
        """Test that username must be unique."""
        duplicate_user = User(
            email="different@email.com",
            username=sample_user.username,
            hashed_password="password"
        )
        session.add(duplicate_user)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_user_timestamps_auto_set(self, session):
        """Test that timestamps are automatically set."""
        user = User(
            email="time@test.com",
            username="timeuser",
            hashed_password="password"
        )
        session.add(user)
        session.commit()

        assert user.created_at is not None
        assert user.updated_at is not None
        assert isinstance(user.created_at, datetime)

    def test_user_last_login_tracking(self, session, sample_user):
        """Test that last login can be tracked."""
        assert sample_user.last_login_at is None

        sample_user.last_login_at = datetime.utcnow()
        session.commit()

        session.refresh(sample_user)
        assert sample_user.last_login_at is not None


# ============================================================================
# PERMISSION TESTS
# ============================================================================

class TestPermissions:
    """Test permission system."""

    def test_user_has_permission_admin(self, session, sample_admin_user):
        """Test that admin has all permissions."""
        # Admin should have any permission
        assert sample_admin_user.has_permission(PermissionScope.READ_COMPANIES)
        assert sample_admin_user.has_permission(PermissionScope.WRITE_COMPANIES)
        assert sample_admin_user.has_permission(PermissionScope.MANAGE_USERS)
        assert sample_admin_user.has_permission(PermissionScope.MANAGE_SYSTEM)

    def test_user_has_permission_role_based(self, session):
        """Test role-based permissions."""
        viewer = User(
            email="viewer@test.com",
            username="viewer",
            hashed_password="pwd",
            role=UserRole.VIEWER
        )
        session.add(viewer)
        session.commit()

        # Viewer should have read permissions
        assert viewer.has_permission(PermissionScope.READ_COMPANIES)
        assert viewer.has_permission(PermissionScope.READ_FILINGS)

        # Viewer should NOT have write permissions
        assert not viewer.has_permission(PermissionScope.WRITE_COMPANIES)
        assert not viewer.has_permission(PermissionScope.MANAGE_USERS)

    def test_analyst_permissions(self, session):
        """Test analyst role permissions."""
        analyst = User(
            email="analyst@test.com",
            username="analyst",
            hashed_password="pwd",
            role=UserRole.ANALYST
        )
        session.add(analyst)
        session.commit()

        # Analyst should have read and analysis permissions
        assert analyst.has_permission(PermissionScope.READ_COMPANIES)
        assert analyst.has_permission(PermissionScope.RUN_ANALYSIS)
        assert analyst.has_permission(PermissionScope.EXPORT_DATA)

        # Analyst should NOT have user management
        assert not analyst.has_permission(PermissionScope.MANAGE_USERS)

    def test_individual_permission_assignment(self, session, sample_user):
        """Test assigning individual permissions to user."""
        # Create permission
        permission = Permission(
            scope=PermissionScope.WRITE_ANALYSIS,
            description="Permission to write analysis"
        )
        session.add(permission)
        session.commit()

        # Assign to user
        sample_user.permissions.append(permission)
        session.commit()

        # Check permission
        session.refresh(sample_user)
        assert sample_user.has_permission(PermissionScope.WRITE_ANALYSIS)


# ============================================================================
# RATE LIMITING TESTS
# ============================================================================

class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_get_rate_limit_viewer(self, session):
        """Test rate limit for viewer role."""
        user = User(
            email="rate@test.com",
            username="rateuser",
            hashed_password="pwd",
            role=UserRole.VIEWER
        )
        session.add(user)
        session.commit()

        used, limit = user.get_rate_limit()

        assert used == 0
        assert limit == 1000  # Viewer limit

    def test_get_rate_limit_analyst(self, session):
        """Test rate limit for analyst role."""
        analyst = User(
            email="analyst@test.com",
            username="analyst",
            hashed_password="pwd",
            role=UserRole.ANALYST
        )
        session.add(analyst)
        session.commit()

        used, limit = analyst.get_rate_limit()

        assert limit == 5000  # Analyst limit

    def test_get_rate_limit_admin(self, session, sample_admin_user):
        """Test rate limit for admin role."""
        used, limit = sample_admin_user.get_rate_limit()

        assert limit == 10000  # Admin limit

    def test_rate_limit_counter_increment(self, session, sample_user):
        """Test that rate limit counter increments."""
        sample_user.api_calls_today = 10
        session.commit()

        used, limit = sample_user.get_rate_limit()

        assert used == 10

    def test_rate_limit_reset(self, session, sample_user):
        """Test that rate limit resets after expiry."""
        # Set old reset time
        sample_user.api_calls_today = 100
        sample_user.api_calls_reset_at = datetime.utcnow() - timedelta(days=1)
        session.commit()

        used, limit = sample_user.get_rate_limit()

        # Should reset to 0
        assert used == 0


# ============================================================================
# API KEY MODEL TESTS
# ============================================================================

class TestAPIKeyModel:
    """Test APIKey model."""

    def test_api_key_generation(self):
        """Test API key generation."""
        key, key_hash = APIKey.generate_key()

        assert key.startswith("ci_")
        assert len(key) > 40  # Should be reasonably long
        assert len(key_hash) == 64  # SHA256 hash length

        # Verify hash is correct
        expected_hash = hashlib.sha256(key.encode()).hexdigest()
        assert key_hash == expected_hash

    def test_api_key_creation(self, session, sample_user):
        """Test creating API key."""
        key, key_hash = APIKey.generate_key()

        api_key = APIKey(
            user_id=sample_user.id,
            name="Test API Key",
            key_hash=key_hash,
            key_prefix=key[:8],
            scopes=f"{PermissionScope.READ_COMPANIES},{PermissionScope.READ_METRICS}",
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(days=30)
        )
        session.add(api_key)
        session.commit()

        assert api_key.id is not None
        assert api_key.key_prefix == key[:8]

    def test_api_key_has_scope(self, session, sample_user):
        """Test checking API key scopes."""
        api_key = APIKey(
            user_id=sample_user.id,
            name="Test Key",
            key_hash="hash123",
            key_prefix="ci_12345",
            scopes=f"{PermissionScope.READ_COMPANIES.value},{PermissionScope.READ_METRICS.value}"
        )
        session.add(api_key)
        session.commit()

        assert api_key.has_scope(PermissionScope.READ_COMPANIES)
        assert api_key.has_scope(PermissionScope.READ_METRICS)
        assert not api_key.has_scope(PermissionScope.WRITE_COMPANIES)

    def test_api_key_expiry(self, session, sample_user):
        """Test API key expiration."""
        api_key = APIKey(
            user_id=sample_user.id,
            name="Expired Key",
            key_hash="hash123",
            key_prefix="ci_12345",
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        session.add(api_key)
        session.commit()

        assert api_key.expires_at < datetime.utcnow()

    def test_api_key_user_relationship(self, session, sample_user):
        """Test API key-user relationship."""
        api_key = APIKey(
            user_id=sample_user.id,
            name="Test Key",
            key_hash="hash123",
            key_prefix="ci_12345"
        )
        session.add(api_key)
        session.commit()

        session.refresh(sample_user)
        assert len(sample_user.api_keys) == 1
        assert sample_user.api_keys[0].name == "Test Key"


# ============================================================================
# USER SESSION MODEL TESTS
# ============================================================================

class TestUserSessionModel:
    """Test UserSession model."""

    def test_session_creation(self, session, sample_user):
        """Test creating user session."""
        user_session = UserSession(
            user_id=sample_user.id,
            token_jti="unique-jwt-id-123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        session.add(user_session)
        session.commit()

        assert user_session.id is not None
        assert user_session.token_jti == "unique-jwt-id-123"

    def test_session_token_jti_unique(self, session, sample_user):
        """Test that token JTI must be unique."""
        session1 = UserSession(
            user_id=sample_user.id,
            token_jti="jti-123",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        session.add(session1)
        session.commit()

        session2 = UserSession(
            user_id=sample_user.id,
            token_jti="jti-123",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        session.add(session2)

        with pytest.raises(IntegrityError):
            session.commit()

    def test_session_revocation(self, session, sample_user):
        """Test session revocation."""
        user_session = UserSession(
            user_id=sample_user.id,
            token_jti="jti-456",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        session.add(user_session)
        session.commit()

        # Revoke session
        user_session.is_active = False
        user_session.revoked_at = datetime.utcnow()
        session.commit()

        session.refresh(user_session)
        assert user_session.is_active is False
        assert user_session.revoked_at is not None


# ============================================================================
# PYDANTIC MODEL TESTS
# ============================================================================

class TestPydanticModels:
    """Test Pydantic validation models."""

    def test_user_create_validation(self):
        """Test UserCreate validation."""
        valid_data = UserCreate(
            email="test@example.com",
            username="testuser",
            password="Test123!@#",
            full_name="Test User"
        )

        assert valid_data.email == "test@example.com"
        assert valid_data.username == "testuser"

    def test_user_create_password_complexity(self):
        """Test password complexity requirements."""
        # Missing uppercase
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="test123!@#"
            )
        assert "uppercase" in str(exc_info.value).lower()

        # Missing lowercase
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="TEST123!@#"
            )

        # Missing digit
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="TestTest!@#"
            )

        # Missing special character
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="Test12345"
            )

    def test_user_create_password_minimum_length(self):
        """Test password minimum length requirement."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                username="testuser",
                password="Te1!"
            )
        assert "min_length" in str(exc_info.value).lower()

    def test_user_create_username_minimum_length(self):
        """Test username minimum length requirement."""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                email="test@example.com",
                username="ab",
                password="Test123!@#"
            )
        assert "min_length" in str(exc_info.value).lower()

    def test_api_key_create_validation(self):
        """Test APIKeyCreate validation."""
        valid_data = APIKeyCreate(
            name="Test API Key",
            scopes=[PermissionScope.READ_COMPANIES, PermissionScope.READ_METRICS],
            expires_in_days=30
        )

        assert valid_data.name == "Test API Key"
        assert len(valid_data.scopes) == 2

    def test_api_key_create_expiry_bounds(self):
        """Test API key expiry day bounds."""
        # Too short
        with pytest.raises(ValidationError):
            APIKeyCreate(
                name="Test Key",
                scopes=[PermissionScope.READ_COMPANIES],
                expires_in_days=0
            )

        # Too long
        with pytest.raises(ValidationError):
            APIKeyCreate(
                name="Test Key",
                scopes=[PermissionScope.READ_COMPANIES],
                expires_in_days=400
            )

    def test_token_response_structure(self):
        """Test TokenResponse structure."""
        token = TokenResponse(
            access_token="access_token_123",
            refresh_token="refresh_token_456",
            expires_in=3600
        )

        assert token.token_type == "bearer"
        assert token.access_token == "access_token_123"
        assert token.expires_in == 3600


# ============================================================================
# ROLE PERMISSIONS MAPPING TESTS
# ============================================================================

class TestRolePermissions:
    """Test ROLE_PERMISSIONS mapping."""

    def test_viewer_permissions(self):
        """Test viewer role has correct permissions."""
        viewer_perms = ROLE_PERMISSIONS[UserRole.VIEWER]

        assert PermissionScope.READ_COMPANIES in viewer_perms
        assert PermissionScope.READ_FILINGS in viewer_perms
        assert PermissionScope.READ_METRICS in viewer_perms
        assert PermissionScope.WRITE_COMPANIES not in viewer_perms

    def test_analyst_permissions(self):
        """Test analyst role has correct permissions."""
        analyst_perms = ROLE_PERMISSIONS[UserRole.ANALYST]

        assert PermissionScope.READ_COMPANIES in analyst_perms
        assert PermissionScope.RUN_ANALYSIS in analyst_perms
        assert PermissionScope.EXPORT_DATA in analyst_perms
        assert PermissionScope.MANAGE_USERS not in analyst_perms

    def test_admin_has_all_permissions(self):
        """Test admin role has all permissions."""
        admin_perms = ROLE_PERMISSIONS[UserRole.ADMIN]

        # Should have all permission scopes
        all_scopes = set(PermissionScope)
        assert admin_perms == all_scopes


# ============================================================================
# CASCADE DELETE TESTS
# ============================================================================

class TestCascadeDelete:
    """Test cascade delete behavior."""

    def test_delete_user_cascades_api_keys(self, session, sample_user):
        """Test deleting user cascades to API keys."""
        # Create API key
        api_key = APIKey(
            user_id=sample_user.id,
            name="Test Key",
            key_hash="hash123",
            key_prefix="ci_12345"
        )
        session.add(api_key)
        session.commit()

        # Delete user
        session.delete(sample_user)
        session.commit()

        # Verify API key was deleted
        remaining_keys = session.query(APIKey).filter_by(
            user_id=sample_user.id
        ).count()
        assert remaining_keys == 0

    def test_delete_user_cascades_sessions(self, session, sample_user):
        """Test deleting user cascades to sessions."""
        # Create session
        user_session = UserSession(
            user_id=sample_user.id,
            token_jti="jti-789",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        session.add(user_session)
        session.commit()

        # Delete user
        session.delete(sample_user)
        session.commit()

        # Verify session was deleted
        remaining_sessions = session.query(UserSession).filter_by(
            user_id=sample_user.id
        ).count()
        assert remaining_sessions == 0
