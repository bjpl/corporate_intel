# Dashboard Service Layer Guide

## Overview

The `DashboardService` provides a clean, cached interface for querying dbt mart tables and serving data to the dashboard visualizations. It handles database queries, Redis caching, error handling, and data transformations.

## Architecture

```
Dashboard (Dash) → DashboardService → dbt Marts (PostgreSQL)
                         ↓
                    Redis Cache
```

### Key Components

1. **DashboardService** (`src/services/dashboard_service.py`)
   - Main service class with async methods
   - Queries dbt mart tables
   - Implements Redis caching
   - Returns data in dashboard-ready formats

2. **dbt Marts** (created by dbt agent)
   - `mart_company_performance`: Company-level metrics
   - `mart_competitive_landscape`: Segment-level aggregations

3. **Redis Cache**
   - 5-minute default TTL for most queries
   - 1-hour TTL for static data (company details)
   - Automatic cache key generation
   - Graceful degradation on cache failures

## Usage

### Basic Pattern

```python
from src.db.session import get_db
from src.services.dashboard_service import DashboardService

async def my_callback():
    async with get_db() as session:
        service = DashboardService(session, cache_ttl=300)

        # Fetch data
        companies = await service.get_company_performance(category="k12")

        return companies
```

### Available Methods

#### 1. `get_company_performance(category, limit, min_revenue)`

Fetch company performance metrics from `mart_company_performance`.

**Parameters:**
- `category` (str, optional): EdTech category filter (k12, higher_education, etc.)
- `limit` (int, optional): Max companies to return
- `min_revenue` (float, optional): Minimum revenue filter (USD)

**Returns:**
```python
[
    {
        "ticker": "DUOL",
        "company_name": "Duolingo",
        "edtech_category": "direct_to_consumer",
        "latest_revenue": 484200000.0,
        "revenue_yoy_growth": 42.9,
        "latest_nrr": 124,
        "latest_mau": 83100000,
        "latest_arpu": 4.9,
        "latest_ltv_cac_ratio": 4.1,
        "overall_score": 89,
        "data_freshness": "2025-10-06T04:00:00"
    }
]
```

**Example:**
```python
# Get all K-12 companies
k12_companies = await service.get_company_performance(category="k12")

# Get top 10 by revenue
top_10 = await service.get_company_performance(limit=10)

# Get companies with >$500M revenue
large_caps = await service.get_company_performance(min_revenue=500e6)
```

---

#### 2. `get_competitive_landscape(category)`

Fetch market segment data from `mart_competitive_landscape`.

**Parameters:**
- `category` (str, optional): Filter by EdTech category

**Returns:**
```python
{
    "segments": [
        {
            "edtech_category": "k12",
            "total_segment_revenue": 2300000000.0,
            "companies_in_segment": 12,
            "avg_revenue_growth": 15.2,
            "avg_nrr": 108,
            "hhi_index": 1823,
            "top_3_market_share": 45.3,
            "data_freshness": "2025-10-06T04:00:00"
        }
    ],
    "market_summary": {
        "total_market_revenue": 17300000000.0,
        "total_companies": 78,
        "num_segments": 5
    }
}
```

**Example:**
```python
landscape = await service.get_competitive_landscape()
for segment in landscape['segments']:
    print(f"{segment['edtech_category']}: ${segment['total_segment_revenue']/1e9:.1f}B")
```

---

#### 3. `get_company_details(ticker)`

Get comprehensive details for a specific company.

**Parameters:**
- `ticker` (str): Company stock ticker

**Returns:**
```python
{
    "ticker": "DUOL",
    "name": "Duolingo",
    "category": "direct_to_consumer",
    "sector": "Technology",
    "delivery_model": "B2C",
    "founded_year": 2011,
    "headquarters": "Pittsburgh, PA",
    "website": "https://duolingo.com",
    "latest_metrics": {
        "latest_revenue": 484200000.0,
        "revenue_yoy_growth": 42.9,
        ...
    }
}
```

**Example:**
```python
company = await service.get_company_details("DUOL")
if company:
    print(f"{company['name']} - {company['category']}")
```

---

#### 4. `get_quarterly_metrics(ticker, metric_type, quarters)`

Fetch time-series quarterly metrics for trend analysis.

**Parameters:**
- `ticker` (str): Company ticker
- `metric_type` (str): Metric type (revenue, mau, arpu, nrr, etc.)
- `quarters` (int, optional): Number of quarters (default: 8)

**Returns:**
```python
# pandas DataFrame with columns:
#   metric_date, value, unit, period_type, qoq_growth, yoy_growth
```

**Example:**
```python
import plotly.express as px

# Get revenue trend
revenue_df = await service.get_quarterly_metrics("DUOL", "revenue")

# Create trend chart
fig = px.line(revenue_df, x='metric_date', y='value',
              title='Quarterly Revenue Trend')
```

---

#### 5. `get_market_summary()`

Get market-wide KPIs for dashboard cards.

**Returns:**
```python
{
    "total_market_revenue": 17300000000.0,
    "avg_yoy_growth": 18.2,
    "avg_nrr": 107,
    "total_active_users": 220500000,
    "num_companies": 78,
    "data_freshness": "2025-10-06T04:00:00"
}
```

**Example:**
```python
summary = await service.get_market_summary()
print(f"Market Size: ${summary['total_market_revenue']/1e9:.1f}B")
print(f"Avg Growth: {summary['avg_yoy_growth']:.1f}%")
```

---

#### 6. `get_segment_comparison(metrics)`

Get normalized metrics for radar chart comparisons.

**Parameters:**
- `metrics` (list, optional): Metrics to include (default: 5 key metrics)

**Returns:**
```python
{
    "segments": ["k12", "higher_education", "corporate_learning"],
    "metrics": ["avg_revenue_growth", "avg_nrr", "avg_ltv_cac_ratio", ...],
    "values": [
        [15.2, 108, 85, 65, 60],  # k12
        [8.9, 102, 78, 45, 90],   # higher_education
        ...
    ]
}
```

**Example:**
```python
comparison = await service.get_segment_comparison()
# Use with create_segment_comparison_radar()
```

---

#### 7. `get_data_freshness()`

Check data freshness and availability.

**Returns:**
```python
{
    "last_updated": "2025-10-06T04:00:00",
    "companies_count": 78,
    "metrics_count": 1245,
    "coverage_by_category": {
        "k12": 12,
        "higher_education": 18,
        ...
    }
}
```

## Integration with Dash

### Simple Callback

```python
@app.callback(
    Output("company-table", "data"),
    Input("category-filter", "value")
)
async def update_table(category):
    async with get_db() as session:
        service = DashboardService(session)
        companies = await service.get_company_performance(category=category)
        return companies
```

### Multiple Data Sources

```python
@app.callback(
    [Output("table", "data"),
     Output("landscape-chart", "figure")],
    Input("category-filter", "value")
)
async def update_dashboard(category):
    async with get_db() as session:
        service = DashboardService(session)

        # Fetch data in parallel (all async)
        companies = await service.get_company_performance(category=category)
        landscape = await service.get_competitive_landscape(category=category)

        # Transform for Dash
        table_data = companies
        chart_figure = create_landscape_chart(landscape)

        return table_data, chart_figure
```

### With Error Handling

```python
@app.callback(
    Output("data-store", "data"),
    Input("refresh-button", "n_clicks")
)
async def refresh_data(n_clicks):
    try:
        async with get_db() as session:
            service = DashboardService(session)
            companies = await service.get_company_performance()
            return companies
    except Exception as e:
        logger.error(f"Error refreshing data: {e}")
        return []  # Return empty data on error
```

## Caching Strategy

### Cache Keys

Cache keys are automatically generated based on method and parameters:

```
dashboard:company_performance:{category}:{limit}:{min_revenue}
dashboard:competitive_landscape:{category}
dashboard:company_details:{ticker}
dashboard:quarterly_metrics:{ticker}:{metric_type}:{quarters}
dashboard:market_summary
```

### TTL Settings

| Data Type | Default TTL | Reason |
|-----------|-------------|--------|
| Company performance | 5 minutes | Frequently updated |
| Competitive landscape | 5 minutes | Aggregated metrics change |
| Company details | 1 hour | Static info changes rarely |
| Quarterly metrics | 5 minutes | Time-series data |
| Market summary | 5 minutes | High-level KPIs |
| Data freshness | 1 minute | Metadata for monitoring |

### Manual Cache Control

```python
# Override TTL for specific query
await service._set_cached("custom_key", data, ttl=3600)

# Get cached value
cached = await service._get_cached("custom_key")
```

## Error Handling

The service includes multiple layers of error handling:

1. **Cache Failures**: Gracefully degrade to database queries
2. **Missing Tables**: Fallback to raw tables if marts don't exist
3. **Query Errors**: Return empty structures instead of crashing
4. **Logging**: All errors logged with context

```python
# Example: Service handles missing mart table
companies = await service.get_company_performance()
# If mart_company_performance doesn't exist, falls back to raw tables
# Returns empty list on complete failure
```

## Testing

Run the comprehensive test suite:

```bash
pytest tests/services/test_dashboard_service.py -v
```

Test coverage includes:
- All service methods
- Cache hit/miss scenarios
- Error handling and fallbacks
- Data transformations
- Edge cases (empty results, missing data)

## Performance Tips

1. **Use Caching**: Default 5-minute TTL is good for most use cases
2. **Limit Results**: Use `limit` parameter for large datasets
3. **Filter Early**: Apply category/revenue filters at query level
4. **Batch Queries**: Fetch multiple datasets in parallel with async
5. **Monitor Freshness**: Use `get_data_freshness()` for health checks

## dbt Mart Dependencies

The service expects these dbt marts to exist:

### `mart_company_performance`
```sql
Columns:
- ticker (str)
- company_name (str)
- edtech_category (str)
- latest_revenue (float)
- revenue_yoy_growth (float)
- latest_nrr (float)
- latest_mau (float)
- latest_arpu (float)
- latest_ltv_cac_ratio (float)
- overall_score (float)
- data_freshness (timestamp)
```

### `mart_competitive_landscape`
```sql
Columns:
- edtech_category (str)
- total_segment_revenue (float)
- companies_in_segment (int)
- avg_revenue_growth (float)
- avg_nrr (float)
- hhi_index (float)
- top_3_market_share (float)
- data_freshness (timestamp)
```

If these marts don't exist, the service falls back to raw tables with limited metrics.

## See Also

- `src/services/example_usage.py` - Complete usage examples
- `tests/services/test_dashboard_service.py` - Unit tests
- `src/visualization/dash_app.py` - Dashboard implementation
- `src/db/models.py` - Database models
