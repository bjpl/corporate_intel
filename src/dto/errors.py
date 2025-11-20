"""Error response DTOs and error handling utilities.

This module provides standardized error response structures that integrate
with the existing exception hierarchy in src.core.exceptions.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.dto.base import BaseDTO
from src.dto.responses import ResponseMetadata


class ErrorDetail(BaseModel):
    """Detailed error information.

    Provides structured error details for API responses, including
    field-level validation errors and error context.
    """

    field: Optional[str] = Field(
        None,
        description="Field name that caused the error (for validation errors)",
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
    )
    code: Optional[str] = Field(
        None,
        description="Machine-readable error code",
    )
    context: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error context",
    )


class ErrorResponseDTO(BaseDTO):
    """Standardized error response.

    Provides consistent error response structure across all API endpoints,
    integrating with CorporateIntelException hierarchy.

    Example:
        ErrorResponseDTO(
            success=False,
            error="VALIDATION_ERROR",
            message="Invalid company data",
            details=[
                ErrorDetail(
                    field="ticker",
                    message="Ticker must be 1-5 uppercase letters",
                    code="INVALID_TICKER_FORMAT"
                )
            ]
        )
    """

    success: bool = Field(
        False,
        description="Always False for error responses",
    )
    error: str = Field(
        ...,
        description="Error code (matches exception error_code)",
    )
    message: str = Field(
        ...,
        description="Human-readable error message",
    )
    details: Optional[List[ErrorDetail]] = Field(
        None,
        description="Detailed error information",
    )
    status_code: int = Field(
        ...,
        description="HTTP status code",
    )
    metadata: ResponseMetadata = Field(
        default_factory=ResponseMetadata,
        description="Response metadata",
    )

    @classmethod
    def from_exception(
        cls,
        exception: Exception,
        status_code: int = 500,
        error_code: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> "ErrorResponseDTO":
        """Create ErrorResponseDTO from exception.

        Args:
            exception: Exception instance
            status_code: HTTP status code
            error_code: Optional error code (uses exception class name if not provided)
            request_id: Optional request ID for tracing

        Returns:
            ErrorResponseDTO instance

        Example:
            try:
                # ... some operation
            except CorporateIntelException as e:
                return ErrorResponseDTO.from_exception(e, e.status_code, e.error_code)
        """
        from src.core.exceptions import CorporateIntelException

        # Handle CorporateIntelException with full context
        if isinstance(exception, CorporateIntelException):
            details = None
            if exception.kwargs:
                details = [
                    ErrorDetail(
                        field=key,
                        message=str(value),
                        code=exception.error_code,
                    )
                    for key, value in exception.kwargs.items()
                ]

            metadata = ResponseMetadata()
            if request_id:
                metadata.request_id = request_id

            return cls(
                success=False,
                error=exception.error_code,
                message=exception.detail,
                details=details,
                status_code=exception.status_code,
                metadata=metadata,
            )

        # Handle generic exceptions
        metadata = ResponseMetadata()
        if request_id:
            metadata.request_id = request_id

        return cls(
            success=False,
            error=error_code or exception.__class__.__name__,
            message=str(exception),
            status_code=status_code,
            metadata=metadata,
        )


class ValidationErrorDTO(BaseDTO):
    """Pydantic validation error response.

    Specialized error response for Pydantic validation errors,
    converting validation errors into standardized format.
    """

    success: bool = Field(
        False,
        description="Always False for error responses",
    )
    error: str = Field(
        "VALIDATION_ERROR",
        description="Error code",
    )
    message: str = Field(
        "Request validation failed",
        description="Error message",
    )
    validation_errors: List[Dict[str, Any]] = Field(
        ...,
        description="Pydantic validation errors",
    )
    status_code: int = Field(
        422,
        description="HTTP status code",
    )
    metadata: ResponseMetadata = Field(
        default_factory=ResponseMetadata,
        description="Response metadata",
    )

    @classmethod
    def from_pydantic_errors(
        cls,
        errors: List[Dict[str, Any]],
        request_id: Optional[str] = None,
    ) -> "ValidationErrorDTO":
        """Create ValidationErrorDTO from Pydantic validation errors.

        Args:
            errors: List of Pydantic error dictionaries
            request_id: Optional request ID for tracing

        Returns:
            ValidationErrorDTO instance

        Example:
            from pydantic import ValidationError

            try:
                CompanyDTO(**data)
            except ValidationError as e:
                return ValidationErrorDTO.from_pydantic_errors(e.errors())
        """
        metadata = ResponseMetadata()
        if request_id:
            metadata.request_id = request_id

        return cls(
            validation_errors=errors,
            metadata=metadata,
        )


class NotFoundErrorDTO(BaseDTO):
    """Resource not found error response.

    Specialized error response for 404 Not Found errors.
    """

    success: bool = Field(
        False,
        description="Always False for error responses",
    )
    error: str = Field(
        "NOT_FOUND",
        description="Error code",
    )
    message: str = Field(
        ...,
        description="Error message",
    )
    resource_type: Optional[str] = Field(
        None,
        description="Type of resource that was not found",
    )
    resource_id: Optional[str] = Field(
        None,
        description="ID of resource that was not found",
    )
    status_code: int = Field(
        404,
        description="HTTP status code",
    )
    metadata: ResponseMetadata = Field(
        default_factory=ResponseMetadata,
        description="Response metadata",
    )


class ConflictErrorDTO(BaseDTO):
    """Conflict error response (409).

    Used for duplicate records, concurrent modifications, etc.
    """

    success: bool = Field(
        False,
        description="Always False for error responses",
    )
    error: str = Field(
        "CONFLICT",
        description="Error code",
    )
    message: str = Field(
        ...,
        description="Error message",
    )
    conflict_type: Optional[str] = Field(
        None,
        description="Type of conflict (duplicate, concurrent_modification, etc.)",
    )
    conflicting_field: Optional[str] = Field(
        None,
        description="Field that caused the conflict",
    )
    existing_value: Optional[str] = Field(
        None,
        description="Existing value that conflicts",
    )
    status_code: int = Field(
        409,
        description="HTTP status code",
    )
    metadata: ResponseMetadata = Field(
        default_factory=ResponseMetadata,
        description="Response metadata",
    )


class RateLimitErrorDTO(BaseDTO):
    """Rate limit exceeded error response (429).

    Provides information about rate limits and retry timing.
    """

    success: bool = Field(
        False,
        description="Always False for error responses",
    )
    error: str = Field(
        "RATE_LIMIT_EXCEEDED",
        description="Error code",
    )
    message: str = Field(
        "Rate limit exceeded",
        description="Error message",
    )
    retry_after: Optional[int] = Field(
        None,
        description="Seconds until rate limit resets",
    )
    limit: Optional[int] = Field(
        None,
        description="Rate limit threshold",
    )
    remaining: Optional[int] = Field(
        0,
        description="Remaining requests in current window",
    )
    reset_at: Optional[str] = Field(
        None,
        description="ISO 8601 timestamp when limit resets",
    )
    status_code: int = Field(
        429,
        description="HTTP status code",
    )
    metadata: ResponseMetadata = Field(
        default_factory=ResponseMetadata,
        description="Response metadata",
    )


# Utility functions for creating error responses

def error_response(
    error: str,
    message: str,
    status_code: int = 500,
    details: Optional[List[ErrorDetail]] = None,
    request_id: Optional[str] = None,
) -> ErrorResponseDTO:
    """Create a standardized error response.

    Args:
        error: Error code
        message: Human-readable error message
        status_code: HTTP status code
        details: Optional detailed error information
        request_id: Optional request ID for tracing

    Returns:
        ErrorResponseDTO instance

    Example:
        return error_response(
            error="DATABASE_ERROR",
            message="Failed to connect to database",
            status_code=500
        )
    """
    metadata = ResponseMetadata()
    if request_id:
        metadata.request_id = request_id

    return ErrorResponseDTO(
        success=False,
        error=error,
        message=message,
        details=details,
        status_code=status_code,
        metadata=metadata,
    )


def not_found_error(
    message: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> NotFoundErrorDTO:
    """Create a not found error response.

    Args:
        message: Error message
        resource_type: Type of resource
        resource_id: ID of resource
        request_id: Optional request ID

    Returns:
        NotFoundErrorDTO instance
    """
    metadata = ResponseMetadata()
    if request_id:
        metadata.request_id = request_id

    return NotFoundErrorDTO(
        message=message,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata,
    )


def conflict_error(
    message: str,
    conflict_type: Optional[str] = None,
    conflicting_field: Optional[str] = None,
    existing_value: Optional[str] = None,
    request_id: Optional[str] = None,
) -> ConflictErrorDTO:
    """Create a conflict error response.

    Args:
        message: Error message
        conflict_type: Type of conflict
        conflicting_field: Field that caused conflict
        existing_value: Existing conflicting value
        request_id: Optional request ID

    Returns:
        ConflictErrorDTO instance
    """
    metadata = ResponseMetadata()
    if request_id:
        metadata.request_id = request_id

    return ConflictErrorDTO(
        message=message,
        conflict_type=conflict_type,
        conflicting_field=conflicting_field,
        existing_value=existing_value,
        metadata=metadata,
    )
