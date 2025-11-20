# Large File Refactoring Analysis
## Corporate Intelligence Platform - Frontend File Splitting Strategy

**Generated:** 2025-11-20
**Analyst:** Code Quality Analyzer (Claude Code)
**Total Files Analyzed:** 7
**Total Lines:** 4,726 lines

---

## Executive Summary

This analysis examines 7 large Python files (>500 lines) in the corporate intelligence platform that exceed maintainability thresholds. The analysis identifies logical module boundaries, dependency patterns, and provides concrete refactoring recommendations to improve code organization, testability, and developer productivity.

### Key Findings

- **Total LOC to Refactor:** 4,726 lines across 7 files
- **Primary Issues:**
  - Monolithic file structures (largest: 833 lines)
  - Mixed responsibilities (data access + business logic + API clients)
  - Duplicate utility functions across files
  - Tight coupling between layers
- **Recommended Modules:** 21 new focused modules
- **Shared Utilities:** 8 common utility modules to extract
- **Estimated Effort:** 3-5 days (with comprehensive testing)

---

## 1. SEC Ingestion Pipeline (833 lines)
**File:** `src/pipeline/sec_ingestion.py`
**Current Complexity:** High
**Refactoring Priority:** Critical

### Current Structure Analysis

```
sec_ingestion.py (833 lines)
├── Models (72 lines)
│   ├── FilingRequest (BaseModel)
│   └── SECAPIClient (class)
├── API Client (191 lines)
│   ├── Rate limiting
│   ├── Ticker-to-CIK mapping
│   ├── Company info fetching
│   ├── Filing retrieval
│   └── Content downloading
├── Rate Limiter (16 lines)
├── Prefect Tasks (229 lines)
│   ├── fetch_company_data
│   ├── fetch_filings
│   ├── download_filing
│   ├── validate_filing_data (157 lines GX validation)
│   └── store_filing (118 lines DB logic)
├── Database Operations (94 lines)
│   └── get_or_create_company
├── Business Logic (24 lines)
│   └── classify_edtech_company
└── Prefect Flows (77 lines)
    ├── sec_ingestion_flow
    └── batch_sec_ingestion_flow
```

### Issues Identified

1. **Mixed Concerns**: API client, data validation, DB operations, workflow orchestration in one file
2. **God Class**: SECAPIClient handles multiple responsibilities (HTTP, caching, rate limiting, data transformation)
3. **Validation Complexity**: Great Expectations validation logic (157 lines) embedded in task
4. **Database Logic**: Company lookup/creation mixed with filing ingestion
5. **Code Duplication**: RateLimiter duplicated from data_sources.py
6. **Testing Challenges**: Monolithic structure makes unit testing difficult

### Proposed Module Structure

```
src/pipeline/sec/
├── __init__.py
├── models.py                      # 50 lines - Pydantic models
│   ├── FilingRequest
│   ├── FilingData
│   └── CompanyData
├── client.py                      # 180 lines - SEC API client
│   └── SECAPIClient
│       ├── get_ticker_to_cik_mapping()
│       ├── get_company_info()
│       ├── get_filings()
│       └── download_filing_content()
├── validators.py                  # 170 lines - Data validation
│   ├── FilingValidator
│   │   ├── validate_filing_data()
│   │   ├── validate_schema()
│   │   ├── validate_formats()
│   │   └── validate_content_quality()
│   └── ValidationSuite (Great Expectations wrapper)
├── tasks.py                       # 150 lines - Prefect tasks
│   ├── fetch_company_data()
│   ├── fetch_filings()
│   ├── download_filing()
│   ├── validate_filing()
│   └── store_filing()
├── flows.py                       # 100 lines - Prefect workflows
│   ├── sec_ingestion_flow()
│   └── batch_sec_ingestion_flow()
├── repository.py                  # 120 lines - Database operations
│   └── SECFilingRepository
│       ├── get_or_create_company()
│       ├── find_filing_by_accession()
│       ├── upsert_filing()
│       └── get_recent_filings()
└── classifiers.py                 # 40 lines - Business logic
    ├── classify_edtech_company()
    └── classify_by_sic_code()
```

### Benefits

- **Separation of Concerns**: API client, validation, storage, orchestration separated
- **Testability**: Each module can be tested independently
- **Reusability**: SECAPIClient can be used outside Prefect workflows
- **Maintainability**: Files under 200 lines, focused responsibilities
- **Extensibility**: Easy to add new validators or filing types

### Migration Steps

1. **Phase 1: Extract Models** (30 min)
   - Create `models.py` with FilingRequest
   - Add FilingData, CompanyData models
   - Update imports in main file

2. **Phase 2: Extract API Client** (1 hour)
   - Move SECAPIClient to `client.py`
   - Extract rate limiting to shared utility
   - Add comprehensive docstrings
   - Write unit tests for API client

3. **Phase 3: Extract Validators** (1.5 hours)
   - Create `validators.py` with FilingValidator
   - Wrap Great Expectations in ValidationSuite
   - Add custom validation rules
   - Test validation edge cases

4. **Phase 4: Extract Repository** (1 hour)
   - Create SECFilingRepository in `repository.py`
   - Move get_or_create_company
   - Add filing CRUD operations
   - Test database operations

5. **Phase 5: Reorganize Tasks & Flows** (1 hour)
   - Split tasks.py and flows.py
   - Update task dependencies
   - Add integration tests
   - Update documentation

6. **Phase 6: Extract Classifiers** (30 min)
   - Move business logic to `classifiers.py`
   - Add category mapping
   - Test classification rules

### Import Changes Required

**Before:**
```python
from src.pipeline.sec_ingestion import (
    SECAPIClient,
    FilingRequest,
    sec_ingestion_flow
)
```

**After:**
```python
from src.pipeline.sec.models import FilingRequest
from src.pipeline.sec.client import SECAPIClient
from src.pipeline.sec.flows import sec_ingestion_flow
from src.pipeline.sec.validators import FilingValidator
from src.pipeline.sec.repository import SECFilingRepository
```

---

## 2. Visualization Components (765 lines)
**File:** `src/visualization/components.py`
**Current Complexity:** High
**Refactoring Priority:** High

### Current Structure Analysis

```
components.py (765 lines)
├── VisualizationComponents (class) - 28 lines
│   ├── COLORS (constants)
│   └── CATEGORY_COLORS (constants)
├── Chart Functions (737 lines)
│   ├── create_metrics_waterfall (65 lines)
│   ├── create_cohort_heatmap (74 lines)
│   ├── create_competitive_landscape_scatter (98 lines)
│   ├── create_segment_comparison_radar (63 lines)
│   ├── create_market_share_sunburst (55 lines)
│   ├── create_revenue_comparison_bar (52 lines)
│   ├── create_margin_comparison_chart (63 lines)
│   ├── create_earnings_growth_distribution (69 lines)
│   ├── create_revenue_by_category_treemap (71 lines)
│   └── create_retention_curves (58 lines)
└── SPARC Documentation (35 lines)
```

### Issues Identified

1. **Functional Organization**: All visualization functions in one file despite different categories
2. **God Class Pattern**: VisualizationComponents class only holds constants (anti-pattern)
3. **Data Transformation Mixed**: Business logic (data prep) mixed with visualization
4. **Color Management**: Colors scattered across functions and class
5. **Duplicate Logic**: Similar data validation/formatting in multiple functions
6. **No Abstraction**: Common chart patterns not extracted

### Proposed Module Structure

```
src/visualization/
├── __init__.py
├── constants.py                   # 40 lines - Theme & colors
│   ├── CHART_COLORS
│   ├── CATEGORY_COLORS
│   ├── DEFAULT_LAYOUT
│   └── CHART_TEMPLATES
├── base.py                        # 80 lines - Base chart utilities
│   ├── BaseChartBuilder
│   ├── format_currency()
│   ├── format_percentage()
│   ├── create_empty_figure()
│   └── add_source_annotation()
├── financial.py                   # 180 lines - Financial charts
│   ├── create_metrics_waterfall()
│   ├── create_revenue_comparison_bar()
│   └── create_margin_comparison_chart()
├── behavioral.py                  # 140 lines - User behavior charts
│   ├── create_cohort_heatmap()
│   └── create_retention_curves()
├── competitive.py                 # 160 lines - Market analysis charts
│   ├── create_competitive_landscape_scatter()
│   └── create_segment_comparison_radar()
├── hierarchical.py                # 140 lines - Tree/hierarchy charts
│   ├── create_market_share_sunburst()
│   └── create_revenue_by_category_treemap()
└── statistical.py                 # 90 lines - Distribution charts
    └── create_earnings_growth_distribution()
```

### Benefits

- **Logical Grouping**: Charts grouped by purpose (financial, behavioral, competitive)
- **Discoverability**: Developers can quickly find relevant chart types
- **Reduced File Size**: Each module <200 lines
- **Shared Utilities**: Common formatting/validation extracted to base.py
- **Theme Management**: Centralized color/layout configuration
- **Testing**: Easier to test chart categories independently

### Migration Steps

1. **Phase 1: Extract Constants** (20 min)
   - Create `constants.py`
   - Move all color definitions
   - Define default layouts and templates

2. **Phase 2: Create Base Utilities** (45 min)
   - Create `base.py` with BaseChartBuilder
   - Extract common formatting functions
   - Add empty figure generator
   - Test utility functions

3. **Phase 3: Group Financial Charts** (30 min)
   - Create `financial.py`
   - Move waterfall, revenue, margin charts
   - Update imports

4. **Phase 4: Group Behavioral Charts** (20 min)
   - Create `behavioral.py`
   - Move cohort and retention charts

5. **Phase 5: Group Competitive Charts** (25 min)
   - Create `competitive.py`
   - Move landscape scatter and radar charts

6. **Phase 6: Group Hierarchical Charts** (20 min)
   - Create `hierarchical.py`
   - Move sunburst and treemap charts

7. **Phase 7: Group Statistical Charts** (15 min)
   - Create `statistical.py`
   - Move distribution charts

8. **Phase 8: Update Imports** (30 min)
   - Update all imports across codebase
   - Run tests to ensure nothing broke

### Import Changes Required

**Before:**
```python
from src.visualization.components import (
    create_metrics_waterfall,
    create_cohort_heatmap,
    create_competitive_landscape_scatter
)
```

**After:**
```python
from src.visualization.financial import create_metrics_waterfall
from src.visualization.behavioral import create_cohort_heatmap
from src.visualization.competitive import create_competitive_landscape_scatter
```

---

## 3. Dashboard Service (745 lines)
**File:** `src/services/dashboard_service.py`
**Current Complexity:** High
**Refactoring Priority:** High

### Current Structure Analysis

```
dashboard_service.py (745 lines)
├── DashboardService (class) - 704 lines
│   ├── __init__ (9 lines)
│   ├── Cache Management (46 lines)
│   │   ├── _init_cache()
│   │   ├── _get_cached()
│   │   └── _set_cached()
│   ├── Company Performance (139 lines)
│   │   ├── get_company_performance()
│   │   └── _get_company_performance_fallback()
│   ├── Competitive Landscape (114 lines)
│   │   └── get_competitive_landscape()
│   ├── Company Details (84 lines)
│   │   └── get_company_details()
│   ├── Time Series Metrics (82 lines)
│   │   └── get_quarterly_metrics()
│   ├── Market Summary (83 lines)
│   │   └── get_market_summary()
│   ├── Segment Comparison (87 lines)
│   │   └── get_segment_comparison()
│   └── Data Freshness (52 lines)
│       └── get_data_freshness()
└── Docstrings (41 lines)
```

### Issues Identified

1. **God Class**: DashboardService has 8+ distinct responsibilities
2. **Query Complexity**: Raw SQL queries mixed with service logic
3. **Cache Management**: Manual cache operations in every method (code duplication)
4. **Fallback Logic**: Fallback to repositories mixed in service layer
5. **Data Transformation**: JSON serialization logic scattered throughout
6. **No Query Builder**: Complex SQL strings hard to maintain/test
7. **Error Handling**: Inconsistent error handling patterns

### Proposed Module Structure

```
src/services/dashboard/
├── __init__.py
├── base.py                        # 60 lines - Base service class
│   └── BaseCachedService
│       ├── _init_cache()
│       ├── _get_cached()
│       ├── _set_cached()
│       └── _cache_decorator()
├── company_service.py             # 180 lines - Company data
│   └── CompanyService(BaseCachedService)
│       ├── get_company_performance()
│       ├── get_company_details()
│       └── _build_performance_query()
├── market_service.py              # 140 lines - Market analysis
│   └── MarketService(BaseCachedService)
│       ├── get_competitive_landscape()
│       ├── get_market_summary()
│       └── get_segment_comparison()
├── metrics_service.py             # 120 lines - Time series data
│   └── MetricsService(BaseCachedService)
│       ├── get_quarterly_metrics()
│       ├── calculate_growth_rates()
│       └── aggregate_metrics()
├── metadata_service.py            # 60 lines - System metadata
│   └── MetadataService(BaseCachedService)
│       └── get_data_freshness()
├── queries/                       # SQL query builders
│   ├── __init__.py
│   ├── company_queries.py         # 80 lines
│   ├── market_queries.py          # 70 lines
│   └── metrics_queries.py         # 50 lines
└── transformers.py                # 80 lines - Data transformation
    ├── transform_company_data()
    ├── transform_metrics_to_dataframe()
    └── calculate_composite_scores()
```

### Benefits

- **Single Responsibility**: Each service handles one domain
- **DRY Cache Logic**: BaseCachedService eliminates duplication
- **Query Organization**: SQL queries separated and testable
- **Data Transformation**: Centralized transformation logic
- **Error Handling**: Consistent patterns across services
- **Testability**: Small, focused services easy to mock and test
- **Extensibility**: Easy to add new services or queries

### Migration Steps

1. **Phase 1: Create Base Service** (1 hour)
   - Create `base.py` with BaseCachedService
   - Implement cache decorator
   - Add error handling patterns
   - Test base functionality

2. **Phase 2: Extract Query Builders** (1.5 hours)
   - Create `queries/` package
   - Move SQL queries to builders
   - Parameterize queries
   - Test query generation

3. **Phase 3: Extract Company Service** (45 min)
   - Create `company_service.py`
   - Move company-related methods
   - Inherit from BaseCachedService
   - Test company operations

4. **Phase 4: Extract Market Service** (45 min)
   - Create `market_service.py`
   - Move market analysis methods
   - Test market operations

5. **Phase 5: Extract Metrics Service** (30 min)
   - Create `metrics_service.py`
   - Move time-series methods
   - Test metrics operations

6. **Phase 6: Extract Metadata Service** (20 min)
   - Create `metadata_service.py`
   - Move freshness tracking

7. **Phase 7: Create Transformers** (45 min)
   - Create `transformers.py`
   - Extract data transformation logic
   - Add unit tests

8. **Phase 8: Integration Testing** (1 hour)
   - Update imports in dashboard app
   - Run full integration tests
   - Performance benchmarking

### Import Changes Required

**Before:**
```python
from src.services.dashboard_service import DashboardService

service = DashboardService(session)
companies = await service.get_company_performance()
```

**After:**
```python
from src.services.dashboard import CompanyService, MarketService

company_service = CompanyService(session)
market_service = MarketService(session)

companies = await company_service.get_company_performance()
landscape = await market_service.get_competitive_landscape()
```

---

## 4. Yahoo Finance Ingestion (632 lines)
**File:** `src/pipeline/yahoo_finance_ingestion.py`
**Current Complexity:** Medium-High
**Refactoring Priority:** Medium

### Current Structure Analysis

```
yahoo_finance_ingestion.py (632 lines)
├── Company List (205 lines)
│   └── EDTECH_COMPANIES (27 company dictionaries)
├── Custom Exception (3 lines)
├── YahooFinanceIngestionPipeline (277 lines)
│   ├── __init__
│   ├── run() - main orchestration
│   ├── _fetch_yahoo_finance_data() - API calls
│   ├── _upsert_company() - DB operations
│   ├── _ingest_quarterly_financials() - data processing
│   ├── _notify_progress() - coordination hooks
│   └── _generate_report() - reporting
├── run_ingestion() (46 lines)
└── Main Entry Point (18 lines)
```

### Issues Identified

1. **Data Embedded**: 205 lines of company data in code (should be config/database)
2. **Mixed Concerns**: API client, DB operations, orchestration in one class
3. **Limited Reusability**: Pipeline class tightly coupled to specific workflow
4. **Circuit Breaker Duplication**: Similar patterns as sec_ingestion.py
5. **Error Handling**: Stats tracking mixed with business logic
6. **Testing**: Hard to test individual components

### Proposed Module Structure

```
src/pipeline/yahoo_finance/
├── __init__.py
├── config.py                      # 30 lines - Configuration
│   ├── load_companies_config()
│   └── CompanyListValidator
├── client.py                      # 120 lines - Yahoo Finance client
│   └── YahooFinanceClient
│       ├── get_stock_info()
│       ├── get_quarterly_financials()
│       └── get_company_overview()
├── processors.py                  # 140 lines - Data processing
│   └── FinancialDataProcessor
│       ├── process_income_statement()
│       ├── process_balance_sheet()
│       ├── calculate_metrics()
│       └── extract_quarterly_data()
├── pipeline.py                    # 150 lines - Orchestration
│   └── YahooFinanceIngestionPipeline
│       ├── run()
│       ├── process_company()
│       └── generate_report()
├── repository.py                  # 100 lines - Database operations
│   └── YahooFinanceRepository
│       ├── upsert_company()
│       ├── upsert_metrics()
│       └── get_ingestion_stats()
└── data/
    └── edtech_companies.yaml      # 230 lines - Company data
```

### Benefits

- **Configuration Management**: Companies in YAML (easier to update, validate)
- **Separation of Concerns**: API, processing, storage separated
- **Reusability**: YahooFinanceClient can be used elsewhere
- **Testability**: Mock API responses, test processing independently
- **Maintainability**: Clear boundaries between responsibilities

### Migration Steps

1. **Phase 1: Extract Company Data** (30 min)
   - Create `data/edtech_companies.yaml`
   - Move EDTECH_COMPANIES to YAML
   - Create config loader
   - Add validation schema

2. **Phase 2: Extract API Client** (45 min)
   - Create `client.py`
   - Move yfinance interaction code
   - Add rate limiting
   - Test API client

3. **Phase 3: Extract Data Processors** (1 hour)
   - Create `processors.py`
   - Move financial data extraction
   - Add metric calculations
   - Test data transformations

4. **Phase 4: Extract Repository** (45 min)
   - Create `repository.py`
   - Move DB operations
   - Add stats tracking

5. **Phase 5: Refactor Pipeline** (30 min)
   - Simplify pipeline class
   - Use extracted modules
   - Update error handling

6. **Phase 6: Testing & Documentation** (1 hour)
   - Write unit tests
   - Integration tests
   - Update README

### Import Changes Required

**Before:**
```python
from src.pipeline.yahoo_finance_ingestion import (
    YahooFinanceIngestionPipeline,
    EDTECH_COMPANIES
)
```

**After:**
```python
from src.pipeline.yahoo_finance.pipeline import YahooFinanceIngestionPipeline
from src.pipeline.yahoo_finance.config import load_companies_config
from src.pipeline.yahoo_finance.client import YahooFinanceClient
```

---

## 5. Metrics Repository (599 lines)
**File:** `src/repositories/metrics_repository.py`
**Current Complexity:** Medium
**Refactoring Priority:** Low-Medium

### Current Structure Analysis

```
metrics_repository.py (599 lines)
├── MetricsRepository (class) - 538 lines
│   ├── CRUD Operations (175 lines)
│   │   ├── upsert_metric() - 107 lines
│   │   ├── get_metrics_by_period() - 68 lines
│   │   └── Bulk operations
│   ├── Query Methods (140 lines)
│   │   ├── get_latest_metric()
│   │   ├── get_all_metrics_for_company()
│   │   ├── get_metrics_by_category()
│   │   └── delete_metrics_for_company()
│   ├── Aggregation Methods (130 lines)
│   │   ├── calculate_growth_rate()
│   │   └── get_metric_statistics()
│   └── Bulk Operations (93 lines)
│       └── bulk_upsert_metrics()
└── Docstrings (61 lines)
```

### Issues Identified

1. **Feature Clustering**: Analytics functions (growth, stats) mixed with CRUD
2. **Complex Upsert Logic**: 107 lines for single operation (could be simplified)
3. **Query Duplication**: Similar query patterns repeated
4. **No Query Builder**: SQL construction scattered in methods
5. **Limited Abstraction**: Time-series operations could be abstracted
6. **Testing Challenges**: Hard to test analytics separate from CRUD

### Proposed Module Structure

```
src/repositories/metrics/
├── __init__.py
├── base.py                        # 80 lines - Base repository
│   └── BaseMetricsRepository(BaseRepository)
│       ├── _build_filters()
│       └── _build_time_range_filter()
├── crud.py                        # 200 lines - CRUD operations
│   └── MetricsCRUDRepository(BaseMetricsRepository)
│       ├── upsert_metric()
│       ├── bulk_upsert_metrics()
│       ├── get_metrics_by_period()
│       ├── get_latest_metric()
│       └── delete_metrics_for_company()
├── analytics.py                   # 140 lines - Analytics operations
│   └── MetricsAnalyticsRepository(BaseMetricsRepository)
│       ├── calculate_growth_rate()
│       ├── get_metric_statistics()
│       ├── calculate_moving_average()
│       └── detect_trends()
├── queries.py                     # 100 lines - Query builders
│   ├── build_metric_query()
│   ├── build_time_series_query()
│   └── build_aggregation_query()
└── repository.py                  # 80 lines - Main interface
    └── MetricsRepository (facade combining CRUD + Analytics)
```

### Benefits

- **Separation of Concerns**: CRUD separated from analytics
- **Query Reusability**: Shared query builders
- **Extensibility**: Easy to add new analytics functions
- **Testing**: Test CRUD and analytics independently
- **Performance**: Optimized queries for specific use cases

### Migration Steps

1. **Phase 1: Create Base** (30 min)
   - Create `base.py`
   - Extract common query patterns

2. **Phase 2: Extract CRUD** (45 min)
   - Create `crud.py`
   - Move upsert and basic queries
   - Test CRUD operations

3. **Phase 3: Extract Analytics** (45 min)
   - Create `analytics.py`
   - Move growth and statistics methods
   - Add new analytics features

4. **Phase 4: Create Query Builders** (30 min)
   - Create `queries.py`
   - Extract SQL construction logic

5. **Phase 5: Create Facade** (20 min)
   - Create main `repository.py`
   - Combine CRUD + Analytics
   - Maintain backward compatibility

### Import Changes Required

**Before:**
```python
from src.repositories.metrics_repository import MetricsRepository

repo = MetricsRepository(session)
await repo.upsert_metric(...)
growth = await repo.calculate_growth_rate(...)
```

**After:**
```python
from src.repositories.metrics import MetricsRepository

# Same interface, improved internal structure
repo = MetricsRepository(session)
await repo.upsert_metric(...)
growth = await repo.calculate_growth_rate(...)
```

---

## 6. Data Sources Connectors (583 lines)
**File:** `src/connectors/data_sources.py`
**Current Complexity:** Medium-High
**Refactoring Priority:** Medium

### Current Structure Analysis

```
data_sources.py (583 lines)
├── Utility Functions (38 lines)
│   ├── safe_float()
│   └── RateLimiter (class)
├── Connector Classes (482 lines)
│   ├── SECEdgarConnector (60 lines)
│   ├── YahooFinanceConnector (66 lines)
│   ├── AlphaVantageConnector (87 lines)
│   ├── NewsAPIConnector (84 lines)
│   ├── CrunchbaseConnector (41 lines)
│   └── GitHubConnector (52 lines)
└── DataAggregator (102 lines)
    ├── get_comprehensive_company_data()
    └── _calculate_composite_score()
```

### Issues Identified

1. **Monolithic File**: 6 different API connectors in one file
2. **Code Duplication**: Rate limiting pattern repeated (also in sec_ingestion.py)
3. **Mixed Abstractions**: HTTP clients, business logic, scoring mixed
4. **No Base Class**: Common connector patterns not abstracted
5. **Error Handling**: Inconsistent across connectors
6. **Configuration**: API keys scattered in __init__ methods
7. **Testing**: Hard to test individual connectors in isolation

### Proposed Module Structure

```
src/connectors/
├── __init__.py
├── base/
│   ├── __init__.py
│   ├── connector.py               # 80 lines - Base connector
│   │   └── BaseAPIConnector
│   │       ├── __init__()
│   │       ├── _make_request()
│   │       ├── _handle_rate_limit()
│   │       └── _handle_errors()
│   ├── rate_limiter.py            # 40 lines - Rate limiting
│   │   └── RateLimiter (shared utility)
│   └── utils.py                   # 30 lines - Utilities
│       ├── safe_float()
│       └── safe_parse_date()
├── sec_edgar.py                   # 80 lines - SEC connector
│   └── SECEdgarConnector(BaseAPIConnector)
├── yahoo_finance.py               # 90 lines - Yahoo Finance
│   └── YahooFinanceConnector(BaseAPIConnector)
├── alpha_vantage.py               # 110 lines - Alpha Vantage
│   └── AlphaVantageConnector(BaseAPIConnector)
├── news_api.py                    # 100 lines - News API
│   └── NewsAPIConnector(BaseAPIConnector)
│       └── _analyze_sentiment()
├── crunchbase.py                  # 60 lines - Crunchbase
│   └── CrunchbaseConnector(BaseAPIConnector)
├── github.py                      # 70 lines - GitHub
│   └── GitHubConnector(BaseAPIConnector)
└── aggregator.py                  # 120 lines - Data aggregation
    └── DataAggregator
        ├── get_comprehensive_company_data()
        ├── _calculate_composite_score()
        └── _merge_data_sources()
```

### Benefits

- **Modularity**: Each connector in separate file
- **Reusability**: BaseAPIConnector provides common patterns
- **Maintainability**: Easy to update individual connectors
- **Testing**: Mock each connector independently
- **Extensibility**: Add new connectors by extending base class
- **Configuration**: Centralized in BaseAPIConnector

### Migration Steps

1. **Phase 1: Create Base Infrastructure** (1 hour)
   - Create `base/connector.py`
   - Implement BaseAPIConnector
   - Move RateLimiter to `base/rate_limiter.py`
   - Create `base/utils.py`

2. **Phase 2: Extract Individual Connectors** (2 hours)
   - Create each connector file
   - Inherit from BaseAPIConnector
   - Update error handling
   - Test each connector

3. **Phase 3: Extract Aggregator** (30 min)
   - Create `aggregator.py`
   - Update imports
   - Test aggregation logic

4. **Phase 4: Update Imports** (30 min)
   - Update all connector usage
   - Run integration tests

### Import Changes Required

**Before:**
```python
from src.connectors.data_sources import (
    SECEdgarConnector,
    YahooFinanceConnector,
    DataAggregator
)
```

**After:**
```python
from src.connectors.sec_edgar import SECEdgarConnector
from src.connectors.yahoo_finance import YahooFinanceConnector
from src.connectors.aggregator import DataAggregator
```

---

## 7. Dashboard Callbacks (569 lines)
**File:** `src/visualization/callbacks.py`
**Current Complexity:** Medium
**Refactoring Priority:** Low-Medium

### Current Structure Analysis

```
callbacks.py (569 lines)
├── register_callbacks() (537 lines)
│   ├── toggle_auto_refresh (12 lines)
│   ├── update_data (96 lines) - Main data fetching
│   ├── update_kpis (88 lines) - KPI card generation
│   ├── update_revenue_chart (32 lines)
│   ├── update_margin_chart (32 lines)
│   ├── update_treemap_chart (32 lines)
│   ├── update_earnings_chart (32 lines)
│   └── update_performance_table (125 lines)
└── Imports (32 lines)
```

### Issues Identified

1. **God Function**: `register_callbacks()` contains all callback definitions (537 lines)
2. **Code Duplication**: Chart update callbacks nearly identical (4x ~32 lines)
3. **Data Transformation**: DataFrame manipulation scattered across callbacks
4. **Error Handling**: Repeated try/except patterns
5. **SQL Queries**: Embedded in callbacks (should be in service layer)
6. **Testing**: Callbacks hard to test in isolation

### Proposed Module Structure

```
src/visualization/dash/
├── __init__.py
├── callbacks/
│   ├── __init__.py
│   ├── data.py                    # 120 lines - Data callbacks
│   │   ├── register_data_callbacks()
│   │   ├── update_data()
│   │   └── toggle_auto_refresh()
│   ├── kpis.py                    # 100 lines - KPI callbacks
│   │   ├── register_kpi_callbacks()
│   │   └── update_kpis()
│   ├── charts.py                  # 120 lines - Chart callbacks
│   │   ├── register_chart_callbacks()
│   │   ├── update_revenue_chart()
│   │   ├── update_margin_chart()
│   │   ├── update_treemap_chart()
│   │   └── update_earnings_chart()
│   ├── tables.py                  # 130 lines - Table callbacks
│   │   ├── register_table_callbacks()
│   │   └── update_performance_table()
│   └── registry.py                # 40 lines - Callback registration
│       └── register_all_callbacks()
├── formatters.py                  # 60 lines - Data formatting
│   ├── format_currency()
│   ├── format_percentage()
│   └── prepare_table_data()
└── helpers.py                     # 50 lines - Helper functions
    ├── create_empty_figure()
    ├── create_data_alert()
    └── calculate_time_ago()
```

### Benefits

- **Logical Grouping**: Callbacks grouped by functionality
- **DRY Code**: Common patterns extracted to helpers
- **Testability**: Individual callback groups testable
- **Maintainability**: Small, focused files
- **Extensibility**: Easy to add new callbacks

### Migration Steps

1. **Phase 1: Create Infrastructure** (30 min)
   - Create `callbacks/` package
   - Create `formatters.py` and `helpers.py`

2. **Phase 2: Extract Data Callbacks** (30 min)
   - Create `callbacks/data.py`
   - Move data fetching callbacks

3. **Phase 3: Extract KPI Callbacks** (20 min)
   - Create `callbacks/kpis.py`
   - Move KPI update logic

4. **Phase 4: Extract Chart Callbacks** (30 min)
   - Create `callbacks/charts.py`
   - Consolidate chart updates

5. **Phase 5: Extract Table Callbacks** (25 min)
   - Create `callbacks/tables.py`
   - Move table logic

6. **Phase 6: Create Registry** (15 min)
   - Create `callbacks/registry.py`
   - Implement register_all_callbacks()

7. **Phase 7: Update Main App** (20 min)
   - Update dashboard app imports
   - Test all callbacks work

### Import Changes Required

**Before:**
```python
from src.visualization.callbacks import register_callbacks

register_callbacks(app, engine)
```

**After:**
```python
from src.visualization.dash.callbacks import register_all_callbacks

register_all_callbacks(app, engine)
```

---

## Cross-File Dependencies & Shared Utilities

### Identified Shared Code

1. **RateLimiter** (duplicated 3x)
   - `sec_ingestion.py` (16 lines)
   - `data_sources.py` (16 lines)
   - `yahoo_finance_ingestion.py` (implicit in client usage)

   **Action:** Extract to `src/core/rate_limiter.py`

2. **safe_float()** utility
   - `data_sources.py` (7 lines)
   - Needed in multiple connectors

   **Action:** Extract to `src/connectors/base/utils.py`

3. **Circuit Breaker Integration**
   - Used in `sec_ingestion.py`, `data_sources.py`, `yahoo_finance_ingestion.py`
   - Patterns vary slightly

   **Action:** Standardize in `src/core/circuit_breaker.py` (already exists)

4. **Cache Management**
   - `dashboard_service.py` has manual cache logic
   - `data_sources.py` uses `@cache_key_wrapper`

   **Action:** Consolidate into `src/core/cache_decorator.py`

5. **Data Formatting Functions**
   - Currency formatting in multiple visualization files
   - Percentage formatting duplicated

   **Action:** Create `src/visualization/formatters.py`

6. **Database Error Handling**
   - Similar patterns across repositories

   **Action:** Create `src/repositories/base/error_handlers.py`

7. **Company Lookup Logic**
   - `sec_ingestion.py::get_or_create_company`
   - Similar in `yahoo_finance_ingestion.py`

   **Action:** Create `src/repositories/company_repository.py` (already exists, consolidate usage)

8. **Progress Notification**
   - Coordination hooks scattered across pipelines

   **Action:** Create `src/pipeline/common/notifications.py`

### Recommended Shared Modules

```
src/core/
├── rate_limiter.py                # Unified rate limiting
├── cache_decorator.py             # Standardized caching
├── formatters.py                  # Common formatting utilities
└── validators.py                  # Data validation utilities

src/connectors/base/
├── connector.py                   # Base API connector
├── rate_limiter.py                # HTTP rate limiting
└── utils.py                       # Connector utilities

src/repositories/base/
├── error_handlers.py              # DB error handling
├── query_builders.py              # SQL query construction
└── validators.py                  # Data validation

src/pipeline/common/
├── notifications.py               # Progress notifications
├── reporters.py                   # Ingestion reporting
└── validators.py                  # Pipeline validation

src/visualization/
├── formatters.py                  # Display formatters
├── constants.py                   # Theme & colors
└── helpers.py                     # Chart utilities
```

---

## Dependency Graph

### Current State (Simplified)

```
┌─────────────────────────┐
│  Dashboard App          │
│  (Callbacks)            │
└─────────┬───────────────┘
          │
          ├─→ VisualizationComponents (all charts)
          │
          ├─→ DashboardService (all queries)
          │       │
          │       ├─→ CompanyRepository
          │       ├─→ MetricsRepository
          │       └─→ Cache Manager
          │
          └─→ Database Engine (raw SQL)

┌─────────────────────────┐
│  Ingestion Pipelines    │
└─────────┬───────────────┘
          │
          ├─→ SECAPIClient
          │       │
          │       └─→ RateLimiter (duplicated)
          │
          ├─→ YahooFinanceClient
          │       │
          │       └─→ RateLimiter (duplicated)
          │
          └─→ DataSourceConnectors
                  │
                  ├─→ RateLimiter (duplicated)
                  └─→ CircuitBreaker
```

### Proposed State (After Refactoring)

```
┌─────────────────────────────────────────────────┐
│  Dashboard App                                  │
└─────────┬───────────────────────────────────────┘
          │
          ├─→ Callbacks/                       (Organized)
          │   ├─→ data.py
          │   ├─→ kpis.py
          │   ├─→ charts.py
          │   └─→ tables.py
          │
          ├─→ Visualization/                   (Categorized)
          │   ├─→ financial.py
          │   ├─→ behavioral.py
          │   ├─→ competitive.py
          │   └─→ formatters.py (shared)
          │
          └─→ Services/                        (Specialized)
              ├─→ CompanyService
              ├─→ MarketService
              ├─→ MetricsService
              └─→ BaseCachedService (shared)

┌─────────────────────────────────────────────────┐
│  Ingestion Pipelines                            │
└─────────┬───────────────────────────────────────┘
          │
          ├─→ SEC Pipeline/                    (Modular)
          │   ├─→ client.py
          │   ├─→ validators.py
          │   ├─→ repository.py
          │   └─→ flows.py
          │
          ├─→ Yahoo Finance Pipeline/          (Modular)
          │   ├─→ client.py
          │   ├─→ processors.py
          │   └─→ repository.py
          │
          └─→ Connectors/                      (Individual)
              ├─→ BaseAPIConnector (shared)
              ├─→ sec_edgar.py
              ├─→ yahoo_finance.py
              └─→ alpha_vantage.py

┌─────────────────────────────────────────────────┐
│  Shared Infrastructure                          │
└─────────────────────────────────────────────────┘
          │
          ├─→ Core/
          │   ├─→ rate_limiter.py      (unified)
          │   ├─→ cache_decorator.py   (standardized)
          │   └─→ circuit_breaker.py   (existing)
          │
          └─→ Repositories/
              ├─→ BaseRepository       (existing)
              └─→ query_builders.py    (new)
```

---

## Migration Strategy

### Phase 1: Foundation (Day 1)
**Priority:** Critical shared infrastructure

1. **Extract Shared Utilities** (2 hours)
   - Create unified `RateLimiter` in `src/core/rate_limiter.py`
   - Create `src/connectors/base/utils.py` with `safe_float()`
   - Create `src/visualization/formatters.py`

2. **Create Base Classes** (2 hours)
   - Create `BaseAPIConnector` in `src/connectors/base/connector.py`
   - Create `BaseCachedService` in `src/services/dashboard/base.py`
   - Create query builder utilities

3. **Testing** (1 hour)
   - Unit tests for utilities
   - Integration tests for base classes

### Phase 2: Data Layer (Day 2)
**Priority:** High - Reduce duplication in data access

1. **Refactor Data Sources** (3 hours)
   - Extract individual connector files
   - Implement inheritance from BaseAPIConnector
   - Test each connector

2. **Refactor Metrics Repository** (2 hours)
   - Split into CRUD and Analytics
   - Extract query builders
   - Test repository operations

### Phase 3: Service Layer (Day 2-3)
**Priority:** High - Improve service organization

1. **Refactor Dashboard Service** (4 hours)
   - Create specialized services
   - Extract query builders
   - Implement BaseCachedService
   - Test service operations

### Phase 4: Pipeline Layer (Day 3-4)
**Priority:** Medium - Improve pipeline maintainability

1. **Refactor SEC Ingestion** (3 hours)
   - Extract models, client, validators, repository
   - Reorganize flows and tasks
   - Test pipeline components

2. **Refactor Yahoo Finance Ingestion** (2 hours)
   - Extract client and processors
   - Move company data to YAML
   - Test pipeline

### Phase 5: Presentation Layer (Day 4-5)
**Priority:** Medium - Improve UI component organization

1. **Refactor Visualization Components** (3 hours)
   - Group by chart type
   - Extract constants and base utilities
   - Test chart generation

2. **Refactor Dashboard Callbacks** (2 hours)
   - Group callbacks by functionality
   - Extract helpers and formatters
   - Test callback logic

### Phase 6: Integration & Testing (Day 5)
**Priority:** Critical - Ensure everything works

1. **Integration Testing** (3 hours)
   - End-to-end pipeline tests
   - Dashboard rendering tests
   - Performance benchmarks

2. **Documentation** (2 hours)
   - Update README
   - Add migration guide
   - Document new structure

---

## Testing Strategy

### Unit Tests

For each new module:
```python
# Example: test_sec_client.py
async def test_get_ticker_to_cik_mapping():
    """Test ticker to CIK mapping retrieval."""
    client = SECAPIClient()
    mapping = await client.get_ticker_to_cik_mapping()

    assert "AAPL" in mapping
    assert len(mapping["AAPL"]) == 10  # CIK is 10 digits

async def test_rate_limiter_respects_limits():
    """Test rate limiter enforces delays."""
    limiter = RateLimiter(calls_per_second=2)

    start = time.time()
    await limiter.acquire()
    await limiter.acquire()
    await limiter.acquire()
    duration = time.time() - start

    assert duration >= 1.0  # 3 calls at 2/sec = at least 1 second
```

### Integration Tests

Test module interactions:
```python
# Example: test_sec_pipeline_integration.py
async def test_full_sec_ingestion_flow():
    """Test complete SEC ingestion pipeline."""
    # Arrange
    pipeline = SECIngestionPipeline(session)
    request = FilingRequest(company_ticker="DUOL")

    # Act
    result = await sec_ingestion_flow(request)

    # Assert
    assert result["filings_stored"] > 0
    assert result["ticker"] == "DUOL"

    # Verify database
    company = await session.execute(
        select(Company).where(Company.ticker == "DUOL")
    )
    assert company is not None
```

### Performance Tests

Benchmark refactored code:
```python
# Example: test_dashboard_service_performance.py
@pytest.mark.benchmark
async def test_company_performance_query_speed():
    """Benchmark company performance query."""
    service = CompanyService(session)

    start = time.time()
    companies = await service.get_company_performance(limit=100)
    duration = time.time() - start

    assert duration < 0.5  # Should complete in <500ms
    assert len(companies) <= 100
```

---

## Risk Mitigation

### Potential Risks

1. **Import Breakage**
   - **Risk:** Changing imports breaks existing code
   - **Mitigation:**
     - Create backward-compatible facades
     - Gradual migration with deprecation warnings
     - Comprehensive import tests

2. **Performance Regression**
   - **Risk:** Refactoring introduces overhead
   - **Mitigation:**
     - Performance benchmarks before/after
     - Profile critical paths
     - Optimize query builders

3. **Data Loss**
   - **Risk:** Database operations modified incorrectly
   - **Mitigation:**
     - Test database operations extensively
     - Use transactions
     - Backup database before deployment

4. **Integration Issues**
   - **Risk:** Modules don't work together
   - **Mitigation:**
     - Integration tests for each phase
     - Gradual rollout
     - Feature flags for new code paths

### Rollback Plan

1. **Version Control**: Tag current state before refactoring
2. **Feature Flags**: Use flags to switch between old/new implementations
3. **Database Migrations**: Reversible migration scripts
4. **Monitoring**: Enhanced logging during migration period

---

## Success Metrics

### Code Quality Metrics

**Before Refactoring:**
- Average file size: 676 lines
- Largest file: 833 lines
- Files >500 lines: 7
- Duplicate code blocks: ~15
- Test coverage: ~60%

**After Refactoring (Targets):**
- Average file size: <200 lines
- Largest file: <300 lines
- Files >500 lines: 0
- Duplicate code blocks: 0
- Test coverage: >85%

### Performance Metrics

- Dashboard load time: <2s (no regression)
- API query time: <500ms (no regression)
- Memory usage: <15% increase acceptable
- Test suite runtime: <5 minutes

### Developer Productivity Metrics

- Time to locate relevant code: 50% reduction
- Time to add new features: 30% reduction
- Code review time: 40% reduction
- Onboarding time: 50% reduction

---

## Conclusion

This comprehensive refactoring plan addresses technical debt accumulated in 7 large files totaling 4,726 lines of code. By splitting these files into 21 focused modules and extracting 8 shared utilities, we achieve:

1. **Improved Maintainability**: Files under 200 lines, single responsibilities
2. **Enhanced Testability**: Small, focused modules easy to test
3. **Better Organization**: Logical grouping by domain and functionality
4. **Reduced Duplication**: Shared utilities eliminate copy-paste code
5. **Increased Productivity**: Developers can navigate and understand code faster

The phased migration approach minimizes risk while delivering incremental value. With proper testing and monitoring, this refactoring will significantly improve the codebase quality and developer experience.

---

## Appendix A: File Size Comparison

| File | Before | After (Total) | Largest Module |
|------|--------|---------------|----------------|
| sec_ingestion.py | 833 | 810 (7 files) | 180 lines |
| components.py | 765 | 730 (7 files) | 180 lines |
| dashboard_service.py | 745 | 750 (9 files) | 180 lines |
| yahoo_finance_ingestion.py | 632 | 640 (6 files) | 150 lines |
| metrics_repository.py | 599 | 610 (5 files) | 200 lines |
| data_sources.py | 583 | 660 (9 files) | 120 lines |
| callbacks.py | 569 | 580 (7 files) | 130 lines |
| **Total** | **4,726** | **4,780 (50 files)** | **200 lines** |

**Note:** Slight increase in total LOC due to:
- Module docstrings and headers
- Explicit imports
- Type hints
- Additional error handling

This is acceptable trade-off for improved organization.

---

## Appendix B: Recommended Reading Order

For developers implementing this refactoring:

1. **Start with:** Section 1 (SEC Ingestion) - Most complex, sets patterns
2. **Then:** Section 8 (Cross-File Dependencies) - Understand shared code
3. **Next:** Section 6 (Data Sources) - Similar patterns to SEC
4. **Follow with:** Section 3 (Dashboard Service) - Service layer patterns
5. **Continue:** Remaining sections in any order

---

**End of Analysis**
