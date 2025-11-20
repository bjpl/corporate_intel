"""Tests for API endpoint DTOs."""

import pytest
from datetime import datetime
from uuid import uuid4, UUID
from pydantic import ValidationError

from src.dto.base import BaseDTO, IDMixin, TimestampedDTO, PaginatedResponse


class TestCompanyDTOs:
    """Test Company-related DTOs."""

    def test_company_create_dto(self):
        """Test company creation DTO."""

        class CompanyCreateDTO(BaseDTO):
            ticker: str
            name: str
            cik: str = None
            sector: str = None

        dto = CompanyCreateDTO(
            ticker="DUOL",
            name="Duolingo Inc.",
            sector="EdTech"
        )

        assert dto.ticker == "DUOL"
        assert dto.name == "Duolingo Inc."
        assert dto.sector == "EdTech"
        assert dto.cik is None

    def test_company_response_dto(self):
        """Test company response DTO."""

        class CompanyResponseDTO(IDMixin, TimestampedDTO):
            ticker: str
            name: str
            sector: str = None

        company_id = uuid4()
        now = datetime.utcnow()

        dto = CompanyResponseDTO(
            id=company_id,
            ticker="DUOL",
            name="Duolingo Inc.",
            sector="EdTech",
            created_at=now
        )

        assert dto.id == company_id
        assert dto.ticker == "DUOL"
        assert dto.created_at == now

    def test_company_update_dto(self):
        """Test company update DTO with optional fields."""

        class CompanyUpdateDTO(BaseDTO):
            name: str = None
            sector: str = None
            website: str = None

        # Partial update
        dto = CompanyUpdateDTO(name="Updated Name")
        assert dto.name == "Updated Name"
        assert dto.sector is None

        # No fields updated
        dto = CompanyUpdateDTO()
        assert dto.name is None


class TestMetricDTOs:
    """Test Financial Metric DTOs."""

    def test_metric_create_dto(self):
        """Test metric creation DTO."""

        class MetricCreateDTO(BaseDTO):
            company_id: UUID
            metric_date: datetime
            metric_type: str
            value: float
            unit: str = None

        company_id = uuid4()
        metric_date = datetime(2025, 1, 1)

        dto = MetricCreateDTO(
            company_id=company_id,
            metric_date=metric_date,
            metric_type="revenue",
            value=1000000.0,
            unit="USD"
        )

        assert dto.company_id == company_id
        assert dto.value == 1000000.0

    def test_metric_response_dto(self):
        """Test metric response DTO."""

        class MetricResponseDTO(BaseDTO):
            id: int
            company_id: UUID
            metric_type: str
            value: float
            metric_date: datetime

        company_id = uuid4()

        dto = MetricResponseDTO(
            id=1,
            company_id=company_id,
            metric_type="revenue",
            value=1000000.0,
            metric_date=datetime(2025, 1, 1)
        )

        assert dto.id == 1
        assert dto.metric_type == "revenue"


class TestFilingDTOs:
    """Test SEC Filing DTOs."""

    def test_filing_create_dto(self):
        """Test filing creation DTO."""

        class FilingCreateDTO(BaseDTO):
            company_id: UUID
            form_type: str
            filing_date: datetime
            accession_number: str
            document_url: str = None

        company_id = uuid4()

        dto = FilingCreateDTO(
            company_id=company_id,
            form_type="10-K",
            filing_date=datetime(2025, 3, 31),
            accession_number="0001234567-25-000001"
        )

        assert dto.form_type == "10-K"
        assert dto.accession_number == "0001234567-25-000001"

    def test_filing_response_dto(self):
        """Test filing response DTO."""

        class FilingResponseDTO(IDMixin, TimestampedDTO):
            company_id: UUID
            form_type: str
            filing_date: datetime
            accession_number: str

        filing_id = uuid4()
        company_id = uuid4()
        now = datetime.utcnow()

        dto = FilingResponseDTO(
            id=filing_id,
            company_id=company_id,
            form_type="10-K",
            filing_date=datetime(2025, 3, 31),
            accession_number="0001234567-25-000001",
            created_at=now
        )

        assert dto.id == filing_id
        assert dto.company_id == company_id


class TestPaginatedDTOs:
    """Test paginated response DTOs."""

    def test_paginated_company_response(self):
        """Test paginated company response."""

        class CompanyDTO(BaseDTO):
            id: UUID
            ticker: str
            name: str

        companies = [
            CompanyDTO(id=uuid4(), ticker="DUOL", name="Duolingo"),
            CompanyDTO(id=uuid4(), ticker="CHGG", name="Chegg"),
        ]

        response = PaginatedResponse.create(
            items=companies,
            total=100,
            limit=10,
            offset=0
        )

        assert len(response.items) == 2
        assert response.total == 100
        assert response.has_more is True

    def test_paginated_metric_response(self):
        """Test paginated metric response."""

        class MetricDTO(BaseDTO):
            id: int
            value: float

        metrics = [
            MetricDTO(id=i, value=float(i * 100))
            for i in range(5)
        ]

        response = PaginatedResponse.create(
            items=metrics,
            total=5,
            limit=10,
            offset=0
        )

        assert len(response.items) == 5
        assert response.has_more is False


class TestFilterDTOs:
    """Test filter and query parameter DTOs."""

    def test_company_filter_dto(self):
        """Test company filter parameters."""

        from pydantic import Field

        class CompanyFilterDTO(BaseDTO):
            sector: str = None
            category: str = None
            ticker: str = None
            limit: int = Field(default=100, ge=1, le=500)
            offset: int = Field(default=0, ge=0)

        # Default values
        filters = CompanyFilterDTO()
        assert filters.limit == 100
        assert filters.offset == 0

        # Custom filters
        filters = CompanyFilterDTO(
            sector="EdTech",
            ticker="DUOL",
            limit=50
        )
        assert filters.sector == "EdTech"
        assert filters.ticker == "DUOL"

    def test_date_range_filter_dto(self):
        """Test date range filter parameters."""

        class DateRangeFilterDTO(BaseDTO):
            start_date: datetime = None
            end_date: datetime = None

        start = datetime(2025, 1, 1)
        end = datetime(2025, 12, 31)

        filters = DateRangeFilterDTO(start_date=start, end_date=end)
        assert filters.start_date == start
        assert filters.end_date == end


class TestErrorDTOs:
    """Test error response DTOs."""

    def test_validation_error_dto(self):
        """Test validation error DTO."""

        from src.dto.base import ErrorDetail, ErrorResponse

        error = ErrorResponse(
            error="ValidationError",
            message="Invalid input",
            details=[
                ErrorDetail(
                    code="INVALID_TICKER",
                    message="Ticker must be uppercase",
                    field="ticker"
                )
            ]
        )

        assert error.error == "ValidationError"
        assert len(error.details) == 1
        assert error.details[0].field == "ticker"

    def test_not_found_error_dto(self):
        """Test not found error DTO."""

        from src.dto.base import ErrorResponse

        error = ErrorResponse(
            error="NotFound",
            message="Company not found",
            request_id="req_123"
        )

        assert error.error == "NotFound"
        assert error.message == "Company not found"
        assert error.request_id == "req_123"


class TestSuccessDTOs:
    """Test success response DTOs."""

    def test_delete_success_dto(self):
        """Test delete success response."""

        from src.dto.base import SuccessResponse

        response = SuccessResponse(
            message="Company deleted successfully"
        )

        assert response.success is True
        assert response.message == "Company deleted successfully"

    def test_update_success_dto(self):
        """Test update success response."""

        from src.dto.base import SuccessResponse

        response = SuccessResponse(
            message="Company updated successfully"
        )

        assert response.success is True


class TestBatchDTOs:
    """Test batch operation DTOs."""

    def test_batch_create_dto(self):
        """Test batch creation DTO."""

        class ItemDTO(BaseDTO):
            name: str
            value: int

        class BatchCreateDTO(BaseDTO):
            items: list[ItemDTO]

        dto = BatchCreateDTO(items=[
            {"name": "item1", "value": 1},
            {"name": "item2", "value": 2},
        ])

        assert len(dto.items) == 2
        assert dto.items[0].name == "item1"

    def test_batch_response_dto(self):
        """Test batch operation response."""

        class ResultDTO(BaseDTO):
            id: UUID
            status: str

        class BatchResponseDTO(BaseDTO):
            succeeded: list[ResultDTO]
            failed: list[dict]
            total_processed: int

        response = BatchResponseDTO(
            succeeded=[
                {"id": str(uuid4()), "status": "created"}
            ],
            failed=[
                {"index": 1, "error": "Validation failed"}
            ],
            total_processed=2
        )

        assert len(response.succeeded) == 1
        assert len(response.failed) == 1
        assert response.total_processed == 2


class TestSearchDTOs:
    """Test search-related DTOs."""

    def test_search_query_dto(self):
        """Test search query parameters."""

        from pydantic import Field

        class SearchQueryDTO(BaseDTO):
            query: str = Field(min_length=1, max_length=200)
            filters: dict = {}
            limit: int = Field(default=20, ge=1, le=100)

        dto = SearchQueryDTO(
            query="EdTech companies",
            filters={"sector": "Education"},
            limit=50
        )

        assert dto.query == "EdTech companies"
        assert dto.filters["sector"] == "Education"
        assert dto.limit == 50

    def test_search_result_dto(self):
        """Test search result DTO."""

        class SearchHitDTO(BaseDTO):
            id: UUID
            score: float
            highlight: dict = {}

        class SearchResultDTO(BaseDTO):
            hits: list[SearchHitDTO]
            total_hits: int
            max_score: float

        result = SearchResultDTO(
            hits=[
                {"id": str(uuid4()), "score": 0.95, "highlight": {"name": "Duolingo"}},
                {"id": str(uuid4()), "score": 0.85, "highlight": {"name": "Chegg"}},
            ],
            total_hits=2,
            max_score=0.95
        )

        assert len(result.hits) == 2
        assert result.max_score == 0.95


class TestStatsDTOs:
    """Test statistics and aggregation DTOs."""

    def test_company_stats_dto(self):
        """Test company statistics DTO."""

        class CompanyStatsDTO(BaseDTO):
            total_companies: int
            by_sector: dict[str, int]
            by_category: dict[str, int]

        stats = CompanyStatsDTO(
            total_companies=100,
            by_sector={"EdTech": 50, "FinTech": 30, "HealthTech": 20},
            by_category={"K12": 30, "Higher Ed": 40, "Corporate": 30}
        )

        assert stats.total_companies == 100
        assert stats.by_sector["EdTech"] == 50

    def test_metric_aggregation_dto(self):
        """Test metric aggregation DTO."""

        class MetricAggregationDTO(BaseDTO):
            metric_type: str
            avg_value: float
            min_value: float
            max_value: float
            count: int

        agg = MetricAggregationDTO(
            metric_type="revenue",
            avg_value=1500000.0,
            min_value=100000.0,
            max_value=5000000.0,
            count=50
        )

        assert agg.metric_type == "revenue"
        assert agg.avg_value == 1500000.0
