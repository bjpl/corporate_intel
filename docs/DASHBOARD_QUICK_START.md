# Dashboard Quick Start Guide

## Prerequisites

Ensure you have the required dependencies installed:

```bash
pip install dash-bootstrap-components
```

All other dependencies (dash, plotly, pandas) should already be installed.

## Running the Dashboard

### Option 1: Direct Python Execution
```bash
cd corporate_intel
python src/visualization/dash_app.py
```

### Option 2: As a Module
```bash
python -m src.visualization.dash_app
```

## Accessing the Dashboard

Once running, open your browser to:
```
http://localhost:8050
```

The dashboard will auto-refresh every 60 seconds with the latest data.

## Features Overview

### 1. Filters (Top Bar)
- **EdTech Category**: Filter by market segment (K-12, Higher Ed, etc.)
- **Time Period**: Select historical range (1Q, 2Q, 4Q, 8Q)
- **Comparison Companies**: Multi-select for detailed analysis

### 2. KPI Cards (Row 1)
Four key metrics with trend indicators:
- Total Market Revenue
- Average YoY Growth
- Average Net Revenue Retention
- Total Active Users

**Hover over** any card for contextual information.

### 3. Market Overview (Row 2)
**Competitive Landscape (Left)**
- Scatter plot: Growth vs. NRR
- Bubble size: Revenue
- Color: Category
- **ⓘ Click icon** for detailed explanation

**Market Share (Right)**
- Sunburst chart: Hierarchical view
- Inner ring: Categories
- Outer ring: Companies
- **ⓘ Click icon** for breakdown details

### 4. Performance Analysis (Row 3)
**Revenue Waterfall (Left)**
- Component breakdown
- Requires company selection
- Shows new/expansion/churn

**Segment Radar (Right)**
- Multi-metric comparison
- Normalized 0-100 scale
- All segments overlaid

### 5. Retention & Cohorts (Row 4)
**Retention Curves (Left)**
- Customer retention over time
- Multiple cohorts
- Months since acquisition

**Cohort Heatmap (Right)**
- Revenue by cohort
- Color intensity = value
- Requires company selection

### 6. Performance Table (Row 5)
- Sortable columns
- Searchable/filterable
- Top 10 or selected companies
- Formatted metrics

## Interactivity Guide

### Selecting Companies
1. Click "Comparison Companies" dropdown
2. Type to search or browse
3. Select multiple companies
4. Charts update automatically

### Reading Tooltips
1. Hover over **ⓘ** icon next to chart titles
2. Popover shows:
   - Chart explanation
   - How to interpret
   - Data sources
   - Calculation methods

### Understanding Data Badges
At bottom of each chart:
- **Blue badge**: Data source table
- **Green badge**: Last update time

### Empty States
If you see "No data available":
1. Check data freshness alert at top
2. Run data ingestion: `python -m src.ingestion.sec_ingestion`
3. Refresh dashboard

## Data Flow

```
User Filters → Callbacks → DashboardService → PostgreSQL/Redis → Charts
                                      ↓
                              Cache (5 min TTL)
```

### What Happens on Filter Change
1. Dash callback triggered
2. Async service queries database
3. Redis cache checked first
4. Data transformed to DataFrames
5. All dependent charts update
6. Badges refresh with timestamps

## Troubleshooting

### Dashboard Won't Start
```bash
# Check dependencies
pip install -r requirements.txt

# Verify imports
python -c "import dash_bootstrap_components; print('OK')"
```

### No Data Showing
1. **Check alert banner** at top
2. **Run ingestion**:
   ```bash
   python -m src.ingestion.sec_ingestion
   ```
3. **Verify database connection** in `.env`:
   ```
   DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
   ```

### Charts Not Updating
1. Check browser console for errors (F12)
2. Verify callback outputs match component IDs
3. Restart dashboard server

### Slow Performance
1. Redis cache may be disabled
2. Check `REDIS_URL` in `.env`
3. Verify TimescaleDB compression:
   ```sql
   SELECT * FROM timescaledb_information.compression_settings;
   ```

## Advanced Usage

### Custom Port
```python
dashboard.run(debug=True, port=8080)
```

### Production Mode
```python
dashboard.run(debug=False, port=8050, host="0.0.0.0")
```

### Behind Reverse Proxy
Update `app.server` in dash_app.py:
```python
app.server.config['APPLICATION_ROOT'] = '/dashboard'
```

## Development Tips

### Adding New Visualizations
1. Create chart function in `src/visualization/components.py`
2. Add card layout in `_setup_layout()`
3. Include info popover with explanation
4. Register callback in `_register_callbacks()`
5. Add loading wrapper
6. Include empty state handling

### Modifying KPI Cards
Edit the `update_kpis()` callback:
```python
@self.app.callback(
    Output("kpi-cards", "children"),
    [Input("filtered-data", "data")]
)
def update_kpis(companies_data):
    # Calculate your metric
    # Create dbc.Col with dbc.Card
    # Return list of columns
```

### Custom Tooltips
```python
dbc.Popover([
    dbc.PopoverHeader("Your Title"),
    dbc.PopoverBody([
        html.P("Explanation"),
        html.Ul([html.Li("Point 1"), html.Li("Point 2")]),
        html.Hr(),
        html.Small("Data source info", className="text-muted")
    ])
], target="your-id", trigger="hover")
```

## Performance Optimization

### Redis Caching
Ensure Redis is running:
```bash
redis-cli ping
# Should return: PONG
```

### Database Indexes
Verify indexes on mart tables:
```sql
-- Check indexes
\d+ mart_company_performance
\d+ mart_competitive_landscape
```

### Callback Optimization
- Use `prevent_initial_call=True` for expensive callbacks
- Batch related outputs in single callback
- Use `dcc.Store` for intermediate data

## Security Considerations

### Production Deployment
1. **Disable debug mode**: `debug=False`
2. **Set secret key**: `app.server.secret_key = os.environ['SECRET_KEY']`
3. **Use HTTPS**: Deploy behind nginx/Apache
4. **Authentication**: Add Flask-Login or OAuth
5. **Rate limiting**: Implement with Redis

### Data Access
- Dashboard uses read-only service account
- Sensitive data masked by default
- Audit logging in DashboardService

## Next Steps

1. **Explore the dashboard** - Click around, hover over icons
2. **Load real data** - Run SEC ingestion and transforms
3. **Customize filters** - Add your own categories
4. **Extend visualizations** - Create new chart types
5. **Deploy to production** - Use Docker + nginx

## Support

For issues or questions:
- Check logs: `tail -f logs/dashboard.log`
- Review documentation: `docs/DASHBOARD_MODERNIZATION.md`
- Examine code: `src/visualization/dash_app.py`

---

**Happy Analyzing! 📊**
