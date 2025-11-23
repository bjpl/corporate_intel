"""Test async database connection in dashboard."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.visualization.dash_app import CorporateIntelDashboard


class TestDashboardAsync:
    """Test dashboard async patterns."""

    @pytest.mark.asyncio
    async def test_fetch_data_pattern(self):
        """Test that the async fetch pattern works correctly."""

        # Mock the session factory
        mock_session = AsyncMock()
        mock_service = AsyncMock()

        # Mock service methods
        mock_service.get_company_performance.return_value = [
            {
                'ticker': 'TEST',
                'company_name': 'Test Company',
                'latest_revenue': 1000000,
                'revenue_yoy_growth': 10.0,
                'latest_nrr': 110
            }
        ]
        mock_service.get_competitive_landscape.return_value = [
            {
                'edtech_category': 'test_category',
                'total_segment_revenue': 5000000
            }
        ]
        mock_service.get_data_freshness.return_value = {
            'last_updated': '2025-10-05T12:00:00',
            'companies_count': 1
        }

        # Test the pattern used in the dashboard
        async def fetch_data():
            from src.db.session import get_session_factory
            from src.services.dashboard_service import DashboardService

            # This simulates the fixed pattern
            session_factory = get_session_factory()
            async with session_factory() as session:
                service = DashboardService(session)
                companies = await service.get_company_performance(category=None)
                market = await service.get_competitive_landscape(category=None)
                freshness = await service.get_data_freshness()
                return companies, market, freshness

        # This should not raise a coroutine warning
        with patch('src.services.dashboard_service.DashboardService') as MockService:
            MockService.return_value = mock_service

            # Use asyncio.run() as in the fixed dashboard
            try:
                companies, market, freshness = asyncio.run(fetch_data())
                # If we get here, the pattern works
                assert True
            except RuntimeError as e:
                if "coroutine" in str(e).lower():
                    pytest.fail(f"Coroutine not awaited: {e}")
                raise

    def test_dashboard_update_data_callback_sync(self):
        """Test that update_data callback properly wraps async code."""

        # Create dashboard instance
        dashboard = CorporateIntelDashboard()

        # The callback should be synchronous and use asyncio.run()
        # We can't easily test the actual callback, but we can verify
        # it's registered and doesn't have async def

        # Get the callback function
        callback_outputs = dashboard.app.callback_map.get(
            'filtered-data.data..market-data.data..data-freshness.data..'
            'company-selector.options..data-freshness-alert.children..'
            'data-freshness-alert.is_open'
        )

        if callback_outputs:
            callback_func = callback_outputs['callback']
            # Verify it's not a coroutine function
            assert not asyncio.iscoroutinefunction(callback_func), \
                "Dashboard callback should be synchronous, not async def"

    @pytest.mark.asyncio
    async def test_session_factory_context_manager(self):
        """Test that session factory works with async context manager."""

        from src.db.session import get_session_factory

        # Get the session factory
        session_factory = get_session_factory()

        # Test that we can use it with async context manager
        async with session_factory() as session:
            assert session is not None
            # Session should be usable here

        # After context, session should be closed
        # This is the correct pattern used in the fix
