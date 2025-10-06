"""Plotly Dash application for corporate intelligence visualization."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback, dcc, html
from dash.dash_table import DataTable
from plotly.subplots import make_subplots
import dash_bootstrap_components as dbc

from src.core.config import get_settings
from src.db.session import get_db, get_session_factory
from src.services.dashboard_service import DashboardService
from src.visualization.components import (
    create_cohort_heatmap,
    create_competitive_landscape_scatter,
    create_earnings_growth_distribution,
    create_margin_comparison_chart,
    create_market_share_sunburst,
    create_metrics_waterfall,
    create_retention_curves,
    create_revenue_by_category_treemap,
    create_revenue_comparison_bar,
    create_segment_comparison_radar,
)


class CorporateIntelDashboard:
    """Main dashboard application for EdTech intelligence."""

    def __init__(self):
        self.settings = get_settings()
        self.app = Dash(
            __name__,
            title="Corporate Intelligence Platform",
            update_title="Loading...",
            suppress_callback_exceptions=True,
            external_stylesheets=[dbc.themes.COSMO, dbc.icons.FONT_AWESOME],
        )
        self._setup_layout()
        self._register_callbacks()
    
    def _setup_layout(self):
        """Create dashboard layout."""
        self.app.layout = dbc.Container([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H1([
                        html.I(className="fas fa-chart-line me-3"),
                        "EdTech Corporate Intelligence Platform"
                    ], className="dashboard-title text-white"),
                    html.P([
                        "Real-time competitive analysis and market intelligence",
                        dbc.Badge("Live", color="success", className="ms-3"),
                    ], className="dashboard-subtitle text-white-50"),
                ], width=12, className="py-4", style={"backgroundColor": "#2C5282"}),
            ], className="mb-4"),

            # Data Freshness Banner
            dbc.Row([
                dbc.Col([
                    dbc.Alert(id="data-freshness-alert", color="info", className="mb-0", is_open=False),
                ], width=12),
            ], className="mb-3"),

            # Filters
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label([
                                html.I(className="fas fa-filter me-2"),
                                "EdTech Category"
                            ], className="fw-bold"),
                            dcc.Dropdown(
                                id="category-filter",
                                options=[
                                    {"label": "All Categories", "value": "all"},
                                    {"label": "K-12", "value": "k12"},
                                    {"label": "Higher Education", "value": "higher_education"},
                                    {"label": "Corporate Learning", "value": "corporate_learning"},
                                    {"label": "Direct to Consumer", "value": "direct_to_consumer"},
                                    {"label": "Enabling Technology", "value": "enabling_technology"},
                                ],
                                value="all",
                                clearable=False,
                            ),
                        ], md=4),

                        dbc.Col([
                            html.Label([
                                html.I(className="fas fa-calendar me-2"),
                                "Time Period"
                            ], className="fw-bold"),
                            dcc.Dropdown(
                                id="period-filter",
                                options=[
                                    {"label": "Last Quarter", "value": "1Q"},
                                    {"label": "Last 2 Quarters", "value": "2Q"},
                                    {"label": "Last Year", "value": "4Q"},
                                    {"label": "Last 2 Years", "value": "8Q"},
                                ],
                                value="4Q",
                                clearable=False,
                            ),
                        ], md=4),

                        dbc.Col([
                            html.Label([
                                html.I(className="fas fa-building me-2"),
                                "Comparison Companies"
                            ], className="fw-bold"),
                            dcc.Dropdown(
                                id="company-selector",
                                options=[],
                                value=[],
                                multi=True,
                                placeholder="Select companies to compare",
                            ),
                        ], md=4),
                    ]),
                ]),
            ], className="mb-4"),

            # KPI Cards
            dbc.Row(id="kpi-cards", className="mb-4"),

            # Main visualizations
            dbc.Row([
                # Competitive Landscape
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.Div([
                                html.H4([
                                    html.I(className="fas fa-globe me-2"),
                                    "Competitive Landscape"
                                ], className="d-inline"),
                                dbc.Button(
                                    html.I(className="fas fa-info-circle"),
                                    id="info-competitive",
                                    color="link",
                                    size="sm",
                                    className="float-end"
                                ),
                                dbc.Popover([
                                    dbc.PopoverHeader("Competitive Landscape Analysis"),
                                    dbc.PopoverBody([
                                        html.P("This scatter plot visualizes company positioning based on:"),
                                        html.Ul([
                                            html.Li("X-axis: Revenue growth rate (YoY %)"),
                                            html.Li("Y-axis: Net Revenue Retention (NRR %)"),
                                            html.Li("Bubble size: Total revenue"),
                                            html.Li("Color: EdTech category segment"),
                                        ]),
                                        html.Hr(),
                                        html.Small([
                                            html.I(className="fas fa-database me-2"),
                                            "Data from mart_company_performance"
                                        ], className="text-muted"),
                                    ]),
                                ], target="info-competitive", trigger="hover"),
                            ]),
                        ]),
                        dbc.CardBody([
                            dcc.Loading(
                                id="loading-competitive",
                                type="default",
                                children=[dcc.Graph(id="competitive-landscape-chart")],
                            ),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Badge([
                                        html.I(className="fas fa-table me-1"),
                                        "Source: mart_company_performance"
                                    ], color="info", className="me-2"),
                                    dbc.Badge(id="badge-competitive-updated", color="success"),
                                ], className="mt-2"),
                            ]),
                        ]),
                    ]),
                ], md=6, className="mb-4"),

                # Market Share
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.Div([
                                html.H4([
                                    html.I(className="fas fa-chart-pie me-2"),
                                    "Market Share Distribution"
                                ], className="d-inline"),
                                dbc.Button(
                                    html.I(className="fas fa-info-circle"),
                                    id="info-market-share",
                                    color="link",
                                    size="sm",
                                    className="float-end"
                                ),
                                dbc.Popover([
                                    dbc.PopoverHeader("Market Share Breakdown"),
                                    dbc.PopoverBody([
                                        html.P("Hierarchical view of market segmentation:"),
                                        html.Ul([
                                            html.Li("Inner ring: EdTech categories"),
                                            html.Li("Outer ring: Individual companies"),
                                            html.Li("Size: Revenue contribution"),
                                        ]),
                                        html.Hr(),
                                        html.Small([
                                            html.I(className="fas fa-database me-2"),
                                            "Data from mart_competitive_landscape"
                                        ], className="text-muted"),
                                    ]),
                                ], target="info-market-share", trigger="hover"),
                            ]),
                        ]),
                        dbc.CardBody([
                            dcc.Loading(
                                id="loading-market-share",
                                type="default",
                                children=[dcc.Graph(id="market-share-chart")],
                            ),
                            dbc.Row([
                                dbc.Col([
                                    dbc.Badge([
                                        html.I(className="fas fa-table me-1"),
                                        "Source: mart_competitive_landscape"
                                    ], color="info", className="me-2"),
                                    dbc.Badge(id="badge-market-share-updated", color="success"),
                                ], className="mt-2"),
                            ]),
                        ]),
                    ]),
                ], md=6, className="mb-4"),
            ]),

            # Row 2: Performance Metrics
            dbc.Row([
                # Waterfall Chart
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.Div([
                                html.H4([
                                    html.I(className="fas fa-water me-2"),
                                    "Revenue Waterfall Analysis"
                                ], className="d-inline"),
                                dbc.Button(
                                    html.I(className="fas fa-info-circle"),
                                    id="info-waterfall",
                                    color="link",
                                    size="sm",
                                    className="float-end"
                                ),
                                dbc.Popover([
                                    dbc.PopoverHeader("Revenue Waterfall"),
                                    dbc.PopoverBody([
                                        html.P("Breakdown of revenue components:"),
                                        html.Ul([
                                            html.Li("Starting revenue baseline"),
                                            html.Li("New customer revenue (green)"),
                                            html.Li("Expansion revenue (green)"),
                                            html.Li("Churn revenue (red)"),
                                            html.Li("Ending revenue total"),
                                        ]),
                                        html.P([
                                            html.Strong("Note: "),
                                            "Select a company to view waterfall analysis"
                                        ], className="text-warning small"),
                                    ]),
                                ], target="info-waterfall", trigger="hover"),
                            ]),
                        ]),
                        dbc.CardBody([
                            dcc.Loading(
                                id="loading-waterfall",
                                type="default",
                                children=[dcc.Graph(id="waterfall-chart")],
                            ),
                        ]),
                    ]),
                ], md=6, className="mb-4"),

                # Radar Chart
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.Div([
                                html.H4([
                                    html.I(className="fas fa-radar me-2"),
                                    "Segment Performance Radar"
                                ], className="d-inline"),
                                dbc.Button(
                                    html.I(className="fas fa-info-circle"),
                                    id="info-radar",
                                    color="link",
                                    size="sm",
                                    className="float-end"
                                ),
                                dbc.Popover([
                                    dbc.PopoverHeader("Multi-Metric Comparison"),
                                    dbc.PopoverBody([
                                        html.P("Normalized performance across metrics:"),
                                        html.Ul([
                                            html.Li("Revenue growth rate"),
                                            html.Li("Net revenue retention"),
                                            html.Li("LTV/CAC ratio"),
                                            html.Li("Market concentration"),
                                            html.Li("Segment maturity"),
                                        ]),
                                        html.P("All values normalized to 0-100 scale", className="small text-muted"),
                                    ]),
                                ], target="info-radar", trigger="hover"),
                            ]),
                        ]),
                        dbc.CardBody([
                            dcc.Loading(
                                id="loading-radar",
                                type="default",
                                children=[dcc.Graph(id="radar-chart")],
                            ),
                        ]),
                    ]),
                ], md=6, className="mb-4"),
            ]),

            # Row 3: Retention & Cohorts
            dbc.Row([
                # Retention Curves
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.Div([
                                html.H4([
                                    html.I(className="fas fa-chart-line me-2"),
                                    "Retention Curves"
                                ], className="d-inline"),
                                dbc.Button(
                                    html.I(className="fas fa-info-circle"),
                                    id="info-retention",
                                    color="link",
                                    size="sm",
                                    className="float-end"
                                ),
                                dbc.Popover([
                                    dbc.PopoverHeader("Customer Retention Analysis"),
                                    dbc.PopoverBody([
                                        html.P("Track customer retention over time:"),
                                        html.Ul([
                                            html.Li("X-axis: Months since acquisition"),
                                            html.Li("Y-axis: Retention rate (%)"),
                                            html.Li("Multiple cohorts compared"),
                                        ]),
                                        html.P("Higher curves indicate better retention", className="small text-muted"),
                                    ]),
                                ], target="info-retention", trigger="hover"),
                            ]),
                        ]),
                        dbc.CardBody([
                            dcc.Loading(
                                id="loading-retention",
                                type="default",
                                children=[dcc.Graph(id="retention-curves-chart")],
                            ),
                        ]),
                    ]),
                ], md=6, className="mb-4"),

                # Cohort Heatmap
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.Div([
                                html.H4([
                                    html.I(className="fas fa-th me-2"),
                                    "Cohort Analysis Heatmap"
                                ], className="d-inline"),
                                dbc.Button(
                                    html.I(className="fas fa-info-circle"),
                                    id="info-cohort",
                                    color="link",
                                    size="sm",
                                    className="float-end"
                                ),
                                dbc.Popover([
                                    dbc.PopoverHeader("Cohort Revenue Heatmap"),
                                    dbc.PopoverBody([
                                        html.P("Visualize cohort performance:"),
                                        html.Ul([
                                            html.Li("Rows: Acquisition cohorts"),
                                            html.Li("Columns: Months since acquisition"),
                                            html.Li("Color: Revenue or retention %"),
                                        ]),
                                        html.P("Darker colors indicate higher values", className="small text-muted"),
                                    ]),
                                ], target="info-cohort", trigger="hover"),
                            ]),
                        ]),
                        dbc.CardBody([
                            dcc.Loading(
                                id="loading-cohort",
                                type="default",
                                children=[dcc.Graph(id="cohort-heatmap")],
                            ),
                        ]),
                    ]),
                ], md=6, className="mb-4"),
            ]),

            # Row 4: Detailed Table
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4([
                                html.I(className="fas fa-table me-2"),
                                "Company Performance Details"
                            ]),
                        ]),
                        dbc.CardBody([
                            dcc.Loading(
                                id="loading-table",
                                type="default",
                                children=[html.Div(id="performance-table")],
                            ),
                        ]),
                    ]),
                ], width=12),
            ]),

            # Interval for auto-refresh
            dcc.Interval(
                id="interval-component",
                interval=60*1000,  # Update every minute
                n_intervals=0
            ),

            # Store components for data
            dcc.Store(id="filtered-data"),
            dcc.Store(id="market-data"),
            dcc.Store(id="data-freshness"),

        ], fluid=True, className="px-4 py-3")
    
    def _register_callbacks(self):
        """Register dashboard callbacks."""

        @self.app.callback(
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
        def update_data(category, period, n_intervals):
            """Fetch and filter data based on selections using DashboardService."""
            try:
                async def fetch_data():
                    # Get session factory and create a session context
                    session_factory = get_session_factory()
                    async with session_factory() as session:
                        service = DashboardService(session)

                        # Fetch company performance data
                        companies_data = await service.get_company_performance(
                            category=None if category == "all" else category
                        )

                        # Fetch competitive landscape
                        market_data = await service.get_competitive_landscape(
                            category=None if category == "all" else category
                        )

                        # Fetch data freshness
                        freshness = await service.get_data_freshness()

                        return companies_data, market_data, freshness

                # Run the async function using asyncio.run()
                companies_data, market_data, freshness = asyncio.run(fetch_data())

                # Build company selector options
                company_options = [
                    {"label": f"{c['ticker']} - {c['company_name']}",
                     "value": c['ticker']}
                    for c in companies_data
                ]

                # Build freshness alert
                if freshness.get("last_updated"):
                    last_updated = datetime.fromisoformat(freshness["last_updated"])
                    time_ago = datetime.utcnow() - last_updated
                    if time_ago.total_seconds() < 3600:
                        minutes = int(time_ago.total_seconds() / 60)
                        freshness_text = f"Data updated {minutes} minutes ago"
                    else:
                        hours = int(time_ago.total_seconds() / 3600)
                        freshness_text = f"Data updated {hours} hours ago"

                    alert_content = [
                        html.I(className="fas fa-info-circle me-2"),
                        freshness_text,
                        html.Span(f" | {freshness.get('companies_count', 0)} companies tracked", className="ms-3"),
                    ]
                    show_alert = True
                else:
                    alert_content = [
                        html.I(className="fas fa-exclamation-triangle me-2"),
                        "No data available. Run data ingestion to populate dashboard.",
                    ]
                    show_alert = True

                return companies_data, market_data, freshness, company_options, alert_content, show_alert

            except Exception as e:
                # Log the error and fallback to sample data
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Database query failed: {e}", exc_info=True)

                # Fallback to sample data
                companies_df = self._fetch_company_performance(category, period)
                market_df = self._fetch_market_data(category, period)

                company_options = [
                    {"label": f"{row['ticker']} - {row['company_name']}",
                     "value": row['ticker']}
                    for _, row in companies_df.iterrows()
                ]

                alert_content = [
                    html.I(className="fas fa-database me-2"),
                    "Using sample data (database not available)",
                ]

                return companies_df.to_dict('records'), market_df.to_dict('records'), {}, company_options, alert_content, True
        
        @self.app.callback(
            Output("kpi-cards", "children"),
            [Input("filtered-data", "data"),
             Input("market-data", "data")]
        )
        def update_kpis(companies_data, market_data):
            """Update KPI cards with modern design."""
            if not companies_data:
                return [
                    dbc.Col([
                        dbc.Alert([
                            html.I(className="fas fa-exclamation-circle me-2"),
                            "No data available. Please run data ingestion first."
                        ], color="warning")
                    ], width=12)
                ]

            companies_df = pd.DataFrame(companies_data)

            # Calculate KPIs
            total_revenue = companies_df['latest_revenue'].fillna(0).sum() / 1e9
            avg_growth = companies_df['revenue_yoy_growth'].fillna(0).mean()
            avg_nrr = companies_df['latest_nrr'].fillna(0).mean()
            total_users = companies_df['latest_mau'].fillna(0).sum() / 1e6

            # Calculate trends (mock data for now)
            revenue_trend = "+12.3%"
            growth_trend = "+2.1pp"
            nrr_trend = "+5pp"
            users_trend = "+18.5%"

            kpi_cards = [
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className="fas fa-dollar-sign fa-2x text-primary mb-3"),
                                html.H6("Total Market Revenue", className="text-muted mb-2"),
                                html.H3(f"${total_revenue:.1f}B", className="mb-1 fw-bold text-primary"),
                                html.Div([
                                    html.I(className="fas fa-arrow-up me-1 text-success"),
                                    html.Span(revenue_trend, className="text-success fw-bold"),
                                    html.Span(" vs. last period", className="text-muted small ms-1"),
                                ]),
                            ]),
                            html.Hr(className="my-2"),
                            html.Small([
                                html.I(className="fas fa-info-circle me-1"),
                                "Sum of all tracked companies"
                            ], className="text-muted"),
                        ]),
                    ], className="h-100 border-start border-primary border-4"),
                ], lg=3, md=6, className="mb-3"),

                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className="fas fa-chart-line fa-2x text-success mb-3"),
                                html.H6("Avg YoY Growth", className="text-muted mb-2"),
                                html.H3(f"{avg_growth:.1f}%", className="mb-1 fw-bold text-success"),
                                html.Div([
                                    html.I(className="fas fa-arrow-up me-1 text-success"),
                                    html.Span(growth_trend, className="text-success fw-bold"),
                                    html.Span(" percentage points", className="text-muted small ms-1"),
                                ]),
                            ]),
                            html.Hr(className="my-2"),
                            html.Small([
                                html.I(className="fas fa-info-circle me-1"),
                                "Year-over-year revenue growth"
                            ], className="text-muted"),
                        ]),
                    ], className="h-100 border-start border-success border-4"),
                ], lg=3, md=6, className="mb-3"),

                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className="fas fa-redo fa-2x text-info mb-3"),
                                html.H6("Avg Net Revenue Retention", className="text-muted mb-2"),
                                html.H3(f"{avg_nrr:.0f}%", className="mb-1 fw-bold text-info"),
                                html.Div([
                                    html.I(className="fas fa-arrow-up me-1 text-success"),
                                    html.Span(nrr_trend, className="text-success fw-bold"),
                                    html.Span(" improvement", className="text-muted small ms-1"),
                                ]),
                            ]),
                            html.Hr(className="my-2"),
                            html.Small([
                                html.I(className="fas fa-info-circle me-1"),
                                "Customer revenue retention rate"
                            ], className="text-muted"),
                        ]),
                    ], className="h-100 border-start border-info border-4"),
                ], lg=3, md=6, className="mb-3"),

                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.Div([
                                html.I(className="fas fa-users fa-2x text-warning mb-3"),
                                html.H6("Total Active Users", className="text-muted mb-2"),
                                html.H3(f"{total_users:.1f}M", className="mb-1 fw-bold text-warning"),
                                html.Div([
                                    html.I(className="fas fa-arrow-up me-1 text-success"),
                                    html.Span(users_trend, className="text-success fw-bold"),
                                    html.Span(" user growth", className="text-muted small ms-1"),
                                ]),
                            ]),
                            html.Hr(className="my-2"),
                            html.Small([
                                html.I(className="fas fa-info-circle me-1"),
                                "Monthly active users across all companies"
                            ], className="text-muted"),
                        ]),
                    ], className="h-100 border-start border-warning border-4"),
                ], lg=3, md=6, className="mb-3"),
            ]

            return kpi_cards
        
        @self.app.callback(
            [Output("competitive-landscape-chart", "figure"),
             Output("badge-competitive-updated", "children")],
            [Input("filtered-data", "data"),
             Input("company-selector", "value"),
             Input("data-freshness", "data")]
        )
        def update_competitive_landscape(companies_data, selected_companies, freshness):
            """Update competitive landscape scatter plot."""
            if not companies_data:
                empty_fig = go.Figure()
                empty_fig.add_annotation(
                    text="No data available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=20, color="gray")
                )
                return empty_fig, "No data"

            df = pd.DataFrame(companies_data)

            # Highlight selected companies
            if selected_companies:
                df['selected'] = df['ticker'].isin(selected_companies)
            else:
                df['selected'] = False

            figure = create_competitive_landscape_scatter(df, selected_companies or [])

            # Create timestamp badge
            if freshness.get("last_updated"):
                time_ago = "Updated recently"
            else:
                time_ago = "Using sample data"

            badge_content = [html.I(className="fas fa-clock me-1"), time_ago]

            return figure, badge_content
        
        @self.app.callback(
            [Output("market-share-chart", "figure"),
             Output("badge-market-share-updated", "children")],
            [Input("market-data", "data"),
             Input("category-filter", "value"),
             Input("data-freshness", "data")]
        )
        def update_market_share(market_data, category, freshness):
            """Update market share sunburst chart."""
            if not market_data:
                empty_fig = go.Figure()
                empty_fig.add_annotation(
                    text="No market data available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=20, color="gray")
                )
                return empty_fig, "No data"

            # Handle both dict and list formats
            if isinstance(market_data, dict) and 'segments' in market_data:
                df = pd.DataFrame(market_data['segments'])
            else:
                df = pd.DataFrame(market_data)

            figure = create_market_share_sunburst(df, category)

            badge_content = [html.I(className="fas fa-clock me-1"), "Updated recently"]
            return figure, badge_content
        
        @self.app.callback(
            Output("waterfall-chart", "figure"),
            [Input("filtered-data", "data"),
             Input("company-selector", "value")]
        )
        def update_waterfall(companies_data, selected_companies):
            """Update revenue waterfall chart."""
            if not companies_data or not selected_companies:
                empty_fig = go.Figure()
                empty_fig.add_annotation(
                    text="Select a company to view waterfall analysis",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16, color="gray")
                )
                return empty_fig

            df = pd.DataFrame(companies_data)
            company_data = df[df['ticker'] == selected_companies[0]]

            if company_data.empty:
                empty_fig = go.Figure()
                empty_fig.add_annotation(
                    text="Company data not available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16, color="gray")
                )
                return empty_fig

            return create_metrics_waterfall(company_data.iloc[0])

        @self.app.callback(
            Output("radar-chart", "figure"),
            [Input("market-data", "data")]
        )
        def update_radar_chart(market_data):
            """Update segment performance radar chart."""
            if not market_data:
                empty_fig = go.Figure()
                empty_fig.add_annotation(
                    text="No segment data available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16, color="gray")
                )
                return empty_fig

            # Handle both dict and list formats
            if isinstance(market_data, dict) and 'segments' in market_data:
                df = pd.DataFrame(market_data['segments'])
            else:
                df = pd.DataFrame(market_data)

            return create_segment_comparison_radar(df)

        @self.app.callback(
            Output("retention-curves-chart", "figure"),
            [Input("filtered-data", "data"),
             Input("company-selector", "value")]
        )
        def update_retention_curves(companies_data, selected_companies):
            """Update retention curves chart."""
            if not companies_data:
                empty_fig = go.Figure()
                empty_fig.add_annotation(
                    text="No retention data available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16, color="gray")
                )
                return empty_fig

            df = pd.DataFrame(companies_data)

            # Filter by selected companies if any
            if selected_companies:
                df = df[df['ticker'].isin(selected_companies)]

            return create_retention_curves(df)

        @self.app.callback(
            Output("cohort-heatmap", "figure"),
            [Input("filtered-data", "data"),
             Input("company-selector", "value")]
        )
        def update_cohort_heatmap(companies_data, selected_companies):
            """Update cohort analysis heatmap."""
            if not companies_data:
                empty_fig = go.Figure()
                empty_fig.add_annotation(
                    text="No cohort data available",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16, color="gray")
                )
                return empty_fig

            df = pd.DataFrame(companies_data)

            # Use first selected company or first in list
            if selected_companies:
                company_data = df[df['ticker'] == selected_companies[0]]
            else:
                company_data = df.head(1)

            if company_data.empty:
                empty_fig = go.Figure()
                empty_fig.add_annotation(
                    text="Select a company to view cohort analysis",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16, color="gray")
                )
                return empty_fig

            return create_cohort_heatmap(company_data.iloc[0])

        @self.app.callback(
            Output("performance-table", "children"),
            [Input("filtered-data", "data"),
             Input("company-selector", "value")]
        )
        def update_performance_table(companies_data, selected_companies):
            """Update performance details table."""
            if not companies_data:
                return dbc.Alert([
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    "No data available. Please run data ingestion first."
                ], color="warning")

            df = pd.DataFrame(companies_data)

            # Filter for selected companies or show top 10
            if selected_companies:
                df = df[df['ticker'].isin(selected_companies)]
            else:
                # Sort by revenue and take top 10
                df = df.sort_values('latest_revenue', ascending=False, na_position='last').head(10)

            if df.empty:
                return dbc.Alert([
                    html.I(className="fas fa-info-circle me-2"),
                    "No companies match the current filters."
                ], color="info")

            # Format columns
            display_columns = [
                'ticker', 'company_name', 'edtech_category',
                'latest_revenue', 'revenue_yoy_growth', 'latest_nrr',
                'latest_mau', 'latest_arpu', 'overall_score'
            ]

            # Ensure all columns exist
            for col in display_columns:
                if col not in df.columns:
                    df[col] = None

            df_display = df[display_columns].copy()

            # Format numbers
            df_display['latest_revenue'] = df_display['latest_revenue'].apply(
                lambda x: f"${x/1e6:.1f}M" if pd.notna(x) and x > 0 else "-"
            )
            df_display['revenue_yoy_growth'] = df_display['revenue_yoy_growth'].apply(
                lambda x: f"{x:.1f}%" if pd.notna(x) else "-"
            )
            df_display['latest_nrr'] = df_display['latest_nrr'].apply(
                lambda x: f"{x:.0f}%" if pd.notna(x) else "-"
            )
            df_display['latest_mau'] = df_display['latest_mau'].apply(
                lambda x: f"{x/1e3:.0f}K" if pd.notna(x) and x > 0 else "-"
            )
            df_display['latest_arpu'] = df_display['latest_arpu'].apply(
                lambda x: f"${x:.0f}" if pd.notna(x) else "-"
            )
            df_display['overall_score'] = df_display['overall_score'].apply(
                lambda x: f"{x:.0f}" if pd.notna(x) else "-"
            )

            return DataTable(
                data=df_display.to_dict('records'),
                columns=[
                    {"name": "Ticker", "id": "ticker"},
                    {"name": "Company", "id": "company_name"},
                    {"name": "Category", "id": "edtech_category"},
                    {"name": "Revenue", "id": "latest_revenue"},
                    {"name": "YoY Growth", "id": "revenue_yoy_growth"},
                    {"name": "NRR", "id": "latest_nrr"},
                    {"name": "MAU", "id": "latest_mau"},
                    {"name": "ARPU", "id": "latest_arpu"},
                    {"name": "Score", "id": "overall_score"},
                ],
                style_cell={
                    'textAlign': 'left',
                    'padding': '12px',
                    'fontFamily': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
                    'fontSize': '14px',
                },
                style_data_conditional=[
                    {
                        'if': {'column_id': 'overall_score'},
                        'backgroundColor': '#e3f2fd',
                        'fontWeight': '600',
                    },
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': '#f8f9fa',
                    }
                ],
                style_header={
                    'backgroundColor': '#2C5282',
                    'color': 'white',
                    'fontWeight': '600',
                    'textTransform': 'uppercase',
                    'fontSize': '12px',
                    'letterSpacing': '0.05em',
                    'padding': '12px',
                },
                style_table={
                    'overflowX': 'auto',
                },
                sort_action="native",
                filter_action="native",
                page_size=10,
                page_action="native",
            )
    
    
    def _fetch_company_performance(self, category: str, period: str) -> pd.DataFrame:
        """Fetch company performance data from database."""
        # In production, this would query mart_company_performance
        # Using sample data structure for demonstration
        
        sample_data = {
            'ticker': ['CHGG', 'COUR', 'DUOL', 'TWOU', 'ARCE'],
            'company_name': ['Chegg', 'Coursera', 'Duolingo', '2U', 'Arco Platform'],
            'edtech_category': ['direct_to_consumer', 'higher_education', 'direct_to_consumer', 
                               'higher_education', 'k12'],
            'latest_revenue': [644.9e6, 523.8e6, 484.2e6, 945.8e6, 312.4e6],
            'revenue_yoy_growth': [-7.2, 21.0, 42.9, -12.5, 18.3],
            'latest_nrr': [92, 108, 124, 85, 115],
            'latest_mau': [4.2e6, 118e6, 83.1e6, 12.8e6, 2.1e6],
            'latest_arpu': [12.8, 48.5, 4.9, 245.0, 124.0],
            'latest_ltv_cac_ratio': [1.2, 2.8, 4.1, 0.9, 3.2],
            'overall_score': [45, 72, 89, 38, 78],
        }
        
        df = pd.DataFrame(sample_data)
        
        if category != "all":
            df = df[df['edtech_category'] == category]
        
        return df
    
    def _fetch_market_data(self, category: str, period: str) -> pd.DataFrame:
        """Fetch market data from database."""
        # In production, this would query mart_competitive_landscape
        # Using sample data structure
        
        sample_data = {
            'edtech_category': ['k12', 'higher_education', 'corporate_learning', 
                               'direct_to_consumer', 'enabling_technology'],
            'total_segment_revenue': [2.3e9, 4.1e9, 3.2e9, 5.8e9, 1.9e9],
            'companies_in_segment': [12, 18, 15, 24, 9],
            'avg_revenue_growth': [15.2, 8.9, 22.4, 31.5, 18.7],
            'avg_nrr': [108, 102, 115, 98, 112],
            'hhi_index': [1823, 2156, 1452, 987, 2534],
        }
        
        df = pd.DataFrame(sample_data)
        
        if category != "all":
            df = df[df['edtech_category'] == category]
        
        return df
    
    def run(self, debug: bool = False, port: int = 8050):
        """Run the dashboard application."""
        self.app.run(debug=debug, port=port, host="0.0.0.0")

if __name__ == "__main__":
    """Run the dashboard application."""
    dashboard = CorporateIntelDashboard()
    print("🚀 Starting Corporate Intelligence Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:8050")
    dashboard.run(debug=True, port=8050)
