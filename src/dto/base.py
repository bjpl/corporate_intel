"""Base DTO classes and serialization utilities.

This module provides foundation classes for all DTOs in the application,
including common mixins, serialization helpers, and ORM conversion utilities.
"""

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer
from sqlalchemy.ext.declarative import DeclarativeMeta

T = TypeVar("T", bound=BaseModel)
ORM = TypeVar("ORM")


class BaseDTO(BaseModel):
    """Base class for all DTOs with common configuration and utilities.

    Provides:
        - Automatic ORM mapping with from_attributes
        - JSON encoding for complex types (UUID, datetime)
        - Null handling and optional field support
        - Serialization customization hooks

    Example:
        class CompanyDTO(BaseDTO):
            id: UUID
            ticker: str
            name: str
            created_at: datetime

            @field_serializer('created_at')
            def serialize_datetime(self, dt: datetime) -> str:
                return dt.isoformat()
    """

    model_config = ConfigDict(
        # Enable ORM mode for SQLAlchemy model conversion
        from_attributes=True,
        # Use enum values instead of enum instances
        use_enum_values=True,
        # Validate assignment after model creation
        validate_assignment=True,
        # Allow arbitrary types (for complex objects)
        arbitrary_types_allowed=True,
        # Populate by name (allows field aliases)
        populate_by_name=True,
        # JSON schema extras
        json_schema_extra={
            "examples": []
        },
    )

    @classmethod
    def from_orm(cls: Type[T], obj: Any) -> T:
        """Create DTO instance from SQLAlchemy ORM model.

        Args:
            obj: SQLAlchemy model instance

        Returns:
            DTO instance populated from ORM model

        Example:
            company = db.query(Company).first()
            company_dto = CompanyDTO.from_orm(company)
        """
        if obj is None:
            return None
        return cls.model_validate(obj)

    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """Create DTO instance from dictionary.

        Args:
            data: Dictionary with field values

        Returns:
            DTO instance
        """
        return cls(**data)

    def to_dict(
        self,
        exclude_none: bool = False,
        exclude_unset: bool = False,
        by_alias: bool = False,
    ) -> Dict[str, Any]:
        """Convert DTO to dictionary.

        Args:
            exclude_none: Exclude fields with None values
            exclude_unset: Exclude fields that weren't explicitly set
            by_alias: Use field aliases instead of field names

        Returns:
            Dictionary representation
        """
        return self.model_dump(
            exclude_none=exclude_none,
            exclude_unset=exclude_unset,
            by_alias=by_alias,
        )

    def to_json(
        self,
        exclude_none: bool = False,
        indent: Optional[int] = None,
    ) -> str:
        """Convert DTO to JSON string.

        Args:
            exclude_none: Exclude fields with None values
            indent: JSON indentation (None for compact)

        Returns:
            JSON string
        """
        return self.model_dump_json(
            exclude_none=exclude_none,
            indent=indent,
        )


class UUIDMixin(BaseModel):
    """Mixin for models with UUID primary key.

    Provides automatic UUID serialization and validation.
    """

    id: UUID = Field(..., description="Unique identifier")

    @field_serializer('id')
    def serialize_uuid(self, uuid_val: UUID) -> str:
        """Serialize UUID to string."""
        return str(uuid_val)


class TimestampMixin(BaseModel):
    """Mixin for models with created_at and updated_at timestamps.

    Provides automatic datetime serialization to ISO format.
    """

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO 8601 string."""
        if dt is None:
            return None
        return dt.isoformat()


class SoftDeleteMixin(BaseModel):
    """Mixin for models with soft delete support."""

    deleted_at: Optional[datetime] = Field(None, description="Deletion timestamp")
    is_deleted: bool = Field(False, description="Soft delete flag")

    @field_serializer('deleted_at')
    def serialize_deleted_at(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize deleted_at datetime."""
        if dt is None:
            return None
        return dt.isoformat()


# Serialization utility functions

def from_orm_list(
    model_class: Type[T],
    orm_objects: List[Any],
) -> List[T]:
    """Convert list of ORM objects to list of DTOs.

    Args:
        model_class: DTO class to convert to
        orm_objects: List of SQLAlchemy ORM instances

    Returns:
        List of DTO instances

    Example:
        companies = db.query(Company).all()
        company_dtos = from_orm_list(CompanyDTO, companies)
    """
    if not orm_objects:
        return []
    return [model_class.from_orm(obj) for obj in orm_objects]


def serialize_sqlalchemy_model(
    obj: Any,
    exclude_fields: Optional[List[str]] = None,
    include_relationships: bool = False,
) -> Dict[str, Any]:
    """Serialize SQLAlchemy model to dictionary.

    Args:
        obj: SQLAlchemy model instance
        exclude_fields: Fields to exclude from serialization
        include_relationships: Whether to include relationship fields

    Returns:
        Dictionary representation of the model

    Example:
        company = db.query(Company).first()
        data = serialize_sqlalchemy_model(company, exclude_fields=['raw_text'])
    """
    if obj is None:
        return None

    exclude_fields = exclude_fields or []
    result = {}

    # Get model mapper
    mapper = obj.__class__.__mapper__

    # Serialize column fields
    for column in mapper.columns:
        if column.name in exclude_fields:
            continue

        value = getattr(obj, column.name)

        # Handle special types
        if isinstance(value, UUID):
            result[column.name] = str(value)
        elif isinstance(value, datetime):
            result[column.name] = value.isoformat()
        else:
            result[column.name] = value

    # Optionally include relationships
    if include_relationships:
        for relationship in mapper.relationships:
            if relationship.key in exclude_fields:
                continue

            rel_value = getattr(obj, relationship.key)

            if rel_value is None:
                result[relationship.key] = None
            elif isinstance(rel_value, list):
                result[relationship.key] = [
                    serialize_sqlalchemy_model(item, exclude_fields)
                    for item in rel_value
                ]
            else:
                result[relationship.key] = serialize_sqlalchemy_model(
                    rel_value,
                    exclude_fields
                )

    return result


def handle_null_values(
    data: Dict[str, Any],
    null_strategy: str = "keep",
) -> Dict[str, Any]:
    """Handle null/None values in dictionary.

    Args:
        data: Dictionary with potential null values
        null_strategy: Strategy for handling nulls:
            - "keep": Keep null values (default)
            - "remove": Remove keys with null values
            - "empty_string": Replace nulls with empty string
            - "zero": Replace numeric nulls with 0

    Returns:
        Processed dictionary
    """
    if null_strategy == "keep":
        return data

    result = {}

    for key, value in data.items():
        if value is None:
            if null_strategy == "remove":
                continue
            elif null_strategy == "empty_string":
                result[key] = ""
            elif null_strategy == "zero":
                result[key] = 0
            else:
                result[key] = None
        else:
            result[key] = value

    return result


def format_currency(
    amount: Optional[float],
    currency: str = "USD",
    decimals: int = 2,
) -> Optional[str]:
    """Format numeric amount as currency string.

    Args:
        amount: Numeric amount
        currency: Currency code (USD, EUR, etc.)
        decimals: Number of decimal places

    Returns:
        Formatted currency string or None

    Example:
        format_currency(1234567.89)  # "$1,234,567.89"
    """
    if amount is None:
        return None

    if currency == "USD":
        return f"${amount:,.{decimals}f}"
    elif currency == "EUR":
        return f"€{amount:,.{decimals}f}"
    else:
        return f"{currency} {amount:,.{decimals}f}"


def format_percentage(
    value: Optional[float],
    decimals: int = 2,
    include_sign: bool = True,
) -> Optional[str]:
    """Format numeric value as percentage string.

    Args:
        value: Numeric value (0.15 for 15%)
        decimals: Number of decimal places
        include_sign: Include + sign for positive values

    Returns:
        Formatted percentage string or None

    Example:
        format_percentage(0.1523)  # "+15.23%"
        format_percentage(-0.05)   # "-5.00%"
    """
    if value is None:
        return None

    percentage = value * 100
    formatted = f"{percentage:.{decimals}f}%"

    if include_sign and percentage > 0:
        formatted = f"+{formatted}"

    return formatted
