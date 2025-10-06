# EdTech Corporate Intelligence Dashboard Architecture

## Executive Summary

This document defines the production-ready architecture for a clean, data-driven dashboard that displays ONLY the metrics we have complete data for. The design prioritizes transparency, performance, and user trust by clearly showing data availability and avoiding fabricated metrics.

---

## 1. Data Reality Assessment

### 1.1 Available Data Sources

**Mart: `public_marts.mart_company_performance`**
- Coverage: 23 companies
- Columns: 31 fields
- Primary metrics with 100% coverage:
  - `latest_revenue` (23/23) - Financial data from SEC filings
  - `latest_gross_margin` (23/23) - Profitability metric
  - `latest_operating_margin` (23/23) - Operational efficiency
  - `latest_profit_margin` (23/23) - Net profitability

- Secondary metrics with partial coverage:
  - `earnings_growth` (12/23) - 52% coverage, quarterly EPS growth
  - `revenue_yoy_growth` (0/23) - No data yet (Alpha Vantage rate limited)
  - `pe_ratio` (0/23) - No data yet
  - `market_cap` (0/23) - No data yet
  - `eps`, `roe` (0/23) - No data yet

- Derived analytics (100% coverage):
  - `growth_score`, `margin_score`, `profitability_score`
  - `overall_score` (composite performance indicator)
  - `company_health_status` (Excellent/Good/Needs Attention/At Risk)
  - Rankings: `revenue_rank_in_category`, `revenue_rank_overall`, etc.

**Mart: `public_marts.mart_competitive_landscape`**
- Coverage: 12 market segments (by category + delivery model combinations)
- Key metrics:
  - `companies_in_segment`, `total_segment_revenue`
  - `avg_gross_margin`, `avg_operating_margin`, `avg_profit_margin`
  - `hhi_index` (market concentration)
  - `market_stage`, `segment_economics`, `strategic_recommendation`
  - `segment_leaders`, `fastest_growers`, `at_risk_companies`

### 1.2 Metrics NOT Available (Public API Limitations)

The following metrics are NOT available from public SEC filings or free API tiers:
- **User metrics**: MAU, DAU, active users
- **Unit economics**: ARPU, LTV, CAC, LTV/CAC ratio
- **Retention metrics**: NRR, GRR, cohort retention, churn rate
- **Real-time growth**: YoY revenue growth (requires time-series data unavailable in current Alpha Vantage tier)
- **Valuation multiples**: P/E, Forward P/E, EV/Revenue (rate limited)

**Design Decision**: Remove all visualizations dependent on unavailable metrics. Display a clear "Data Availability Notice" explaining what's missing and when it will be available.

---

## 2. Dashboard Layout Specification

### 2.1 Grid Structure (Responsive 12-column Bootstrap)

```
┌────────────────────────────────────────────────────────────┐
│  Header: EdTech Corporate Intelligence Platform            │
│  Subtitle: Public SEC Filing Analysis | 23 Companies       │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  Data Availability Notice (Dismissible Alert)               │
│  ✓ Revenue & Margin Data: 100% (SEC 10-K/10-Q)            │
│  ⚠ Earnings Growth: 52% (12/23 companies)                  │
│  ⏳ Valuation Metrics: Coming tomorrow (API rate limit)    │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  Filters: [Category ▼] [Min Revenue: $___M]                │
└────────────────────────────────────────────────────────────┘

┌──────────────────────┬──────────────────────┬──────────────┐
│  KPI Card 1          │  KPI Card 2          │  KPI Card 3  │
│  Total Market        │  Avg Gross Margin    │  Companies   │
│  Revenue: $X.XB      │  XX.X%               │  Tracked: 23 │
│  ↑ from 23 companies │  ↑ Median: XX.X%     │  12 segments │
└──────────────────────┴──────────────────────┴──────────────┘

┌──────────────────────────────┬───────────────────────────────┐
│  Revenue Comparison          │  Margin Comparison            │
│  [Horizontal Bar Chart]      │  [Grouped Bar: GM vs OM]      │
│  All 23 companies            │  Top 15 by revenue            │
│  Color-coded by category     │  Side-by-side comparison      │
└──────────────────────────────┴───────────────────────────────┘

┌──────────────────────────────┬───────────────────────────────┐
│  Market Treemap              │  Earnings Distribution        │
│  [Hierarchical Revenue]      │  [Box Plot by Category]       │
│  Category → Companies        │  Only 12 companies shown      │
│  Sized by revenue            │  Clear N= label               │
└──────────────────────────────┴───────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  Company Performance Table                                  │
│  [Sortable DataTable with all available metrics]           │
│  Shows: Revenue, Margins, Earnings*, Health Status          │
│  *Asterisk indicates partial data availability              │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│  Footer: Data Sources & Methodology                         │
│  Last Updated: YYYY-MM-DD HH:MM UTC                        │
│  Source: SEC EDGAR API (10-K/10-Q filings)                │
└────────────────────────────────────────────────────────────┘
```

### 2.2 Removed Components (Insufficient Data)

The following visualizations have been **REMOVED** from the original design due to lack of data:
- ❌ Competitive Landscape Scatter (requires NRR + YoY growth)
- ❌ Revenue Waterfall (requires detailed revenue breakdown)
- ❌ Segment Radar Chart (requires NRR, LTV/CAC unavailable)
- ❌ Retention Curves (requires cohort data)
- ❌ Cohort Heatmap (requires retention data)

---

## 3. Visualization Specifications

### 3.1 KPI Cards (Row 1)

**Card 1: Total Market Revenue**
```sql
-- Query
SELECT
    SUM(latest_revenue) / 1e9 AS total_revenue_billions,
    COUNT(*) AS companies_counted
FROM public_marts.mart_company_performance
WHERE latest_revenue IS NOT NULL;

-- Display
{total_revenue_billions:.1f}B
Subtitle: "Across {companies_counted} companies"
```

**Card 2: Average Gross Margin**
```sql
-- Query
SELECT
    AVG(latest_gross_margin) AS avg_gm,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY latest_gross_margin) AS median_gm,
    COUNT(*) AS n
FROM public_marts.mart_company_performance
WHERE latest_gross_margin IS NOT NULL;

-- Display
{avg_gm:.1f}%
Subtitle: "Median: {median_gm:.1f}% (n={n})"
```

**Card 3: Data Coverage**
```sql
-- Query
SELECT
    COUNT(*) AS total_companies,
    COUNT(DISTINCT edtech_category) AS categories,
    COUNT(CASE WHEN earnings_growth IS NOT NULL THEN 1 END) AS with_earnings
FROM public_marts.mart_company_performance;

-- Display
{total_companies} companies
{categories} categories
{with_earnings} with earnings
```

### 3.2 Revenue Comparison Bar Chart

**Specification:**
- Chart Type: Horizontal bar chart
- Data: All 23 companies
- X-axis: Revenue in millions ($M)
- Y-axis: Company ticker symbols
- Color: Category-based (using CATEGORY_COLORS palette)
- Sorting: Descending by revenue
- Interactivity: Hover shows company name + exact revenue

**SQL Query:**
```sql
SELECT
    ticker,
    company_name,
    edtech_category AS category,
    latest_revenue AS revenue,
    CASE
        WHEN latest_revenue >= 1e9 THEN 'Large (>$1B)'
        WHEN latest_revenue >= 500e6 THEN 'Medium ($500M-$1B)'
        ELSE 'Small (<$500M)'
    END AS size_category
FROM public_marts.mart_company_performance
WHERE latest_revenue IS NOT NULL
ORDER BY latest_revenue DESC;
```

**Plotly Implementation:**
```python
def create_revenue_comparison_bar(companies_df: pd.DataFrame) -> go.Figure:
    """Create horizontal bar chart of all companies by revenue."""
    df = companies_df.sort_values('revenue', ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df['ticker'],
        x=df['revenue'] / 1e6,  # Convert to millions
        orientation='h',
        marker=dict(
            color=df['category'].map(CATEGORY_COLORS),
            line=dict(color='white', width=1)
        ),
        text=[f"${r/1e6:.1f}M" for r in df['revenue']],
        textposition='outside',
        hovertemplate=(
            "<b>%{y}</b><br>" +
            "Company: %{customdata[0]}<br>" +
            "Revenue: $%{x:.1f}M<br>" +
            "Category: %{customdata[1]}<br>" +
            "<extra></extra>"
        ),
        customdata=df[['company_name', 'category']].values
    ))

    fig.update_layout(
        title="Revenue Comparison - All EdTech Companies",
        xaxis_title="Revenue ($M)",
        yaxis_title="",
        height=max(400, len(df) * 25),
        margin=dict(l=80, r=120, t=60, b=40),
        xaxis=dict(tickformat="$,.0f", ticksuffix="M")
    )

    return fig
```

### 3.3 Margin Comparison Chart

**Specification:**
- Chart Type: Grouped horizontal bar chart
- Data: Top 15 companies by revenue
- Metrics: Gross Margin vs Operating Margin
- Colors: Primary blue (GM), Success green (OM)
- Sorting: By revenue (descending)

**SQL Query:**
```sql
SELECT
    ticker,
    company_name,
    latest_revenue,
    latest_gross_margin AS gross_margin,
    latest_operating_margin AS operating_margin
FROM public_marts.mart_company_performance
WHERE latest_revenue IS NOT NULL
  AND latest_gross_margin IS NOT NULL
  AND latest_operating_margin IS NOT NULL
ORDER BY latest_revenue DESC
LIMIT 15;
```

**Plotly Implementation:**
```python
def create_margin_comparison_chart(companies_df: pd.DataFrame, top_n: int = 15) -> go.Figure:
    """Create grouped bar chart comparing gross and operating margins."""
    df = companies_df.nlargest(top_n, 'revenue').sort_values('revenue', ascending=True)

    fig = go.Figure()

    # Gross Margin
    fig.add_trace(go.Bar(
        name='Gross Margin',
        y=df['ticker'],
        x=df['gross_margin'],
        orientation='h',
        marker=dict(color=COLORS['primary']),
        text=[f"{v:.1f}%" if pd.notna(v) else "N/A" for v in df['gross_margin']],
        textposition='outside'
    ))

    # Operating Margin
    fig.add_trace(go.Bar(
        name='Operating Margin',
        y=df['ticker'],
        x=df['operating_margin'],
        orientation='h',
        marker=dict(color=COLORS['success']),
        text=[f"{v:.1f}%" if pd.notna(v) else "N/A" for v in df['operating_margin']],
        textposition='outside'
    ))

    fig.update_layout(
        title=f"Margin Comparison - Top {top_n} Companies by Revenue",
        xaxis_title="Margin (%)",
        barmode='group',
        height=max(400, top_n * 30),
        xaxis=dict(tickformat=".0f", ticksuffix="%")
    )

    return fig
```

### 3.4 Market Treemap

**Specification:**
- Chart Type: Treemap (2-level hierarchy)
- Structure: Root → Category → Companies
- Size: Proportional to revenue
- Color: Category-based palette
- Labels: Company ticker + revenue

**SQL Query:**
```sql
SELECT
    ticker,
    company_name,
    edtech_category AS category,
    latest_revenue AS revenue
FROM public_marts.mart_company_performance
WHERE latest_revenue IS NOT NULL
  AND latest_revenue > 0
ORDER BY edtech_category, latest_revenue DESC;
```

**Plotly Implementation:**
```python
def create_revenue_by_category_treemap(companies_df: pd.DataFrame) -> go.Figure:
    """Create treemap showing revenue distribution by category."""
    labels = ["EdTech Market"]
    parents = [""]
    values = [0]
    colors = [COLORS['primary']]

    # Add categories
    for category in companies_df['category'].unique():
        df_cat = companies_df[companies_df['category'] == category]
        cat_revenue = df_cat['revenue'].sum()

        labels.append(category.replace('_', ' ').title())
        parents.append("EdTech Market")
        values.append(cat_revenue)
        colors.append(CATEGORY_COLORS.get(category, COLORS['info']))

        # Add companies
        for _, row in df_cat.iterrows():
            if pd.notna(row['revenue']) and row['revenue'] > 0:
                labels.append(row['ticker'])
                parents.append(category.replace('_', ' ').title())
                values.append(row['revenue'])
                colors.append(CATEGORY_COLORS.get(category, COLORS['info']))

    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textinfo="label+value",
        texttemplate="<b>%{label}</b><br>$%{value:,.0f}",
        hovertemplate="<b>%{label}</b><br>Revenue: $%{value:,.0f}<br><extra></extra>"
    ))

    fig.update_layout(
        title="Revenue Distribution - Market Treemap",
        height=500,
        margin=dict(t=60, b=0, l=0, r=0)
    )

    return fig
```

### 3.5 Earnings Growth Distribution

**Specification:**
- Chart Type: Box plot by category
- Data: ONLY 12 companies with earnings_growth data
- Y-axis: Earnings growth (%)
- X-axis: EdTech categories
- Points: Show all individual companies
- Title: Clearly state "N=12 companies with data"

**SQL Query:**
```sql
SELECT
    ticker,
    company_name,
    edtech_category AS category,
    earnings_growth
FROM public_marts.mart_company_performance
WHERE earnings_growth IS NOT NULL
ORDER BY edtech_category, earnings_growth DESC;
```

**Plotly Implementation:**
```python
def create_earnings_growth_distribution(companies_df: pd.DataFrame) -> go.Figure:
    """Create box plot showing earnings growth distribution by category."""
    df = companies_df[companies_df['earnings_growth'].notna()].copy()

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No earnings growth data available yet",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="gray")
        )
        return fig

    fig = go.Figure()

    for category in df['category'].unique():
        df_cat = df[df['category'] == category]

        fig.add_trace(go.Box(
            y=df_cat['earnings_growth'],
            name=category.replace('_', ' ').title(),
            marker=dict(color=CATEGORY_COLORS.get(category, COLORS['info'])),
            boxpoints='all',
            jitter=0.3,
            pointpos=-1.8,
            text=df_cat['ticker'],
            hovertemplate=(
                "<b>%{text}</b><br>" +
                "Earnings Growth: %{y:.1f}%<br>" +
                "<extra></extra>"
            )
        ))

    fig.update_layout(
        title=f"Earnings Growth Distribution by Category (n={len(df)} companies with data)",
        yaxis_title="Earnings Growth (%)",
        xaxis_title="Category",
        height=500,
        showlegend=False,
        yaxis=dict(
            tickformat=".0f",
            ticksuffix="%",
            zeroline=True,
            zerolinecolor='gray'
        )
    )

    return fig
```

### 3.6 Performance Data Table

**Specification:**
- Component: Dash DataTable
- Data: All 23 companies
- Columns: Ticker, Name, Category, Revenue, GM, OM, Earnings*, Health Status, Score
- Features: Sortable, filterable, paginated (10 rows/page)
- Styling: Conditional formatting for health status
- Note: Asterisk (*) on Earnings column header to indicate partial data

**SQL Query:**
```sql
SELECT
    ticker,
    company_name,
    edtech_category,
    latest_revenue,
    latest_gross_margin,
    latest_operating_margin,
    earnings_growth,
    overall_score,
    company_health_status,
    CASE
        WHEN earnings_growth IS NOT NULL THEN 'Yes'
        ELSE 'No'
    END AS has_earnings_data
FROM public_marts.mart_company_performance
ORDER BY overall_score DESC, latest_revenue DESC;
```

**Dash Implementation:**
```python
def create_performance_table(companies_df: pd.DataFrame) -> DataTable:
    """Create comprehensive performance data table."""
    df = companies_df.copy()

    # Format columns
    df['Revenue'] = df['latest_revenue'].apply(
        lambda x: f"${x/1e6:.1f}M" if pd.notna(x) else "-"
    )
    df['Gross Margin'] = df['latest_gross_margin'].apply(
        lambda x: f"{x:.1f}%" if pd.notna(x) else "-"
    )
    df['Operating Margin'] = df['latest_operating_margin'].apply(
        lambda x: f"{x:.1f}%" if pd.notna(x) else "-"
    )
    df['Earnings Growth*'] = df['earnings_growth'].apply(
        lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A"
    )
    df['Score'] = df['overall_score'].apply(
        lambda x: f"{x:.0f}" if pd.notna(x) else "-"
    )

    display_cols = [
        'ticker', 'company_name', 'edtech_category',
        'Revenue', 'Gross Margin', 'Operating Margin',
        'Earnings Growth*', 'company_health_status', 'Score'
    ]

    return DataTable(
        data=df[display_cols].to_dict('records'),
        columns=[
            {"name": "Ticker", "id": "ticker"},
            {"name": "Company", "id": "company_name"},
            {"name": "Category", "id": "edtech_category"},
            {"name": "Revenue", "id": "Revenue"},
            {"name": "Gross Margin", "id": "Gross Margin"},
            {"name": "Operating Margin", "id": "Operating Margin"},
            {"name": "Earnings Growth*", "id": "Earnings Growth*"},
            {"name": "Health", "id": "company_health_status"},
            {"name": "Score", "id": "Score"}
        ],
        style_data_conditional=[
            {
                'if': {'filter_query': '{company_health_status} = "Excellent"'},
                'backgroundColor': '#d4edda',
                'color': '#155724'
            },
            {
                'if': {'filter_query': '{company_health_status} = "At Risk"'},
                'backgroundColor': '#f8d7da',
                'color': '#721c24'
            }
        ],
        sort_action="native",
        filter_action="native",
        page_size=10,
        page_action="native"
    )
```

---

## 4. Data Flow Architecture

### 4.1 Component Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                   │
│  ┌──────────────────────┐  ┌──────────────────────────┐ │
│  │ mart_company_        │  │ mart_competitive_        │ │
│  │ performance          │  │ landscape                │ │
│  │ (23 rows)            │  │ (12 segments)            │ │
│  └──────────────────────┘  └──────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────┐
│              Dash Callback: update_data()                │
│  - Executes SQL queries via SQLAlchemy                   │
│  - Returns JSON to dcc.Store components                  │
│  - Triggers: category filter, refresh interval           │
└─────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────┐
│                 dcc.Store Components                     │
│  ┌──────────────────┐  ┌──────────────────────────────┐ │
│  │ filtered-data    │  │ market-data                  │ │
│  │ (company metrics)│  │ (segment aggregates)         │ │
│  └──────────────────┘  └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────┐
│            Individual Chart Callbacks                    │
│  ┌─────────────┬─────────────┬─────────────────────┐   │
│  │ KPI Cards   │ Revenue Bar │ Margin Comparison   │   │
│  ├─────────────┼─────────────┼─────────────────────┤   │
│  │ Treemap     │ Earnings Box│ Performance Table   │   │
│  └─────────────┴─────────────┴─────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 4.2 SQL Query Map

| Visualization            | Mart Table                  | Filter Support | Update Frequency |
|--------------------------|-----------------------------|----------------|------------------|
| KPI Cards                | mart_company_performance    | Category       | 60s              |
| Revenue Bar              | mart_company_performance    | Category       | 60s              |
| Margin Comparison        | mart_company_performance    | Category       | 60s              |
| Market Treemap           | mart_company_performance    | None           | 60s              |
| Earnings Distribution    | mart_company_performance    | None           | 60s              |
| Performance Table        | mart_company_performance    | Category       | 60s              |

### 4.3 Callback Dependencies

```python
# Primary data fetch callback
@app.callback(
    [Output("filtered-data", "data"),
     Output("market-data", "data"),
     Output("data-freshness", "data")],
    [Input("category-filter", "value"),
     Input("interval-component", "n_intervals")]
)
def update_data(category, n_intervals):
    """Fetch data from database every 60 seconds."""
    # Execute SQL queries
    # Return JSON data to Store components

# KPI callback (depends on filtered-data)
@app.callback(
    Output("kpi-cards", "children"),
    [Input("filtered-data", "data")]
)
def update_kpis(companies_data):
    """Calculate and display KPI metrics."""
    # Aggregate metrics from companies_data
    # Return KPI card components

# Revenue chart callback (depends on filtered-data)
@app.callback(
    Output("revenue-chart", "figure"),
    [Input("filtered-data", "data")]
)
def update_revenue_chart(companies_data):
    """Create revenue comparison bar chart."""
    df = pd.DataFrame(companies_data)
    return create_revenue_comparison_bar(df)

# Similar pattern for other visualizations...
```

---

## 5. Error Handling & Data Quality

### 5.1 Graceful Degradation Strategy

**Scenario 1: No data available**
```python
if not companies_data:
    return dbc.Alert([
        html.I(className="fas fa-exclamation-triangle me-2"),
        "No data available. Please run data ingestion first.",
        html.Br(),
        html.Small("Command: docker-compose exec web python -m src.pipelines.ingestion")
    ], color="warning")
```

**Scenario 2: Partial data (e.g., only 12 companies have earnings_growth)**
```python
df = companies_df[companies_df['earnings_growth'].notna()]
if df.empty:
    # Show placeholder with explanation
    fig.add_annotation(
        text=f"Earnings data pending for {len(companies_df)} companies<br>"
             "Expected availability: Tomorrow (API rate limit)",
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, color="gray")
    )
else:
    # Show chart with clear N= label
    title = f"Earnings Growth Distribution (n={len(df)}/{len(companies_df)} companies)"
```

**Scenario 3: Database connection failure**
```python
try:
    with engine.connect() as conn:
        result = conn.execute(query)
        data = [dict(row._mapping) for row in result]
except SQLAlchemyError as e:
    logger.error(f"Database error: {e}")
    return sample_data, {}, {}, [], warning_alert, True
```

### 5.2 Data Completeness Indicators

**Visual Indicators:**
1. Badge on each chart showing data coverage
   ```python
   dbc.Badge(f"Data: {coverage_pct:.0f}% ({n_with_data}/{n_total})",
             color="success" if coverage_pct > 90 else "warning")
   ```

2. Table column headers with asterisks
   ```python
   {"name": "Earnings Growth*", "id": "earnings_growth"}
   # Footer note: "* Partial data availability (52%)"
   ```

3. Hover tooltips explaining data gaps
   ```python
   html.I(className="fas fa-info-circle",
          title="12 of 23 companies have earnings data. "
                "Remaining data will be available after API rate limit resets.")
   ```

### 5.3 Data Freshness Banner

```python
def create_freshness_banner(last_updated: datetime, companies_count: int) -> dbc.Alert:
    """Create data freshness notification banner."""
    time_ago = datetime.utcnow() - last_updated

    if time_ago < timedelta(hours=1):
        color = "success"
        icon = "fas fa-check-circle"
        message = f"Data updated {int(time_ago.total_seconds() / 60)} minutes ago"
    elif time_ago < timedelta(hours=24):
        color = "info"
        icon = "fas fa-clock"
        message = f"Data updated {int(time_ago.total_seconds() / 3600)} hours ago"
    else:
        color = "warning"
        icon = "fas fa-exclamation-triangle"
        message = "Data may be stale. Run ingestion pipeline."

    return dbc.Alert([
        html.I(className=f"{icon} me-2"),
        message,
        html.Span(f" | {companies_count} companies tracked", className="ms-3")
    ], color=color, dismissable=True)
```

---

## 6. Performance Optimization

### 6.1 Query Optimization

**Use Materialized Views:**
```sql
-- Marts are already materialized tables (dbt config)
-- Refresh strategy: Daily via dbt run
-- Indexes: ticker (unique), edtech_category
```

**Connection Pooling:**
```python
# In config.py
engine = create_engine(
    sync_database_url,
    pool_pre_ping=True,        # Verify connections before use
    pool_size=5,                # Max concurrent connections
    max_overflow=10,            # Extra connections under load
    pool_recycle=3600          # Recycle connections hourly
)
```

### 6.2 Caching Strategy

**Client-Side Caching (dcc.Store):**
```python
dcc.Store(id="filtered-data", storage_type="memory")
# Stores data in browser memory
# Reduces database queries for derived visualizations
```

**Server-Side Caching (Redis):**
```python
# Future enhancement - cache query results for 5 minutes
@cache.memoize(timeout=300)
def fetch_company_metrics(category: str) -> List[Dict]:
    with engine.connect() as conn:
        result = conn.execute(query, {"category": category})
        return [dict(row._mapping) for row in result]
```

### 6.3 Rendering Performance

**Lazy Loading:**
```python
dcc.Loading(
    id="loading-revenue-chart",
    type="default",  # Spinner animation
    children=[dcc.Graph(id="revenue-chart")]
)
```

**Data Sampling for Large Datasets:**
```python
# Not needed yet (only 23 companies)
# Future: If >100 companies, sample top/bottom/random for scatter plots
if len(df) > 100:
    df_display = pd.concat([
        df.nlargest(50, 'revenue'),
        df.nsmallest(25, 'revenue'),
        df.sample(25)
    ]).drop_duplicates()
```

---

## 7. Migration Plan

### 7.1 Current State Analysis

**Broken Components in dash_app.py:**
1. Lines 488-502: Query references `latest_nrr`, `latest_mau`, `latest_arpu` (NOT in schema)
2. Lines 518-520: Query references `avg_nrr`, `avg_ltv_cac_ratio` (NOT in mart_competitive_landscape)
3. Lines 626-629: KPI cards calculate metrics from non-existent columns
4. Lines 736-756: `create_competitive_landscape_scatter()` requires NRR + YoY growth (unavailable)
5. Lines 799-828: Waterfall chart requires revenue breakdown (unavailable)
6. Lines 834-852: Radar chart requires NRR, LTV/CAC (unavailable)
7. Lines 854-877: Retention curves require cohort data (unavailable)
8. Lines 879-914: Cohort heatmap requires retention data (unavailable)

**Broken Components in components.py:**
1. Lines 219-318: `create_competitive_landscape_scatter()` references unavailable metrics
2. Lines 321-384: `create_segment_comparison_radar()` references unavailable metrics
3. Lines 707-765: `create_retention_curves()` generates mock data (no real data)
4. Lines 143-216: `create_cohort_heatmap()` generates mock data (no real data)

### 7.2 Migration Steps

**Step 1: Update dash_app.py SQL queries**
```python
# OLD (broken)
company_query = text("""
    SELECT ticker, company_name, edtech_category,
           latest_revenue, revenue_yoy_growth, latest_nrr,
           latest_mau, latest_arpu, latest_ltv_cac_ratio,
           overall_score
    FROM public_marts.mart_company_performance
""")

# NEW (working)
company_query = text("""
    SELECT ticker, company_name, edtech_category, delivery_model,
           latest_revenue, latest_gross_margin, latest_operating_margin,
           latest_profit_margin, earnings_growth, overall_score,
           company_health_status, revenue_rank_in_category,
           revenue_rank_overall
    FROM public_marts.mart_company_performance
    WHERE (:category IS NULL OR edtech_category = :category)
    ORDER BY latest_revenue DESC NULLS LAST
""")
```

**Step 2: Update components.py - Remove unavailable visualizations**
```python
# Remove these functions entirely:
# - create_competitive_landscape_scatter()
# - create_segment_comparison_radar()
# - create_retention_curves()
# - create_cohort_heatmap()
# - create_metrics_waterfall()

# Keep and enhance:
# - create_revenue_comparison_bar() ✓
# - create_margin_comparison_chart() ✓
# - create_revenue_by_category_treemap() ✓
# - create_earnings_growth_distribution() ✓
```

**Step 3: Update layout in dash_app.py**
```python
# Remove these card sections:
# - Competitive Landscape card (uses scatter plot)
# - Waterfall Analysis card
# - Radar Chart card
# - Retention Curves card
# - Cohort Heatmap card

# Keep these cards:
# - KPI summary cards ✓
# - Revenue comparison ✓
# - Margin comparison ✓
# - Market treemap ✓
# - Earnings distribution ✓
# - Performance table ✓
```

**Step 4: Update callbacks**
```python
# Remove callbacks for deleted visualizations:
# - update_competitive_landscape()
# - update_waterfall()
# - update_radar_chart()
# - update_retention_curves()
# - update_cohort_heatmap()
# - update_market_share() (uses sunburst, replaced with treemap)

# Update callbacks for working visualizations:
@app.callback(
    Output("revenue-chart", "figure"),
    [Input("filtered-data", "data")]
)
def update_revenue_chart(companies_data):
    if not companies_data:
        return create_empty_figure("No data available")
    df = pd.DataFrame(companies_data)
    return create_revenue_comparison_bar(df)

@app.callback(
    Output("margin-chart", "figure"),
    [Input("filtered-data", "data")]
)
def update_margin_chart(companies_data):
    if not companies_data:
        return create_empty_figure("No data available")
    df = pd.DataFrame(companies_data)
    return create_margin_comparison_chart(df, top_n=15)

@app.callback(
    Output("treemap-chart", "figure"),
    [Input("filtered-data", "data")]
)
def update_treemap(companies_data):
    if not companies_data:
        return create_empty_figure("No data available")
    df = pd.DataFrame(companies_data)
    return create_revenue_by_category_treemap(df)

@app.callback(
    Output("earnings-chart", "figure"),
    [Input("filtered-data", "data")]
)
def update_earnings_chart(companies_data):
    if not companies_data:
        return create_empty_figure("No data available")
    df = pd.DataFrame(companies_data)
    return create_earnings_growth_distribution(df)
```

**Step 5: Add data availability notice**
```python
# In _setup_layout(), add after filters:
dbc.Row([
    dbc.Col([
        dbc.Alert([
            html.H6([
                html.I(className="fas fa-info-circle me-2"),
                "Data Availability Status"
            ], className="alert-heading"),
            html.Hr(),
            html.Ul([
                html.Li([
                    html.I(className="fas fa-check-circle text-success me-2"),
                    html.Strong("100% Coverage: "),
                    "Revenue, Gross Margin, Operating Margin, Profit Margin (from SEC 10-K/10-Q filings)"
                ]),
                html.Li([
                    html.I(className="fas fa-exclamation-circle text-warning me-2"),
                    html.Strong("52% Coverage: "),
                    "Earnings Growth (12 of 23 companies have quarterly EPS data)"
                ]),
                html.Li([
                    html.I(className="fas fa-clock text-info me-2"),
                    html.Strong("Coming Soon: "),
                    "Valuation metrics (P/E, Market Cap) - pending API rate limit reset"
                ]),
                html.Li([
                    html.I(className="fas fa-times-circle text-danger me-2"),
                    html.Strong("Not Available: "),
                    "User metrics (MAU, ARPU), retention (NRR, cohorts), unit economics (LTV/CAC) - "
                    "not available in public SEC filings or free API tiers"
                ])
            ], className="mb-0")
        ], color="light", className="border")
    ], width=12)
], className="mb-4")
```

### 7.3 Testing Plan

**Unit Tests:**
```python
# tests/test_visualizations.py
def test_revenue_bar_chart():
    sample_data = pd.DataFrame({
        'ticker': ['CHGG', 'COUR'],
        'company_name': ['Chegg', 'Coursera'],
        'category': ['direct_to_consumer', 'higher_education'],
        'revenue': [644.9e6, 523.8e6]
    })

    fig = create_revenue_comparison_bar(sample_data)

    assert fig.layout.title.text == "Revenue Comparison - All EdTech Companies"
    assert len(fig.data) == 1  # Single trace
    assert len(fig.data[0].y) == 2  # Two companies

def test_margin_chart():
    sample_data = pd.DataFrame({
        'ticker': ['CHGG', 'COUR'],
        'revenue': [644.9e6, 523.8e6],
        'gross_margin': [71.2, 58.4],
        'operating_margin': [-12.3, -8.7]
    })

    fig = create_margin_comparison_chart(sample_data, top_n=2)

    assert len(fig.data) == 2  # Two traces (GM + OM)
    assert fig.data[0].name == "Gross Margin"
    assert fig.data[1].name == "Operating Margin"
```

**Integration Tests:**
```python
# tests/test_dashboard_integration.py
def test_dashboard_loads(dash_duo):
    app = CorporateIntelDashboard()
    dash_duo.start_server(app.app)

    # Wait for page to load
    dash_duo.wait_for_element("#revenue-chart", timeout=10)

    # Check that all main components are present
    assert dash_duo.find_element("#kpi-cards")
    assert dash_duo.find_element("#revenue-chart")
    assert dash_duo.find_element("#margin-chart")
    assert dash_duo.find_element("#treemap-chart")
    assert dash_duo.find_element("#earnings-chart")
    assert dash_duo.find_element("#performance-table")

def test_category_filter(dash_duo):
    app = CorporateIntelDashboard()
    dash_duo.start_server(app.app)

    # Select K-12 category
    dash_duo.select_dcc_dropdown("#category-filter", value="k12")

    # Wait for charts to update
    dash_duo.wait_for_text_to_equal("#kpi-cards", timeout=5)

    # Verify filtered data
    # (Would need to inspect chart data via JavaScript)
```

---

## 8. Technology Stack

### 8.1 Backend Components

| Component       | Technology          | Purpose                          |
|-----------------|---------------------|----------------------------------|
| Database        | PostgreSQL 15       | Data warehouse                   |
| Time-series     | TimescaleDB 2.x     | Hypertable for financial_metrics |
| Vector search   | pgvector 0.5.x      | Document embeddings              |
| Analytics layer | dbt 1.7+            | Mart transformations             |
| ORM             | SQLAlchemy 2.0      | Database connections             |
| Web framework   | FastAPI 0.109+      | REST API (separate service)      |

### 8.2 Frontend Components

| Component       | Technology          | Purpose                          |
|-----------------|---------------------|----------------------------------|
| Dashboard       | Plotly Dash 2.14+   | Interactive visualizations       |
| UI framework    | Dash Bootstrap 1.5+ | Responsive layout                |
| Charts          | Plotly 5.18+        | Graph generation                 |
| Data tables     | Dash DataTable      | Sortable/filterable tables       |
| Icons           | Font Awesome 6.x    | UI icons                         |

### 8.3 Deployment

| Environment | Configuration                          |
|-------------|----------------------------------------|
| Development | Docker Compose, hot reload enabled     |
| Production  | Kubernetes, Nginx reverse proxy, SSL   |
| Database    | Managed PostgreSQL (AWS RDS/GCP SQL)   |
| Monitoring  | Prometheus + Grafana                   |
| Logging     | ELK stack (Elasticsearch, Kibana)      |

---

## 9. Security & Access Control

### 9.1 Authentication

```python
# Require JWT authentication for dashboard access
@app.server.before_request
def check_auth():
    if request.endpoint != 'static':
        token = request.headers.get('Authorization')
        if not token or not verify_jwt(token):
            return jsonify({"error": "Unauthorized"}), 401
```

### 9.2 Row-Level Security (Future Enhancement)

```sql
-- Filter companies based on user's organization
CREATE POLICY company_access_policy ON companies
FOR SELECT
USING (
    organization_id IN (
        SELECT organization_id FROM user_organizations
        WHERE user_id = current_setting('app.current_user_id')::uuid
    )
);
```

---

## 10. Future Enhancements

### 10.1 When YoY Growth Data Becomes Available

Add back competitive landscape scatter:
```python
def create_competitive_landscape_scatter_v2(companies_df: pd.DataFrame) -> go.Figure:
    """
    Scatter plot: X=YoY Growth, Y=Operating Margin, Size=Revenue
    Requirements: revenue_yoy_growth, latest_operating_margin, latest_revenue
    """
    fig = go.Figure()

    for category in companies_df['category'].unique():
        df_cat = companies_df[companies_df['category'] == category]

        fig.add_trace(go.Scatter(
            x=df_cat['revenue_yoy_growth'],
            y=df_cat['latest_operating_margin'],
            mode='markers+text',
            name=category.replace('_', ' ').title(),
            text=df_cat['ticker'],
            marker=dict(
                size=df_cat['latest_revenue'] / 1e7,
                color=CATEGORY_COLORS.get(category)
            )
        ))

    # Add quadrants
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.add_vline(x=0, line_dash="dash", line_color="gray")

    fig.update_layout(
        title="Growth vs Profitability Matrix",
        xaxis_title="Revenue YoY Growth (%)",
        yaxis_title="Operating Margin (%)"
    )

    return fig
```

### 10.2 When Private Company Data Becomes Available

Add cohort analysis for private EdTech companies (via partnerships/data licensing):
- Implement `create_cohort_heatmap()` with real retention data
- Add NRR trend lines
- Implement LTV/CAC analysis

### 10.3 Real-Time Updates

Integrate WebSocket support for live data updates:
```python
# Use Dash's dcc.Interval component with shorter refresh
dcc.Interval(
    id="realtime-interval",
    interval=5*1000,  # 5 seconds for real-time mode
    disabled=True  # Enable via toggle button
)

# Toggle between 60s batch updates and 5s real-time
@app.callback(
    Output("realtime-interval", "disabled"),
    [Input("realtime-toggle", "value")]
)
def toggle_realtime(enabled):
    return not enabled
```

---

## 11. Appendix

### 11.1 Color Palette Reference

```python
COLORS = {
    'primary': '#2C5282',        # Professional blue
    'secondary': '#4A7BA7',      # Medium blue
    'success': '#2F855A',        # Forest green
    'warning': '#D97706',        # Amber
    'danger': '#C53030',         # Deep red
    'info': '#2C5282',           # Same as primary
}

CATEGORY_COLORS = {
    'k12': '#6B8E9F',                    # Slate blue
    'higher_education': '#5A8F7B',       # Sage green
    'corporate_learning': '#7C8FA6',     # Blue-gray
    'direct_to_consumer': '#8B9D83',     # Olive gray
    'enabling_technology': '#9D8E7C',    # Warm gray
}
```

### 11.2 Database Schema Reference

**mart_company_performance (23 rows):**
```
company_id              UUID
ticker                  VARCHAR(10)
company_name            VARCHAR(255)
edtech_category         VARCHAR(50)
delivery_model          VARCHAR(50)
latest_revenue          NUMERIC        ✓ 100% coverage
latest_gross_margin     NUMERIC        ✓ 100% coverage
latest_operating_margin NUMERIC        ✓ 100% coverage
latest_profit_margin    NUMERIC        ✓ 100% coverage
earnings_growth         NUMERIC        ⚠ 52% coverage (12/23)
revenue_yoy_growth      NUMERIC        ✗ 0% coverage (API rate limited)
pe_ratio                NUMERIC        ✗ 0% coverage (API rate limited)
market_cap              NUMERIC        ✗ 0% coverage (API rate limited)
eps                     NUMERIC        ✗ 0% coverage
roe                     NUMERIC        ✗ 0% coverage
revenue_rank_in_category INTEGER       ✓ 100% (derived)
growth_rank_in_category INTEGER        ✓ 100% (derived)
revenue_rank_overall    INTEGER        ✓ 100% (derived)
growth_rank_overall     INTEGER        ✓ 100% (derived)
growth_score            INTEGER        ✓ 100% (derived)
margin_score            INTEGER        ✓ 100% (derived)
profitability_score     INTEGER        ✓ 100% (derived)
overall_score           NUMERIC        ✓ 100% (derived)
company_health_status   VARCHAR(50)    ✓ 100% (derived)
metrics_available       INTEGER        ✓ 100% (count of non-null metrics)
latest_data_date        TIMESTAMP      ✓ 100%
data_freshness          VARCHAR(20)    ✓ 100% (Current/Recent/Stale)
refreshed_at            TIMESTAMP      ✓ 100%
```

**mart_competitive_landscape (12 rows):**
```
edtech_category             VARCHAR(50)
companies_in_segment        INTEGER        ✓ 100%
total_segment_revenue       NUMERIC        ✓ 100%
total_segment_market_cap    NUMERIC        ✗ 0% (depends on market_cap)
avg_revenue_growth          NUMERIC        ✗ 0% (depends on revenue_yoy_growth)
median_revenue_growth       NUMERIC        ✗ 0%
max_revenue_growth          NUMERIC        ✗ 0%
min_revenue_growth          NUMERIC        ✗ 0%
avg_gross_margin            NUMERIC        ✓ 100%
avg_operating_margin        NUMERIC        ✓ 100%
avg_profit_margin           NUMERIC        ✓ 100%
avg_pe_ratio                NUMERIC        ✗ 0%
avg_roe                     NUMERIC        ✗ 0%
hhi_index                   NUMERIC        ✓ 100% (Herfindahl index)
market_concentration        VARCHAR(50)    ✓ 100% (derived from HHI)
market_stage                VARCHAR(50)    ⚠ Partial (depends on growth)
segment_leaders             TEXT           ✓ 100%
fastest_growers             TEXT           ⚠ Partial
at_risk_companies           TEXT           ✓ 100%
disruptor_count             INTEGER        ✓ 100%
leader_market_share         NUMERIC        ✓ 100%
top3_concentration          NUMERIC        ✓ 100%
opportunity_level           VARCHAR(50)    ⚠ Partial
segment_economics           VARCHAR(50)    ✓ 100%
strategic_recommendation    VARCHAR(100)   ⚠ Partial
refreshed_at                TIMESTAMP      ✓ 100%
```

### 11.3 Useful Resources

- **Plotly Documentation**: https://plotly.com/python/
- **Dash Documentation**: https://dash.plotly.com/
- **Bootstrap Components**: https://dash-bootstrap-components.opensource.faculty.ai/
- **dbt Best Practices**: https://docs.getdbt.com/best-practices
- **TimescaleDB Guide**: https://docs.timescale.com/

---

**Document Version**: 1.0
**Last Updated**: 2025-10-05
**Author**: System Architecture Designer
**Status**: Ready for Implementation
