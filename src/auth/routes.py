"""Authentication API routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, Security
from sqlalchemy.orm import Session
import logging

from src.auth.models import (
    User, UserRole, UserCreate, UserLogin,
    TokenResponse, APIKeyCreate, APIKeyResponse
)
from src.auth.service import AuthService, AuthenticationError
from src.auth.dependencies import (
    get_auth_service, get_current_active_user,
    bearer_scheme, RequireAdmin, RequireManageUsers,
    RateLimiter
)
from src.db.base import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
    rate_limit: bool = Depends(RateLimiter(calls=10, period=3600))
):
    """Register a new user account.
    
    Requirements:
    - Unique email and username
    - Password with uppercase, lowercase, digit, and special character
    - Minimum password length of 8 characters
    
    New users are created with VIEWER role by default.
    """
    try:
        user = auth_service.create_user(user_data, role=UserRole.VIEWER)
        
        return {
            "message": "User registered successfully",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "role": user.role
            }
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    rate_limit: bool = Depends(RateLimiter(calls=20, period=3600))
):
    """Login with username/email and password.
    
    Returns JWT access and refresh tokens.
    The access token expires in 1 hour, refresh token in 7 days.
    """
    try:
        user = auth_service.authenticate_user(login_data)
        tokens = auth_service.create_tokens(user)
        
        # Set secure cookie for refresh token (optional)
        response.set_cookie(
            key="refresh_token",
            value=tokens.refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=7 * 24 * 60 * 60  # 7 days
        )
        
        return tokens
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service)
):
    """Refresh access token using refresh token.
    
    Refresh token can be provided either:
    - In the request body as 'refresh_token'
    - As a cookie named 'refresh_token'
    """
    # Try to get refresh token from cookie first
    refresh_token = request.cookies.get("refresh_token")
    
    if not refresh_token:
        # Try to get from request body
        try:
            body = await request.json()
            refresh_token = body.get("refresh_token")
        except:
            pass
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refresh token required"
        )
    
    try:
        tokens = auth_service.refresh_access_token(refresh_token)
        
        # Update refresh token cookie
        response.set_cookie(
            key="refresh_token",
            value=tokens.refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=7 * 24 * 60 * 60
        )
        
        return tokens
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/logout")
async def logout(
    response: Response,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Logout and revoke current access token."""
    
    if credentials:
        auth_service.revoke_token(credentials.credentials)
    
    # Clear refresh token cookie
    response.delete_cookie("refresh_token")
    
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=dict)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user information."""
    
    # Get rate limit info
    used, limit = current_user.get_rate_limit()
    
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "organization": current_user.organization,
        "role": current_user.role,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat(),
        "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
        "rate_limit": {
            "used": used,
            "limit": limit,
            "resets_at": current_user.api_calls_reset_at.isoformat()
        },
        "permissions": [p.scope for p in current_user.permissions]
    }


@router.put("/me", response_model=dict)
async def update_current_user(
    updates: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user information.
    
    Allowed fields: full_name, organization
    """
    
    allowed_fields = {"full_name", "organization"}
    
    for field, value in updates.items():
        if field in allowed_fields:
            setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "message": "User updated successfully",
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "username": current_user.username,
            "full_name": current_user.full_name,
            "organization": current_user.organization
        }
    }


# API Key Management

@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Create a new API key.
    
    The API key is only shown once at creation time.
    Store it securely as it cannot be retrieved later.
    """
    try:
        api_key = auth_service.create_api_key(current_user, key_data)
        return api_key
    except Exception as e:
        logger.error(f"API key creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create API key"
        )


@router.get("/api-keys", response_model=List[dict])
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List user's API keys."""
    
    keys = []
    for key in current_user.api_keys:
        if key.is_active:
            keys.append({
                "id": str(key.id),
                "name": key.name,
                "key_prefix": key.key_prefix,
                "scopes": key.scopes.split(',') if key.scopes else [],
                "created_at": key.created_at.isoformat(),
                "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None
            })
    
    return keys


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Revoke an API key."""
    
    try:
        auth_service.revoke_api_key(current_user, key_id)
        return {"message": "API key revoked successfully"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"API key revocation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke API key"
        )


# Admin endpoints

@router.get("/users", response_model=List[dict])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(RequireAdmin),
    db: Session = Depends(get_db)
):
    """List all users (admin only)."""
    
    users = db.query(User).offset(skip).limit(limit).all()
    
    return [
        {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "organization": user.organization,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat(),
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None
        }
        for user in users
    ]


@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: UserRole,
    current_user: User = Depends(RequireManageUsers),
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Update user role (admin only)."""
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update role
    user.role = role
    
    # Update permissions
    user.permissions.clear()
    auth_service._assign_role_permissions(user)
    
    db.commit()
    
    return {
        "message": "User role updated successfully",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "username": user.username,
            "role": user.role
        }
    }


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    is_active: bool,
    current_user: User = Depends(RequireManageUsers),
    db: Session = Depends(get_db)
):
    """Enable or disable user account (admin only)."""
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = is_active
    db.commit()
    
    return {
        "message": f"User {'activated' if is_active else 'deactivated'} successfully",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "is_active": user.is_active
        }
    }