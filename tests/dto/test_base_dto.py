"""Tests for base DTO infrastructure."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from src.dto.base import (
    BaseDTO,
    ErrorDetail,
    ErrorResponse,
    IDMixin,
    PaginatedRequest,
    PaginatedResponse,
    SuccessResponse,
    TimestampedDTO,
)


class TestBaseDTO:
    """Test BaseDTO functionality."""

    def test_base_dto_creation(self):
        """Test creating a basic DTO."""
        class SimpleDTO(BaseDTO):
            name: str
            value: int

        dto = SimpleDTO(name="test", value=42)
        assert dto.name == "test"
        assert dto.value == 42

    def test_base_dto_validation(self):
        """Test DTO validation."""
        class ValidatedDTO(BaseDTO):
            age: int

        # Valid
        dto = ValidatedDTO(age=25)
        assert dto.age == 25

        # Invalid - wrong type
        with pytest.raises(ValidationError):
            ValidatedDTO(age="not a number")

    def test_base_dto_from_attributes(self):
        """Test DTO creation from object attributes."""
        class MockModel:
            def __init__(self):
                self.name = "test"
                self.value = 42

        class DTOFromModel(BaseDTO):
            name: str
            value: int

        model = MockModel()
        dto = DTOFromModel.model_validate(model)
        assert dto.name == "test"
        assert dto.value == 42


class TestTimestampedDTO:
    """Test TimestampedDTO mixin."""

    def test_timestamped_dto(self):
        """Test DTO with timestamp fields."""
        class TimestampedEntity(TimestampedDTO):
            name: str

        now = datetime.utcnow()
        dto = TimestampedEntity(
            name="test",
            created_at=now,
            updated_at=now
        )

        assert dto.name == "test"
        assert dto.created_at == now
        assert dto.updated_at == now

    def test_optional_updated_at(self):
        """Test that updated_at is optional."""
        class TimestampedEntity(TimestampedDTO):
            name: str

        now = datetime.utcnow()
        dto = TimestampedEntity(
            name="test",
            created_at=now
        )

        assert dto.created_at == now
        assert dto.updated_at is None


class TestPaginatedRequest:
    """Test PaginatedRequest DTO."""

    def test_default_values(self):
        """Test default pagination values."""
        req = PaginatedRequest()
        assert req.limit == 100
        assert req.offset == 0

    def test_custom_values(self):
        """Test custom pagination values."""
        req = PaginatedRequest(limit=50, offset=25)
        assert req.limit == 50
        assert req.offset == 25

    def test_validation_limits(self):
        """Test validation of limit constraints."""
        # Too small
        with pytest.raises(ValidationError):
            PaginatedRequest(limit=0)

        # Too large
        with pytest.raises(ValidationError):
            PaginatedRequest(limit=1000)

        # Negative offset
        with pytest.raises(ValidationError):
            PaginatedRequest(offset=-1)


class TestPaginatedResponse:
    """Test PaginatedResponse DTO."""

    def test_create_factory(self):
        """Test factory method for creating paginated response."""
        items = ["item1", "item2", "item3"]
        response = PaginatedResponse.create(
            items=items,
            total=10,
            limit=3,
            offset=0
        )

        assert response.items == items
        assert response.total == 10
        assert response.limit == 3
        assert response.offset == 0
        assert response.has_more is True

    def test_has_more_false(self):
        """Test has_more calculation when no more items."""
        items = ["item1", "item2"]
        response = PaginatedResponse.create(
            items=items,
            total=2,
            limit=10,
            offset=0
        )

        assert response.has_more is False

    def test_has_more_with_offset(self):
        """Test has_more with offset."""
        items = ["item6", "item7", "item8", "item9", "item10"]
        response = PaginatedResponse.create(
            items=items,
            total=15,
            limit=5,
            offset=5
        )

        assert response.has_more is True


class TestErrorDetail:
    """Test ErrorDetail DTO."""

    def test_basic_error_detail(self):
        """Test creating basic error detail."""
        error = ErrorDetail(
            code="VALIDATION_ERROR",
            message="Invalid input"
        )

        assert error.code == "VALIDATION_ERROR"
        assert error.message == "Invalid input"
        assert error.field is None
        assert error.details is None

    def test_field_specific_error(self):
        """Test error detail with field."""
        error = ErrorDetail(
            code="INVALID_FORMAT",
            message="Invalid ticker format",
            field="ticker",
            details={"pattern": "^[A-Z]+$"}
        )

        assert error.field == "ticker"
        assert error.details["pattern"] == "^[A-Z]+$"


class TestErrorResponse:
    """Test ErrorResponse DTO."""

    def test_basic_error_response(self):
        """Test creating basic error response."""
        response = ErrorResponse(
            error="ValidationError",
            message="Request validation failed"
        )

        assert response.error == "ValidationError"
        assert response.message == "Request validation failed"
        assert response.details is None
        assert isinstance(response.timestamp, datetime)

    def test_error_with_details(self):
        """Test error response with details."""
        detail = ErrorDetail(
            code="INVALID_FORMAT",
            message="Invalid ticker",
            field="ticker"
        )

        response = ErrorResponse(
            error="ValidationError",
            message="Validation failed",
            details=[detail],
            request_id="req_123"
        )

        assert len(response.details) == 1
        assert response.details[0].code == "INVALID_FORMAT"
        assert response.request_id == "req_123"


class TestSuccessResponse:
    """Test SuccessResponse DTO."""

    def test_success_response(self):
        """Test creating success response."""
        response = SuccessResponse(
            message="Operation completed successfully"
        )

        assert response.success is True
        assert response.message == "Operation completed successfully"
        assert isinstance(response.timestamp, datetime)


class TestIDMixin:
    """Test IDMixin."""

    def test_id_mixin(self):
        """Test DTO with ID mixin."""
        class EntityDTO(IDMixin, BaseDTO):
            name: str

        entity_id = uuid4()
        dto = EntityDTO(
            id=entity_id,
            name="test"
        )

        assert dto.id == entity_id
        assert isinstance(dto.id, UUID)

    def test_id_validation(self):
        """Test ID validation."""
        class EntityDTO(IDMixin, BaseDTO):
            name: str

        # Valid UUID
        dto = EntityDTO(
            id="123e4567-e89b-12d3-a456-426614174000",
            name="test"
        )
        assert isinstance(dto.id, UUID)

        # Invalid UUID
        with pytest.raises(ValidationError):
            EntityDTO(id="not-a-uuid", name="test")
