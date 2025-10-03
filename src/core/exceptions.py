"""Custom exceptions for corporate intelligence platform."""

from typing import Any, Optional
from fastapi import status


class CorporateIntelException(Exception):
    """Base exception for corporate intelligence platform."""

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        **kwargs: Any
    ):
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.kwargs = kwargs
        super().__init__(detail)


class DatabaseException(CorporateIntelException):
    """Database operation failed."""

    def __init__(self, detail: str, **kwargs: Any):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            **kwargs
        )


class ValidationException(CorporateIntelException):
    """Data validation failed."""

    def __init__(self, detail: str, **kwargs: Any):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            **kwargs
        )


class AuthenticationException(CorporateIntelException):
    """Authentication failed."""

    def __init__(self, detail: str = "Authentication failed", **kwargs: Any):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_ERROR",
            **kwargs
        )


class AuthorizationException(CorporateIntelException):
    """Authorization failed."""

    def __init__(self, detail: str = "Insufficient permissions", **kwargs: Any):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_ERROR",
            **kwargs
        )


class NotFoundException(CorporateIntelException):
    """Resource not found."""

    def __init__(self, detail: str = "Resource not found", **kwargs: Any):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            **kwargs
        )


class RateLimitException(CorporateIntelException):
    """Rate limit exceeded."""

    def __init__(self, detail: str = "Rate limit exceeded", **kwargs: Any):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_EXCEEDED",
            **kwargs
        )


class ExternalAPIException(CorporateIntelException):
    """External API call failed."""

    def __init__(self, detail: str, service: str, **kwargs: Any):
        super().__init__(
            detail=f"{service}: {detail}",
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="EXTERNAL_API_ERROR",
            service=service,
            **kwargs
        )


class ProcessingException(CorporateIntelException):
    """Data processing failed."""

    def __init__(self, detail: str, **kwargs: Any):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="PROCESSING_ERROR",
            **kwargs
        )
