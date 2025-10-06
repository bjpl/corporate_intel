"""Plotly Dash application for corporate intelligence visualization - UPDATED WITH REAL DATA CHARTS."""

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
    create_earnings_growth_distribution,
    create_margin_comparison_chart,
    create_market_share_sunburst,
    create_revenue_by_category_treemap,
    create_revenue_comparison_bar,
    create_segment_comparison_radar,
)


class CorporateIntelDashboard:
    """Main dashboard application for EdTech intelligence - with data-appropriate visualizations."""

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
        """Create dashboard layout with real-data visualizations."""
        self.app.layout = dbc.Container([
            # Header
            dbc.Row([
                dbc.Col([
                    html.H1([
                        html.I(className="fas fa-chart-line me-3"),
                        "EdTech Corporate Intelligence Platform"
                    ], className="dashboard-title text-white"),
                    html.P([
                        "Data-driven competitive analysis with actual financial metrics",
                        dbc.Badge("Real Data", color="success", className="ms-3"),
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
                        ], md=6),

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
                                placeholder="Select companies to highlight",
                            ),
                        ], md=6),
                    ]),
                ]),
            ], className="mb-4"),

            # KPI Cards
            dbc.Row(id="kpi-cards", className="mb-4"),

            # Row 1: Revenue Visualizations
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4([
                                html.I(className="fas fa-chart-bar me-2"),
                                "Revenue Comparison - All Companies"
                            ]),
                            dbc.Button(
                                html.I(className="fas fa-info-circle"),
                                id="info-revenue",
                                color="link",
                                size="sm",
                                className="float-end"
                            ),
                            dbc.Popover([
                                dbc.PopoverHeader("Actual Revenue Data"),
                                dbc.PopoverBody([
                                    html.P("23 companies ranked by revenue:"),
                                    html.Ul([
                                        html.Li("Color coded by category"),
                                        html.Li("Horizontal bars for easy comparison"),
                                        html.Li("Source: companies.revenue"),
                                    ]),
                                ]),
                            ], target="info-revenue", trigger="hover"),
                        ]),
                        dbc.CardBody([
                            dcc.Loading(children=[dcc.Graph(id="revenue-comparison-chart")]),
                        ]),
                    ]),
                ], md=7, className="mb-4"),

                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4([
                                html.I(className="fas fa-sitemap me-2"),
                                "Market Distribution Treemap"
                            ]),
                        ]),
                        dbc.CardBody([
                            dcc.Loading(children=[dcc.Graph(id="treemap-chart")]),
                        ]),
                    ]),
                ], md=5, className="mb-4"),
            ]),

            # Row 2: Margin & Growth Analysis
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4([
                                html.I(className="fas fa-percent me-2"),
                                "Margin Comparison - Top 15"
                            ]),
                        ]),
                        dbc.CardBody([
                            dcc.Loading(children=[dcc.Graph(id="margins-chart")]),
                        ]),
                    ]),
                ], md=6, className="mb-4"),

                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4([
                                html.I(className="fas fa-chart-line me-2"),
                                "Earnings Growth Distribution"
                            ]),
                        ]),
                        dbc.CardBody([
                            dcc.Loading(children=[dcc.Graph(id="earnings-growth-chart")]),
                        ]),
                    ]),
                ], md=6, className="mb-4"),
            ]),

            # Row 3: Market Share
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader([
                            html.H4([
                                html.I(className="fas fa-chart-pie me-2"),
                                "Market Share by Category"
                            ]),
                        ]),
                        dbc.CardBody([
                            dcc.Loading(children=[dcc.Graph(id="market-share-chart")]),
                        ]),
                    ]),
                ], width=12, className="mb-4"),
            ]),

            # Row 4: Performance Table
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
                            dcc.Loading(children=[html.Div(id="performance-table")]),
                        ]),
                    ]),
                ], width=12),
            ]),

            # Interval for auto-refresh
            dcc.Interval(id="interval-component", interval=60*1000, n_intervals=0),

            # Store components
            dcc.Store(id="filtered-data"),
            dcc.Store(id="market-data"),
            dcc.Store(id="data-freshness"),

        ], fluid=True, className="px-4 py-3")

    def _register_callbacks(self):
        """Register dashboard callbacks for new visualizations."""

        @self.app.callback(
            [Output("filtered-data", "data"),
             Output("market-data", "data"),
             Output("data-freshness", "data"),
             Output("company-selector", "options"),
             Output("data-freshness-alert", "children"),
             Output("data-freshness-alert", "is_open")],
            [Input("category-filter", "value"),
             Input("interval-component", "n_intervals")]
        )
        def update_data(category, n_intervals):
            """Fetch company data from database."""
            try:
                async def fetch_data():
                    session_factory = get_session_factory()
                    async with session_factory() as session:
                        service = DashboardService(session)
                        companies_data = await service.get_company_performance(
                            category=None if category == "all" else category
                        )
                        market_data = await service.get_competitive_landscape(
                            category=None if category == "all" else category
                        )
                        freshness = await service.get_data_freshness()
                        return companies_data, market_data, freshness

                companies_data, market_data, freshness = asyncio.run(fetch_data())

                company_options = [
                    {"label": f"{c['ticker']} - {c['company_name']}", "value": c['ticker']}
                    for c in companies_data
                ]

                alert_content = [
                    html.I(className="fas fa-check-circle me-2"),
                    f"Data loaded: {len(companies_data)} companies tracked"
                ]

                return companies_data, market_data, freshness, company_options, alert_content, True

            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Data fetch failed: {e}")
                # Return empty data with error message
                return [], [], {}, [], [html.I(className="fas fa-exclamation-triangle me-2"), "Database unavailable - check connection"], True

        @self.app.callback(
            Output("kpi-cards", "children"),
            [Input("filtered-data", "data")]
        )
        def update_kpis(companies_data):
            """Update KPI cards with real metrics."""
            if not companies_data:
                return [dbc.Col([dbc.Alert("No data available", color="warning")], width=12)]

            df = pd.DataFrame(companies_data)

            total_revenue = df['revenue'].fillna(0).sum() / 1e9 if 'revenue' in df.columns else 0
            avg_gross_margin = df['gross_margin'].mean() if 'gross_margin' in df.columns else 0
            avg_operating_margin = df['operating_margin'].mean() if 'operating_margin' in df.columns else 0
            earnings_growth_count = df['earnings_growth'].notna().sum() if 'earnings_growth' in df.columns else 0

            return [
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.I(className="fas fa-dollar-sign fa-2x text-primary mb-3"),
                            html.H6("Total Revenue", className="text-muted mb-2"),
                            html.H3(f"${total_revenue:.1f}B", className="mb-1 fw-bold text-primary"),
                            html.Small(f"{len(df)} companies tracked", className="text-muted"),
                        ]),
                    ], className="h-100 border-start border-primary border-4"),
                ], lg=3, md=6, className="mb-3"),

                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.I(className="fas fa-percent fa-2x text-success mb-3"),
                            html.H6("Avg Gross Margin", className="text-muted mb-2"),
                            html.H3(f"{avg_gross_margin:.1f}%", className="mb-1 fw-bold text-success"),
                            html.Small("All companies average", className="text-muted"),
                        ]),
                    ], className="h-100 border-start border-success border-4"),
                ], lg=3, md=6, className="mb-3"),

                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.I(className="fas fa-chart-line fa-2x text-info mb-3"),
                            html.H6("Avg Operating Margin", className="text-muted mb-2"),
                            html.H3(f"{avg_operating_margin:.1f}%", className="mb-1 fw-bold text-info"),
                            html.Small("Profitability metric", className="text-muted"),
                        ]),
                    ], className="h-100 border-start border-info border-4"),
                ], lg=3, md=6, className="mb-3"),

                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.I(className="fas fa-seedling fa-2x text-warning mb-3"),
                            html.H6("Earnings Growth Data", className="text-muted mb-2"),
                            html.H3(f"{earnings_growth_count}", className="mb-1 fw-bold text-warning"),
                            html.Small("companies with data", className="text-muted"),
                        ]),
                    ], className="h-100 border-start border-warning border-4"),
                ], lg=3, md=6, className="mb-3"),
            ]

        @self.app.callback(
            Output("revenue-comparison-chart", "figure"),
            [Input("filtered-data", "data")]
        )
        def update_revenue_comparison(companies_data):
            """Update revenue bar chart."""
            if not companies_data:
                return go.Figure().add_annotation(
                    text="No data available", x=0.5, y=0.5,
                    xref="paper", yref="paper", showarrow=False
                )

            df = pd.DataFrame(companies_data)
            # Map old column names to new if needed
            if 'edtech_category' in df.columns:
                df['category'] = df['edtech_category']
            if 'latest_revenue' in df.columns:
                df['revenue'] = df['latest_revenue']

            return create_revenue_comparison_bar(df)

        @self.app.callback(
            Output("treemap-chart", "figure"),
            [Input("filtered-data", "data")]
        )
        def update_treemap(companies_data):
            """Update revenue treemap."""
            if not companies_data:
                return go.Figure().add_annotation(
                    text="No data available", x=0.5, y=0.5,
                    xref="paper", yref="paper", showarrow=False
                )

            df = pd.DataFrame(companies_data)
            if 'edtech_category' in df.columns:
                df['category'] = df['edtech_category']
            if 'latest_revenue' in df.columns:
                df['revenue'] = df['latest_revenue']

            return create_revenue_by_category_treemap(df)

        @self.app.callback(
            Output("margins-chart", "figure"),
            [Input("filtered-data", "data")]
        )
        def update_margins(companies_data):
            """Update margin comparison chart."""
            if not companies_data:
                return go.Figure().add_annotation(
                    text="No data available", x=0.5, y=0.5,
                    xref="paper", yref="paper", showarrow=False
                )

            df = pd.DataFrame(companies_data)
            if 'latest_revenue' in df.columns:
                df['revenue'] = df['latest_revenue']

            return create_margin_comparison_chart(df)

        @self.app.callback(
            Output("earnings-growth-chart", "figure"),
            [Input("filtered-data", "data")]
        )
        def update_earnings_growth(companies_data):
            """Update earnings growth distribution."""
            if not companies_data:
                return go.Figure().add_annotation(
                    text="No data available", x=0.5, y=0.5,
                    xref="paper", yref="paper", showarrow=False
                )

            df = pd.DataFrame(companies_data)
            if 'edtech_category' in df.columns:
                df['category'] = df['edtech_category']

            return create_earnings_growth_distribution(df)

        @self.app.callback(
            Output("market-share-chart", "figure"),
            [Input("market-data", "data"),
             Input("category-filter", "value")]
        )
        def update_market_share(market_data, category):
            """Update market share sunburst."""
            if not market_data:
                return go.Figure().add_annotation(
                    text="No data available", x=0.5, y=0.5,
                    xref="paper", yref="paper", showarrow=False
                )

            if isinstance(market_data, dict) and 'segments' in market_data:
                df = pd.DataFrame(market_data['segments'])
            else:
                df = pd.DataFrame(market_data)

            return create_market_share_sunburst(df, category)

        @self.app.callback(
            Output("performance-table", "children"),
            [Input("filtered-data", "data"),
             Input("company-selector", "value")]
        )
        def update_table(companies_data, selected_companies):
            """Update performance table."""
            if not companies_data:
                return dbc.Alert("No data available", color="warning")

            df = pd.DataFrame(companies_data)

            if selected_companies:
                df = df[df['ticker'].isin(selected_companies)]
            else:
                # Show top 15 by revenue
                revenue_col = 'revenue' if 'revenue' in df.columns else 'latest_revenue'
                df = df.nlargest(15, revenue_col)

            # Prepare display columns
            display_cols = ['ticker', 'company_name', 'revenue', 'gross_margin', 'operating_margin', 'earnings_growth']
            display_cols = [c for c in display_cols if c in df.columns]

            if 'edtech_category' in df.columns and 'category' not in df.columns:
                df['category'] = df['edtech_category']

            if 'category' in df.columns and 'category' not in display_cols:
                display_cols.insert(2, 'category')

            df_display = df[display_cols].copy()

            # Format revenue
            if 'revenue' in df_display.columns:
                df_display['revenue'] = df_display['revenue'].apply(
                    lambda x: f"${x/1e6:.1f}M" if pd.notna(x) else "-"
                )

            # Format margins
            for col in ['gross_margin', 'operating_margin', 'earnings_growth']:
                if col in df_display.columns:
                    df_display[col] = df_display[col].apply(
                        lambda x: f"{x:.1f}%" if pd.notna(x) else "-"
                    )

            columns = [
                {"name": c.replace('_', ' ').title(), "id": c}
                for c in df_display.columns
            ]

            return DataTable(
                data=df_display.to_dict('records'),
                columns=columns,
                style_cell={'textAlign': 'left', 'padding': '12px'},
                style_header={
                    'backgroundColor': '#2C5282',
                    'color': 'white',
                    'fontWeight': '600',
                },
                sort_action="native",
                filter_action="native",
                page_size=15,
            )

    def run(self, debug: bool = False, port: int = 8050):
        """Run the dashboard application."""
        self.app.run(debug=debug, port=port, host="0.0.0.0")


if __name__ == "__main__":
    dashboard = CorporateIntelDashboard()
    print("🚀 Starting Corporate Intelligence Dashboard...")
    print("📊 Dashboard with REAL DATA visualizations at: http://localhost:8050")
    dashboard.run(debug=True, port=8050)
