# DTO Layer Implementation

## Overview

This document describes the comprehensive Data Transfer Object (DTO) layer implemented for all API endpoints in the corporate intelligence platform. The DTO layer provides type-safe, validated, and well-documented data structures for API requests and responses.

## Architecture

### Directory Structure

```
src/dto/
├── __init__.py              # Main DTO exports
├── base.py                  # Base DTO classes and utilities
├── factories.py             # Model-to-DTO conversion factories
└── api/                     # Endpoint-specific DTOs
    ├── __init__.py          # API DTO exports
    ├── companies.py         # Company management DTOs
    ├── filings.py           # SEC filing DTOs
    ├── metrics.py           # Financial metrics DTOs
    ├── intelligence.py      # Market intelligence DTOs
    ├── reports.py           # Analysis report DTOs
    ├── admin.py             # Admin/monitoring DTOs
    └── health.py            # Health check DTOs

tests/dto/
├── __init__.py
├── test_base_dto.py         # Base infrastructure tests
├── test_companies_dto.py    # Company DTO tests
└── test_factories.py        # Factory function tests
```

## Core Components

### 1. Base DTOs (`src/dto/base.py`)

#### BaseDTO
Foundation for all DTOs with common configuration:
- Validates data using Pydantic v2
- Converts SQLAlchemy models automatically
- Provides strict type checking
- Generates OpenAPI schemas

```python
class BaseDTO(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
        str_strip_whitespace=True
    )
```

#### TimestampedDTO
Mixin for models with timestamp fields:

```python
class TimestampedDTO(BaseDTO):
    created_at: datetime
    updated_at: Optional[datetime] = None
```

#### PaginatedResponse
Generic paginated response wrapper:

```python
class PaginatedResponse(BaseDTO, Generic[T]):
    items: List[T]
    total: int
    limit: int
    offset: int
    has_more: bool
```

#### Error Handling
Standardized error responses:

```python
class ErrorDetail(BaseDTO):
    code: str
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseDTO):
    error: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    timestamp: datetime
    request_id: Optional[str] = None
```

### 2. Endpoint-Specific DTOs

#### Companies (`src/dto/api/companies.py`)

**DTOs:**
- `CompanyCreateDTO` - Creating new companies
- `CompanyUpdateDTO` - Updating companies
- `CompanyDTO` - Full company response
- `CompanyListDTO` - Paginated company list
- `CompanyMetricsDTO` - Company KPIs
- `TrendingCompanyDTO` - Top performers

**Features:**
- Ticker validation (uppercase, alphanumeric)
- CIK validation (10-digit format)
- Category/sector validation
- EdTech-specific fields
- Comprehensive examples

**Example:**
```python
company = CompanyCreateDTO(
    ticker="CHGG",
    name="Chegg, Inc.",
    cik="0001364954",
    category="higher_education",
    delivery_model="b2c",
    monetization_strategy=["subscription"]
)
```

#### Filings (`src/dto/api/filings.py`)

**DTOs:**
- `FilingCreateDTO` - Creating filing records
- `FilingDTO` - Full filing details
- `FilingListItemDTO` - Lightweight list item
- `FilingListDTO` - Paginated filing list
- `FilingFilterDTO` - Query filters

**Features:**
- Filing type validation (10-K, 10-Q, 8-K, etc.)
- Accession number format validation
- Processing status tracking
- Date range filtering

#### Metrics (`src/dto/api/metrics.py`)

**DTOs:**
- `MetricCreateDTO` - Creating metrics
- `MetricDTO` - Full metric details
- `MetricListItemDTO` - Lightweight list item
- `MetricsListDTO` - Paginated metric list
- `MetricFilterDTO` - Query filters
- `MetricAggregationDTO` - Aggregated statistics

**Features:**
- Metric type/category validation
- Period type validation (quarterly, annual, etc.)
- Confidence score tracking
- TimescaleDB compatibility (BigInteger ID)

#### Intelligence (`src/dto/api/intelligence.py`)

**DTOs:**
- `IntelligenceCreateDTO` - Creating intelligence items
- `IntelligenceDTO` - Full intelligence details
- `IntelligenceListItemDTO` - Lightweight list item
- `IntelligenceListDTO` - Paginated list
- `IntelligenceFilterDTO` - Query filters

**Features:**
- Intelligence type validation
- Sentiment score (-1 to 1)
- Confidence score (0 to 1)
- Related companies tracking
- Impact assessment

#### Reports (`src/dto/api/reports.py`)

**DTOs:**
- `ReportGenerationRequestDTO` - Report generation request
- `ReportGenerationResponseDTO` - Generation response
- `ReportDTO` - Full report details
- `ReportListItemDTO` - Lightweight list item
- `ReportListDTO` - Paginated list

**Features:**
- Report type validation
- Company selection (max 50)
- Date range configuration
- Format options (JSON, PDF, HTML, Excel)
- Visualization options

#### Admin (`src/dto/api/admin.py`)

**DTOs:**
- `QueryPerformanceDTO` - Query statistics
- `DatabaseStatsDTO` - Database metrics
- `TableStatsDTO` - Table access patterns
- `IndexUsageDTO` - Index utilization
- `PerformanceRecommendationDTO` - Optimization tips

**Features:**
- pg_stat_statements integration
- Cache hit ratio tracking
- Performance monitoring
- Actionable recommendations

#### Health (`src/dto/api/health.py`)

**DTOs:**
- `HealthDTO` - Basic health check
- `DetailedHealthDTO` - Comprehensive health
- `ComponentHealthDTO` - Component status
- `PlatformMetricsDTO` - System metrics
- `ReadinessDTO` - K8s readiness probe
- `LivenessDTO` - K8s liveness probe
- `ServiceInfoDTO` - Service details

**Features:**
- Component-level health tracking
- Response time monitoring
- Platform statistics
- Kubernetes compatibility

### 3. Factory Functions (`src/dto/factories.py`)

Centralized conversion between SQLAlchemy models and DTOs:

#### Specific Factories

```python
# Companies
def company_to_dto(company: Company) -> CompanyDTO
def companies_to_list_dto(...) -> CompanyListDTO
def company_metrics_to_dto(...) -> CompanyMetricsDTO

# Filings
def filing_to_dto(filing: SECFiling) -> FilingDTO
def filings_to_list_dto(...) -> FilingListDTO

# Metrics
def metric_to_dto(metric: FinancialMetric) -> MetricDTO
def metrics_to_list_dto(...) -> MetricsListDTO

# Intelligence
def intelligence_to_dto(...) -> IntelligenceDTO
def intelligence_to_list_dto(...) -> IntelligenceListDTO

# Reports
def report_to_dto(report: AnalysisReport) -> ReportDTO
def reports_to_list_dto(...) -> ReportListDTO
```

#### Generic Factories

```python
# Convert any model to DTO
def model_to_dto(model: Any, dto_class: Type[T]) -> T

# Convert list of models
def models_to_dtos(models: List[Any], dto_class: Type[T]) -> List[T]

# Convert dictionary to DTO
def dict_to_dto(data: Dict[str, Any], dto_class: Type[T]) -> T

# Create paginated response
def paginated_response(...) -> Any
```

## Usage Examples

### 1. Creating DTOs from Models

```python
from src.dto.factories import company_to_dto, companies_to_list_dto
from src.db.models import Company

# Single company
company = db.query(Company).first()
dto = company_to_dto(company)

# List of companies
companies = db.query(Company).all()
list_dto = companies_to_list_dto(
    companies=companies,
    total=100,
    limit=20,
    offset=0
)
```

### 2. Using DTOs in API Endpoints

```python
from fastapi import APIRouter
from src.dto.api.companies import CompanyDTO, CompanyCreateDTO
from src.dto.factories import company_to_dto

router = APIRouter()

@router.post("/", response_model=CompanyDTO)
async def create_company(
    company_data: CompanyCreateDTO,
    db: Session = Depends(get_db)
):
    # Create company from DTO
    db_company = Company(**company_data.model_dump())
    db.add(db_company)
    db.commit()
    db.refresh(db_company)

    # Convert to response DTO
    return company_to_dto(db_company)
```

### 3. Validation and Error Handling

```python
from pydantic import ValidationError
from src.dto.base import ErrorResponse, ErrorDetail

try:
    company = CompanyCreateDTO(
        ticker="invalid@",  # Invalid format
        name="Test"
    )
except ValidationError as e:
    # Convert to error response
    errors = [
        ErrorDetail(
            code="VALIDATION_ERROR",
            message=err["msg"],
            field=err["loc"][0]
        )
        for err in e.errors()
    ]

    return ErrorResponse(
        error="ValidationError",
        message="Invalid company data",
        details=errors
    )
```

### 4. Paginated Responses

```python
from src.dto.api.companies import CompanyListDTO
from src.dto.factories import companies_to_list_dto

companies = db.query(Company).limit(20).offset(0).all()
total = db.query(Company).count()

response = companies_to_list_dto(
    companies=companies,
    total=total,
    limit=20,
    offset=0
)
```

## Validation Features

### Field Validators

DTOs include comprehensive validation:

1. **String Patterns**: Regex validation for tickers, CIKs, categories
2. **Numeric Bounds**: Min/max values for scores, counts, percentages
3. **Custom Validators**: Field-specific logic (uppercase conversion, date ranges)
4. **Cross-field Validation**: Related field constraints

### Example Validators

```python
@field_validator("ticker")
@classmethod
def validate_ticker(cls, v: str) -> str:
    """Ensure ticker is uppercase."""
    return v.upper()

@field_validator("date_end")
@classmethod
def validate_date_range(cls, v: Optional[datetime], info) -> Optional[datetime]:
    """Ensure end date is after start date."""
    if v and info.data.get("date_start"):
        if v < info.data["date_start"]:
            raise ValueError("date_end must be after date_start")
    return v
```

## OpenAPI Integration

All DTOs automatically generate OpenAPI schemas with:

1. **Field Descriptions**: Clear documentation for each field
2. **Examples**: Realistic example data
3. **Constraints**: Min/max values, patterns, enums
4. **Required Fields**: Clear indication of mandatory fields

### Example Schema

```python
model_config = {
    "json_schema_extra": {
        "example": {
            "ticker": "CHGG",
            "name": "Chegg, Inc.",
            "category": "higher_education",
            "delivery_model": "b2c"
        }
    }
}
```

## Testing

Comprehensive test coverage includes:

1. **Base DTO Tests**: Core functionality, validation, mixins
2. **Endpoint DTO Tests**: Field validation, constraints, examples
3. **Factory Tests**: Model conversion, error handling
4. **Integration Tests**: End-to-end API usage

### Running Tests

```bash
# Run all DTO tests
pytest tests/dto/

# Run specific test file
pytest tests/dto/test_companies_dto.py

# Run with coverage
pytest tests/dto/ --cov=src/dto --cov-report=html
```

## Best Practices

### 1. DTO Naming Conventions

- **Request DTOs**: `{Entity}CreateDTO`, `{Entity}UpdateDTO`
- **Response DTOs**: `{Entity}DTO`, `{Entity}ListItemDTO`
- **List DTOs**: `{Entity}ListDTO`
- **Filter DTOs**: `{Entity}FilterDTO`

### 2. Field Organization

- Required fields first
- Optional fields after
- Group related fields together
- Add descriptive field names

### 3. Documentation

- Add docstrings to all DTOs
- Document field purposes
- Provide realistic examples
- Explain validation rules

### 4. Validation

- Use field validators for complex logic
- Validate at the DTO level, not in endpoints
- Provide clear error messages
- Include examples of valid data

### 5. Factory Usage

- Use specific factories when available
- Fall back to generic factories for custom DTOs
- Keep conversion logic in factories
- Don't duplicate conversion code in endpoints

## Migration Guide

### Updating Existing Endpoints

1. **Import new DTOs**:
```python
from src.dto.api.companies import CompanyDTO, CompanyCreateDTO
from src.dto.factories import company_to_dto
```

2. **Update endpoint signatures**:
```python
# Before
@router.post("/")
async def create_company(company: dict):
    pass

# After
@router.post("/", response_model=CompanyDTO)
async def create_company(company: CompanyCreateDTO):
    pass
```

3. **Use factories for conversion**:
```python
# Before
return company.__dict__

# After
return company_to_dto(company)
```

## Future Enhancements

1. **Computed Fields**: Add derived fields using Pydantic computed fields
2. **Nested DTOs**: Support for complex nested structures
3. **Partial Updates**: PATCH endpoint support with optional fields
4. **DTO Versioning**: Support for API versioning
5. **Auto-documentation**: Generate DTO documentation from code

## References

- [Pydantic V2 Documentation](https://docs.pydantic.dev/latest/)
- [FastAPI Response Models](https://fastapi.tiangolo.com/tutorial/response-model/)
- [OpenAPI Schema Examples](https://swagger.io/docs/specification/adding-examples/)

## Summary

The DTO layer provides:

✅ **Type Safety**: Pydantic validation catches errors early
✅ **Documentation**: Auto-generated OpenAPI schemas
✅ **Consistency**: Standardized response formats
✅ **Maintainability**: Centralized validation logic
✅ **Testing**: Comprehensive test coverage
✅ **Developer Experience**: Clear, intuitive APIs

All API endpoints now have:
- Validated request/response models
- Comprehensive field documentation
- Realistic examples
- Factory functions for easy conversion
- Full test coverage
