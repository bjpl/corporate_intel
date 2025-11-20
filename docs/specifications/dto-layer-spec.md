# DTO Layer Specification for API Responses

**Document Version:** 1.0.0
**Date:** 2025-11-20
**Status:** Draft
**SPARC Phase:** Specification

## Executive Summary

This specification defines a comprehensive Data Transfer Object (DTO) layer for the Corporate Intelligence Platform API. The DTO layer will provide consistent, type-safe, validated, and well-documented API responses while maintaining backward compatibility.

### Key Objectives

1. **Type Safety**: Leverage Pydantic v2 for runtime validation and type checking
2. **Consistency**: Standardize response formats across all endpoints
3. **Validation**: Implement comprehensive input/output validation
4. **Documentation**: Auto-generate OpenAPI schemas with detailed examples
5. **Performance**: Optimize serialization and minimize overhead
6. **Backward Compatibility**: Ensure existing clients continue to function

---

## 1. Current State Analysis

### 1.1 API Endpoint Inventory

#### Companies API (`/api/v1/companies`)
- **GET /** - List companies (paginated)
- **GET /watchlist** - Get watchlist companies
- **GET /{company_id}** - Get company by ID
- **GET /{company_id}/metrics** - Get company metrics
- **GET /trending/top-performers** - Get top performing companies
- **POST /** - Create company (authenticated)
- **PUT /{company_id}** - Update company (authenticated)
- **DELETE /{company_id}** - Delete company (authenticated)

#### Filings API (`/api/v1/filings`)
- **GET /** - List SEC filings (paginated)
- **GET /{filing_id}** - Get filing by ID

#### Metrics API (`/api/v1/metrics`)
- **GET /** - List financial metrics (paginated)

#### Intelligence API (`/api/v1/intelligence`)
- **GET /** - List market intelligence (paginated)

#### Reports API (`/api/v1/reports`)
- **GET /** - List analysis reports (paginated)
- **GET /{report_id}** - Get report by ID
- **POST /generate** - Generate new report (authenticated)

#### Admin API (`/api/v1/admin`)
- **GET /performance/slow-queries** - Get slow queries
- **GET /performance/top-queries** - Get top queries by time
- **GET /performance/low-cache-hit** - Get queries with low cache hits
- **GET /performance/database-stats** - Get database statistics
- **GET /performance/table-stats** - Get table statistics
- **GET /performance/index-usage** - Get index usage statistics

#### Health API (`/api/v1/health`)
- **GET /** - Basic health check
- **GET /ping** - Lightweight ping
- **GET /detailed** - Detailed health check
- **GET /readiness** - Kubernetes readiness probe

### 1.2 Current Response Patterns

#### Issues Identified

1. **Inconsistent Pagination**: Uses `offset`/`limit` query params without standardized response wrapper
2. **Direct ORM Mapping**: Some endpoints return ORM objects with `from_attributes=True`
3. **Timestamp Formats**: Datetime objects returned without consistent ISO string formatting
4. **No Error Standards**: Error responses lack consistent structure
5. **Missing Metadata**: No request IDs, timing information, or API version in responses
6. **JSON Field Typing**: JSON columns (subcategory, monetization_strategy) not validated
7. **UUID Serialization**: UUIDs returned as objects, not strings
8. **Null Handling**: Inconsistent Optional field behavior
9. **No HATEOAS**: Missing hypermedia links for related resources
10. **No Field Documentation**: Responses lack inline field descriptions

### 1.3 Database Models Analysis

#### Core Models

```python
# Primary Models with UUID IDs
- Company (id: UUID)
- SECFiling (id: UUID)
- Document (id: UUID)
- AnalysisReport (id: UUID)
- MarketIntelligence (id: UUID)
- DocumentChunk (id: UUID)

# Time-Series Model (TimescaleDB)
- FinancialMetric (id: BigInteger, metric_date: DateTime - composite PK)
```

#### Common Patterns

1. **TimestampMixin**: All models have `created_at` and `updated_at`
2. **JSON Fields**: Complex data stored as JSON (subcategory, parsed_sections, findings)
3. **Vector Embeddings**: pgvector columns for semantic search
4. **Relationships**: SQLAlchemy relationships with eager loading

### 1.4 Validation & Error Handling

#### Current Exception Hierarchy

```
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
```

#### Exception Features
- HTTP status codes
- Error codes (machine-readable)
- Structured error details
- Original error wrapping
- `to_dict()` serialization

---

## 2. DTO Architecture Design

### 2.1 Base DTO Classes

#### Core Base Classes

```python
# src/api/dto/base.py

from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_serializer

T = TypeVar('T')

class BaseDTO(BaseModel):
    """Base DTO with common configuration."""

    model_config = ConfigDict(
        # Performance optimization
        from_attributes=True,
        validate_assignment=True,
        use_enum_values=True,

        # Serialization
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None,
            UUID: lambda v: str(v) if v else None,
        },

        # Documentation
        populate_by_name=True,  # Allow both field name and alias
    )


class TimestampMixin(BaseModel):
    """Mixin for created/updated timestamps."""

    created_at: datetime = Field(
        ...,
        description="Timestamp when the resource was created",
        json_schema_extra={"example": "2025-01-15T10:30:00Z"}
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Timestamp when the resource was last updated",
        json_schema_extra={"example": "2025-01-15T14:20:00Z"}
    )

    @field_serializer('created_at', 'updated_at')
    def serialize_datetime(self, dt: Optional[datetime]) -> Optional[str]:
        """Serialize datetime to ISO 8601 string."""
        return dt.isoformat() if dt else None


class PaginationRequest(BaseModel):
    """Pagination request parameters."""

    offset: int = Field(
        default=0,
        ge=0,
        description="Number of records to skip",
        json_schema_extra={"example": 0}
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=500,
        description="Maximum number of records to return (max: 500)",
        json_schema_extra={"example": 100}
    )


class PaginationMetadata(BaseModel):
    """Pagination metadata for responses."""

    offset: int = Field(..., description="Current offset")
    limit: int = Field(..., description="Current limit")
    total: Optional[int] = Field(None, description="Total number of records (if available)")
    count: int = Field(..., description="Number of records in current page")
    has_more: bool = Field(..., description="Whether more records are available")

    @classmethod
    def from_request(
        cls,
        request: PaginationRequest,
        count: int,
        total: Optional[int] = None
    ) -> "PaginationMetadata":
        """Create metadata from request and result count."""
        return cls(
            offset=request.offset,
            limit=request.limit,
            total=total,
            count=count,
            has_more=(count == request.limit),
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""

    data: List[T] = Field(..., description="List of items in current page")
    pagination: PaginationMetadata = Field(..., description="Pagination metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "data": ["... items ..."],
                "pagination": {
                    "offset": 0,
                    "limit": 100,
                    "total": 250,
                    "count": 100,
                    "has_more": True
                }
            }
        }
    )


class ResponseMetadata(BaseModel):
    """Common response metadata."""

    request_id: str = Field(..., description="Unique request identifier for tracing")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Server timestamp when response was generated"
    )
    api_version: str = Field(default="v1", description="API version")
    execution_time_ms: Optional[float] = Field(
        None,
        description="Server-side execution time in milliseconds"
    )

    @field_serializer('timestamp')
    def serialize_timestamp(self, dt: datetime) -> str:
        return dt.isoformat()


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response wrapper."""

    success: bool = Field(default=True, description="Indicates successful operation")
    data: T = Field(..., description="Response data")
    meta: ResponseMetadata = Field(..., description="Response metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "data": {"... resource data ..."},
                "meta": {
                    "request_id": "req_abc123",
                    "timestamp": "2025-01-15T10:30:00Z",
                    "api_version": "v1",
                    "execution_time_ms": 42.5
                }
            }
        }
    )
```

### 2.2 Error DTOs

```python
# src/api/dto/errors.py

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ValidationError(BaseModel):
    """Validation error details."""

    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Error message")
    type: str = Field(..., description="Error type")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ErrorDetail(BaseModel):
    """Detailed error information."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error context")
    validation_errors: Optional[List[ValidationError]] = Field(
        None,
        description="Validation errors (if applicable)"
    )
    trace_id: Optional[str] = Field(None, description="Error trace ID for debugging")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "VALIDATION_ERROR",
                "message": "Input validation failed",
                "details": {"field": "ticker", "constraint": "max_length"},
                "validation_errors": [
                    {
                        "field": "ticker",
                        "message": "String should have at most 10 characters",
                        "type": "string_too_long",
                        "context": {"max_length": 10}
                    }
                ],
                "trace_id": "trace_xyz789"
            }
        }
    )


class ErrorResponse(BaseModel):
    """Standard error response."""

    success: bool = Field(default=False, description="Always false for errors")
    error: ErrorDetail = Field(..., description="Error details")
    meta: ResponseMetadata = Field(..., description="Response metadata")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Company with ID abc123 not found",
                    "details": {"resource_type": "Company", "resource_id": "abc123"}
                },
                "meta": {
                    "request_id": "req_abc123",
                    "timestamp": "2025-01-15T10:30:00Z",
                    "api_version": "v1"
                }
            }
        }
    )
```

### 2.3 Company DTOs

```python
# src/api/dto/companies.py

from typing import List, Optional
from uuid import UUID
from pydantic import Field, field_validator, HttpUrl

from .base import BaseDTO, TimestampMixin


class CompanyCategory(str, Enum):
    """EdTech company categories."""

    K12 = "k12"
    HIGHER_EDUCATION = "higher_education"
    CORPORATE_LEARNING = "corporate_learning"
    DIRECT_TO_CONSUMER = "direct_to_consumer"
    ENABLING_TECHNOLOGY = "enabling_technology"


class DeliveryModel(str, Enum):
    """Company delivery models."""

    B2B = "b2b"
    B2C = "b2c"
    B2B2C = "b2b2c"
    MARKETPLACE = "marketplace"
    HYBRID = "hybrid"


class CompanyBase(BaseDTO):
    """Base company fields for create/update."""

    ticker: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Stock ticker symbol",
        json_schema_extra={"example": "DUOL"}
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Company name",
        json_schema_extra={"example": "Duolingo Inc."}
    )
    cik: Optional[str] = Field(
        None,
        pattern=r"^\d{10}$",
        description="SEC CIK number (10 digits)",
        json_schema_extra={"example": "0001609711"}
    )
    sector: Optional[str] = Field(
        None,
        max_length=100,
        description="Industry sector",
        json_schema_extra={"example": "Technology"}
    )
    subsector: Optional[str] = Field(
        None,
        max_length=100,
        description="Industry subsector",
        json_schema_extra={"example": "Educational Software"}
    )
    category: Optional[CompanyCategory] = Field(
        None,
        description="EdTech category classification"
    )
    delivery_model: Optional[DeliveryModel] = Field(
        None,
        description="Primary delivery model"
    )

    @field_validator('ticker')
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        """Validate and normalize ticker symbol."""
        return v.upper().strip()


class CompanyCreate(CompanyBase):
    """Company creation request."""

    subcategory: Optional[List[str]] = Field(
        None,
        description="EdTech subcategories",
        json_schema_extra={"example": ["Language Learning", "Gamification"]}
    )
    monetization_strategy: Optional[List[str]] = Field(
        None,
        description="Revenue models",
        json_schema_extra={"example": ["Freemium", "Subscription"]}
    )
    founded_year: Optional[int] = Field(
        None,
        ge=1800,
        le=2100,
        description="Year company was founded",
        json_schema_extra={"example": 2011}
    )
    headquarters: Optional[str] = Field(
        None,
        max_length=255,
        description="Headquarters location",
        json_schema_extra={"example": "Pittsburgh, PA, USA"}
    )
    website: Optional[HttpUrl] = Field(
        None,
        description="Company website URL",
        json_schema_extra={"example": "https://www.duolingo.com"}
    )
    employee_count: Optional[int] = Field(
        None,
        ge=0,
        description="Number of employees",
        json_schema_extra={"example": 700}
    )


class CompanyUpdate(BaseDTO):
    """Company update request (all fields optional)."""

    ticker: Optional[str] = Field(None, min_length=1, max_length=10)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    cik: Optional[str] = Field(None, pattern=r"^\d{10}$")
    sector: Optional[str] = Field(None, max_length=100)
    subsector: Optional[str] = Field(None, max_length=100)
    category: Optional[CompanyCategory] = None
    delivery_model: Optional[DeliveryModel] = None
    subcategory: Optional[List[str]] = None
    monetization_strategy: Optional[List[str]] = None
    founded_year: Optional[int] = Field(None, ge=1800, le=2100)
    headquarters: Optional[str] = Field(None, max_length=255)
    website: Optional[HttpUrl] = None
    employee_count: Optional[int] = Field(None, ge=0)


class CompanyDTO(CompanyBase, TimestampMixin):
    """Complete company data transfer object."""

    id: UUID = Field(..., description="Unique company identifier")
    subcategory: Optional[List[str]] = Field(None, description="EdTech subcategories")
    monetization_strategy: Optional[List[str]] = Field(None, description="Revenue models")
    founded_year: Optional[int] = Field(None, description="Year founded")
    headquarters: Optional[str] = Field(None, description="Headquarters location")
    website: Optional[str] = Field(None, description="Company website URL")
    employee_count: Optional[int] = Field(None, description="Employee count")

    @field_serializer('id')
    def serialize_uuid(self, v: UUID) -> str:
        """Serialize UUID to string."""
        return str(v)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "ticker": "DUOL",
                "name": "Duolingo Inc.",
                "cik": "0001609711",
                "sector": "Technology",
                "subsector": "Educational Software",
                "category": "direct_to_consumer",
                "delivery_model": "b2c",
                "subcategory": ["Language Learning", "Gamification"],
                "monetization_strategy": ["Freemium", "Subscription"],
                "founded_year": 2011,
                "headquarters": "Pittsburgh, PA, USA",
                "website": "https://www.duolingo.com",
                "employee_count": 700,
                "created_at": "2025-01-15T10:30:00Z",
                "updated_at": "2025-01-15T14:20:00Z"
            }
        }
    )


class CompanyMetricsDTO(BaseDTO):
    """Company key metrics summary."""

    company_id: UUID = Field(..., description="Company identifier")
    ticker: str = Field(..., description="Stock ticker symbol")
    latest_revenue: Optional[float] = Field(None, description="Latest revenue (USD)")
    revenue_growth_yoy: Optional[float] = Field(None, description="YoY revenue growth (%)")
    monthly_active_users: Optional[int] = Field(None, description="Monthly active users")
    arpu: Optional[float] = Field(None, description="Average revenue per user (USD)")
    cac: Optional[float] = Field(None, description="Customer acquisition cost (USD)")
    nrr: Optional[float] = Field(None, description="Net revenue retention (%)")
    last_updated: str = Field(..., description="Last update timestamp (ISO 8601)")

    @field_serializer('company_id')
    def serialize_uuid(self, v: UUID) -> str:
        return str(v)


class TrendingCompanyDTO(BaseDTO):
    """Trending company with performance indicators."""

    ticker: str = Field(..., description="Stock ticker symbol")
    company_name: str = Field(..., description="Company name")
    edtech_category: str = Field(..., description="EdTech category")
    revenue_yoy_growth: Optional[float] = Field(None, description="YoY revenue growth (%)")
    latest_revenue: Optional[float] = Field(None, description="Latest revenue (USD)")
    overall_score: Optional[float] = Field(None, description="Overall performance score")
    growth_rank: Optional[int] = Field(None, description="Growth rank")
    company_health_status: Optional[str] = Field(None, description="Health status")
```

### 2.4 Filing, Metrics, Intelligence, Reports DTOs

```python
# src/api/dto/filings.py

class FilingDTO(BaseDTO, TimestampMixin):
    """SEC filing data transfer object."""

    id: UUID
    company_id: UUID
    filing_type: str = Field(..., description="Filing type (10-K, 10-Q, etc.)")
    filing_date: datetime
    accession_number: str = Field(..., description="SEC accession number")
    filing_url: Optional[str] = Field(None, description="SEC EDGAR URL")
    processing_status: str = Field(..., description="Processing status")


# src/api/dto/metrics.py

class MetricDTO(BaseDTO, TimestampMixin):
    """Financial metric data transfer object."""

    id: int
    company_id: UUID
    metric_date: datetime
    period_type: str = Field(..., description="Period type (quarterly, annual, monthly)")
    metric_type: str = Field(..., description="Metric type (revenue, mau, etc.)")
    metric_category: Optional[str] = Field(None, description="Metric category")
    value: float = Field(..., description="Metric value")
    unit: Optional[str] = Field(None, description="Unit (USD, percent, count)")


# src/api/dto/intelligence.py

class IntelligenceDTO(BaseDTO, TimestampMixin):
    """Market intelligence data transfer object."""

    id: UUID
    intel_type: str = Field(..., description="Intelligence type")
    category: Optional[str] = Field(None, description="EdTech category")
    title: str
    summary: Optional[str] = None
    event_date: Optional[datetime] = None
    source: Optional[str] = None


# src/api/dto/reports.py

class ReportDTO(BaseDTO, TimestampMixin):
    """Analysis report data transfer object."""

    id: UUID
    report_type: str = Field(..., description="Report type")
    title: str
    description: Optional[str] = None
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    format: Optional[str] = Field(None, description="Report format (pdf, html, json)")
    report_url: Optional[str] = Field(None, description="Generated report URL")


class ReportGenerationRequest(BaseDTO):
    """Report generation request."""

    report_type: str = Field(..., description="Type of report")
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    category_filter: Optional[str] = None
    date_range_days: int = Field(default=90, ge=1, le=365)
    include_visualizations: bool = Field(default=True)


class ReportGenerationResponse(BaseDTO):
    """Report generation response."""

    report_id: UUID
    status: str
    title: str
    report_type: str
    companies_analyzed: int
    metrics_included: int
    created_at: datetime
    report_url: Optional[str] = None
```

### 2.5 Health & Admin DTOs

```python
# src/api/dto/health.py

class HealthDTO(BaseDTO):
    """Basic health check response."""

    status: str = Field(..., description="Health status")
    timestamp: datetime
    version: str
    environment: str


class ComponentHealth(BaseDTO):
    """Individual component health."""

    status: str = Field(..., description="Component status (healthy, degraded, unhealthy)")
    response_time_ms: float = Field(..., description="Response time in milliseconds")


class DetailedHealthDTO(BaseDTO):
    """Detailed health check response."""

    status: str
    timestamp: datetime
    version: str
    environment: str
    components: Dict[str, ComponentHealth]
    metrics: Dict[str, Any]


# src/api/dto/admin.py

class SlowQueryDTO(BaseDTO):
    """Slow query statistics."""

    query: str
    calls: int
    total_time_ms: float
    avg_time_ms: float
    max_time_ms: float
    cache_hit_ratio: float


class DatabaseStatsDTO(BaseDTO):
    """Database performance statistics."""

    total_queries: int
    total_calls: int
    total_time_ms: float
    avg_time_ms: float
    cache_hit_ratio: float


class TableStatsDTO(BaseDTO):
    """Table access statistics."""

    table_name: str
    seq_scans: int
    seq_rows_read: int
    idx_scans: int
    idx_rows_fetched: int
    inserts: int
    updates: int
    deletes: int


class IndexUsageDTO(BaseDTO):
    """Index usage statistics."""

    table_name: str
    index_name: str
    scans: int
    rows_read: int
    rows_fetched: int
```

---

## 3. Validation Strategy

### 3.1 Input Validation Rules

#### Field-Level Validation

```python
# String fields
- min_length, max_length: Enforce length constraints
- pattern: Regex validation (e.g., CIK format)
- strip_whitespace: Auto-trim strings

# Numeric fields
- ge, gt, le, lt: Range validation
- multiple_of: Step validation
- allow_inf_nan: Numeric edge cases

# Enums
- Use Python Enum classes for fixed value sets
- Auto-validation of allowed values

# UUIDs
- Auto-validation of UUID format
- Serialization to string for JSON

# Datetimes
- ISO 8601 string parsing
- Timezone awareness required
- Serialization to ISO string

# URLs
- HttpUrl type for validation
- Scheme validation (https://)

# Lists/Arrays
- min_items, max_items: Length validation
- unique_items: Uniqueness enforcement
```

#### Model-Level Validation

```python
@model_validator(mode='after')
def validate_date_range(self) -> Self:
    """Validate date range consistency."""
    if self.date_range_start and self.date_range_end:
        if self.date_range_start > self.date_range_end:
            raise ValueError("Start date must be before end date")
    return self


@field_validator('ticker')
@classmethod
def validate_ticker(cls, v: str) -> str:
    """Validate and normalize ticker symbol."""
    v = v.upper().strip()
    if not v.isalnum():
        raise ValueError("Ticker must be alphanumeric")
    return v
```

### 3.2 Output Validation

#### Serialization Rules

1. **UUID → String**: All UUIDs serialized to string format
2. **Datetime → ISO 8601**: All timestamps in ISO format with timezone
3. **Decimal → Float**: Numeric precision handling
4. **None → null**: Explicit null serialization
5. **Enum → String**: Enum values to string representation

#### Example Serializers

```python
@field_serializer('id', 'company_id')
def serialize_uuid(self, v: Optional[UUID]) -> Optional[str]:
    """Serialize UUID fields to string."""
    return str(v) if v else None


@field_serializer('created_at', 'updated_at')
def serialize_datetime(self, v: Optional[datetime]) -> Optional[str]:
    """Serialize datetime to ISO 8601 string."""
    return v.isoformat() if v else None


@field_serializer('website')
def serialize_url(self, v: Optional[HttpUrl]) -> Optional[str]:
    """Serialize HttpUrl to string."""
    return str(v) if v else None
```

### 3.3 Error Handling

#### Validation Error Mapping

```python
# src/api/middleware/error_handler.py

from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from src.api.dto.errors import ErrorResponse, ErrorDetail, ValidationError as DTOValidationError


async def validation_error_handler(
    request: Request,
    exc: ValidationError
) -> JSONResponse:
    """Handle Pydantic validation errors."""

    validation_errors = []
    for error in exc.errors():
        validation_errors.append(
            DTOValidationError(
                field=".".join(str(loc) for loc in error["loc"]),
                message=error["msg"],
                type=error["type"],
                context=error.get("ctx"),
            )
        )

    error_response = ErrorResponse(
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            validation_errors=validation_errors,
            trace_id=request.state.request_id,
        ),
        meta=ResponseMetadata(
            request_id=request.state.request_id,
            timestamp=datetime.utcnow(),
            api_version="v1",
        ),
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(),
    )
```

---

## 4. Migration Plan

### 4.1 Phase 1: Foundation (Week 1)

#### Objectives
- Create base DTO classes
- Implement error DTOs
- Set up validation infrastructure

#### Tasks
1. Create `src/api/dto/` directory structure
2. Implement base DTOs (`BaseDTO`, `TimestampMixin`, `PaginatedResponse`)
3. Implement error DTOs (`ErrorResponse`, `ErrorDetail`, `ValidationError`)
4. Create middleware for error handling
5. Add unit tests for base classes

#### Deliverables
- `src/api/dto/base.py`
- `src/api/dto/errors.py`
- `src/api/middleware/error_handler.py`
- `tests/unit/dto/test_base.py`

### 4.2 Phase 2: Company DTOs (Week 1-2)

#### Objectives
- Migrate Companies API to DTO layer
- Maintain backward compatibility

#### Tasks
1. Create Company DTOs (`CompanyDTO`, `CompanyCreate`, `CompanyUpdate`)
2. Update Companies API endpoints to use DTOs
3. Add response wrapping with metadata
4. Implement pagination wrapper
5. Add integration tests

#### Deliverables
- `src/api/dto/companies.py`
- Updated `src/api/v1/companies.py`
- `tests/integration/test_companies_dto.py`

### 4.3 Phase 3: Remaining DTOs (Week 2)

#### Objectives
- Migrate all other APIs to DTO layer

#### Tasks
1. Create FilingDTO, MetricDTO, IntelligenceDTO
2. Create ReportDTO and report-specific DTOs
3. Create HealthDTO and AdminDTO classes
4. Update all API endpoints
5. Add comprehensive tests

#### Deliverables
- `src/api/dto/filings.py`
- `src/api/dto/metrics.py`
- `src/api/dto/intelligence.py`
- `src/api/dto/reports.py`
- `src/api/dto/health.py`
- `src/api/dto/admin.py`
- Updated API endpoint files
- Integration tests

### 4.4 Phase 4: Enhancement (Week 3)

#### Objectives
- Add advanced features
- Optimize performance

#### Tasks
1. Implement HATEOAS links (optional)
2. Add response caching headers
3. Implement field filtering (sparse fieldsets)
4. Add API versioning support
5. Performance testing and optimization

#### Deliverables
- HATEOAS link generator
- Field filtering middleware
- Performance benchmarks
- Documentation updates

### 4.5 Backward Compatibility Strategy

#### Approach 1: Dual Responses (Recommended)

```python
# Support both old and new response formats via header

@router.get("/", response_model=Union[List[CompanyDTO], PaginatedResponse[CompanyDTO]])
async def list_companies(
    request: Request,
    pagination: PaginationRequest = Depends(),
    db: Session = Depends(get_db),
):
    """List companies with optional new response format."""

    companies = # ... query logic ...

    # Check for new format opt-in
    use_new_format = request.headers.get("X-API-Version") == "v2"

    if use_new_format:
        return PaginatedResponse(
            data=[CompanyDTO.model_validate(c) for c in companies],
            pagination=PaginationMetadata.from_request(
                pagination,
                count=len(companies),
                total=None,  # Could query total count
            ),
        )
    else:
        # Legacy format
        return [CompanyDTO.model_validate(c) for c in companies]
```

#### Approach 2: Gradual Migration

1. **Phase 1**: Add DTOs alongside existing responses
2. **Phase 2**: Deprecation notice in documentation (3 months)
3. **Phase 3**: Default to new format, old format opt-in
4. **Phase 4**: Remove old format support

---

## 5. API Endpoint Mapping

### 5.1 Companies API

| Endpoint | Method | Request DTO | Response DTO | Wrapper |
|----------|--------|-------------|--------------|---------|
| `/` | GET | `PaginationRequest` | `CompanyDTO` | `PaginatedResponse` |
| `/watchlist` | GET | - | `CompanyDTO` | `PaginatedResponse` |
| `/{id}` | GET | - | `CompanyDTO` | `SuccessResponse` |
| `/{id}/metrics` | GET | - | `CompanyMetricsDTO` | `SuccessResponse` |
| `/trending/top-performers` | GET | Query params | `TrendingCompanyDTO` | `PaginatedResponse` |
| `/` | POST | `CompanyCreate` | `CompanyDTO` | `SuccessResponse` |
| `/{id}` | PUT | `CompanyUpdate` | `CompanyDTO` | `SuccessResponse` |
| `/{id}` | DELETE | - | - | 204 No Content |

### 5.2 Filings API

| Endpoint | Method | Request DTO | Response DTO | Wrapper |
|----------|--------|-------------|--------------|---------|
| `/` | GET | `PaginationRequest` | `FilingDTO` | `PaginatedResponse` |
| `/{id}` | GET | - | `FilingDTO` | `SuccessResponse` |

### 5.3 Metrics API

| Endpoint | Method | Request DTO | Response DTO | Wrapper |
|----------|--------|-------------|--------------|---------|
| `/` | GET | `PaginationRequest` | `MetricDTO` | `PaginatedResponse` |

### 5.4 Intelligence API

| Endpoint | Method | Request DTO | Response DTO | Wrapper |
|----------|--------|-------------|--------------|---------|
| `/` | GET | `PaginationRequest` | `IntelligenceDTO` | `PaginatedResponse` |

### 5.5 Reports API

| Endpoint | Method | Request DTO | Response DTO | Wrapper |
|----------|--------|-------------|--------------|---------|
| `/` | GET | `PaginationRequest` | `ReportDTO` | `PaginatedResponse` |
| `/{id}` | GET | - | `ReportDTO` | `SuccessResponse` |
| `/generate` | POST | `ReportGenerationRequest` | `ReportGenerationResponse` | `SuccessResponse` |

### 5.6 Admin API

| Endpoint | Method | Request DTO | Response DTO | Wrapper |
|----------|--------|-------------|--------------|---------|
| `/performance/slow-queries` | GET | Query params | `SlowQueryDTO` | `List` |
| `/performance/top-queries` | GET | Query params | `SlowQueryDTO` | `List` |
| `/performance/low-cache-hit` | GET | Query params | `SlowQueryDTO` | `List` |
| `/performance/database-stats` | GET | - | `DatabaseStatsDTO` | - |
| `/performance/table-stats` | GET | - | `TableStatsDTO` | `List` |
| `/performance/index-usage` | GET | - | `IndexUsageDTO` | `List` |

### 5.7 Health API

| Endpoint | Method | Request DTO | Response DTO | Wrapper |
|----------|--------|-------------|--------------|---------|
| `/` | GET | - | `HealthDTO` | - |
| `/ping` | GET | - | `Dict` | - |
| `/detailed` | GET | - | `DetailedHealthDTO` | - |
| `/readiness` | GET | - | `Dict` | - |

---

## 6. Performance Considerations

### 6.1 Optimization Strategies

#### 1. Lazy Validation

```python
# Only validate when necessary
model_config = ConfigDict(
    validate_assignment=False,  # Disable validation on assignment
    validate_default=False,  # Skip default value validation
)
```

#### 2. Eager Loading Control

```python
# Control ORM relationship loading
query = db.query(Company).options(
    selectinload(Company.filings),  # Only when needed
    selectinload(Company.metrics),
)
```

#### 3. Field Exclusion

```python
# Allow clients to exclude fields
@router.get("/")
async def list_companies(
    exclude_fields: Optional[List[str]] = Query(None),
):
    companies = # ... query ...

    return [
        CompanyDTO.model_validate(c).model_dump(exclude=set(exclude_fields or []))
        for c in companies
    ]
```

#### 4. Response Caching

```python
# Cache serialized responses
@router.get("/")
@cache_key_wrapper(prefix="companies_dto", expire=3600)
async def list_companies():
    # Response cached as serialized JSON
    pass
```

### 6.2 Performance Benchmarks

#### Target Metrics

- **Serialization Time**: <5ms per object
- **Validation Time**: <10ms per request
- **Memory Overhead**: <20% vs direct ORM mapping
- **Response Size**: <10% increase with metadata

---

## 7. Testing Strategy

### 7.1 Unit Tests

#### DTO Validation Tests

```python
# tests/unit/dto/test_companies.py

def test_company_dto_valid():
    """Test valid company DTO creation."""
    data = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "ticker": "DUOL",
        "name": "Duolingo Inc.",
        # ... other fields ...
    }

    dto = CompanyDTO.model_validate(data)
    assert dto.ticker == "DUOL"
    assert isinstance(dto.id, str)  # UUID serialized to string


def test_company_create_validation():
    """Test company creation validation."""
    with pytest.raises(ValidationError) as exc:
        CompanyCreate(ticker="TOOLONGTICKER", name="Test")

    assert "ticker" in str(exc.value)
    assert "max_length" in str(exc.value)


def test_ticker_normalization():
    """Test ticker symbol normalization."""
    dto = CompanyCreate(ticker=" duol ", name="Test")
    assert dto.ticker == "DUOL"  # Uppercase and trimmed
```

### 7.2 Integration Tests

#### API Response Tests

```python
# tests/integration/test_companies_dto.py

async def test_list_companies_pagination(client):
    """Test paginated company listing."""
    response = await client.get("/api/v1/companies?limit=10&offset=0")

    assert response.status_code == 200
    data = response.json()

    # Check pagination wrapper
    assert "data" in data
    assert "pagination" in data
    assert data["pagination"]["limit"] == 10
    assert data["pagination"]["offset"] == 0
    assert len(data["data"]) <= 10

    # Check DTO fields
    company = data["data"][0]
    assert "id" in company
    assert "ticker" in company
    assert isinstance(company["id"], str)  # UUID as string


async def test_error_response_format(client):
    """Test standardized error response."""
    response = await client.get("/api/v1/companies/invalid-uuid")

    assert response.status_code == 404
    data = response.json()

    assert data["success"] is False
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "meta" in data
    assert "request_id" in data["meta"]
```

### 7.3 Performance Tests

```python
# tests/performance/test_dto_serialization.py

import time

def test_dto_serialization_performance():
    """Test DTO serialization performance."""
    # Create 1000 company objects
    companies = [create_mock_company() for _ in range(1000)]

    start = time.perf_counter()
    dtos = [CompanyDTO.model_validate(c) for c in companies]
    serialized = [dto.model_dump() for dto in dtos]
    end = time.perf_counter()

    elapsed_ms = (end - start) * 1000
    per_object_ms = elapsed_ms / 1000

    assert per_object_ms < 5, f"Serialization too slow: {per_object_ms:.2f}ms per object"
```

---

## 8. Documentation

### 8.1 OpenAPI Schema

DTOs automatically generate OpenAPI schemas with:

- Field descriptions
- Example values
- Validation constraints
- Required/optional indicators
- Data types and formats

### 8.2 API Documentation

```python
@router.get(
    "/",
    response_model=PaginatedResponse[CompanyDTO],
    summary="List companies",
    description="""
    Retrieve a paginated list of EdTech companies.

    Use offset and limit parameters for pagination.
    Results are sorted by created_at descending by default.
    """,
    responses={
        200: {
            "description": "Successful response with paginated companies",
            "content": {
                "application/json": {
                    "example": {
                        "data": [...],
                        "pagination": {...}
                    }
                }
            }
        },
        422: {
            "description": "Validation error",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse,
        }
    },
    tags=["Companies"],
)
async def list_companies(...):
    ...
```

---

## 9. Acceptance Criteria

### 9.1 Functional Requirements

- [ ] All API endpoints use standardized DTOs
- [ ] Pagination wrapper implemented for list endpoints
- [ ] Error responses follow standard format
- [ ] UUID fields serialized to strings
- [ ] Datetime fields serialized to ISO 8601 strings
- [ ] Input validation works for all DTOs
- [ ] Response metadata includes request_id and timestamp

### 9.2 Non-Functional Requirements

- [ ] DTO serialization <5ms per object (p95)
- [ ] Request validation <10ms per request (p95)
- [ ] Memory overhead <20% vs current implementation
- [ ] 100% backward compatibility maintained
- [ ] OpenAPI schema auto-generated
- [ ] All DTOs have comprehensive unit tests
- [ ] Integration tests pass for all endpoints

### 9.3 Documentation Requirements

- [ ] OpenAPI documentation complete
- [ ] Example requests/responses provided
- [ ] Migration guide written
- [ ] Validation rules documented
- [ ] Error code reference created

---

## 10. Risks & Mitigation

### 10.1 Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Breaking changes to existing clients | High | Medium | Dual response format with opt-in |
| Performance degradation | Medium | Low | Benchmarking and optimization |
| Validation too strict | Medium | Medium | Comprehensive testing, gradual rollout |
| Migration takes longer than planned | Low | Medium | Phased approach, clear milestones |

### 10.2 Rollback Plan

1. **Feature flags**: Enable/disable DTO layer per endpoint
2. **Gradual rollout**: Migrate one API at a time
3. **Monitoring**: Track error rates and performance
4. **Quick revert**: Keep old code paths for easy rollback

---

## 11. Success Metrics

### 11.1 Technical Metrics

- **API Response Consistency**: 100% of endpoints use standard format
- **Validation Coverage**: 100% of input fields validated
- **Error Handling**: 100% of errors follow standard format
- **Performance**: <5% overhead vs current implementation
- **Test Coverage**: >95% for DTO code

### 11.2 Quality Metrics

- **Breaking Changes**: 0 unintended breaking changes
- **Bug Reports**: <5 DTO-related bugs in first month
- **API Documentation**: 100% of DTOs documented in OpenAPI
- **Client Adoption**: >80% of clients opt-in to new format within 6 months

---

## 12. Next Steps

1. **Review & Approval**: Stakeholder review of specification (1 week)
2. **Pseudocode Phase**: Design detailed algorithms and transformers (SPARC Phase 2)
3. **Architecture Phase**: Design system architecture and integration (SPARC Phase 3)
4. **Refinement Phase**: TDD implementation (SPARC Phase 4)
5. **Completion Phase**: Integration and deployment (SPARC Phase 5)

---

## Appendices

### Appendix A: Example Request/Response

#### Request
```http
GET /api/v1/companies?limit=2&offset=0 HTTP/1.1
Host: api.corporate-intel.example.com
X-API-Version: v2
Authorization: Bearer <token>
```

#### Response
```json
{
  "data": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "ticker": "DUOL",
      "name": "Duolingo Inc.",
      "cik": "0001609711",
      "sector": "Technology",
      "subsector": "Educational Software",
      "category": "direct_to_consumer",
      "delivery_model": "b2c",
      "subcategory": ["Language Learning", "Gamification"],
      "monetization_strategy": ["Freemium", "Subscription"],
      "founded_year": 2011,
      "headquarters": "Pittsburgh, PA, USA",
      "website": "https://www.duolingo.com",
      "employee_count": 700,
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T14:20:00Z"
    }
  ],
  "pagination": {
    "offset": 0,
    "limit": 2,
    "total": null,
    "count": 1,
    "has_more": false
  }
}
```

### Appendix B: DTO Module Structure

```
src/api/dto/
├── __init__.py
├── base.py              # Base DTOs, pagination, response wrappers
├── errors.py            # Error DTOs
├── companies.py         # Company DTOs
├── filings.py           # Filing DTOs
├── metrics.py           # Metric DTOs
├── intelligence.py      # Intelligence DTOs
├── reports.py           # Report DTOs
├── health.py            # Health check DTOs
├── admin.py             # Admin DTOs
└── serializers.py       # Custom field serializers
```

### Appendix C: References

- [Pydantic V2 Documentation](https://docs.pydantic.dev/latest/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [JSON:API Specification](https://jsonapi.org/) (reference for response format)
- [RFC 7807](https://datatracker.ietf.org/doc/html/rfc7807) (Problem Details for HTTP APIs)

---

**End of Specification Document**
