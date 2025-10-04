"""FastAPI authentication dependencies."""

from typing import Optional, Annotated
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.orm import Session
import logging

from src.auth.service import AuthService, AuthenticationError, AuthorizationError
from src.auth.models import User, APIKey, PermissionScope
from src.db.base import get_db

logger = logging.getLogger(__name__)

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Get authentication service instance."""
    return AuthService(db)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
    auth_service: AuthService = Depends(get_auth_service)
) -> Optional[User]:
    """Get current user from JWT or API key (optional)."""
    
    # Try JWT token first
    if credentials and credentials.credentials:
        try:
            user = auth_service.get_current_user(credentials.credentials)
            return user
        except AuthenticationError:
            pass
    
    # Try API key
    if api_key:
        try:
            user, _ = auth_service.verify_api_key(api_key)
            return user
        except AuthenticationError:
            pass
    
    return None


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Security(api_key_header),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    """Get current user from JWT or API key (required)."""
    
    user = await get_current_user_optional(credentials, api_key, auth_service)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


class RequirePermission:
    """Dependency to require specific permission."""
    
    def __init__(self, scope: PermissionScope):
        self.scope = scope
    
    async def __call__(
        self,
        user: User = Depends(get_current_active_user),
        auth_service: AuthService = Depends(get_auth_service)
    ) -> User:
        """Check permission and return user."""
        try:
            auth_service.require_permission(user, self.scope)
            return user
        except AuthorizationError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )


class RequireRole:
    """Dependency to require specific role."""
    
    def __init__(self, *roles: str):
        self.roles = set(roles)
    
    async def __call__(
        self,
        user: User = Depends(get_current_active_user)
    ) -> User:
        """Check role and return user."""
        if user.role not in self.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(self.roles)}"
            )
        return user


class RateLimiter:
    """Rate limiting dependency with Redis-backed implementation."""

    def __init__(self, calls: int = 100, period: int = 3600):
        """Initialize rate limiter.

        Args:
            calls: Number of calls allowed per period
            period: Time period in seconds (default: 3600 = 1 hour)
        """
        self.calls = calls
        self.period = period

    async def __call__(
        self,
        user: Optional[User] = Depends(get_current_user_optional),
        api_key: Optional[str] = Security(api_key_header),
        auth_service: AuthService = Depends(get_auth_service)
    ) -> bool:
        """Check rate limit for user or API key.

        Returns:
            bool: True if within rate limit

        Raises:
            HTTPException: If rate limit exceeded (429)
        """

        if user:
            # Check user rate limit (daily limit stored in database)
            allowed, used, limit = auth_service.check_rate_limit(user)

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded: {used}/{limit} calls today",
                    headers={
                        "Retry-After": "3600",
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": user.api_calls_reset_at.isoformat()
                    }
                )

        elif api_key:
            # Check API key rate limit (hourly limit via Redis)
            try:
                _, key = auth_service.verify_api_key(api_key)
                allowed, current, limit = await auth_service.check_api_key_rate_limit(key)

                if not allowed:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"API key rate limit exceeded: {current}/{limit} calls this hour",
                        headers={
                            "Retry-After": "3600",
                            "X-RateLimit-Limit": str(limit),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(int((current // limit + 1) * 3600))
                        }
                    )
            except AuthenticationError:
                # Invalid API key, but don't block the request
                # Authentication will fail at the endpoint level
                pass

        return True


# Convenience dependencies
RequireAdmin = RequireRole("admin")
RequireAnalyst = RequireRole("admin", "analyst")
RequireViewer = RequireRole("admin", "analyst", "viewer")

# Permission dependencies
RequireReadCompanies = RequirePermission(PermissionScope.READ_COMPANIES)
RequireWriteCompanies = RequirePermission(PermissionScope.WRITE_COMPANIES)
RequireReadAnalysis = RequirePermission(PermissionScope.READ_ANALYSIS)
RequireRunAnalysis = RequirePermission(PermissionScope.RUN_ANALYSIS)
RequireManageUsers = RequirePermission(PermissionScope.MANAGE_USERS)
RequireExportData = RequirePermission(PermissionScope.EXPORT_DATA)


def get_api_key_scopes(
    api_key: Optional[str] = Security(api_key_header),
    auth_service: AuthService = Depends(get_auth_service)
) -> Optional[list[str]]:
    """Get API key scopes if using API key authentication."""
    if not api_key:
        return None
    
    try:
        _, key = auth_service.verify_api_key(api_key)
        return key.scopes.split(',') if key.scopes else []
    except AuthenticationError:
        return None


class RequireAPIKeyScope:
    """Require specific scope for API key authentication."""
    
    def __init__(self, scope: PermissionScope):
        self.scope = scope
    
    async def __call__(
        self,
        api_key: Optional[str] = Security(api_key_header),
        auth_service: AuthService = Depends(get_auth_service)
    ) -> bool:
        """Check API key scope."""
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required"
            )
        
        try:
            _, key = auth_service.verify_api_key(api_key)
            
            if not key.has_scope(self.scope):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"API key missing scope: {self.scope.value}"
                )
            
            return True
            
        except AuthenticationError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(e)
            )