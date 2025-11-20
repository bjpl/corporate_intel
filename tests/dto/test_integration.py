"""Integration tests for DTO layer with API endpoints."""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, patch

from src.dto.base import (
    BaseDTO,
    IDMixin,
    TimestampedDTO,
    PaginatedResponse,
    ErrorResponse,
    SuccessResponse,
)


class TestAPIIntegration:
    """Test DTO integration with API endpoints."""

    def test_company_create_flow(self):
        """Test complete company creation flow with DTOs."""

        class CompanyCreateDTO(BaseDTO):
            ticker: str
            name: str

        class CompanyResponseDTO(IDMixin, TimestampedDTO):
            ticker: str
            name: str

        # Simulate API request
        request_data = {
            "ticker": "DUOL",
            "name": "Duolingo Inc."
        }

        # Validate request
        create_dto = CompanyCreateDTO(**request_data)
        assert create_dto.ticker == "DUOL"

        # Simulate DB creation
        company_id = uuid4()
        created_at = datetime.utcnow()

        # Create response
        response_dto = CompanyResponseDTO(
            id=company_id,
            ticker=create_dto.ticker,
            name=create_dto.name,
            created_at=created_at
        )

        # Serialize response
        response_data = response_dto.model_dump()
        assert response_data["id"] == company_id
        assert response_data["ticker"] == "DUOL"

    def test_paginated_list_flow(self):
        """Test paginated list endpoint flow."""

        class CompanyDTO(BaseDTO):
            id: str
            ticker: str
            name: str

        # Simulate fetching companies
        companies = [
            CompanyDTO(id=str(uuid4()), ticker="DUOL", name="Duolingo"),
            CompanyDTO(id=str(uuid4()), ticker="CHGG", name="Chegg"),
        ]

        # Create paginated response
        response = PaginatedResponse.create(
            items=companies,
            total=100,
            limit=10,
            offset=0
        )

        # Serialize for API
        data = response.model_dump()
        assert len(data["items"]) == 2
        assert data["total"] == 100
        assert data["has_more"] is True

    def test_error_response_flow(self):
        """Test error response flow."""

        from src.dto.base import ErrorDetail

        # Simulate validation error
        try:
            raise ValueError("Invalid ticker format")
        except ValueError as e:
            error_response = ErrorResponse(
                error="ValidationError",
                message=str(e),
                details=[
                    ErrorDetail(
                        code="INVALID_FORMAT",
                        message="Ticker must be uppercase",
                        field="ticker"
                    )
                ]
            )

        # Serialize error
        error_data = error_response.model_dump()
        assert error_data["error"] == "ValidationError"
        assert len(error_data["details"]) == 1


class TestDatabaseIntegration:
    """Test DTO integration with database models."""

    def test_orm_to_dto_conversion(self):
        """Test converting ORM model to DTO."""

        class CompanyDTO(BaseDTO):
            id: str
            ticker: str
            name: str
            created_at: datetime

        # Mock ORM object
        class MockCompany:
            id = str(uuid4())
            ticker = "DUOL"
            name = "Duolingo Inc."
            created_at = datetime.utcnow()

        orm_company = MockCompany()

        # Convert to DTO
        dto = CompanyDTO.model_validate(orm_company)
        assert dto.ticker == "DUOL"
        assert dto.name == "Duolingo Inc."

    def test_dto_to_orm_data(self):
        """Test extracting data from DTO for ORM."""

        class CompanyCreateDTO(BaseDTO):
            ticker: str
            name: str
            sector: str = None

        dto = CompanyCreateDTO(
            ticker="DUOL",
            name="Duolingo Inc.",
            sector="EdTech"
        )

        # Extract data for ORM
        orm_data = dto.model_dump()

        # Simulate ORM creation
        class MockCompany:
            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        company = MockCompany(**orm_data)
        assert company.ticker == "DUOL"
        assert company.sector == "EdTech"


class TestCacheIntegration:
    """Test DTO integration with caching."""

    def test_dto_cache_serialization(self):
        """Test DTO serialization for caching."""

        class CompanyDTO(BaseDTO):
            id: str
            ticker: str
            data: dict

        dto = CompanyDTO(
            id=str(uuid4()),
            ticker="DUOL",
            data={"sector": "EdTech"}
        )

        # Serialize for cache
        cache_data = dto.model_dump_json()
        assert isinstance(cache_data, str)

        # Deserialize from cache
        cached_dto = CompanyDTO.model_validate_json(cache_data)
        assert cached_dto.ticker == "DUOL"
        assert cached_dto.data["sector"] == "EdTech"

    def test_dto_cache_key_generation(self):
        """Test generating cache keys from DTOs."""

        class CacheKeyDTO(BaseDTO):
            resource: str
            id: str
            params: dict = {}

        dto = CacheKeyDTO(
            resource="companies",
            id="123",
            params={"include": "metrics"}
        )

        # Generate cache key
        cache_key = f"{dto.resource}:{dto.id}:{hash(frozenset(dto.params.items()))}"
        assert "companies:123:" in cache_key


class TestValidationIntegration:
    """Test DTO validation in request/response flow."""

    def test_request_validation_success(self):
        """Test successful request validation."""

        from pydantic import Field

        class MetricCreateDTO(BaseDTO):
            company_id: str
            value: float = Field(gt=0)
            metric_type: str

        # Valid request
        request_data = {
            "company_id": str(uuid4()),
            "value": 1000000.0,
            "metric_type": "revenue"
        }

        dto = MetricCreateDTO(**request_data)
        assert dto.value == 1000000.0

    def test_request_validation_failure(self):
        """Test request validation failure."""

        from pydantic import Field, ValidationError

        class MetricCreateDTO(BaseDTO):
            company_id: str
            value: float = Field(gt=0)

        # Invalid request (negative value)
        request_data = {
            "company_id": str(uuid4()),
            "value": -100.0
        }

        with pytest.raises(ValidationError) as exc_info:
            MetricCreateDTO(**request_data)

        assert "value" in str(exc_info.value)


class TestEndToEndFlow:
    """Test complete end-to-end flows."""

    def test_company_crud_flow(self):
        """Test complete CRUD flow with DTOs."""

        class CompanyCreateDTO(BaseDTO):
            ticker: str
            name: str

        class CompanyUpdateDTO(BaseDTO):
            name: str = None
            sector: str = None

        class CompanyResponseDTO(IDMixin):
            ticker: str
            name: str
            sector: str = None

        # CREATE
        create_data = {"ticker": "DUOL", "name": "Duolingo"}
        create_dto = CompanyCreateDTO(**create_data)

        company_id = uuid4()
        created = CompanyResponseDTO(
            id=company_id,
            ticker=create_dto.ticker,
            name=create_dto.name
        )

        # READ
        read_dto = CompanyResponseDTO(
            id=company_id,
            ticker="DUOL",
            name="Duolingo"
        )
        assert read_dto.ticker == "DUOL"

        # UPDATE
        update_data = {"sector": "EdTech"}
        update_dto = CompanyUpdateDTO(**update_data)

        updated = CompanyResponseDTO(
            id=company_id,
            ticker=read_dto.ticker,
            name=read_dto.name,
            sector=update_dto.sector
        )
        assert updated.sector == "EdTech"

        # DELETE
        delete_response = SuccessResponse(
            message="Company deleted successfully"
        )
        assert delete_response.success is True

    def test_metric_ingestion_flow(self):
        """Test metric ingestion flow with DTOs."""

        class MetricBatchDTO(BaseDTO):
            company_id: str
            metrics: list[dict]

        class MetricResponseDTO(BaseDTO):
            id: int
            company_id: str
            value: float

        # Batch ingestion request
        batch_data = {
            "company_id": str(uuid4()),
            "metrics": [
                {"type": "revenue", "value": 1000000.0},
                {"type": "users", "value": 50000.0},
            ]
        }

        batch_dto = MetricBatchDTO(**batch_data)
        assert len(batch_dto.metrics) == 2

        # Create responses
        responses = [
            MetricResponseDTO(
                id=i,
                company_id=batch_dto.company_id,
                value=metric["value"]
            )
            for i, metric in enumerate(batch_dto.metrics)
        ]

        assert len(responses) == 2
        assert responses[0].value == 1000000.0


class TestErrorHandlingIntegration:
    """Test error handling with DTOs."""

    def test_validation_error_to_dto(self):
        """Test converting validation errors to DTOs."""

        from pydantic import ValidationError, Field
        from src.dto.base import ErrorDetail

        class StrictDTO(BaseDTO):
            ticker: str = Field(min_length=1, max_length=5)
            value: int = Field(gt=0)

        try:
            StrictDTO(ticker="TOOLONG", value=-1)
        except ValidationError as e:
            errors = []
            for error in e.errors():
                errors.append(ErrorDetail(
                    code="VALIDATION_ERROR",
                    message=error["msg"],
                    field=".".join(str(loc) for loc in error["loc"])
                ))

            error_response = ErrorResponse(
                error="ValidationError",
                message="Request validation failed",
                details=errors
            )

            assert len(error_response.details) >= 1

    def test_http_error_to_dto(self):
        """Test converting HTTP errors to DTOs."""

        # Simulate 404 Not Found
        error_response = ErrorResponse(
            error="NotFound",
            message="Company not found",
            request_id="req_123"
        )

        assert error_response.error == "NotFound"
        assert error_response.request_id == "req_123"

        # Simulate 500 Internal Server Error
        error_response = ErrorResponse(
            error="InternalServerError",
            message="An unexpected error occurred"
        )

        assert error_response.error == "InternalServerError"


class TestPerformanceIntegration:
    """Test DTO performance in realistic scenarios."""

    def test_bulk_dto_creation(self):
        """Test creating many DTOs efficiently."""

        class ItemDTO(BaseDTO):
            id: int
            value: str

        # Create 1000 DTOs
        dtos = [
            ItemDTO(id=i, value=f"item_{i}")
            for i in range(1000)
        ]

        assert len(dtos) == 1000
        assert dtos[0].id == 0

    def test_bulk_dto_serialization(self):
        """Test serializing many DTOs."""

        class ItemDTO(BaseDTO):
            id: int
            value: str

        dtos = [ItemDTO(id=i, value=f"item_{i}") for i in range(1000)]

        # Serialize all
        serialized = [dto.model_dump() for dto in dtos]

        assert len(serialized) == 1000
        assert serialized[0]["id"] == 0
