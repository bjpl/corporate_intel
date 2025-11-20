"""Pagination DTOs and utilities.

This module provides standardized pagination support for list endpoints,
including cursor-based and offset-based pagination strategies.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from urllib.parse import urlencode

from pydantic import BaseModel, Field, field_validator

from src.dto.base import BaseDTO
from src.dto.responses import ResponseMetadata

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Query parameters for pagination.

    Supports both offset-based and cursor-based pagination.

    Offset-based (default):
        ?limit=20&offset=40

    Cursor-based:
        ?limit=20&cursor=abc123
    """

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (1-100)",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip (offset-based pagination)",
    )
    cursor: Optional[str] = Field(
        None,
        description="Pagination cursor (cursor-based pagination)",
    )

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        """Ensure limit is within acceptable range."""
        if v < 1:
            return 1
        if v > 100:
            return 100
        return v

    @property
    def page(self) -> int:
        """Calculate current page number (1-indexed)."""
        return (self.offset // self.limit) + 1

    def to_query_params(self) -> Dict[str, Any]:
        """Convert to query parameter dictionary."""
        params = {"limit": self.limit}

        if self.cursor:
            params["cursor"] = self.cursor
        else:
            params["offset"] = self.offset

        return params


class PageMetadata(BaseModel):
    """Metadata for paginated responses.

    Provides information about the current page and available navigation.
    """

    total_items: int = Field(
        ...,
        description="Total number of items across all pages",
    )
    total_pages: int = Field(
        ...,
        description="Total number of pages",
    )
    current_page: int = Field(
        ...,
        description="Current page number (1-indexed)",
    )
    page_size: int = Field(
        ...,
        description="Number of items per page",
    )
    has_next: bool = Field(
        ...,
        description="Whether there is a next page",
    )
    has_previous: bool = Field(
        ...,
        description="Whether there is a previous page",
    )
    next_cursor: Optional[str] = Field(
        None,
        description="Cursor for next page (cursor-based pagination)",
    )
    previous_cursor: Optional[str] = Field(
        None,
        description="Cursor for previous page (cursor-based pagination)",
    )

    @classmethod
    def from_offset(
        cls,
        total_items: int,
        limit: int,
        offset: int,
    ) -> "PageMetadata":
        """Create PageMetadata from offset-based pagination parameters.

        Args:
            total_items: Total number of items
            limit: Page size
            offset: Current offset

        Returns:
            PageMetadata instance
        """
        total_pages = (total_items + limit - 1) // limit if total_items > 0 else 0
        current_page = (offset // limit) + 1 if total_items > 0 else 0
        has_next = (offset + limit) < total_items
        has_previous = offset > 0

        return cls(
            total_items=total_items,
            total_pages=total_pages,
            current_page=current_page,
            page_size=limit,
            has_next=has_next,
            has_previous=has_previous,
        )

    @classmethod
    def from_cursor(
        cls,
        total_items: int,
        page_size: int,
        current_page: int,
        has_next: bool,
        has_previous: bool,
        next_cursor: Optional[str] = None,
        previous_cursor: Optional[str] = None,
    ) -> "PageMetadata":
        """Create PageMetadata from cursor-based pagination.

        Args:
            total_items: Total number of items
            page_size: Number of items per page
            current_page: Current page number
            has_next: Whether next page exists
            has_previous: Whether previous page exists
            next_cursor: Cursor for next page
            previous_cursor: Cursor for previous page

        Returns:
            PageMetadata instance
        """
        total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0

        return cls(
            total_items=total_items,
            total_pages=total_pages,
            current_page=current_page,
            page_size=page_size,
            has_next=has_next,
            has_previous=has_previous,
            next_cursor=next_cursor,
            previous_cursor=previous_cursor,
        )


class PaginatedResponseDTO(BaseDTO, Generic[T]):
    """Paginated response wrapper.

    Provides standardized structure for paginated list responses.

    Type Parameters:
        T: Type of items in the data list

    Example:
        PaginatedResponseDTO[CompanyDTO](
            success=True,
            data=[company1, company2, ...],
            pagination=PageMetadata.from_offset(
                total_items=100,
                limit=20,
                offset=0
            ),
            message="Companies retrieved successfully"
        )
    """

    success: bool = Field(
        True,
        description="Whether the request was successful",
    )
    data: List[T] = Field(
        ...,
        description="List of items for current page",
    )
    pagination: PageMetadata = Field(
        ...,
        description="Pagination metadata",
    )
    message: Optional[str] = Field(
        None,
        description="Optional message",
    )
    metadata: ResponseMetadata = Field(
        default_factory=ResponseMetadata,
        description="Response metadata",
    )


class PageLinks(BaseModel):
    """Navigation links for paginated responses.

    Provides HATEOAS-style navigation links for API clients.
    """

    self: str = Field(..., description="Current page URL")
    first: str = Field(..., description="First page URL")
    last: str = Field(..., description="Last page URL")
    next: Optional[str] = Field(None, description="Next page URL")
    previous: Optional[str] = Field(None, description="Previous page URL")

    @classmethod
    def generate(
        cls,
        base_url: str,
        current_params: PaginationParams,
        page_metadata: PageMetadata,
        additional_params: Optional[Dict[str, Any]] = None,
    ) -> "PageLinks":
        """Generate navigation links for paginated response.

        Args:
            base_url: Base URL for the endpoint
            current_params: Current pagination parameters
            page_metadata: Page metadata with navigation info
            additional_params: Additional query parameters (filters, etc.)

        Returns:
            PageLinks instance
        """
        def build_url(limit: int, offset: int) -> str:
            params = {"limit": limit, "offset": offset}
            if additional_params:
                params.update(additional_params)
            return f"{base_url}?{urlencode(params)}"

        limit = current_params.limit
        offset = current_params.offset

        # Self link
        self_link = build_url(limit, offset)

        # First page link
        first_link = build_url(limit, 0)

        # Last page link
        last_offset = max(0, (page_metadata.total_pages - 1) * limit)
        last_link = build_url(limit, last_offset)

        # Next page link
        next_link = None
        if page_metadata.has_next:
            next_link = build_url(limit, offset + limit)

        # Previous page link
        previous_link = None
        if page_metadata.has_previous:
            previous_offset = max(0, offset - limit)
            previous_link = build_url(limit, previous_offset)

        return cls(
            self=self_link,
            first=first_link,
            last=last_link,
            next=next_link,
            previous=previous_link,
        )


# Utility functions for creating paginated responses

def paginated_response(
    data: List[T],
    total_items: int,
    pagination_params: PaginationParams,
    message: Optional[str] = None,
) -> PaginatedResponseDTO[T]:
    """Create a paginated response using offset-based pagination.

    Args:
        data: List of items for current page
        total_items: Total number of items across all pages
        pagination_params: Pagination parameters from request
        message: Optional message

    Returns:
        PaginatedResponseDTO instance

    Example:
        # In API endpoint
        params = PaginationParams(limit=20, offset=0)
        companies = query.offset(params.offset).limit(params.limit).all()
        total = query.count()

        return paginated_response(
            data=[CompanyDTO.from_orm(c) for c in companies],
            total_items=total,
            pagination_params=params
        )
    """
    pagination = PageMetadata.from_offset(
        total_items=total_items,
        limit=pagination_params.limit,
        offset=pagination_params.offset,
    )

    return PaginatedResponseDTO(
        success=True,
        data=data,
        pagination=pagination,
        message=message,
    )


def cursor_paginated_response(
    data: List[T],
    total_items: int,
    page_size: int,
    current_page: int,
    next_cursor: Optional[str] = None,
    previous_cursor: Optional[str] = None,
    message: Optional[str] = None,
) -> PaginatedResponseDTO[T]:
    """Create a paginated response using cursor-based pagination.

    Args:
        data: List of items for current page
        total_items: Total number of items
        page_size: Number of items per page
        current_page: Current page number
        next_cursor: Cursor for next page
        previous_cursor: Cursor for previous page
        message: Optional message

    Returns:
        PaginatedResponseDTO instance
    """
    has_next = next_cursor is not None
    has_previous = previous_cursor is not None

    pagination = PageMetadata.from_cursor(
        total_items=total_items,
        page_size=page_size,
        current_page=current_page,
        has_next=has_next,
        has_previous=has_previous,
        next_cursor=next_cursor,
        previous_cursor=previous_cursor,
    )

    return PaginatedResponseDTO(
        success=True,
        data=data,
        pagination=pagination,
        message=message,
    )
