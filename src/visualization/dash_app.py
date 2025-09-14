"""Plotly Dash application for corporate intelligence visualization."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, State, callback, dcc, html
from dash.dash_table import DataTable
from plotly.subplots import make_subplots

from src.core.config import get_settings
from src.visualization.components import (
    create_cohort_heatmap,
    create_competitive_landscape_scatter,
    create_market_share_sunburst,
    create_metrics_waterfall,
    create_retention_curves,
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
        )
        self._setup_layout()
        self._register_callbacks()
    
    def _setup_layout(self):
        """Create dashboard layout."""
        self.app.layout = html.Div([
            # Header
            html.Div([
                html.H1("EdTech Corporate Intelligence Platform", 
                       className="dashboard-title"),
                html.P("Real-time competitive analysis and market intelligence",
                      className="dashboard-subtitle"),
            ], className="header"),
            
            # Filters
            html.Div([
                html.Div([
                    html.Label("EdTech Category"),
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
                        className="dropdown"
                    ),
                ], className="filter-group"),
                
                html.Div([
                    html.Label("Time Period"),
                    dcc.Dropdown(
                        id="period-filter",
                        options=[
                            {"label": "Last Quarter", "value": "1Q"},
                            {"label": "Last 2 Quarters", "value": "2Q"},
                            {"label": "Last Year", "value": "4Q"},
                            {"label": "Last 2 Years", "value": "8Q"},
                        ],
                        value="4Q",
                        className="dropdown"
                    ),
                ], className="filter-group"),
                
                html.Div([
                    html.Label("Comparison Companies"),
                    dcc.Dropdown(
                        id="company-selector",
                        options=[],  # Populated dynamically
                        value=[],
                        multi=True,
                        placeholder="Select companies to compare",
                        className="dropdown"
                    ),
                ], className="filter-group"),
            ], className="filters-container"),
            
            # KPI Cards
            html.Div(id="kpi-cards", className="kpi-container"),
            
            # Main visualizations
            html.Div([
                # Row 1: Market Overview
                html.Div([
                    html.Div([
                        html.H3("Competitive Landscape"),
                        dcc.Graph(id="competitive-landscape-chart"),
                    ], className="chart-container half"),
                    
                    html.Div([
                        html.H3("Market Share Distribution"),
                        dcc.Graph(id="market-share-chart"),
                    ], className="chart-container half"),
                ], className="chart-row"),
                
                # Row 2: Performance Metrics
                html.Div([
                    html.Div([
                        html.H3("Revenue Waterfall Analysis"),
                        dcc.Graph(id="waterfall-chart"),
                    ], className="chart-container half"),
                    
                    html.Div([
                        html.H3("Segment Performance Radar"),
                        dcc.Graph(id="radar-chart"),
                    ], className="chart-container half"),
                ], className="chart-row"),
                
                # Row 3: Retention & Cohorts
                html.Div([
                    html.Div([
                        html.H3("Retention Curves"),
                        dcc.Graph(id="retention-curves-chart"),
                    ], className="chart-container half"),
                    
                    html.Div([
                        html.H3("Cohort Analysis Heatmap"),
                        dcc.Graph(id="cohort-heatmap"),
                    ], className="chart-container half"),
                ], className="chart-row"),
                
                # Row 4: Detailed Table
                html.Div([
                    html.H3("Company Performance Details"),
                    html.Div(id="performance-table"),
                ], className="chart-container full"),
            ], className="charts-container"),
            
            # Interval for auto-refresh
            dcc.Interval(
                id="interval-component",
                interval=60*1000,  # Update every minute
                n_intervals=0
            ),
            
            # Store components for data
            dcc.Store(id="filtered-data"),
            dcc.Store(id="market-data"),
        ])
    
    def _register_callbacks(self):
        """Register dashboard callbacks."""
        
        @self.app.callback(
            [Output("filtered-data", "data"),
             Output("market-data", "data"),
             Output("company-selector", "options")],
            [Input("category-filter", "value"),
             Input("period-filter", "value"),
             Input("interval-component", "n_intervals")]
        )
        def update_data(category, period, n_intervals):
            """Fetch and filter data based on selections."""
            # In production, this would query the database
            # For now, using sample data structure
            
            companies_df = self._fetch_company_performance(category, period)
            market_df = self._fetch_market_data(category, period)
            
            company_options = [
                {"label": f"{row['ticker']} - {row['company_name']}", 
                 "value": row['ticker']}
                for _, row in companies_df.iterrows()
            ]
            
            return companies_df.to_dict(), market_df.to_dict(), company_options
        
        @self.app.callback(
            Output("kpi-cards", "children"),
            [Input("filtered-data", "data"),
             Input("market-data", "data")]
        )
        def update_kpis(companies_data, market_data):
            """Update KPI cards."""
            if not companies_data:
                return []
            
            companies_df = pd.DataFrame(companies_data)
            market_df = pd.DataFrame(market_data)
            
            # Calculate KPIs
            total_revenue = companies_df['latest_revenue'].sum() / 1e9  # In billions
            avg_growth = companies_df['revenue_yoy_growth'].mean()
            avg_nrr = companies_df['latest_nrr'].mean()
            total_users = companies_df['latest_mau'].sum() / 1e6  # In millions
            
            kpi_cards = [
                self._create_kpi_card("Total Market Revenue", f"${total_revenue:.1f}B", "+12.3%"),
                self._create_kpi_card("Avg YoY Growth", f"{avg_growth:.1f}%", "+2.1pp"),
                self._create_kpi_card("Avg Net Revenue Retention", f"{avg_nrr:.0f}%", "+5pp"),
                self._create_kpi_card("Total Active Users", f"{total_users:.1f}M", "+18.5%"),
            ]
            
            return kpi_cards
        
        @self.app.callback(
            Output("competitive-landscape-chart", "figure"),
            [Input("filtered-data", "data"),
             Input("company-selector", "value")]
        )
        def update_competitive_landscape(companies_data, selected_companies):
            """Update competitive landscape scatter plot."""
            if not companies_data:
                return go.Figure()
            
            df = pd.DataFrame(companies_data)
            
            # Highlight selected companies
            df['selected'] = df['ticker'].isin(selected_companies)
            
            return create_competitive_landscape_scatter(df, selected_companies)
        
        @self.app.callback(
            Output("market-share-chart", "figure"),
            [Input("market-data", "data"),
             Input("category-filter", "value")]
        )
        def update_market_share(market_data, category):
            """Update market share sunburst chart."""
            if not market_data:
                return go.Figure()
            
            df = pd.DataFrame(market_data)
            return create_market_share_sunburst(df, category)
        
        @self.app.callback(
            Output("waterfall-chart", "figure"),
            [Input("filtered-data", "data"),
             Input("company-selector", "value")]
        )
        def update_waterfall(companies_data, selected_companies):
            """Update revenue waterfall chart."""
            if not companies_data or not selected_companies:
                return go.Figure()
            
            df = pd.DataFrame(companies_data)
            company_data = df[df['ticker'] == selected_companies[0]] if selected_companies else None
            
            if company_data is None or company_data.empty:
                return go.Figure()
            
            return create_metrics_waterfall(company_data.iloc[0])
        
        @self.app.callback(
            Output("performance-table", "children"),
            [Input("filtered-data", "data"),
             Input("company-selector", "value")]
        )
        def update_performance_table(companies_data, selected_companies):
            """Update performance details table."""
            if not companies_data:
                return html.Div("No data available")
            
            df = pd.DataFrame(companies_data)
            
            # Filter for selected companies or show top 10
            if selected_companies:
                df = df[df['ticker'].isin(selected_companies)]
            else:
                df = df.nlargest(10, 'latest_revenue')
            
            # Format columns
            display_columns = [
                'ticker', 'company_name', 'edtech_category',
                'latest_revenue', 'revenue_yoy_growth', 'latest_nrr',
                'latest_mau', 'latest_arpu', 'overall_score'
            ]
            
            df_display = df[display_columns].copy()
            
            # Format numbers
            df_display['latest_revenue'] = df_display['latest_revenue'].apply(
                lambda x: f"${x/1e6:.1f}M" if pd.notna(x) else "-"
            )
            df_display['revenue_yoy_growth'] = df_display['revenue_yoy_growth'].apply(
                lambda x: f"{x:.1f}%" if pd.notna(x) else "-"
            )
            df_display['latest_nrr'] = df_display['latest_nrr'].apply(
                lambda x: f"{x:.0f}%" if pd.notna(x) else "-"
            )
            df_display['latest_mau'] = df_display['latest_mau'].apply(
                lambda x: f"{x/1e3:.0f}K" if pd.notna(x) else "-"
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
                    'padding': '10px',
                    'fontFamily': 'Arial',
                },
                style_data_conditional=[
                    {
                        'if': {'column_id': 'overall_score'},
                        'backgroundColor': '#e6f3ff',
                        'fontWeight': 'bold',
                    }
                ],
                style_header={
                    'backgroundColor': '#1e3a5f',
                    'color': 'white',
                    'fontWeight': 'bold',
                },
                sort_action="native",
                filter_action="native",
                page_size=10,
            )
    
    def _create_kpi_card(self, title: str, value: str, change: str) -> html.Div:
        """Create a KPI card component."""
        change_color = "green" if change.startswith("+") else "red"
        
        return html.Div([
            html.H4(title, className="kpi-title"),
            html.H2(value, className="kpi-value"),
            html.P(change, className=f"kpi-change {change_color}"),
        ], className="kpi-card")
    
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
        self.app.run_server(debug=debug, port=port, host="0.0.0.0")