"""Tests for base DTO functionality."""

import pytest
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import ValidationError

from src.dto.base import (
    BaseDTO,
    TimestampedDTO,
    PaginatedRequest,
    PaginatedResponse,
    ErrorDetail,
    ErrorResponse,
    SuccessResponse,
    IDMixin,
    OptionalFilterDTO,
    create_example_schema,
)


class TestBaseDTO:
    """Test BaseDTO core functionality."""

    def test_base_dto_initialization(self):
        """Test basic DTO initialization."""

        class TestDTO(BaseDTO):
            name: str
            value: int

        dto = TestDTO(name="test", value=42)
        assert dto.name == "test"
        assert dto.value == 42

    def test_base_dto_from_dict(self):
        """Test DTO creation from dictionary."""

        class TestDTO(BaseDTO):
            name: str
            count: int

        data = {"name": "test", "count": 10}
        dto = TestDTO(**data)
        assert dto.name == "test"
        assert dto.count == 10

    def test_base_dto_to_dict(self):
        """Test DTO serialization to dictionary."""

        class TestDTO(BaseDTO):
            name: str
            value: int

        dto = TestDTO(name="test", value=42)
        data = dto.model_dump()
        assert data == {"name": "test", "value": 42}

    def test_base_dto_validation_error(self):
        """Test DTO validation errors."""

        class TestDTO(BaseDTO):
            name: str
            count: int

        with pytest.raises(ValidationError) as exc_info:
            TestDTO(name="test", count="invalid")

        assert "count" in str(exc_info.value)

    def test_base_dto_whitespace_stripping(self):
        """Test automatic whitespace stripping."""

        class TestDTO(BaseDTO):
            name: str

        dto = TestDTO(name="  test  ")
        assert dto.name == "test"

    def test_base_dto_from_attributes(self):
        """Test DTO creation from ORM object."""

        class TestDTO(BaseDTO):
            id: int
            name: str

        class MockORM:
            id = 1
            name = "test"

        dto = TestDTO.model_validate(MockORM)
        assert dto.id == 1
        assert dto.name == "test"


class TestTimestampedDTO:
    """Test TimestampedDTO with timestamp fields."""

    def test_timestamped_dto_creation(self):
        """Test creation with timestamp fields."""
        now = datetime.utcnow()

        class TestDTO(TimestampedDTO):
            name: str

        dto = TestDTO(name="test", created_at=now)
        assert dto.name == "test"
        assert dto.created_at == now
        assert dto.updated_at is None

    def test_timestamped_dto_with_updates(self):
        """Test DTO with update timestamp."""
        created = datetime(2025, 1, 1, 12, 0, 0)
        updated = datetime(2025, 1, 2, 12, 0, 0)

        class TestDTO(TimestampedDTO):
            name: str

        dto = TestDTO(name="test", created_at=created, updated_at=updated)
        assert dto.created_at == created
        assert dto.updated_at == updated


class TestPaginatedRequest:
    """Test pagination request parameters."""

    def test_default_pagination_params(self):
        """Test default pagination values."""
        request = PaginatedRequest()
        assert request.limit == 100
        assert request.offset == 0

    def test_custom_pagination_params(self):
        """Test custom pagination values."""
        request = PaginatedRequest(limit=50, offset=25)
        assert request.limit == 50
        assert request.offset == 25

    def test_pagination_limit_validation(self):
        """Test pagination limit bounds."""
        # Valid limit
        request = PaginatedRequest(limit=100)
        assert request.limit == 100

        # Minimum limit
        request = PaginatedRequest(limit=1)
        assert request.limit == 1

        # Maximum limit
        request = PaginatedRequest(limit=500)
        assert request.limit == 500

        # Below minimum
        with pytest.raises(ValidationError):
            PaginatedRequest(limit=0)

        # Above maximum
        with pytest.raises(ValidationError):
            PaginatedRequest(limit=501)

    def test_pagination_offset_validation(self):
        """Test pagination offset validation."""
        # Valid offset
        request = PaginatedRequest(offset=0)
        assert request.offset == 0

        # Negative offset should fail
        with pytest.raises(ValidationError):
            PaginatedRequest(offset=-1)


class TestPaginatedResponse:
    """Test paginated response wrapper."""

    def test_paginated_response_creation(self):
        """Test manual paginated response creation."""
        items = [1, 2, 3, 4, 5]
        response = PaginatedResponse(
            items=items,
            total=100,
            limit=10,
            offset=0,
            has_more=True
        )

        assert response.items == items
        assert response.total == 100
        assert response.limit == 10
        assert response.offset == 0
        assert response.has_more is True

    def test_paginated_response_factory(self):
        """Test factory method for paginated response."""
        items = [1, 2, 3, 4, 5]
        response = PaginatedResponse.create(
            items=items,
            total=100,
            limit=10,
            offset=0
        )

        assert response.items == items
        assert response.total == 100
        assert response.limit == 10
        assert response.offset == 0
        assert response.has_more is True

    def test_paginated_response_has_more_calculation(self):
        """Test has_more flag calculation."""
        # Has more items
        response = PaginatedResponse.create(
            items=[1, 2, 3],
            total=10,
            limit=3,
            offset=0
        )
        assert response.has_more is True

        # No more items
        response = PaginatedResponse.create(
            items=[8, 9, 10],
            total=10,
            limit=3,
            offset=7
        )
        assert response.has_more is False

        # Exact last page
        response = PaginatedResponse.create(
            items=[1, 2],
            total=2,
            limit=2,
            offset=0
        )
        assert response.has_more is False


class TestErrorDetail:
    """Test error detail structure."""

    def test_error_detail_minimal(self):
        """Test error detail with minimal fields."""
        error = ErrorDetail(
            code="VALIDATION_ERROR",
            message="Invalid input"
        )

        assert error.code == "VALIDATION_ERROR"
        assert error.message == "Invalid input"
        assert error.field is None
        assert error.details is None

    def test_error_detail_complete(self):
        """Test error detail with all fields."""
        error = ErrorDetail(
            code="VALIDATION_ERROR",
            message="Invalid ticker format",
            field="ticker",
            details={"pattern": "^[A-Z]{1,5}$", "provided": "invalid123"}
        )

        assert error.code == "VALIDATION_ERROR"
        assert error.message == "Invalid ticker format"
        assert error.field == "ticker"
        assert error.details["pattern"] == "^[A-Z]{1,5}$"


class TestErrorResponse:
    """Test error response structure."""

    def test_error_response_minimal(self):
        """Test error response with minimal fields."""
        response = ErrorResponse(
            error="ValidationError",
            message="Request validation failed"
        )

        assert response.error == "ValidationError"
        assert response.message == "Request validation failed"
        assert response.details is None
        assert response.request_id is None
        assert isinstance(response.timestamp, datetime)

    def test_error_response_with_details(self):
        """Test error response with detailed errors."""
        detail = ErrorDetail(
            code="INVALID_FORMAT",
            message="Ticker must be uppercase",
            field="ticker"
        )

        response = ErrorResponse(
            error="ValidationError",
            message="Request validation failed",
            details=[detail],
            request_id="req_123"
        )

        assert len(response.details) == 1
        assert response.details[0].code == "INVALID_FORMAT"
        assert response.request_id == "req_123"


class TestSuccessResponse:
    """Test success response structure."""

    def test_success_response(self):
        """Test success response creation."""
        response = SuccessResponse(message="Operation completed successfully")

        assert response.success is True
        assert response.message == "Operation completed successfully"
        assert isinstance(response.timestamp, datetime)


class TestIDMixin:
    """Test UUID ID mixin."""

    def test_id_mixin(self):
        """Test ID mixin with UUID."""
        test_id = uuid4()

        class TestDTO(IDMixin):
            name: str

        dto = TestDTO(id=test_id, name="test")
        assert dto.id == test_id
        assert isinstance(dto.id, UUID)

    def test_id_mixin_validation(self):
        """Test ID validation."""

        class TestDTO(IDMixin):
            name: str

        # Valid UUID string
        dto = TestDTO(id="550e8400-e29b-41d4-a716-446655440000", name="test")
        assert isinstance(dto.id, UUID)

        # Invalid UUID
        with pytest.raises(ValidationError):
            TestDTO(id="invalid-uuid", name="test")


class TestOptionalFilterDTO:
    """Test optional filter parameters."""

    def test_optional_filter_defaults(self):
        """Test default filter values."""
        filters = OptionalFilterDTO()

        assert filters.created_after is None
        assert filters.created_before is None
        assert filters.sort_by is None
        assert filters.sort_order == "desc"

    def test_optional_filter_custom_values(self):
        """Test custom filter values."""
        after = datetime(2025, 1, 1)
        before = datetime(2025, 12, 31)

        filters = OptionalFilterDTO(
            created_after=after,
            created_before=before,
            sort_by="created_at",
            sort_order="asc"
        )

        assert filters.created_after == after
        assert filters.created_before == before
        assert filters.sort_by == "created_at"
        assert filters.sort_order == "asc"

    def test_sort_order_validation(self):
        """Test sort order validation."""
        # Valid values
        filters = OptionalFilterDTO(sort_order="asc")
        assert filters.sort_order == "asc"

        filters = OptionalFilterDTO(sort_order="desc")
        assert filters.sort_order == "desc"

        # Invalid value
        with pytest.raises(ValidationError):
            OptionalFilterDTO(sort_order="invalid")


class TestUtilityFunctions:
    """Test utility functions."""

    def test_create_example_schema(self):
        """Test example schema creation."""
        examples = [
            {"name": "test1", "value": 1},
            {"name": "test2", "value": 2}
        ]

        schema = create_example_schema(examples)

        assert "json_schema_extra" in schema
        assert schema["json_schema_extra"]["examples"] == examples


class TestDTOSerialization:
    """Test DTO serialization and deserialization."""

    def test_dto_json_serialization(self):
        """Test JSON serialization."""

        class TestDTO(BaseDTO):
            id: UUID
            created_at: datetime
            name: str

        test_id = uuid4()
        now = datetime.utcnow()

        dto = TestDTO(id=test_id, created_at=now, name="test")
        json_str = dto.model_dump_json()

        assert str(test_id) in json_str
        assert "test" in json_str

    def test_dto_json_deserialization(self):
        """Test JSON deserialization."""

        class TestDTO(BaseDTO):
            id: UUID
            name: str

        json_str = '{"id": "550e8400-e29b-41d4-a716-446655440000", "name": "test"}'
        dto = TestDTO.model_validate_json(json_str)

        assert dto.name == "test"
        assert isinstance(dto.id, UUID)


class TestDTOValidation:
    """Test DTO validation edge cases."""

    def test_required_field_validation(self):
        """Test required field validation."""

        class TestDTO(BaseDTO):
            required_field: str
            optional_field: str = None

        # Missing required field
        with pytest.raises(ValidationError) as exc_info:
            TestDTO(optional_field="test")

        assert "required_field" in str(exc_info.value)

    def test_type_coercion(self):
        """Test type coercion."""

        class TestDTO(BaseDTO):
            count: int
            price: float

        # String to int
        dto = TestDTO(count="42", price="3.14")
        assert dto.count == 42
        assert dto.price == 3.14
        assert isinstance(dto.count, int)
        assert isinstance(dto.price, float)

    def test_nested_dto_validation(self):
        """Test nested DTO validation."""

        class InnerDTO(BaseDTO):
            value: int

        class OuterDTO(BaseDTO):
            name: str
            inner: InnerDTO

        # Valid nested structure
        dto = OuterDTO(
            name="test",
            inner=InnerDTO(value=42)
        )
        assert dto.inner.value == 42

        # Valid with dict
        dto = OuterDTO(
            name="test",
            inner={"value": 42}
        )
        assert dto.inner.value == 42

        # Invalid nested structure
        with pytest.raises(ValidationError):
            OuterDTO(
                name="test",
                inner={"value": "invalid"}
            )


class TestDTOPerformance:
    """Test DTO performance characteristics."""

    def test_large_list_validation(self):
        """Test validation of large lists."""

        class ItemDTO(BaseDTO):
            id: int
            name: str

        class ListDTO(BaseDTO):
            items: list[ItemDTO]

        # Create 1000 items
        items = [{"id": i, "name": f"item_{i}"} for i in range(1000)]
        dto = ListDTO(items=items)

        assert len(dto.items) == 1000
        assert dto.items[0].id == 0
        assert dto.items[999].name == "item_999"

    def test_dto_copy_performance(self):
        """Test DTO copying."""

        class TestDTO(BaseDTO):
            id: int
            name: str
            data: dict

        original = TestDTO(
            id=1,
            name="test",
            data={"key": "value"}
        )

        # Shallow copy
        copy = original.model_copy()
        assert copy.id == original.id
        assert copy.name == original.name
        assert copy is not original
