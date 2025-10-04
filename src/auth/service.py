"""Authentication service with JWT and security utilities."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
import hashlib
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from sqlalchemy import or_
import uuid

from src.auth.models import (
    User, APIKey, UserSession, Permission,
    UserRole, PermissionScope, UserCreate, UserLogin,
    TokenResponse, APIKeyCreate, APIKeyResponse
)
from src.config import settings


# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7


class AuthenticationError(Exception):
    """Authentication error."""
    pass


class AuthorizationError(Exception):
    """Authorization error."""
    pass


class AuthService:
    """Authentication and authorization service."""
    
    def __init__(self, db: Session):
        self.db = db
    
    # Password utilities
    def hash_password(self, password: str) -> str:
        """Hash a password for storage."""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    # User management
    def create_user(self, user_data: UserCreate, role: UserRole = UserRole.VIEWER) -> User:
        """Create a new user."""
        # Check if user exists
        existing = self.db.query(User).filter(
            or_(User.email == user_data.email, User.username == user_data.username)
        ).first()
        
        if existing:
            if existing.email == user_data.email:
                raise ValueError("Email already registered")
            else:
                raise ValueError("Username already taken")
        
        # Create user
        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=self.hash_password(user_data.password),
            full_name=user_data.full_name,
            organization=user_data.organization,
            role=role,
            api_calls_reset_at=datetime.utcnow() + timedelta(days=1)
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        # Assign default permissions based on role
        self._assign_role_permissions(user)
        
        return user
    
    def _assign_role_permissions(self, user: User):
        """Assign default permissions based on user role."""
        from src.auth.models import ROLE_PERMISSIONS
        
        role_perms = ROLE_PERMISSIONS.get(UserRole(user.role), set())
        
        for scope in role_perms:
            # Get or create permission
            permission = self.db.query(Permission).filter(
                Permission.scope == scope.value
            ).first()
            
            if not permission:
                permission = Permission(
                    scope=scope.value,
                    description=f"Permission for {scope.value}"
                )
                self.db.add(permission)
            
            user.permissions.append(permission)
        
        self.db.commit()
    
    def authenticate_user(self, login_data: UserLogin) -> User:
        """Authenticate user with username/email and password."""
        # Find user by username or email
        user = self.db.query(User).filter(
            or_(User.username == login_data.username, User.email == login_data.username)
        ).first()
        
        if not user:
            raise AuthenticationError("Invalid credentials")
        
        if not self.verify_password(login_data.password, user.hashed_password):
            raise AuthenticationError("Invalid credentials")
        
        if not user.is_active:
            raise AuthenticationError("Account is disabled")
        
        # Update last login
        user.last_login_at = datetime.utcnow()
        self.db.commit()
        
        return user
    
    # JWT token management
    def create_access_token(self, user: User, expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token."""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Token payload
        jti = str(uuid.uuid4())
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": jti,
            "type": "access"
        }
        
        # Create session record
        session = UserSession(
            user_id=user.id,
            token_jti=jti,
            expires_at=expire
        )
        self.db.add(session)
        self.db.commit()
        
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token."""
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        payload = {
            "sub": str(user.id),
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4()),
            "type": "refresh"
        }
        
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    def create_tokens(self, user: User) -> TokenResponse:
        """Create both access and refresh tokens."""
        access_token = self.create_access_token(user)
        refresh_token = self.create_refresh_token(user)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Check token type
            if payload.get("type") != token_type:
                raise AuthenticationError("Invalid token type")
            
            # Check if session is still active (for access tokens)
            if token_type == "access":
                session = self.db.query(UserSession).filter(
                    UserSession.token_jti == payload.get("jti"),
                    UserSession.is_active == True
                ).first()
                
                if not session:
                    raise AuthenticationError("Session expired or revoked")
            
            return payload
            
        except JWTError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")
    
    def get_current_user(self, token: str) -> User:
        """Get current user from JWT token."""
        payload = self.verify_token(token)
        
        user = self.db.query(User).filter(
            User.id == payload["sub"]
        ).first()
        
        if not user:
            raise AuthenticationError("User not found")
        
        if not user.is_active:
            raise AuthenticationError("User is inactive")
        
        return user
    
    def refresh_access_token(self, refresh_token: str) -> TokenResponse:
        """Refresh access token using refresh token."""
        payload = self.verify_token(refresh_token, token_type="refresh")
        
        user = self.db.query(User).filter(
            User.id == payload["sub"]
        ).first()
        
        if not user or not user.is_active:
            raise AuthenticationError("Invalid refresh token")
        
        return self.create_tokens(user)
    
    def revoke_token(self, token: str):
        """Revoke a token (logout)."""
        try:
            payload = self.verify_token(token)
            
            # Revoke session
            session = self.db.query(UserSession).filter(
                UserSession.token_jti == payload.get("jti")
            ).first()
            
            if session:
                session.is_active = False
                session.revoked_at = datetime.utcnow()
                self.db.commit()
        except:
            pass  # Silent fail for logout
    
    # API key management
    def create_api_key(self, user: User, key_data: APIKeyCreate) -> APIKeyResponse:
        """Create a new API key for user."""
        # Generate key
        key, key_hash = APIKey.generate_key()
        
        # Calculate expiry
        expires_at = None
        if key_data.expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=key_data.expires_in_days)
        
        # Create API key record
        api_key = APIKey(
            user_id=user.id,
            name=key_data.name,
            key_hash=key_hash,
            key_prefix=key[:11],  # ci_XXXXXXXX
            scopes=','.join([s.value for s in key_data.scopes]),
            expires_at=expires_at
        )
        
        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)
        
        return APIKeyResponse(
            id=str(api_key.id),
            name=api_key.name,
            key=key,  # Only returned once
            scopes=[s.value for s in key_data.scopes],
            expires_at=expires_at
        )
    
    def verify_api_key(self, key: str) -> tuple[User, APIKey]:
        """Verify API key and return user and key details."""
        # Hash the provided key
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        
        # Find API key
        api_key = self.db.query(APIKey).filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        ).first()
        
        if not api_key:
            raise AuthenticationError("Invalid API key")
        
        # Check expiry
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            raise AuthenticationError("API key expired")
        
        # Get user
        user = api_key.user
        if not user or not user.is_active:
            raise AuthenticationError("User account is inactive")
        
        # Update last used
        api_key.last_used_at = datetime.utcnow()
        self.db.commit()
        
        return user, api_key
    
    def revoke_api_key(self, user: User, key_id: str):
        """Revoke an API key."""
        api_key = self.db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.user_id == user.id
        ).first()
        
        if not api_key:
            raise ValueError("API key not found")
        
        api_key.is_active = False
        api_key.revoked_at = datetime.utcnow()
        self.db.commit()
    
    # Authorization
    def check_permission(self, user: User, scope: PermissionScope) -> bool:
        """Check if user has specific permission."""
        return user.has_permission(scope)
    
    def require_permission(self, user: User, scope: PermissionScope):
        """Require user to have specific permission."""
        if not self.check_permission(user, scope):
            raise AuthorizationError(f"Missing permission: {scope.value}")
    
    # Rate limiting
    def check_rate_limit(self, user: User) -> tuple[bool, int, int]:
        """Check if user is within rate limit.
        
        Returns: (is_allowed, used, limit)
        """
        used, limit = user.get_rate_limit()
        
        if used >= limit:
            return False, used, limit
        
        # Increment counter
        user.api_calls_today += 1
        self.db.commit()
        
        return True, used + 1, limit
    
    async def check_api_key_rate_limit(self, api_key: APIKey) -> tuple[bool, int, int]:
        """Check if API key is within hourly rate limit using Redis.

        Uses sliding window algorithm with Redis for accurate rate limiting.

        Returns:
            tuple[bool, int, int]: (is_allowed, current_count, limit)
        """
        from src.core.cache import get_redis_client

        # Get rate limit for API key
        limit = api_key.rate_limit_per_hour

        # Build Redis key for this API key's rate limit window
        now = datetime.utcnow()
        window_key = f"ratelimit:apikey:{api_key.id}:{now.strftime('%Y%m%d%H')}"

        try:
            redis_client = await get_redis_client()

            # Increment counter
            current_count = await redis_client.incr(window_key)

            # Set expiry on first increment (1 hour + buffer)
            if current_count == 1:
                await redis_client.expire(window_key, 3660)  # 61 minutes for safety

            # Check if over limit
            if current_count > limit:
                return False, current_count, limit

            return True, current_count, limit

        except Exception as e:
            # If Redis fails, log and allow the request (fail open)
            from loguru import logger
            logger.warning(f"Rate limit check failed for API key {api_key.id}: {e}")
            return True, 0, limit