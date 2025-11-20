"""
Navigation and Chart Callback Functions
=======================================

This module contains callbacks for chart updates and view navigation.

SPARC Design:
- Specification: Update charts and tables based on data changes
- Architecture: Reactive chart rendering with empty state handling
- Refinement: Responsive updates with loading states
"""

import logging
from typing import Any, Dict, List, Tuple, Optional

import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, html
from dash.dash_table import DataTable
import dash_bootstrap_components as dbc
from sqlalchemy.engine import Engine

from src.visualization.components.tables import (
    create_earnings_growth_distribution,
    create_margin_comparison_chart,
    create_revenue_by_category_treemap,
    create_revenue_comparison_bar,
)

logger = logging.getLogger(__name__)


def register_navigation_callbacks(app, engine: Optional[Engine]):
    """Register chart and table update callbacks.

    Args:
        app: Dash application instance
        engine: SQLAlchemy database engine (can be None if DB unavailable)
    """

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
