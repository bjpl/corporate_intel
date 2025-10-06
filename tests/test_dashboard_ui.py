"""Test suite for dashboard UI components and functionality.

This test suite verifies that the modernized dashboard:
1. Initializes without errors
2. Has all required components
3. Callbacks are properly registered
4. UI elements are accessible
"""

import pytest
from dash import Dash
from dash.testing.application_runners import import_app

from src.visualization.dash_app import CorporateIntelDashboard


class TestDashboardInitialization:
    """Test dashboard initialization and setup."""

    def test_dashboard_creates_app(self):
        """Test that dashboard initializes Dash app."""
        dashboard = CorporateIntelDashboard()
        assert isinstance(dashboard.app, Dash)
        assert dashboard.app.title == "Corporate Intelligence Platform"

    def test_dashboard_has_bootstrap_theme(self):
        """Test that Bootstrap theme is loaded."""
        dashboard = CorporateIntelDashboard()
        external_stylesheets = dashboard.app.config.external_stylesheets

        # Check for COSMO theme and Font Awesome
        assert any("COSMO" in str(s) or "cosmo" in str(s) for s in external_stylesheets)
        assert any("FONT_AWESOME" in str(s) or "font-awesome" in str(s) for s in external_stylesheets)

    def test_dashboard_layout_exists(self):
        """Test that layout is properly set."""
        dashboard = CorporateIntelDashboard()
        assert dashboard.app.layout is not None


class TestDashboardComponents:
    """Test dashboard UI components."""

    @pytest.fixture
    def dashboard(self):
        """Create dashboard instance for testing."""
        return CorporateIntelDashboard()

    def test_filter_components_exist(self, dashboard):
        """Test that filter components are in layout."""
        layout_str = str(dashboard.app.layout)

        # Check for filter component IDs
        assert "category-filter" in layout_str
        assert "period-filter" in layout_str
        assert "company-selector" in layout_str

    def test_kpi_cards_container_exists(self, dashboard):
        """Test that KPI cards container exists."""
        layout_str = str(dashboard.app.layout)
        assert "kpi-cards" in layout_str

    def test_visualization_charts_exist(self, dashboard):
        """Test that all visualization charts are present."""
        layout_str = str(dashboard.app.layout)

        expected_charts = [
            "competitive-landscape-chart",
            "market-share-chart",
            "waterfall-chart",
            "radar-chart",
            "retention-curves-chart",
            "cohort-heatmap",
        ]

        for chart_id in expected_charts:
            assert chart_id in layout_str, f"Missing chart: {chart_id}"

    def test_performance_table_exists(self, dashboard):
        """Test that performance table component exists."""
        layout_str = str(dashboard.app.layout)
        assert "performance-table" in layout_str

    def test_loading_components_exist(self, dashboard):
        """Test that loading components are present."""
        layout_str = str(dashboard.app.layout)

        # Check for loading wrappers
        assert "loading-competitive" in layout_str
        assert "loading-market-share" in layout_str
        assert "loading-waterfall" in layout_str
        assert "loading-radar" in layout_str
        assert "loading-retention" in layout_str
        assert "loading-cohort" in layout_str
        assert "loading-table" in layout_str

    def test_info_popovers_exist(self, dashboard):
        """Test that info popovers are present for charts."""
        layout_str = str(dashboard.app.layout)

        # Check for info button IDs
        assert "info-competitive" in layout_str
        assert "info-market-share" in layout_str
        assert "info-waterfall" in layout_str
        assert "info-radar" in layout_str
        assert "info-retention" in layout_str
        assert "info-cohort" in layout_str

    def test_data_source_badges_exist(self, dashboard):
        """Test that data source badges are present."""
        layout_str = str(dashboard.app.layout)

        # Check for badge component IDs
        assert "badge-competitive-updated" in layout_str
        assert "badge-market-share-updated" in layout_str

    def test_data_freshness_alert_exists(self, dashboard):
        """Test that data freshness alert component exists."""
        layout_str = str(dashboard.app.layout)
        assert "data-freshness-alert" in layout_str


class TestDashboardCallbacks:
    """Test dashboard callbacks are registered."""

    @pytest.fixture
    def dashboard(self):
        """Create dashboard instance for testing."""
        return CorporateIntelDashboard()

    def test_callbacks_registered(self, dashboard):
        """Test that callbacks are registered."""
        callbacks = dashboard.app.callback_map
        assert len(callbacks) > 0

    def test_data_update_callback_exists(self, dashboard):
        """Test that main data update callback is registered."""
        callbacks = dashboard.app.callback_map

        # Check for filtered-data output (main data callback)
        assert any("filtered-data.data" in str(cb) for cb in callbacks.keys())

    def test_kpi_callback_exists(self, dashboard):
        """Test that KPI cards callback is registered."""
        callbacks = dashboard.app.callback_map

        # Check for kpi-cards output
        assert any("kpi-cards.children" in str(cb) for cb in callbacks.keys())

    def test_chart_callbacks_exist(self, dashboard):
        """Test that all chart update callbacks are registered."""
        callbacks = dashboard.app.callback_map
        callback_str = str(callbacks.keys())

        expected_outputs = [
            "competitive-landscape-chart.figure",
            "market-share-chart.figure",
            "waterfall-chart.figure",
            "radar-chart.figure",
            "retention-curves-chart.figure",
            "cohort-heatmap.figure",
        ]

        for output in expected_outputs:
            assert output in callback_str, f"Missing callback for: {output}"


class TestDashboardAccessibility:
    """Test accessibility features."""

    @pytest.fixture
    def dashboard(self):
        """Create dashboard instance for testing."""
        return CorporateIntelDashboard()

    def test_icons_present(self, dashboard):
        """Test that Font Awesome icons are used."""
        layout_str = str(dashboard.app.layout)

        # Check for icon classes
        assert "fas fa-" in layout_str or "fa-" in layout_str

    def test_semantic_html_structure(self, dashboard):
        """Test that semantic HTML elements are used."""
        layout_str = str(dashboard.app.layout)

        # Check for Bootstrap semantic classes
        assert "card" in layout_str.lower()
        assert "container" in layout_str.lower()
        assert "row" in layout_str.lower()

    def test_responsive_classes(self, dashboard):
        """Test that responsive grid classes are used."""
        layout_str = str(dashboard.app.layout)

        # Check for responsive column classes
        assert "md=" in layout_str or "lg=" in layout_str


class TestDashboardFallback:
    """Test fallback data methods."""

    @pytest.fixture
    def dashboard(self):
        """Create dashboard instance for testing."""
        return CorporateIntelDashboard()

    def test_fetch_company_performance_fallback(self, dashboard):
        """Test fallback company data method."""
        df = dashboard._fetch_company_performance("all", "4Q")

        assert not df.empty
        assert "ticker" in df.columns
        assert "company_name" in df.columns
        assert "latest_revenue" in df.columns

    def test_fetch_market_data_fallback(self, dashboard):
        """Test fallback market data method."""
        df = dashboard._fetch_market_data("all", "4Q")

        assert not df.empty
        assert "edtech_category" in df.columns
        assert "total_segment_revenue" in df.columns

    def test_category_filter_works(self, dashboard):
        """Test that category filtering works in fallback."""
        df_all = dashboard._fetch_company_performance("all", "4Q")
        df_k12 = dashboard._fetch_company_performance("k12", "4Q")

        assert len(df_k12) <= len(df_all)
        if len(df_k12) > 0:
            assert all(df_k12["edtech_category"] == "k12")


class TestDashboardIntegration:
    """Integration tests for dashboard functionality."""

    def test_dashboard_runs_without_errors(self):
        """Test that dashboard initializes and runs without errors."""
        try:
            dashboard = CorporateIntelDashboard()
            # If we get here, initialization succeeded
            assert True
        except Exception as e:
            pytest.fail(f"Dashboard initialization failed: {e}")

    def test_sample_data_loads(self):
        """Test that sample data can be loaded."""
        dashboard = CorporateIntelDashboard()

        # Test fallback data methods
        companies = dashboard._fetch_company_performance("all", "4Q")
        market = dashboard._fetch_market_data("all", "4Q")

        assert not companies.empty
        assert not market.empty


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
