"""Test dashboard database connectivity with synchronous SQLAlchemy."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from src.core.config import get_settings


def test_sync_database_url_format():
    """Test that sync database URL is properly formatted."""
    settings = get_settings()
    sync_url = settings.sync_database_url

    # Should use postgresql:// (not postgresql+asyncpg://)
    assert sync_url.startswith("postgresql://")
    assert "asyncpg" not in sync_url
    assert settings.POSTGRES_USER in sync_url
    assert settings.POSTGRES_DB in sync_url


def test_create_sync_engine():
    """Test creating a synchronous database engine."""
    settings = get_settings()

    try:
        engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
        assert engine is not None

        # Test basic connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            assert row[0] == 1

    except SQLAlchemyError as e:
        pytest.skip(f"Database not available: {e}")


def test_query_company_performance_mart():
    """Test querying the company performance mart with sync engine."""
    settings = get_settings()

    try:
        engine = create_engine(settings.sync_database_url, pool_pre_ping=True)

        with engine.connect() as conn:
            query = text("""
                SELECT
                    ticker,
                    company_name,
                    edtech_category,
                    latest_revenue
                FROM public_marts.mart_company_performance
                WHERE latest_revenue IS NOT NULL
                ORDER BY latest_revenue DESC
                LIMIT 5
            """)

            result = conn.execute(query)
            companies = [dict(row._mapping) for row in result]

            # If mart exists and has data, verify structure
            if companies:
                assert all('ticker' in c for c in companies)
                assert all('company_name' in c for c in companies)
                assert all('edtech_category' in c for c in companies)

    except SQLAlchemyError as e:
        pytest.skip(f"Mart table not available yet: {e}")


def test_query_with_category_filter():
    """Test querying with category filter (NULL handling)."""
    settings = get_settings()

    try:
        engine = create_engine(settings.sync_database_url, pool_pre_ping=True)

        with engine.connect() as conn:
            # Test NULL category (should return all)
            query = text("""
                SELECT COUNT(*) as count
                FROM public_marts.mart_company_performance
                WHERE (:category IS NULL OR edtech_category = :category)
            """)

            result = conn.execute(query, {"category": None})
            row = result.fetchone()
            total_count = row[0]

            # Test specific category
            result = conn.execute(query, {"category": "k12"})
            row = result.fetchone()
            k12_count = row[0]

            # k12 count should be <= total count
            assert k12_count <= total_count

    except SQLAlchemyError as e:
        pytest.skip(f"Mart table not available yet: {e}")


def test_no_event_loop_conflict():
    """Test that synchronous queries don't conflict with event loops."""
    import asyncio

    settings = get_settings()

    # Create a running event loop (simulating Dash environment)
    async def run_sync_query():
        """Run sync query inside async context (like Dash callback)."""
        engine = create_engine(settings.sync_database_url, pool_pre_ping=True)

        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                return row[0]
        except SQLAlchemyError:
            pytest.skip("Database not available")

    # This should NOT raise "asyncio.run() cannot be called from a running event loop"
    try:
        result = asyncio.run(run_sync_query())
        assert result == 1
    except SQLAlchemyError:
        pytest.skip("Database not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
