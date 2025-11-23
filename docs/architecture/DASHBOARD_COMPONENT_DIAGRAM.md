# Dashboard Component Flow Diagram

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER INTERACTION                            │
│  Browser → http://localhost:8050 → Dash Frontend (React-based)      │
└─────────────────────────────────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         DASH APPLICATION LAYER                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  CorporateIntelDashboard.__init__()                          │   │
│  │  - Initialize settings                                        │   │
│  │  - Create SQLAlchemy engine (sync)                           │   │
│  │  - Setup layout (_setup_layout)                              │   │
│  │  - Register callbacks (_register_callbacks)                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         LAYOUT COMPONENTS                            │
│  ┌─────────────────┬─────────────────┬──────────────────────────┐  │
│  │ Header          │ Filters         │ Data Availability Notice │  │
│  │ - Title         │ - Category      │ - Coverage badges        │  │
│  │ - Subtitle      │ - Auto-refresh  │ - Data freshness         │  │
│  └─────────────────┴─────────────────┴──────────────────────────┘  │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                      KPI Cards Row                             │ │
│  │  ┌──────────┬──────────┬──────────┬──────────────────────┐   │ │
│  │  │ Total    │ Avg Gross│ Avg Op   │ Companies with       │   │ │
│  │  │ Revenue  │ Margin   │ Margin   │ Earnings             │   │ │
│  │  └──────────┴──────────┴──────────┴──────────────────────┘   │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                     Chart Row 1                                │ │
│  │  ┌──────────────────────────┬──────────────────────────────┐ │ │
│  │  │ Revenue Comparison       │ Margin Comparison            │ │ │
│  │  │ [Horizontal Bar]         │ [Grouped Bar]                │ │ │
│  │  │ All 23 companies         │ Top 15 by revenue            │ │ │
│  │  └──────────────────────────┴──────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                     Chart Row 2                                │ │
│  │  ┌──────────────────────────┬──────────────────────────────┐ │ │
│  │  │ Market Treemap           │ Earnings Distribution        │ │ │
│  │  │ [Hierarchical View]      │ [Box Plot]                   │ │ │
│  │  │ Category → Companies     │ By category (12 companies)   │ │ │
│  │  └──────────────────────────┴──────────────────────────────┘ │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                   Performance Table                            │ │
│  │  - All companies, sortable, filterable                        │ │
│  │  - Paginated (20 rows/page)                                   │ │
│  │  - Color-coded health status                                  │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         CALLBACK LAYER                               │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Callback 1: toggle_auto_refresh                             │   │
│  │  Input: auto-refresh-toggle.value                            │   │
│  │  Output: interval-component.disabled                         │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Callback 2: update_data (PRIMARY DATA FETCH)                │   │
│  │  Inputs: category-filter, interval-component                 │   │
│  │  Outputs: filtered-data, data-freshness, alert               │   │
│  │  Logic:                                                       │   │
│  │    1. Connect to PostgreSQL                                  │   │
│  │    2. Execute SQL query on mart_company_performance          │   │
│  │    3. Filter by category if selected                         │   │
│  │    4. Query data freshness (last update timestamp)           │   │
│  │    5. Return JSON to dcc.Store components                    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Callback 3: update_kpis                                     │   │
│  │  Input: filtered-data                                        │   │
│  │  Output: kpi-cards.children                                  │   │
│  │  Logic:                                                       │   │
│  │    1. Load DataFrame from filtered-data                      │   │
│  │    2. Calculate: total_revenue, avg_gross_margin,            │   │
│  │       avg_operating_margin, companies_with_earnings          │   │
│  │    3. Return 4 KPI card components                           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Callback 4: update_revenue_chart                            │   │
│  │  Input: filtered-data, data-freshness                        │   │
│  │  Output: revenue-chart.figure, badge-revenue-updated         │   │
│  │  Logic:                                                       │   │
│  │    1. Load DataFrame, rename columns                         │   │
│  │    2. Call create_revenue_comparison_bar(df)                 │   │
│  │    3. Return Plotly figure + timestamp badge                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Callback 5: update_margin_chart                             │   │
│  │  Input: filtered-data, data-freshness                        │   │
│  │  Output: margin-chart.figure, badge-margin-updated           │   │
│  │  Logic:                                                       │   │
│  │    1. Load DataFrame, rename columns                         │   │
│  │    2. Call create_margin_comparison_chart(df, top_n=15)      │   │
│  │    3. Return Plotly figure + timestamp badge                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Callback 6: update_treemap_chart                            │   │
│  │  Input: filtered-data, data-freshness                        │   │
│  │  Output: treemap-chart.figure, badge-treemap-updated         │   │
│  │  Logic:                                                       │   │
│  │    1. Load DataFrame, rename columns                         │   │
│  │    2. Call create_revenue_by_category_treemap(df)            │   │
│  │    3. Return Plotly figure + timestamp badge                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Callback 7: update_earnings_chart                           │   │
│  │  Input: filtered-data, data-freshness                        │   │
│  │  Output: earnings-chart.figure, badge-earnings-updated       │   │
│  │  Logic:                                                       │   │
│  │    1. Load DataFrame, rename columns                         │   │
│  │    2. Call create_earnings_growth_distribution(df)           │   │
│  │    3. Return Plotly figure + timestamp badge                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  Callback 8: update_performance_table                        │   │
│  │  Input: filtered-data                                        │   │
│  │  Output: performance-table.children                          │   │
│  │  Logic:                                                       │   │
│  │    1. Load DataFrame, format numbers                         │   │
│  │    2. Create Dash DataTable with conditional styling         │   │
│  │    3. Return DataTable component                             │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    VISUALIZATION FUNCTIONS LAYER                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  create_revenue_comparison_bar(df: DataFrame) → Figure       │   │
│  │  Source: components.py                                       │   │
│  │  Input columns: ticker, company_name, category, revenue      │   │
│  │  Returns: Horizontal bar chart (Plotly go.Bar)              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  create_margin_comparison_chart(df, top_n) → Figure          │   │
│  │  Source: components.py                                       │   │
│  │  Input columns: ticker, revenue, gross_margin, op_margin     │   │
│  │  Returns: Grouped horizontal bar chart (2 traces)           │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  create_revenue_by_category_treemap(df) → Figure             │   │
│  │  Source: components.py                                       │   │
│  │  Input columns: ticker, category, revenue                    │   │
│  │  Returns: Treemap (go.Treemap)                               │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  create_earnings_growth_distribution(df) → Figure            │   │
│  │  Source: components.py                                       │   │
│  │  Input columns: ticker, category, earnings_growth            │   │
│  │  Returns: Box plot by category (go.Box)                      │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DATABASE LAYER                                │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  PostgreSQL 15 + TimescaleDB + pgvector                      │   │
│  │                                                               │   │
│  │  Schema: public_marts                                        │   │
│  │  ┌────────────────────────────────────────────────────────┐ │   │
│  │  │  Table: mart_company_performance                        │ │   │
│  │  │  Rows: 23 companies                                     │ │   │
│  │  │  Columns:                                                │ │   │
│  │  │    - ticker (PK)                                        │ │   │
│  │  │    - company_name                                       │ │   │
│  │  │    - edtech_category                                    │ │   │
│  │  │    - latest_revenue ✓ 100%                              │ │   │
│  │  │    - latest_gross_margin ✓ 100%                         │ │   │
│  │  │    - latest_operating_margin ✓ 100%                     │ │   │
│  │  │    - latest_profit_margin ✓ 100%                        │ │   │
│  │  │    - earnings_growth ⚠ 52% (12/23)                      │ │   │
│  │  │    - revenue_yoy_growth ✗ 0% (rate limited)             │ │   │
│  │  │    - overall_score ✓ 100% (derived)                     │ │   │
│  │  │    - company_health_status ✓ 100% (derived)             │ │   │
│  │  │    - rankings, scores, metadata                         │ │   │
│  │  └────────────────────────────────────────────────────────┘ │   │
│  │                                                               │   │
│  │  ┌────────────────────────────────────────────────────────┐ │   │
│  │  │  Table: mart_competitive_landscape                     │ │   │
│  │  │  Rows: 12 segments                                      │ │   │
│  │  │  Columns:                                                │ │   │
│  │  │    - edtech_category (PK)                               │ │   │
│  │  │    - companies_in_segment                               │ │   │
│  │  │    - total_segment_revenue                              │ │   │
│  │  │    - avg_gross_margin, avg_operating_margin             │ │   │
│  │  │    - hhi_index (market concentration)                   │ │   │
│  │  │    - market_stage, segment_economics                    │ │   │
│  │  │    - strategic_recommendation                           │ │   │
│  │  └────────────────────────────────────────────────────────┘ │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                                    ▲
┌─────────────────────────────────────────────────────────────────────┐
│                         DATA INGESTION PIPELINE                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  SEC EDGAR API → financial_metrics table                     │   │
│  │  Alpha Vantage API → financial_metrics table                 │   │
│  │  dbt transformations → marts (daily refresh)                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Sequence Diagram

```
User                 Dash App           Callback Layer     Database          Components
 │                       │                    │               │                   │
 │  Load dashboard       │                    │               │                   │
 │──────────────────────>│                    │               │                   │
 │                       │                    │               │                   │
 │                       │  Render layout     │               │                   │
 │                       │<───────────────────│               │                   │
 │                       │                    │               │                   │
 │  Select category      │                    │               │                   │
 │──────────────────────>│                    │               │                   │
 │                       │                    │               │                   │
 │                       │  update_data()     │               │                   │
 │                       │───────────────────>│               │                   │
 │                       │                    │               │                   │
 │                       │                    │  SQL query    │                   │
 │                       │                    │──────────────>│                   │
 │                       │                    │               │                   │
 │                       │                    │  23 rows JSON │                   │
 │                       │                    │<──────────────│                   │
 │                       │                    │               │                   │
 │                       │  Store data        │               │                   │
 │                       │<───────────────────│               │                   │
 │                       │                    │               │                   │
 │                       │  update_kpis()     │               │                   │
 │                       │───────────────────>│               │                   │
 │                       │                    │               │                   │
 │                       │  KPI cards         │               │                   │
 │                       │<───────────────────│               │                   │
 │                       │                    │               │                   │
 │                       │  update_revenue_chart()            │                   │
 │                       │───────────────────>│               │                   │
 │                       │                    │               │                   │
 │                       │                    │  Call visualization function      │
 │                       │                    │──────────────────────────────────>│
 │                       │                    │               │                   │
 │                       │                    │  Plotly Figure                    │
 │                       │                    │<──────────────────────────────────│
 │                       │                    │               │                   │
 │                       │  Revenue chart     │               │                   │
 │                       │<───────────────────│               │                   │
 │                       │                    │               │                   │
 │  [Repeat for margin, treemap, earnings charts]             │                   │
 │                       │                    │               │                   │
 │                       │  update_performance_table()         │                   │
 │                       │───────────────────>│               │                   │
 │                       │                    │               │                   │
 │                       │  DataTable         │               │                   │
 │                       │<───────────────────│               │                   │
 │                       │                    │               │                   │
 │  Render complete UI   │                    │               │                   │
 │<──────────────────────│                    │               │                   │
 │                       │                    │               │                   │
 │  [60 seconds later - auto-refresh if enabled]              │                   │
 │                       │                    │               │                   │
 │  Interval tick        │                    │               │                   │
 │──────────────────────>│                    │               │                   │
 │                       │                    │               │                   │
 │  [Repeat update_data() and all chart callbacks]            │                   │
```

---

## Component Dependencies

### Import Graph

```
dash_app.py
  ├── src.core.config (get_settings)
  ├── src.visualization.components
  │     ├── create_revenue_comparison_bar
  │     ├── create_margin_comparison_chart
  │     ├── create_revenue_by_category_treemap
  │     └── create_earnings_growth_distribution
  ├── dash (Dash, Input, Output, dcc, html)
  ├── dash.dash_table (DataTable)
  ├── dash_bootstrap_components (dbc)
  ├── sqlalchemy (create_engine, text)
  └── pandas (pd)

components.py
  ├── plotly.graph_objects (go)
  ├── numpy (np)
  └── pandas (pd)

config.py
  ├── pydantic_settings (BaseSettings)
  └── pathlib (Path)
```

### File Locations

```
corporate_intel/
├── src/
│   ├── visualization/
│   │   ├── dash_app.py           (Main dashboard class)
│   │   ├── components.py         (Visualization functions)
│   │   └── assets/
│   │       └── style.css         (Custom CSS styling)
│   ├── core/
│   │   └── config.py             (Settings management)
│   └── db/
│       ├── session.py            (Database connection)
│       └── models.py             (SQLAlchemy models)
├── docs/
│   └── architecture/
│       ├── DASHBOARD_ARCHITECTURE_FINAL.md
│       └── DASHBOARD_COMPONENT_DIAGRAM.md (this file)
├── dbt/
│   └── models/
│       └── marts/
│           ├── finance/
│           │   └── mart_company_performance.sql
│           └── intelligence/
│               └── mart_competitive_landscape.sql
└── docker-compose.yml
```

---

## Key Architectural Decisions

### 1. Synchronous Database Access
**Decision**: Use synchronous SQLAlchemy engine for Dash callbacks
**Rationale**: Dash callbacks are synchronous functions; async/await not supported
**Implementation**: `create_engine(sync_database_url)`

### 2. Client-Side Data Caching
**Decision**: Use `dcc.Store` components to cache fetched data
**Rationale**: Reduces database queries; multiple charts use same data
**Implementation**: `dcc.Store(id="filtered-data")` updated by `update_data()` callback

### 3. Materialized Marts
**Decision**: Pre-compute aggregations in dbt marts
**Rationale**: Fast query performance; complex calculations done once
**Implementation**: `mart_company_performance` refreshed daily by dbt

### 4. Error Handling Strategy
**Decision**: Graceful degradation with informative messages
**Rationale**: User trust; transparency about data availability
**Implementation**: Empty figures with annotations when data unavailable

### 5. Removed Features
**Decision**: Remove visualizations requiring unavailable metrics
**Rationale**: No fake data; only show what we can prove with real data
**Removed**: Scatter plots (NRR), waterfalls (revenue breakdown), retention curves (cohorts)

---

## Performance Characteristics

### Query Performance
- **Primary data fetch**: ~50-100ms (23 rows from indexed mart)
- **Chart rendering**: ~20-50ms per chart (client-side Plotly)
- **Total page load**: <1 second

### Scalability Limits
- **Current**: 23 companies, 4 charts → no performance issues
- **Projected**: Up to 500 companies without optimization
- **Bottleneck**: DataTable with >100 rows (use server-side pagination)

### Optimization Opportunities
1. **Redis caching**: Cache query results for 5 minutes
2. **Connection pooling**: Already implemented (pool_size=5)
3. **Lazy loading**: Charts render only when scrolled into view
4. **WebSocket updates**: Push updates instead of polling

---

## Security Considerations

### Current State
- No authentication (development mode)
- Database credentials in environment variables
- All data visible to all users

### Production Requirements
1. JWT authentication middleware
2. Row-level security policies (filter by organization)
3. HTTPS encryption (Nginx reverse proxy)
4. CSRF protection (built into Dash)
5. SQL injection protection (parameterized queries)

---

## Testing Strategy

### Unit Tests
- Test each visualization function with sample data
- Verify correct handling of missing data
- Check color mapping consistency

### Integration Tests
- Test full dashboard load with real database
- Verify callback chains execute correctly
- Check filter interactions

### End-to-End Tests
- Use Selenium/Playwright to test UI interactions
- Verify charts update when category changed
- Test auto-refresh toggle

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Production Deployment                  │
└─────────────────────────────────────────────────────────┘

Internet
   ↓
┌──────────────────────────┐
│  Nginx Reverse Proxy     │ (Port 443, HTTPS)
│  - SSL termination       │
│  - Rate limiting         │
│  - Static file caching   │
└──────────────────────────┘
   ↓
┌──────────────────────────┐
│  Gunicorn (WSGI)         │ (Port 8050)
│  - Workers: 4            │
│  - Threads: 2            │
│  - Timeout: 30s          │
└──────────────────────────┘
   ↓
┌──────────────────────────┐
│  Dash Application        │
│  - CorporateIntelDashboard
│  - Callbacks registered  │
└──────────────────────────┘
   ↓
┌──────────────────────────┐
│  PostgreSQL (Managed)    │
│  - AWS RDS / GCP SQL     │
│  - Read replicas for BI  │
│  - Automated backups     │
└──────────────────────────┘
```

---

**Document Version**: 1.0
**Last Updated**: 2025-10-05
**Author**: System Architecture Designer
