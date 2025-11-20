"""Data Transfer Objects (DTOs) for API request/response models.

This module provides a comprehensive DTO layer for standardized API responses,
validation, serialization, and error handling across the corporate intelligence platform.

Core Components:
    - BaseDTO: Foundation for all DTOs with common functionality
    - ResponseDTO: Standardized success response wrapper
    - ErrorResponseDTO: Standardized error response format
    - PaginatedResponseDTO: Paginated data responses
    - ValidationMixin: Common validation utilities

Usage:
    from src.dto import BaseDTO, ResponseDTO, ErrorResponseDTO
    from src.dto.responses import success_response, paginated_response
    from src.dto.validators import validate_ticker, validate_date_range

Example:
    class CompanyDTO(BaseDTO):
        ticker: str
        name: str

        class Config:
            from_attributes = True

    # In API endpoint
    return success_response(
        data=CompanyDTO.from_orm(company),
        message="Company retrieved successfully"
    )
"""

from src.dto.base import BaseDTO, TimestampMixin, UUIDMixin, from_orm_list
from src.dto.errors import ErrorDetail, ErrorResponseDTO, ValidationErrorDTO
from src.dto.pagination import (
    PageMetadata,
    PaginatedResponseDTO,
    PaginationParams,
)
from src.dto.responses import ResponseDTO, ResponseMetadata, success_response
from src.dto.validators import (
    validate_date_range,
    validate_ticker,
    validate_uuid,
    ValidationMixin,
)

__all__ = [
    # Base classes
    "BaseDTO",
    "TimestampMixin",
    "UUIDMixin",
    "ValidationMixin",
    # Response models
    "ResponseDTO",
    "ResponseMetadata",
    "ErrorResponseDTO",
    "ErrorDetail",
    "ValidationErrorDTO",
    "PaginatedResponseDTO",
    "PageMetadata",
    "PaginationParams",
    # Utility functions
    "success_response",
    "from_orm_list",
    "validate_ticker",
    "validate_uuid",
    "validate_date_range",
]
