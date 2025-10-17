"""Custom exceptions for corporate intelligence platform.

This module provides a comprehensive exception hierarchy for standardized
error handling across the entire application. All exceptions inherit from
CorporateIntelException and include structured error information for logging
and API responses.

Exception Hierarchy:
    CorporateIntelException (base)
    ├── DatabaseException
    │   ├── ConnectionException
    │   ├── QueryException
    │   └── IntegrityException
    ├── DataSourceException
    │   ├── APIException
    │   │   ├── RateLimitException
    │   │   ├── AuthenticationException
    │   │   └── APIResponseException
    │   └── DataValidationException
    ├── PipelineException
    │   ├── IngestionException
    │   ├── TransformationException
    │   └── LoadException
    ├── RepositoryException
    │   ├── RecordNotFoundException
    │   └── DuplicateRecordException
    └── ConfigurationException

Usage:
    from src.core.exceptions import APIException, wrap_exception

    try:
        response = await api.fetch()
    except aiohttp.ClientError as e:
        raise wrap_exception(e, APIException, "API request failed")
"""

from typing import Any, Dict, Optional
from fastapi import status


class CorporateIntelException(Exception):
    """Base exception for corporate intelligence platform.

    All custom exceptions inherit from this base to enable catch-all
    error handling while maintaining specificity.

    Attributes:
        detail: Human-readable error message
        status_code: HTTP status code for API responses
        error_code: Machine-readable error code
        kwargs: Additional context (metadata, IDs, values)
        original_error: Original exception if wrapping another error
    """

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        original_error: Optional[Exception] = None,
        **kwargs: Any
    ):
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.kwargs = kwargs
        self.original_error = original_error
        super().__init__(detail)

    def __str__(self) -> str:
        """Format error message with code and details."""
        parts = [f"{self.error_code}: {self.detail}"]
        if self.kwargs:
            parts.append(f"Details: {self.kwargs}")
        if self.original_error:
            parts.append(f"Caused by: {type(self.original_error).__name__}: {self.original_error}")
        return " | ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/API responses."""
        return {
            "error": self.error_code,
            "message": self.detail,
            "status_code": self.status_code,
            "details": self.kwargs,
            "original_error": str(self.original_error) if self.original_error else None
        }


class DatabaseException(CorporateIntelException):
    """Database operation failed."""

    def __init__(self, detail: str, **kwargs: Any):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
            **kwargs
        )


class ConnectionException(DatabaseException):
    """Database connection failed or was lost."""

    def __init__(self, detail: str, **kwargs: Any):
        super().__init__(
            detail=detail,
            error_code="DATABASE_CONNECTION_ERROR",
            **kwargs
        )


class QueryException(DatabaseException):
    """Database query execution failed."""

    def __init__(self, detail: str, query: Optional[str] = None, **kwargs: Any):
        if query:
            kwargs['query'] = query
        super().__init__(
            detail=detail,
            error_code="DATABASE_QUERY_ERROR",
            **kwargs
        )


class IntegrityException(DatabaseException):
    """Database constraint violation (unique, foreign key, etc.)."""

    def __init__(self, detail: str, constraint: Optional[str] = None, **kwargs: Any):
        if constraint:
            kwargs['constraint'] = constraint
        super().__init__(
            detail=detail,
            error_code="DATABASE_INTEGRITY_ERROR",
            **kwargs
        )


class DataValidationException(CorporateIntelException):
    """Data validation failed."""

    def __init__(self, detail: str, field: Optional[str] = None, value: Any = None, **kwargs: Any):
        if field:
            kwargs['field'] = field
        if value is not None:
            kwargs['value'] = value
        super().__init__(
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            **kwargs
        )


# Alias for backwards compatibility
ValidationException = DataValidationException


class DataSourceException(CorporateIntelException):
    """Base exception for external data source errors."""

    def __init__(self, detail: str, **kwargs: Any):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="DATA_SOURCE_ERROR",
            **kwargs
        )


class APIException(DataSourceException):
    """External API call failed."""

    def __init__(
        self,
        detail: str,
        service: Optional[str] = None,
        api_status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        **kwargs: Any
    ):
        if service:
            kwargs['service'] = service
        if api_status_code:
            kwargs['api_status_code'] = api_status_code
        if response_body:
            kwargs['response_body'] = response_body
        super().__init__(
            detail=detail,
            error_code="EXTERNAL_API_ERROR",
            **kwargs
        )


# Alias for backwards compatibility
ExternalAPIException = APIException


class RateLimitException(APIException):
    """API rate limit exceeded."""

    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        retry_after: Optional[int] = None,
        **kwargs: Any
    ):
        if retry_after:
            kwargs['retry_after'] = retry_after
        super().__init__(
            detail=detail,
            error_code="RATE_LIMIT_EXCEEDED",
            api_status_code=429,
            **kwargs
        )
        # Override status code for consistency
        self.status_code = status.HTTP_429_TOO_MANY_REQUESTS


class AuthenticationException(APIException):
    """API authentication failed."""

    def __init__(self, detail: str = "Authentication failed", **kwargs: Any):
        super().__init__(
            detail=detail,
            error_code="AUTHENTICATION_ERROR",
            api_status_code=401,
            **kwargs
        )
        # Override status code for consistency
        self.status_code = status.HTTP_401_UNAUTHORIZED


class AuthorizationException(CorporateIntelException):
    """Authorization failed."""

    def __init__(self, detail: str = "Insufficient permissions", **kwargs: Any):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_ERROR",
            **kwargs
        )


class APIResponseException(APIException):
    """API returned invalid or unexpected response."""

    def __init__(self, detail: str, **kwargs: Any):
        super().__init__(
            detail=detail,
            error_code="API_RESPONSE_ERROR",
            **kwargs
        )


class NotFoundException(CorporateIntelException):
    """Resource not found."""

    def __init__(self, detail: str = "Resource not found", resource_type: Optional[str] = None, resource_id: Any = None, **kwargs: Any):
        if resource_type:
            kwargs['resource_type'] = resource_type
        if resource_id is not None:
            kwargs['resource_id'] = str(resource_id)
        super().__init__(
            detail=detail,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            **kwargs
        )


# Pipeline Errors
class PipelineException(CorporateIntelException):
    """Base exception for data pipeline errors."""

    def __init__(self, detail: str, **kwargs: Any):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="PIPELINE_ERROR",
            **kwargs
        )


# Alias for backwards compatibility
ProcessingException = PipelineException


class IngestionException(PipelineException):
    """Data ingestion from source failed."""

    def __init__(
        self,
        detail: str,
        source: Optional[str] = None,
        ticker: Optional[str] = None,
        **kwargs: Any
    ):
        if source:
            kwargs['source'] = source
        if ticker:
            kwargs['ticker'] = ticker
        super().__init__(
            detail=detail,
            error_code="INGESTION_ERROR",
            **kwargs
        )


class TransformationException(PipelineException):
    """Data transformation or processing failed."""

    def __init__(self, detail: str, **kwargs: Any):
        super().__init__(
            detail=detail,
            error_code="TRANSFORMATION_ERROR",
            **kwargs
        )


class LoadException(PipelineException):
    """Loading data into database failed."""

    def __init__(self, detail: str, **kwargs: Any):
        super().__init__(
            detail=detail,
            error_code="LOAD_ERROR",
            **kwargs
        )


# Repository Errors
class RepositoryException(CorporateIntelException):
    """Base exception for repository layer errors."""

    def __init__(self, detail: str, **kwargs: Any):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="REPOSITORY_ERROR",
            **kwargs
        )


class RecordNotFoundException(RepositoryException):
    """Requested record does not exist."""

    def __init__(
        self,
        detail: str,
        model: Optional[str] = None,
        record_id: Any = None,
        **kwargs: Any
    ):
        if model:
            kwargs['model'] = model
        if record_id is not None:
            kwargs['record_id'] = str(record_id)
        super().__init__(
            detail=detail,
            error_code="RECORD_NOT_FOUND",
            **kwargs
        )
        # Override status code for consistency
        self.status_code = status.HTTP_404_NOT_FOUND


class DuplicateRecordException(RepositoryException):
    """Record with same unique key already exists."""

    def __init__(
        self,
        detail: str,
        model: Optional[str] = None,
        duplicate_key: Optional[str] = None,
        **kwargs: Any
    ):
        if model:
            kwargs['model'] = model
        if duplicate_key:
            kwargs['duplicate_key'] = duplicate_key
        super().__init__(
            detail=detail,
            error_code="DUPLICATE_RECORD",
            **kwargs
        )
        # Override status code for consistency
        self.status_code = status.HTTP_409_CONFLICT


# Configuration Errors
class ConfigurationException(CorporateIntelException):
    """Invalid configuration or environment setup."""

    def __init__(
        self,
        detail: str,
        config_key: Optional[str] = None,
        **kwargs: Any
    ):
        if config_key:
            kwargs['config_key'] = config_key
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="CONFIGURATION_ERROR",
            **kwargs
        )


# Helper functions for error handling
def wrap_exception(
    original_error: Exception,
    error_class: type[CorporateIntelException],
    detail: Optional[str] = None,
    **kwargs
) -> CorporateIntelException:
    """Wrap a generic exception in a custom exception type.

    Args:
        original_error: The original exception to wrap
        error_class: The custom exception class to use
        detail: Optional custom message (uses original if not provided)
        **kwargs: Additional arguments for the exception

    Returns:
        Instance of error_class wrapping the original exception

    Example:
        try:
            result = await session.execute(query)
        except SQLAlchemyError as e:
            raise wrap_exception(e, QueryException, "Failed to fetch companies")
    """
    return error_class(
        detail=detail or str(original_error),
        original_error=original_error,
        **kwargs
    )
