# Dashboard Integration Guide

## Integrating DashboardService with Dash App

This guide shows how to update `src/visualization/dash_app.py` to use the new `DashboardService` for data queries.

## Before & After Comparison

### Before (Current Implementation)

```python
# src/visualization/dash_app.py - OLD
def _fetch_company_performance(self, category: str, period: str) -> pd.DataFrame:
    """Fetch company performance data from database."""
    # In production, this would query mart_company_performance
    # Using sample data structure for demonstration

    sample_data = {
        'ticker': ['CHGG', 'COUR', 'DUOL', 'TWOU', 'ARCE'],
        'company_name': ['Chegg', 'Coursera', 'Duolingo', '2U', 'Arco Platform'],
        ...
    }

    df = pd.DataFrame(sample_data)
    return df
```

### After (With DashboardService)

```python
# src/visualization/dash_app.py - NEW
from src.db.session import get_db
from src.services import DashboardService

async def _fetch_company_performance(self, category: str, period: str) -> pd.DataFrame:
    """Fetch company performance data from database via service layer."""
    async with get_db() as session:
        service = DashboardService(session, cache_ttl=300)

        # Get company performance with category filter
        category_filter = None if category == "all" else category
        companies = await service.get_company_performance(category=category_filter)

        # Convert to DataFrame
        df = pd.DataFrame(companies)
        return df
```

## Step-by-Step Migration

### 1. Add Imports

```python
# At the top of src/visualization/dash_app.py
from src.db.session import get_db
from src.services import DashboardService
```

### 2. Update Callback Methods

Replace the mock data methods with real service calls:

#### Update `update_data` Callback

```python
@self.app.callback(
    [Output("filtered-data", "data"),
     Output("market-data", "data"),
     Output("company-selector", "options")],
    [Input("category-filter", "value"),
     Input("period-filter", "value"),
     Input("interval-component", "n_intervals")]
)
async def update_data(category, period, n_intervals):
    """Fetch and filter data based on selections."""
    async with get_db() as session:
        service = DashboardService(session)

        # Fetch company performance
        category_filter = None if category == "all" else category
        companies = await service.get_company_performance(category=category_filter)

        # Fetch competitive landscape
        landscape = await service.get_competitive_landscape(category=category_filter)

        # Convert to format expected by callbacks
        companies_dict = companies  # Already list of dicts
        market_dict = landscape['segments']  # List of segment dicts

        # Build company selector options
        company_options = [
            {"label": f"{c['ticker']} - {c['company_name']}",
             "value": c['ticker']}
            for c in companies
        ]

        return companies_dict, market_dict, company_options
```

#### Update `update_kpis` Callback

```python
@self.app.callback(
    Output("kpi-cards", "children"),
    [Input("interval-component", "n_intervals")]
)
async def update_kpis(n_intervals):
    """Update KPI cards with market summary."""
    async with get_db() as session:
        service = DashboardService(session)

        # Get market summary
        summary = await service.get_market_summary()

        # Create KPI cards
        kpi_cards = [
            self._create_kpi_card(
                "Total Market Revenue",
                f"${summary['total_market_revenue'] / 1e9:.1f}B",
                "+12.3%"
            ),
            self._create_kpi_card(
                "Avg YoY Growth",
                f"{summary['avg_yoy_growth']:.1f}%",
                "+2.1pp"
            ),
            self._create_kpi_card(
                "Avg Net Revenue Retention",
                f"{summary['avg_nrr']:.0f}%",
                "+5pp"
            ),
            self._create_kpi_card(
                "Total Active Users",
                f"{summary['total_active_users'] / 1e6:.1f}M",
                "+18.5%"
            ),
        ]

        return kpi_cards
```

#### Update `update_competitive_landscape` Callback

```python
@self.app.callback(
    Output("competitive-landscape-chart", "figure"),
    [Input("filtered-data", "data"),
     Input("company-selector", "value")]
)
def update_competitive_landscape(companies_data, selected_companies):
    """Update competitive landscape scatter plot."""
    if not companies_data:
        return go.Figure()

    # Convert to DataFrame
    df = pd.DataFrame(companies_data)

    # Create chart using existing component function
    return create_competitive_landscape_scatter(df, selected_companies)
```

### 3. Remove Mock Data Methods

Delete or comment out these methods:
- `_fetch_company_performance()` (replace with service call)
- `_fetch_market_data()` (replace with service call)

### 4. Handle Async Callbacks

Dash supports async callbacks. Ensure your app is initialized with async support:

```python
class CorporateIntelDashboard:
    def __init__(self):
        self.settings = get_settings()
        self.app = Dash(
            __name__,
            title="Corporate Intelligence Platform",
            update_title="Loading...",
            suppress_callback_exceptions=True,
        )
        # Async callbacks work automatically in modern Dash
        self._setup_layout()
        self._register_callbacks()
```

### 5. Add Error Handling

Wrap service calls in try-except blocks:

```python
@self.app.callback(
    Output("filtered-data", "data"),
    Input("category-filter", "value")
)
async def update_data(category):
    """Fetch data with error handling."""
    try:
        async with get_db() as session:
            service = DashboardService(session)
            companies = await service.get_company_performance(category=category)
            return companies
    except Exception as e:
        logger.error(f"Error fetching company data: {e}")
        return []  # Return empty list on error
```

## Complete Updated Callback Example

Here's a complete example of a modernized callback:

```python
@self.app.callback(
    [Output("competitive-landscape-chart", "figure"),
     Output("market-share-chart", "figure"),
     Output("performance-table", "children"),
     Output("kpi-cards", "children")],
    [Input("category-filter", "value"),
     Input("company-selector", "value"),
     Input("interval-component", "n_intervals")]
)
async def update_dashboard(category, selected_companies, n_intervals):
    """Update entire dashboard with fresh data."""
    try:
        async with get_db() as session:
            service = DashboardService(session)

            # Fetch all data in parallel
            category_filter = None if category == "all" else category

            # Get company performance
            companies = await service.get_company_performance(category=category_filter)

            # Get competitive landscape
            landscape = await service.get_competitive_landscape(category=category_filter)

            # Get market summary for KPIs
            summary = await service.get_market_summary()

            # Convert to DataFrames for charts
            companies_df = pd.DataFrame(companies)

            # Create visualizations
            landscape_chart = create_competitive_landscape_scatter(
                companies_df, selected_companies
            )
            market_share_chart = create_market_share_sunburst(
                pd.DataFrame(landscape['segments']), category
            )

            # Create performance table
            table = self._create_performance_table(companies_df, selected_companies)

            # Create KPI cards
            kpi_cards = [
                self._create_kpi_card(
                    "Total Market Revenue",
                    f"${summary['total_market_revenue'] / 1e9:.1f}B",
                    "+12.3%"
                ),
                self._create_kpi_card(
                    "Avg YoY Growth",
                    f"{summary['avg_yoy_growth']:.1f}%",
                    "+2.1pp"
                ),
                self._create_kpi_card(
                    "Avg NRR",
                    f"{summary['avg_nrr']:.0f}%",
                    "+5pp"
                ),
                self._create_kpi_card(
                    "Total Users",
                    f"{summary['total_active_users'] / 1e6:.1f}M",
                    "+18.5%"
                ),
            ]

            return landscape_chart, market_share_chart, table, kpi_cards

    except Exception as e:
        logger.error(f"Dashboard update error: {e}")
        # Return empty/default components on error
        return go.Figure(), go.Figure(), html.Div("Error loading data"), []
```

## Testing the Integration

### 1. Unit Test the Updated Callbacks

```python
# tests/visualization/test_dash_callbacks.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_update_data_callback():
    """Test update_data callback with mocked service."""
    with patch('src.visualization.dash_app.get_db') as mock_db:
        # Mock the service
        mock_service = AsyncMock()
        mock_service.get_company_performance.return_value = [
            {"ticker": "DUOL", "company_name": "Duolingo", ...}
        ]
        mock_service.get_competitive_landscape.return_value = {
            "segments": [...]
        }

        # Test callback
        # ... test logic ...
```

### 2. Integration Test with Real Database

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_dashboard_with_real_db():
    """Test dashboard with real database connection."""
    async with get_db() as session:
        service = DashboardService(session)

        # Verify data flows correctly
        companies = await service.get_company_performance()
        assert len(companies) > 0

        landscape = await service.get_competitive_landscape()
        assert len(landscape['segments']) > 0
```

### 3. Manual Testing

```bash
# Start the dashboard
python src/visualization/dash_app.py

# Access at http://localhost:8050
# Verify:
# - Data loads correctly
# - Filters work
# - Charts update
# - No errors in console
```

## Performance Considerations

### 1. Enable Caching

The service layer includes Redis caching by default. Ensure Redis is running:

```bash
docker-compose up redis
```

### 2. Monitor Cache Hit Rates

```python
# Add to dashboard for monitoring
async def get_cache_stats():
    cache = await get_cache()
    info = await cache.info('stats')
    hit_rate = info['keyspace_hits'] / (info['keyspace_hits'] + info['keyspace_misses'])
    return hit_rate
```

### 3. Optimize Callback Frequency

```python
# Adjust auto-refresh interval based on data update frequency
dcc.Interval(
    id="interval-component",
    interval=5*60*1000,  # 5 minutes instead of 1 minute
    n_intervals=0
)
```

### 4. Use Dash Loading States

```python
# Add loading indicators
dcc.Loading(
    id="loading-landscape",
    type="default",
    children=dcc.Graph(id="competitive-landscape-chart")
)
```

## Troubleshooting

### Issue: "mart_company_performance does not exist"

**Solution:** The service falls back to raw tables automatically. Run dbt to create marts:

```bash
cd path/to/dbt
dbt run --select mart_company_performance mart_competitive_landscape
```

### Issue: "Redis connection refused"

**Solution:** The service degrades gracefully without cache. To enable caching:

```bash
docker-compose up -d redis
```

### Issue: "Async callbacks not working"

**Solution:** Ensure you're using Dash 2.0+ which supports async callbacks natively:

```bash
pip install --upgrade dash>=2.0.0
```

## Next Steps

1. **Update Dashboard**: Migrate `dash_app.py` to use `DashboardService`
2. **Create dbt Marts**: Build mart tables for optimal performance
3. **Add Monitoring**: Track cache hit rates and query performance
4. **Extend Service**: Add new methods as dashboard grows

## See Also

- `src/services/dashboard_service.py` - Service implementation
- `src/services/example_usage.py` - Usage examples
- `docs/services/SERVICE_LAYER_GUIDE.md` - Complete service documentation
- `tests/services/test_dashboard_service.py` - Test suite
