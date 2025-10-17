"""Dashboard callback functions and data logic.

This module contains all Dash callbacks that handle user interactions
and data updates for the Corporate Intelligence Dashboard.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, html
from dash.dash_table import DataTable
import dash_bootstrap_components as dbc
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine

from src.visualization.components import (
    create_earnings_growth_distribution,
    create_margin_comparison_chart,
    create_revenue_by_category_treemap,
    create_revenue_comparison_bar,
)

logger = logging.getLogger(__name__)


def register_callbacks(app, engine: Optional[Engine]):
    """Register all dashboard callbacks.

    Args:
        app: Dash application instance
        engine: SQLAlchemy database engine (can be None if DB unavailable)
    """

    @app.callback(
        Output("interval-component", "disabled"),
        Input("auto-refresh-toggle", "value")
    )
    def toggle_auto_refresh(auto_refresh: bool) -> bool:
        """Enable/disable auto-refresh based on toggle state.

        Args:
            auto_refresh: Boolean state of auto-refresh toggle

        Returns:
            bool: Inverted state (disabled = not auto_refresh)
        """
        return not auto_refresh

    @app.callback(
        [Output("filtered-data", "data"),
         Output("data-freshness", "data"),
         Output("data-freshness-alert", "children"),
         Output("data-freshness-alert", "is_open")],
        [Input("category-filter", "value"),
         Input("interval-component", "n_intervals")]
    )
    def update_data(
        category: str,
        n_intervals: int
    ) -> Tuple[List[Dict], Dict, List, bool]:
        """Fetch and filter data based on selections using synchronous database queries.

        Args:
            category: Selected category filter value
            n_intervals: Auto-refresh interval counter

        Returns:
            Tuple containing:
                - List of company data dictionaries
                - Data freshness metadata
                - Alert content HTML elements
                - Boolean to show/hide alert
        """
        try:
            # Only attempt database queries if engine is available
            if engine is None:
                raise SQLAlchemyError("Database engine not initialized")

            with engine.connect() as conn:
                # Query company performance data from mart
                category_filter = None if category == "all" else category

                company_query = text("""
                    SELECT
                        ticker,
                        company_name,
                        edtech_category,
                        latest_revenue,
                        latest_gross_margin,
                        latest_operating_margin,
                        latest_profit_margin,
                        revenue_yoy_growth,
                        earnings_growth,
                        overall_score,
                        company_health_status,
                        revenue_rank_in_category,
                        revenue_rank_overall
                    FROM public_marts.mart_company_performance
                    WHERE (:category IS NULL OR edtech_category = :category)
                    ORDER BY latest_revenue DESC NULLS LAST
                """)

                company_result = conn.execute(
                    company_query,
                    {"category": category_filter}
                )
                companies_data = [dict(row._mapping) for row in company_result]

                # Query data freshness
                freshness_query = text("""
                    SELECT
                        MAX(refreshed_at) as last_updated,
                        COUNT(DISTINCT ticker) as companies_count
                    FROM public_marts.mart_company_performance
                """)

                freshness_result = conn.execute(freshness_query)
                freshness_row = freshness_result.fetchone()

                if freshness_row and freshness_row[0]:
                    freshness = {
                        "last_updated": freshness_row[0].isoformat() if freshness_row[0] else None,
                        "companies_count": freshness_row[1] or 0
                    }
                else:
                    freshness = {}

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
                    html.Span(
                        f" | {freshness.get('companies_count', 0)} companies tracked",
                        className="ms-3"
                    ),
                ]
                show_alert = True
            else:
                alert_content = [
                    html.I(className="fas fa-exclamation-triangle me-2"),
                    "No data available. Run data ingestion to populate dashboard.",
                ]
                show_alert = True

            logger.info(f"Successfully fetched {len(companies_data)} companies from database")
            return companies_data, freshness, alert_content, show_alert

        except (SQLAlchemyError, Exception) as e:
            # Log the error
            logger.error(f"Database query failed: {e}", exc_info=True)

            alert_content = [
                html.I(className="fas fa-database me-2"),
                "Database connection error. Please check your connection.",
            ]

            return [], {}, alert_content, True

    @app.callback(
        Output("kpi-cards", "children"),
        Input("filtered-data", "data")
    )
    def update_kpis(companies_data: List[Dict]) -> List:
        """Update KPI cards with real data.

        Args:
            companies_data: List of company data dictionaries

        Returns:
            List of dbc.Col components containing KPI cards
        """
        if not companies_data:
            return [
                dbc.Col([
                    dbc.Alert([
                        html.I(className="fas fa-exclamation-circle me-2"),
                        "No data available. Please run data ingestion first."
                    ], color="warning")
                ], width=12)
            ]

        df = pd.DataFrame(companies_data)

        # Calculate KPIs from real data
        total_revenue = df['latest_revenue'].fillna(0).sum() / 1e9
        avg_gross_margin = df['latest_gross_margin'].fillna(0).mean()
        avg_operating_margin = df['latest_operating_margin'].fillna(0).mean()
        companies_with_earnings = df['earnings_growth'].notna().sum()

        kpi_cards = [
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-dollar-sign fa-2x text-primary mb-3"),
                            html.H6("Total Revenue", className="text-muted mb-2"),
                            html.H3(f"${total_revenue:.2f}B", className="mb-1 fw-bold text-primary"),
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
                            html.H6("Avg Gross Margin", className="text-muted mb-2"),
                            html.H3(f"{avg_gross_margin:.1f}%", className="mb-1 fw-bold text-success"),
                        ]),
                        html.Hr(className="my-2"),
                        html.Small([
                            html.I(className="fas fa-info-circle me-1"),
                            "Average across all companies"
                        ], className="text-muted"),
                    ]),
                ], className="h-100 border-start border-success border-4"),
            ], lg=3, md=6, className="mb-3"),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-percentage fa-2x text-info mb-3"),
                            html.H6("Avg Operating Margin", className="text-muted mb-2"),
                            html.H3(f"{avg_operating_margin:.1f}%", className="mb-1 fw-bold text-info"),
                        ]),
                        html.Hr(className="my-2"),
                        html.Small([
                            html.I(className="fas fa-info-circle me-1"),
                            "Operating efficiency metric"
                        ], className="text-muted"),
                    ]),
                ], className="h-100 border-start border-info border-4"),
            ], lg=3, md=6, className="mb-3"),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.I(className="fas fa-building fa-2x text-warning mb-3"),
                            html.H6("Companies with Earnings", className="text-muted mb-2"),
                            html.H3(f"{companies_with_earnings}", className="mb-1 fw-bold text-warning"),
                        ]),
                        html.Hr(className="my-2"),
                        html.Small([
                            html.I(className="fas fa-info-circle me-1"),
                            "Companies reporting earnings growth"
                        ], className="text-muted"),
                    ]),
                ], className="h-100 border-start border-warning border-4"),
            ], lg=3, md=6, className="mb-3"),
        ]

        return kpi_cards

    @app.callback(
        [Output("revenue-chart", "figure"),
         Output("badge-revenue-updated", "children")],
        [Input("filtered-data", "data"),
         Input("data-freshness", "data")]
    )
    def update_revenue_chart(
        companies_data: List[Dict],
        freshness: Dict
    ) -> Tuple[go.Figure, List]:
        """Update revenue comparison chart.

        Args:
            companies_data: List of company data dictionaries
            freshness: Data freshness metadata

        Returns:
            Tuple of (figure, badge_content)
        """
        if not companies_data:
            empty_fig = go.Figure()
            empty_fig.add_annotation(
                text="No data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=20, color="gray")
            )
            empty_fig.update_layout(template="plotly_white", height=400)
            return empty_fig, "No data"

        # Prepare DataFrame with correct column names
        df = pd.DataFrame(companies_data)
        df = df.rename(columns={
            'latest_revenue': 'revenue',
            'edtech_category': 'category'
        })

        figure = create_revenue_comparison_bar(df)

        badge_content = [html.I(className="fas fa-clock me-1"), "Updated recently"]
        return figure, badge_content

    @app.callback(
        [Output("margin-chart", "figure"),
         Output("badge-margin-updated", "children")],
        [Input("filtered-data", "data"),
         Input("data-freshness", "data")]
    )
    def update_margin_chart(
        companies_data: List[Dict],
        freshness: Dict
    ) -> Tuple[go.Figure, List]:
        """Update margin comparison chart.

        Args:
            companies_data: List of company data dictionaries
            freshness: Data freshness metadata

        Returns:
            Tuple of (figure, badge_content)
        """
        if not companies_data:
            empty_fig = go.Figure()
            empty_fig.add_annotation(
                text="No data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=20, color="gray")
            )
            empty_fig.update_layout(template="plotly_white", height=400)
            return empty_fig, "No data"

        df = pd.DataFrame(companies_data)
        df = df.rename(columns={
            'latest_revenue': 'revenue',
            'latest_gross_margin': 'gross_margin',
            'latest_operating_margin': 'operating_margin'
        })

        figure = create_margin_comparison_chart(df, top_n=15)

        badge_content = [html.I(className="fas fa-clock me-1"), "Updated recently"]
        return figure, badge_content

    @app.callback(
        [Output("treemap-chart", "figure"),
         Output("badge-treemap-updated", "children")],
        [Input("filtered-data", "data"),
         Input("data-freshness", "data")]
    )
    def update_treemap_chart(
        companies_data: List[Dict],
        freshness: Dict
    ) -> Tuple[go.Figure, List]:
        """Update market treemap chart.

        Args:
            companies_data: List of company data dictionaries
            freshness: Data freshness metadata

        Returns:
            Tuple of (figure, badge_content)
        """
        if not companies_data:
            empty_fig = go.Figure()
            empty_fig.add_annotation(
                text="No data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=20, color="gray")
            )
            empty_fig.update_layout(template="plotly_white", height=400)
            return empty_fig, "No data"

        df = pd.DataFrame(companies_data)
        df = df.rename(columns={
            'latest_revenue': 'revenue',
            'edtech_category': 'category'
        })

        figure = create_revenue_by_category_treemap(df)

        badge_content = [html.I(className="fas fa-clock me-1"), "Updated recently"]
        return figure, badge_content

    @app.callback(
        [Output("earnings-chart", "figure"),
         Output("badge-earnings-updated", "children")],
        [Input("filtered-data", "data"),
         Input("data-freshness", "data")]
    )
    def update_earnings_chart(
        companies_data: List[Dict],
        freshness: Dict
    ) -> Tuple[go.Figure, List]:
        """Update earnings growth distribution chart.

        Args:
            companies_data: List of company data dictionaries
            freshness: Data freshness metadata

        Returns:
            Tuple of (figure, badge_content)
        """
        if not companies_data:
            empty_fig = go.Figure()
            empty_fig.add_annotation(
                text="No data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=20, color="gray")
            )
            empty_fig.update_layout(template="plotly_white", height=400)
            return empty_fig, "No data"

        df = pd.DataFrame(companies_data)
        df = df.rename(columns={
            'edtech_category': 'category'
        })

        figure = create_earnings_growth_distribution(df)

        badge_content = [html.I(className="fas fa-clock me-1"), "Updated recently"]
        return figure, badge_content

    @app.callback(
        Output("performance-table", "children"),
        Input("filtered-data", "data")
    )
    def update_performance_table(companies_data: List[Dict]):
        """Update performance details table.

        Args:
            companies_data: List of company data dictionaries

        Returns:
            DataTable component or Alert component
        """
        if not companies_data:
            return dbc.Alert([
                html.I(className="fas fa-exclamation-triangle me-2"),
                "No data available. Please run data ingestion first."
            ], color="warning")

        df = pd.DataFrame(companies_data)

        # Sort by revenue and take all companies
        df = df.sort_values('latest_revenue', ascending=False, na_position='last')

        if df.empty:
            return dbc.Alert([
                html.I(className="fas fa-info-circle me-2"),
                "No companies match the current filters."
            ], color="info")

        # Format columns for display
        display_columns = [
            'ticker', 'company_name', 'edtech_category',
            'latest_revenue', 'latest_gross_margin', 'latest_operating_margin',
            'revenue_yoy_growth', 'earnings_growth', 'overall_score', 'company_health_status'
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
        df_display['latest_gross_margin'] = df_display['latest_gross_margin'].apply(
            lambda x: f"{x:.1f}%" if pd.notna(x) else "-"
        )
        df_display['latest_operating_margin'] = df_display['latest_operating_margin'].apply(
            lambda x: f"{x:.1f}%" if pd.notna(x) else "-"
        )
        df_display['revenue_yoy_growth'] = df_display['revenue_yoy_growth'].apply(
            lambda x: f"{x:.1f}%" if pd.notna(x) else "-"
        )
        df_display['earnings_growth'] = df_display['earnings_growth'].apply(
            lambda x: f"{x:.1f}%" if pd.notna(x) else "-"
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
                {"name": "Gross Margin", "id": "latest_gross_margin"},
                {"name": "Operating Margin", "id": "latest_operating_margin"},
                {"name": "YoY Growth", "id": "revenue_yoy_growth"},
                {"name": "Earnings Growth", "id": "earnings_growth"},
                {"name": "Score", "id": "overall_score"},
                {"name": "Health Status", "id": "company_health_status"},
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
                },
                {
                    'if': {
                        'filter_query': '{company_health_status} = "Excellent"',
                        'column_id': 'company_health_status'
                    },
                    'backgroundColor': '#d4edda',
                    'color': '#155724',
                },
                {
                    'if': {
                        'filter_query': '{company_health_status} = "At Risk"',
                        'column_id': 'company_health_status'
                    },
                    'backgroundColor': '#f8d7da',
                    'color': '#721c24',
                },
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
            page_size=20,
            page_action="native",
        )
