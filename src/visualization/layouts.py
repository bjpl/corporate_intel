"""Dashboard layout components and UI structure.

This module contains all the UI layout definitions for the Corporate Intelligence Dashboard.
Separated from callbacks for better maintainability and testability.
"""

from dash import dcc, html
import dash_bootstrap_components as dbc


def create_header() -> dbc.Row:
    """Create dashboard header with title and subtitle."""
    return dbc.Row([
        dbc.Col([
            html.H1([
                html.I(className="fas fa-chart-line me-3"),
                "EdTech Corporate Intelligence Platform"
            ], className="dashboard-title text-white"),
            html.P([
                "Real-time competitive analysis and market intelligence",
                dbc.Badge("Live Data", color="success", className="ms-3"),
            ], className="dashboard-subtitle text-white-50"),
        ], width=12, className="py-4", style={"backgroundColor": "#2C5282"}),
    ], className="mb-4")


def create_data_freshness_banner() -> dbc.Row:
    """Create data freshness alert banner."""
    return dbc.Row([
        dbc.Col([
            dbc.Alert(
                id="data-freshness-alert",
                color="info",
                className="mb-0",
                is_open=False
            ),
        ], width=12),
    ], className="mb-3")


def create_filter_controls() -> dbc.Card:
    """Create filter and control panel."""
    return dbc.Card([
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
                        html.I(className="fas fa-sync me-2"),
                        "Auto-Refresh"
                    ], className="fw-bold"),
                    dbc.Switch(
                        id="auto-refresh-toggle",
                        label="Enable auto-refresh (1 min)",
                        value=False,
                    ),
                ], md=6),
            ]),
        ]),
    ], className="mb-4")


def create_kpi_cards_container() -> dbc.Row:
    """Create container for KPI cards (populated by callback)."""
    return dbc.Row(id="kpi-cards", className="mb-4")


def create_chart_card(
    chart_id: str,
    title: str,
    icon_class: str,
    info_id: str,
    popover_title: str,
    popover_content: list,
    badge_id: str
) -> dbc.Card:
    """Create a reusable chart card component.

    Args:
        chart_id: ID for the chart graph component
        title: Chart title
        icon_class: FontAwesome icon class
        info_id: ID for info button
        popover_title: Title for info popover
        popover_content: Content for info popover
        badge_id: ID for update badge
    """
    return dbc.Card([
        dbc.CardHeader([
            html.Div([
                html.H4([
                    html.I(className=f"{icon_class} me-2"),
                    title
                ], className="d-inline"),
                dbc.Button(
                    html.I(className="fas fa-info-circle"),
                    id=info_id,
                    color="link",
                    size="sm",
                    className="float-end"
                ),
                dbc.Popover([
                    dbc.PopoverHeader(popover_title),
                    dbc.PopoverBody(popover_content),
                ], target=info_id, trigger="hover"),
            ]),
        ]),
        dbc.CardBody([
            dcc.Loading(
                id=f"loading-{chart_id}",
                type="default",
                children=[dcc.Graph(id=chart_id)],
            ),
            dbc.Row([
                dbc.Col([
                    dbc.Badge([
                        html.I(className="fas fa-table me-1"),
                        "Source: mart_company_performance"
                    ], color="info", className="me-2"),
                    dbc.Badge(id=badge_id, color="success"),
                ], className="mt-2"),
            ]),
        ]),
    ])


def create_revenue_chart_card() -> dbc.Card:
    """Create revenue comparison chart card."""
    popover_content = [
        html.P("Shows latest revenue for all tracked companies:"),
        html.Ul([
            html.Li("Companies sorted by revenue (ascending)"),
            html.Li("Color-coded by EdTech category"),
            html.Li("Hover for exact revenue values"),
        ]),
        html.Hr(),
        html.Small([
            html.I(className="fas fa-database me-2"),
            "Data from mart_company_performance"
        ], className="text-muted"),
    ]

    return create_chart_card(
        chart_id="revenue-chart",
        title="Revenue Comparison",
        icon_class="fas fa-chart-bar",
        info_id="info-revenue",
        popover_title="Company Revenue Analysis",
        popover_content=popover_content,
        badge_id="badge-revenue-updated"
    )


def create_margin_chart_card() -> dbc.Card:
    """Create margin comparison chart card."""
    popover_content = [
        html.P("Compares gross and operating margins:"),
        html.Ul([
            html.Li("Top 15 companies by revenue"),
            html.Li("Gross margin (blue) vs Operating margin (green)"),
            html.Li("Grouped bars for easy comparison"),
        ]),
        html.Hr(),
        html.Small([
            html.I(className="fas fa-database me-2"),
            "Data from mart_company_performance"
        ], className="text-muted"),
    ]

    return create_chart_card(
        chart_id="margin-chart",
        title="Margin Comparison",
        icon_class="fas fa-percentage",
        info_id="info-margin",
        popover_title="Profitability Analysis",
        popover_content=popover_content,
        badge_id="badge-margin-updated"
    )


def create_treemap_chart_card() -> dbc.Card:
    """Create market treemap chart card."""
    popover_content = [
        html.P("Hierarchical revenue distribution:"),
        html.Ul([
            html.Li("Categories: EdTech segments"),
            html.Li("Companies: Individual players"),
            html.Li("Size represents revenue"),
            html.Li("Color indicates category"),
        ]),
        html.Hr(),
        html.Small([
            html.I(className="fas fa-database me-2"),
            "Data from mart_company_performance"
        ], className="text-muted"),
    ]

    return create_chart_card(
        chart_id="treemap-chart",
        title="Market Distribution Treemap",
        icon_class="fas fa-sitemap",
        info_id="info-treemap",
        popover_title="Market Segmentation",
        popover_content=popover_content,
        badge_id="badge-treemap-updated"
    )


def create_earnings_chart_card() -> dbc.Card:
    """Create earnings growth distribution chart card."""
    popover_content = [
        html.P("Distribution of earnings growth by category:"),
        html.Ul([
            html.Li("Box plot shows quartiles and outliers"),
            html.Li("Individual points for each company"),
            html.Li("Color-coded by category"),
        ]),
        html.Hr(),
        html.Small([
            html.I(className="fas fa-database me-2"),
            "Data from mart_company_performance"
        ], className="text-muted"),
    ]

    return create_chart_card(
        chart_id="earnings-chart",
        title="Earnings Growth Distribution",
        icon_class="fas fa-chart-area",
        info_id="info-earnings",
        popover_title="Growth Analysis",
        popover_content=popover_content,
        badge_id="badge-earnings-updated"
    )


def create_visualizations_row_1() -> dbc.Row:
    """Create first row of visualizations (Revenue and Margin)."""
    return dbc.Row([
        dbc.Col([create_revenue_chart_card()], md=6, className="mb-4"),
        dbc.Col([create_margin_chart_card()], md=6, className="mb-4"),
    ])


def create_visualizations_row_2() -> dbc.Row:
    """Create second row of visualizations (Treemap and Earnings)."""
    return dbc.Row([
        dbc.Col([create_treemap_chart_card()], md=6, className="mb-4"),
        dbc.Col([create_earnings_chart_card()], md=6, className="mb-4"),
    ])


def create_performance_table_card() -> dbc.Row:
    """Create detailed performance table card."""
    return dbc.Row([
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
    ])


def create_interval_component() -> dcc.Interval:
    """Create interval component for auto-refresh."""
    return dcc.Interval(
        id="interval-component",
        interval=60*1000,  # Update every minute
        n_intervals=0,
        disabled=True  # Start disabled
    )


def create_store_components() -> list:
    """Create store components for data management."""
    return [
        dcc.Store(id="filtered-data"),
        dcc.Store(id="data-freshness"),
    ]


def create_dashboard_layout() -> dbc.Container:
    """Create complete dashboard layout.

    This is the main layout function that assembles all components
    into the final dashboard structure.

    Returns:
        dbc.Container: Complete dashboard layout
    """
    return dbc.Container([
        # Header
        create_header(),

        # Data Freshness Banner
        create_data_freshness_banner(),

        # Filters
        create_filter_controls(),

        # KPI Cards
        create_kpi_cards_container(),

        # Main visualizations - Row 1
        create_visualizations_row_1(),

        # Main visualizations - Row 2
        create_visualizations_row_2(),

        # Detailed Table
        create_performance_table_card(),

        # Interval for auto-refresh
        create_interval_component(),

        # Store components for data
        *create_store_components(),

    ], fluid=True, className="px-4 py-3")
