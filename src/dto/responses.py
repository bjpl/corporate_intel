"""Standard response wrappers for API endpoints.

This module provides consistent response structures for all API endpoints,
including success responses, metadata, and utility functions for creating responses.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union

from pydantic import BaseModel, Field

from src.dto.base import BaseDTO

T = TypeVar("T")


class ResponseMetadata(BaseModel):
    """Metadata for API responses.

    Provides additional context about the response such as timestamps,
    request IDs for tracing, and API version information.
    """

    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="ISO 8601 timestamp when response was generated",
    )
    request_id: Optional[str] = Field(
        None,
        description="Unique request ID for tracing and debugging",
    )
    api_version: str = Field(
        default="v1",
        description="API version that handled the request",
    )
    execution_time_ms: Optional[float] = Field(
        None,
        description="Request execution time in milliseconds",
    )


class ResponseDTO(BaseDTO, Generic[T]):
    """Generic success response wrapper.

    Provides standardized structure for successful API responses with:
        - Consistent success flag
        - Typed data payload
        - Optional message
        - Response metadata

    Type Parameters:
        T: Type of the data payload

    Example:
        # Single object response
        ResponseDTO[CompanyDTO](
            success=True,
            data=company_dto,
            message="Company retrieved successfully"
        )

        # List response
        ResponseDTO[List[CompanyDTO]](
            success=True,
            data=company_list,
            message="Companies retrieved successfully"
        )
    """

    success: bool = Field(
        True,
        description="Whether the request was successful",
    )
    data: Optional[T] = Field(
        None,
        description="Response payload data",
    )
    message: Optional[str] = Field(
        None,
        description="Optional human-readable message",
    )
    metadata: ResponseMetadata = Field(
        default_factory=ResponseMetadata,
        description="Response metadata",
    )


class EmptyResponseDTO(BaseDTO):
    """Empty success response for operations that don't return data.

    Used for DELETE operations and other actions that succeed but
    don't need to return payload data.

    Example:
        # DELETE endpoint
        return EmptyResponseDTO(
            success=True,
            message="Company deleted successfully"
        )
    """

    success: bool = Field(
        True,
        description="Whether the request was successful",
    )
    message: Optional[str] = Field(
        None,
        description="Optional human-readable message",
    )
    metadata: ResponseMetadata = Field(
        default_factory=ResponseMetadata,
        description="Response metadata",
    )


class BulkOperationResponseDTO(BaseDTO):
    """Response for bulk operations.

    Provides detailed results for operations affecting multiple records,
    including counts of successful, failed, and skipped operations.

    Example:
        BulkOperationResponseDTO(
            success=True,
            total=100,
            successful=95,
            failed=3,
            skipped=2,
            message="Bulk import completed with 3 failures"
        )
    """

    success: bool = Field(
        ...,
        description="Whether the overall operation was successful",
    )
    total: int = Field(
        ...,
        description="Total number of records processed",
    )
    successful: int = Field(
        ...,
        description="Number of successful operations",
    )
    failed: int = Field(
        0,
        description="Number of failed operations",
    )
    skipped: int = Field(
        0,
        description="Number of skipped operations",
    )
    errors: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="List of errors for failed operations",
    )
    message: Optional[str] = Field(
        None,
        description="Overall operation message",
    )
    metadata: ResponseMetadata = Field(
        default_factory=ResponseMetadata,
        description="Response metadata",
    )


# Utility functions for creating responses

def success_response(
    data: Optional[T] = None,
    message: Optional[str] = None,
    metadata: Optional[ResponseMetadata] = None,
) -> ResponseDTO[T]:
    """Create a standardized success response.

    Args:
        data: Response payload data
        message: Optional success message
        metadata: Optional custom metadata

    Returns:
        ResponseDTO instance

    Example:
        # Simple success response
        return success_response(
            data=CompanyDTO.from_orm(company),
            message="Company created successfully"
        )

        # Response with custom metadata
        return success_response(
            data=companies,
            metadata=ResponseMetadata(request_id="abc123")
        )
    """
    return ResponseDTO(
        success=True,
        data=data,
        message=message,
        metadata=metadata or ResponseMetadata(),
    )


def empty_success_response(
    message: Optional[str] = None,
    metadata: Optional[ResponseMetadata] = None,
) -> EmptyResponseDTO:
    """Create an empty success response (no data payload).

    Args:
        message: Optional success message
        metadata: Optional custom metadata

    Returns:
        EmptyResponseDTO instance

    Example:
        # DELETE endpoint
        return empty_success_response(
            message="Company deleted successfully"
        )
    """
    return EmptyResponseDTO(
        success=True,
        message=message,
        metadata=metadata or ResponseMetadata(),
    )


def bulk_operation_response(
    total: int,
    successful: int,
    failed: int = 0,
    skipped: int = 0,
    errors: Optional[List[Dict[str, Any]]] = None,
    message: Optional[str] = None,
) -> BulkOperationResponseDTO:
    """Create a bulk operation response.

    Args:
        total: Total records processed
        successful: Number of successful operations
        failed: Number of failed operations
        skipped: Number of skipped operations
        errors: List of error details
        message: Optional message

    Returns:
        BulkOperationResponseDTO instance

    Example:
        return bulk_operation_response(
            total=100,
            successful=95,
            failed=5,
            errors=[{"id": "123", "error": "Duplicate ticker"}],
            message="Bulk import completed with some failures"
        )
    """
    success = failed == 0

    if not message:
        if success:
            message = f"Successfully processed {successful} of {total} records"
        else:
            message = f"Processed {total} records: {successful} successful, {failed} failed"

    return BulkOperationResponseDTO(
        success=success,
        total=total,
        successful=successful,
        failed=failed,
        skipped=skipped,
        errors=errors,
        message=message,
    )


class HealthCheckResponseDTO(BaseDTO):
    """Health check response.

    Provides service health status and component details.
    """

    status: str = Field(
        ...,
        description="Overall health status: healthy, degraded, unhealthy",
    )
    version: str = Field(
        ...,
        description="Application version",
    )
    environment: str = Field(
        ...,
        description="Deployment environment",
    )
    components: Optional[Dict[str, Any]] = Field(
        None,
        description="Health status of individual components",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Health check timestamp",
    )


def health_check_response(
    status: str,
    version: str,
    environment: str,
    components: Optional[Dict[str, Any]] = None,
) -> HealthCheckResponseDTO:
    """Create a health check response.

    Args:
        status: Health status (healthy, degraded, unhealthy)
        version: Application version
        environment: Deployment environment
        components: Component health details

    Returns:
        HealthCheckResponseDTO instance
    """
    return HealthCheckResponseDTO(
        status=status,
        version=version,
        environment=environment,
        components=components,
    )
