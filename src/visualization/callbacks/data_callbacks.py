"""
Data Callback Functions
=======================

This module contains callbacks for data fetching, filtering, and KPI updates.

SPARC Design:
- Specification: Handle data retrieval and metric calculations
- Architecture: Synchronous database queries with error handling
- Refinement: Real-time data freshness tracking
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional

import pandas as pd
from dash import Input, Output, html
import dash_bootstrap_components as dbc
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def register_data_callbacks(app, engine: Optional[Engine]):
    """Register data fetching and KPI callbacks.

    Args:
        app: Dash application instance
        engine: SQLAlchemy database engine (can be None if DB unavailable)
    """

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
                from datetime import timezone
                last_updated = datetime.fromisoformat(freshness["last_updated"])
                time_ago = datetime.now(timezone.utc) - last_updated
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
