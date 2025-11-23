# Corporate Intelligence Dashboard

## Overview

A modern, professional Plotly Dash application for visualizing EdTech competitive intelligence data. Built with Dash Bootstrap Components for a SaaS-quality user experience.

## Features

### 🎨 Modern UI Design
- **Material Design Components**: Bootstrap 5 cards, badges, and alerts
- **Professional Theme**: COSMO theme with custom gradients
- **Font Awesome Icons**: Visual hierarchy and context
- **Responsive Layout**: Mobile-first grid system
- **Hover Effects**: Smooth animations and transitions

### 📊 Comprehensive Visualizations
1. **Competitive Landscape**: Scatter plot (Growth vs. NRR)
2. **Market Share**: Hierarchical sunburst chart
3. **Revenue Waterfall**: Component breakdown analysis
4. **Segment Radar**: Multi-metric comparison
5. **Retention Curves**: Customer retention tracking
6. **Cohort Heatmap**: Cohort performance visualization
7. **Performance Table**: Sortable, filterable data grid

### 💡 User Experience Enhancements
- **Tooltips Everywhere**: Click ⓘ icons for explanations
- **Data Transparency**: Source badges on all charts
- **Loading States**: Professional spinners during data fetch
- **Empty States**: Helpful messages when no data
- **Real-time Updates**: Auto-refresh every 60 seconds

### 🔧 Technical Features
- **Async Data Service**: PostgreSQL + TimescaleDB integration
- **Redis Caching**: 5-minute TTL for performance
- **dbt Mart Queries**: Optimized analytical queries
- **Fallback Data**: Sample data when DB unavailable
- **Error Handling**: Graceful degradation

## File Structure

```
src/visualization/
├── dash_app.py              # Main dashboard application
├── components.py            # Reusable chart components
├── assets/
│   └── style.css           # Custom CSS styling
└── README.md               # This file
```

## Quick Start

### 1. Install Dependencies
```bash
pip install dash-bootstrap-components
```

### 2. Run Dashboard
```bash
cd corporate_intel
python src/visualization/dash_app.py
```

### 3. Access
Open browser to: http://localhost:8050

## Architecture

### Component Hierarchy
```
CorporateIntelDashboard
├── __init__()
│   ├── Initialize settings
│   ├── Create Dash app with Bootstrap theme
│   ├── Setup layout
│   └── Register callbacks
│
├── _setup_layout()
│   ├── Header with branding
│   ├── Data freshness alert
│   ├── Filters (category, period, companies)
│   ├── KPI cards (4 metrics)
│   ├── Visualizations (6 charts)
│   ├── Performance table
│   └── Store components
│
└── _register_callbacks()
    ├── update_data() - Main data fetch
    ├── update_kpis() - KPI cards
    ├── update_competitive_landscape() - Scatter plot
    ├── update_market_share() - Sunburst chart
    ├── update_waterfall() - Waterfall chart
    ├── update_radar_chart() - Radar chart
    ├── update_retention_curves() - Retention curves
    ├── update_cohort_heatmap() - Cohort heatmap
    └── update_performance_table() - Data table
```

### Data Flow
```
User Interaction
    ↓
Dash Callback Triggered
    ↓
Async Data Fetch
    ↓
┌─────────────────┐
│ DashboardService│
└─────────────────┘
    ↓           ↓
Redis Cache   PostgreSQL
(5min TTL)    (dbt marts)
    ↓           ↓
Data Transformation
    ↓
Update Visualizations
```

## Key Components

### 1. KPI Cards
```python
dbc.Col([
    dbc.Card([
        dbc.CardBody([
            html.I(className="fas fa-dollar-sign fa-2x"),
            html.H6("Total Market Revenue"),
            html.H3("$12.5B"),
            html.Div([
                html.I(className="fas fa-arrow-up"),
                html.Span("+12.3%"),
            ]),
        ]),
    ]),
])
```

### 2. Chart with Tooltip
```python
dbc.Card([
    dbc.CardHeader([
        html.H4("Chart Title"),
        dbc.Button(html.I(className="fas fa-info-circle"), id="info-btn"),
        dbc.Popover([
            dbc.PopoverHeader("Explanation"),
            dbc.PopoverBody("Detailed description..."),
        ], target="info-btn", trigger="hover"),
    ]),
    dbc.CardBody([
        dcc.Loading(children=[dcc.Graph(id="chart")]),
        dbc.Badge("Source: mart_table", color="info"),
    ]),
])
```

### 3. Empty State
```python
if not data:
    empty_fig = go.Figure()
    empty_fig.add_annotation(
        text="No data available",
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=16, color="gray")
    )
    return empty_fig
```

## Customization

### Adding New KPI Card
1. Update `update_kpis()` callback
2. Calculate your metric from data
3. Create `dbc.Col` with `dbc.Card`
4. Add to return list

### Adding New Chart
1. Create chart function in `components.py`
2. Add card to layout in `_setup_layout()`
3. Include info popover
4. Register callback in `_register_callbacks()`
5. Add loading wrapper
6. Handle empty state

### Changing Theme
```python
self.app = Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.FLATLY,  # Change theme here
        dbc.icons.FONT_AWESOME
    ]
)
```

Available themes: COSMO, FLATLY, LITERA, MINTY, PULSE, SANDSTONE, SIMPLEX, SKETCHY, UNITED, YETI, etc.

### Custom Colors
Edit `assets/style.css`:
```css
:root {
    --primary: #2C5282;      /* Your primary color */
    --success: #28a745;      /* Success color */
    --warning: #ffc107;      /* Warning color */
    /* ... */
}
```

## Callbacks Reference

### Main Data Callback
```python
@app.callback(
    [Output("filtered-data", "data"),
     Output("market-data", "data"),
     Output("data-freshness", "data"),
     Output("company-selector", "options"),
     Output("data-freshness-alert", "children"),
     Output("data-freshness-alert", "is_open")],
    [Input("category-filter", "value"),
     Input("period-filter", "value"),
     Input("interval-component", "n_intervals")]
)
```

### Chart Callback Pattern
```python
@app.callback(
    [Output("chart-id", "figure"),
     Output("badge-id", "children")],
    [Input("filtered-data", "data"),
     Input("data-freshness", "data")]
)
```

## Performance Optimization

### Redis Caching
```python
# In DashboardService
cache_key = f"dashboard:company_performance:{category}"
cached_data = await self._get_cached(cache_key)
if cached_data:
    return cached_data
# ... fetch from DB and cache
```

### Async Data Fetching
```python
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

async def fetch_data():
    async for session in get_db():
        service = DashboardService(session)
        return await service.get_company_performance()

data = loop.run_until_complete(fetch_data())
loop.close()
```

### Callback Optimization
- Use `dcc.Store` for intermediate data
- Batch related outputs in single callback
- Use `prevent_initial_call=True` where appropriate

## Deployment

### Development
```bash
python src/visualization/dash_app.py
```

### Production
```python
# In dash_app.py
if __name__ == "__main__":
    dashboard = CorporateIntelDashboard()
    dashboard.run(
        debug=False,
        port=8050,
        host="0.0.0.0"
    )
```

### Docker
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "src/visualization/dash_app.py"]
```

### Nginx Reverse Proxy
```nginx
location /dashboard {
    proxy_pass http://localhost:8050;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

## Troubleshooting

### Dashboard Won't Start
```bash
# Check dependencies
pip install -r requirements.txt

# Verify dash-bootstrap-components
python -c "import dash_bootstrap_components; print('OK')"
```

### No Data Showing
1. Check data freshness alert
2. Run data ingestion
3. Verify database connection
4. Check Redis cache

### Charts Not Updating
1. Open browser console (F12)
2. Check for JavaScript errors
3. Verify callback outputs
4. Restart dashboard server

### Slow Performance
1. Enable Redis caching
2. Check TimescaleDB compression
3. Optimize dbt mart queries
4. Review callback dependencies

## Best Practices

### UI/UX
- ✅ Always include tooltips
- ✅ Show data sources
- ✅ Handle empty states
- ✅ Add loading indicators
- ✅ Use semantic colors

### Code Quality
- ✅ Type hints on functions
- ✅ Docstrings for callbacks
- ✅ Error handling with try/except
- ✅ Fallback data patterns
- ✅ Async for DB operations

### Accessibility
- ✅ WCAG AA contrast ratios
- ✅ Semantic HTML structure
- ✅ Keyboard navigation
- ✅ Screen reader support
- ✅ Reduced motion support

## Resources

### Documentation
- [Dash Docs](https://dash.plotly.com/)
- [Dash Bootstrap Components](https://dash-bootstrap-components.opensource.faculty.ai/)
- [Plotly Python](https://plotly.com/python/)
- [Font Awesome Icons](https://fontawesome.com/icons)

### Examples
- [Dash Gallery](https://dash.gallery/)
- [Bootstrap Themes](https://bootswatch.com/)
- [Plotly Examples](https://plotly.com/python/plotly-express/)

### Related Files
- `docs/DASHBOARD_MODERNIZATION.md` - Implementation summary
- `docs/DASHBOARD_QUICK_START.md` - Quick start guide
- `tests/test_dashboard_ui.py` - Test suite

## Contributing

When adding features:
1. Follow existing patterns
2. Add tooltips and context
3. Include empty states
4. Handle errors gracefully
5. Update documentation
6. Test on mobile devices

## License

Same as parent project.

---

**Built with ❤️ using Dash + Bootstrap**
