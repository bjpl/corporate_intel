"""Authentication and authorization models."""

from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum
import secrets
import hashlib
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Table, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from src.db.base import Base


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    ANALYST = "analyst" 
    VIEWER = "viewer"
    SERVICE = "service"  # For API keys/service accounts


class PermissionScope(str, Enum):
    """Permission scopes for fine-grained access control."""
    # Read permissions
    READ_COMPANIES = "read:companies"
    READ_FILINGS = "read:filings"
    READ_METRICS = "read:metrics"
    READ_ANALYSIS = "read:analysis"
    READ_DOCUMENTS = "read:documents"
    
    # Write permissions
    WRITE_COMPANIES = "write:companies"
    WRITE_FILINGS = "write:filings"
    WRITE_METRICS = "write:metrics"
    WRITE_ANALYSIS = "write:analysis"
    WRITE_DOCUMENTS = "write:documents"
    
    # Admin permissions
    MANAGE_USERS = "manage:users"
    MANAGE_API_KEYS = "manage:api_keys"
    MANAGE_SYSTEM = "manage:system"
    
    # Analysis permissions
    RUN_ANALYSIS = "run:analysis"
    EXPORT_DATA = "export:data"
    CREATE_REPORTS = "create:reports"


# Association table for many-to-many relationship
user_permissions = Table(
    'user_permissions',
    Base.metadata,
    Column('user_id', UUID(as_uuid=True), ForeignKey('users.id')),
    Column('permission_id', Integer, ForeignKey('permissions.id'))
)


class User(Base):
    """User model with authentication details."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    
    # User details
    full_name = Column(String)
    organization = Column(String)
    role = Column(String, nullable=False, default=UserRole.VIEWER)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    email_verified_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at = Column(DateTime)
    
    # Rate limiting
    api_calls_today = Column(Integer, default=0)
    api_calls_reset_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    permissions = relationship("Permission", secondary=user_permissions, back_populates="users")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    
    def has_permission(self, scope: PermissionScope) -> bool:
        """Check if user has specific permission."""
        # Admins have all permissions
        if self.role == UserRole.ADMIN:
            return True
        
        # Check role-based permissions
        role_permissions = ROLE_PERMISSIONS.get(UserRole(self.role), set())
        if scope in role_permissions:
            return True
        
        # Check individual permissions
        return any(p.scope == scope for p in self.permissions)
    
    def get_rate_limit(self) -> tuple[int, int]:
        """Get user's rate limit (used, limit)."""
        # Reset counter if needed
        if self.api_calls_reset_at < datetime.utcnow():
            self.api_calls_today = 0
            self.api_calls_reset_at = datetime.utcnow() + timedelta(days=1)
        
        # Get limit based on role
        limits = {
            UserRole.ADMIN: 10000,
            UserRole.ANALYST: 5000,
            UserRole.VIEWER: 1000,
            UserRole.SERVICE: 50000
        }
        
        return self.api_calls_today, limits.get(UserRole(self.role), 1000)


class Permission(Base):
    """Individual permission model."""
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True)
    scope = Column(String, unique=True, nullable=False)
    description = Column(String)
    
    # Relationships
    users = relationship("User", secondary=user_permissions, back_populates="permissions")


class APIKey(Base):
    """API key for programmatic access."""
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Key details
    name = Column(String, nullable=False)
    key_hash = Column(String, nullable=False, unique=True)  # SHA256 hash
    key_prefix = Column(String, nullable=False)  # First 8 chars for identification
    
    # Permissions
    scopes = Column(String)  # Comma-separated list of PermissionScope values
    
    # Validity
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime)
    last_used_at = Column(DateTime)
    
    # Rate limiting
    rate_limit_per_hour = Column(Integer, default=1000)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    @classmethod
    def generate_key(cls) -> tuple[str, str]:
        """Generate a new API key and its hash.

        Returns:
            Tuple of (raw_key, key_hash) where raw_key is the full key with prefix
            and key_hash is the SHA-256 hash for storage.
        """
        # Generate 32-byte random key
        raw_key = secrets.token_urlsafe(32)
        key = f"ci_{raw_key}"  # Prefix for identification
        
        # Hash the key for storage
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        return key, key_hash
    
    def has_scope(self, scope: PermissionScope) -> bool:
        """Check if API key has specific scope."""
        if not self.scopes:
            return False
        
        key_scopes = set(self.scopes.split(','))
        return scope.value in key_scopes


class UserSession(Base):
    """User session tracking for security."""
    __tablename__ = "user_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    # Session details
    token_jti = Column(String, unique=True, nullable=False)  # JWT ID
    ip_address = Column(String)
    user_agent = Column(String)
    
    # Validity
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="sessions")


# Role-based permission mappings
ROLE_PERMISSIONS = {
    UserRole.VIEWER: {
        PermissionScope.READ_COMPANIES,
        PermissionScope.READ_FILINGS,
        PermissionScope.READ_METRICS,
        PermissionScope.READ_ANALYSIS,
        PermissionScope.READ_DOCUMENTS,
    },
    UserRole.ANALYST: {
        PermissionScope.READ_COMPANIES,
        PermissionScope.READ_FILINGS,
        PermissionScope.READ_METRICS,
        PermissionScope.READ_ANALYSIS,
        PermissionScope.READ_DOCUMENTS,
        PermissionScope.WRITE_ANALYSIS,
        PermissionScope.RUN_ANALYSIS,
        PermissionScope.EXPORT_DATA,
        PermissionScope.CREATE_REPORTS,
    },
    UserRole.ADMIN: {
        # Admins get all permissions dynamically
        *[scope for scope in PermissionScope]
    },
    UserRole.SERVICE: {
        # Service accounts get specific permissions via API key scopes
    }
}


# Pydantic models for API
class UserCreate(BaseModel):
    """User creation request."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    organization: Optional[str] = None
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Ensure password meets complexity requirements."""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain digit')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in v):
            raise ValueError('Password must contain special character')
        return v


class UserLogin(BaseModel):
    """User login request."""
    username: str  # Can be email or username
    password: str
    

class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    

class APIKeyCreate(BaseModel):
    """API key creation request."""
    name: str = Field(..., min_length=3, max_length=100)
    scopes: List[PermissionScope]
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)
    

class APIKeyResponse(BaseModel):
    """API key creation response."""
    id: str
    name: str
    key: str  # Only shown once at creation
    scopes: List[str]
    expires_at: Optional[datetime]

    model_config = {
        "ser_json_timedelta": "iso8601",
    }

    # Pydantic V2 custom serializer for datetime
    @staticmethod
    def serialize_datetime(dt: Optional[datetime]) -> Optional[str]:
        return dt.isoformat() if dt else None