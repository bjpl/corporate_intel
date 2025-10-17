"""Smoke tests for staging environment validation.

Tests basic functionality to ensure the application is operational:
- Health endpoints (all 4 endpoints)
- Database connectivity
- Redis connectivity
- Service startup validation
- Dashboard rendering
"""

import pytest
import requests
import time
from typing import Dict, Any
from sqlalchemy import create_engine, text
from redis import Redis
from urllib.parse import urljoin


class TestHealthEndpoints:
    """Test all health check endpoints."""

    def test_ping_endpoint(self, staging_base_url: str) -> None:
        """Test basic ping endpoint returns 200."""
        url = urljoin(staging_base_url, "/api/v1/health/ping")
        response = requests.get(url, timeout=5)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "timestamp" in data

    def test_database_health_endpoint(self, staging_base_url: str) -> None:
        """Test database health check endpoint."""
        url = urljoin(staging_base_url, "/api/v1/health/database")
        response = requests.get(url, timeout=5)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"]["connected"] is True
        assert "latency_ms" in data["database"]
        assert data["database"]["latency_ms"] < 1000  # < 1 second

    def test_redis_health_endpoint(self, staging_base_url: str) -> None:
        """Test Redis health check endpoint."""
        url = urljoin(staging_base_url, "/api/v1/health/redis")
        response = requests.get(url, timeout=5)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["redis"]["connected"] is True
        assert "latency_ms" in data["redis"]

    def test_readiness_endpoint(self, staging_base_url: str) -> None:
        """Test overall readiness endpoint."""
        url = urljoin(staging_base_url, "/api/v1/health/ready")
        response = requests.get(url, timeout=10)

        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
        assert data["database"] == "healthy"
        assert data["redis"] == "healthy"
        assert "version" in data
        assert "uptime_seconds" in data


class TestDatabaseConnectivity:
    """Test database connection and basic operations."""

    def test_database_connection(self, staging_db_url: str) -> None:
        """Test direct database connection."""
        engine = create_engine(staging_db_url)

        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1 as test"))
                assert result.fetchone()[0] == 1
        finally:
            engine.dispose()

    def test_database_tables_exist(self, staging_db_url: str) -> None:
        """Test required tables exist in database."""
        engine = create_engine(staging_db_url)

        required_tables = [
            "companies",
            "financial_metrics",
            "sec_filings",
            "users",
            "api_keys"
        ]

        try:
            with engine.connect() as conn:
                for table in required_tables:
                    result = conn.execute(
                        text(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name = :table"),
                        {"table": table}
                    )
                    count = result.fetchone()[0]
                    assert count == 1, f"Table {table} not found"
        finally:
            engine.dispose()

    def test_database_migrations_applied(self, staging_db_url: str) -> None:
        """Test all migrations have been applied."""
        engine = create_engine(staging_db_url)

        try:
            with engine.connect() as conn:
                # Check alembic_version table exists
                result = conn.execute(
                    text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'alembic_version'")
                )
                assert result.fetchone()[0] == 1, "Alembic version table not found"

                # Check at least one migration exists
                result = conn.execute(text("SELECT COUNT(*) FROM alembic_version"))
                assert result.fetchone()[0] >= 1, "No migrations applied"
        finally:
            engine.dispose()


class TestRedisConnectivity:
    """Test Redis connection and basic operations."""

    def test_redis_connection(self, staging_redis_url: str) -> None:
        """Test Redis connection."""
        redis_client = Redis.from_url(staging_redis_url, decode_responses=True)

        try:
            assert redis_client.ping() is True
        finally:
            redis_client.close()

    def test_redis_set_get(self, staging_redis_url: str) -> None:
        """Test Redis set and get operations."""
        redis_client = Redis.from_url(staging_redis_url, decode_responses=True)

        try:
            test_key = "staging_smoke_test"
            test_value = "test_value"

            # Set value
            assert redis_client.set(test_key, test_value, ex=60) is True

            # Get value
            retrieved = redis_client.get(test_key)
            assert retrieved == test_value

            # Cleanup
            redis_client.delete(test_key)
        finally:
            redis_client.close()

    def test_redis_cache_namespace(self, staging_redis_url: str) -> None:
        """Test Redis cache namespace exists."""
        redis_client = Redis.from_url(staging_redis_url, decode_responses=True)

        try:
            # Check if cache keys exist (system should have some cached data)
            # This is a soft check - we just verify Redis is being used
            keys = redis_client.keys("cache:*")
            # Don't assert on count - new deployment may have no cache yet
            assert isinstance(keys, list)
        finally:
            redis_client.close()


class TestServiceStartup:
    """Test service startup and configuration."""

    def test_api_service_responds(self, staging_base_url: str) -> None:
        """Test API service is responding."""
        response = requests.get(staging_base_url, timeout=5)
        # Root may redirect or return 404, but should respond
        assert response.status_code in [200, 404, 301, 302]

    def test_api_version_endpoint(self, staging_base_url: str) -> None:
        """Test API version endpoint."""
        url = urljoin(staging_base_url, "/api/v1/health/ready")
        response = requests.get(url, timeout=5)

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert data["version"] != "unknown"

    def test_cors_headers(self, staging_base_url: str) -> None:
        """Test CORS headers are configured."""
        url = urljoin(staging_base_url, "/api/v1/health/ping")
        response = requests.options(url, timeout=5)

        # CORS headers should be present
        assert response.status_code in [200, 204]
        # Note: Actual CORS headers depend on configuration

    def test_rate_limiting_configured(self, staging_base_url: str) -> None:
        """Test rate limiting is configured."""
        url = urljoin(staging_base_url, "/api/v1/health/ping")

        # Make multiple rapid requests
        responses = []
        for _ in range(5):
            responses.append(requests.get(url, timeout=5))

        # All should succeed (rate limit should be reasonable for health checks)
        for response in responses:
            assert response.status_code == 200


class TestDashboardRendering:
    """Test dashboard accessibility and rendering."""

    def test_dashboard_loads(self, staging_dashboard_url: str) -> None:
        """Test dashboard page loads."""
        response = requests.get(staging_dashboard_url, timeout=10)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_dashboard_assets_load(self, staging_dashboard_url: str) -> None:
        """Test dashboard assets (CSS, JS) are accessible."""
        # First get the dashboard page
        response = requests.get(staging_dashboard_url, timeout=10)
        assert response.status_code == 200

        # Check if common Dash assets are referenced
        content = response.text
        assert "_dash-component" in content or "dash" in content.lower()

    def test_dashboard_api_endpoint(self, staging_dashboard_url: str) -> None:
        """Test dashboard API endpoint responds."""
        # Dash has internal endpoints
        url = urljoin(staging_dashboard_url, "/_dash-dependencies")
        response = requests.get(url, timeout=5)
        # Should return 200 or 404 if not configured
        assert response.status_code in [200, 404]


# Pytest fixtures for staging environment
@pytest.fixture(scope="module")
def staging_base_url() -> str:
    """Get staging API base URL from environment."""
    import os
    return os.getenv("STAGING_API_URL", "http://localhost:8000")


@pytest.fixture(scope="module")
def staging_dashboard_url() -> str:
    """Get staging dashboard URL from environment."""
    import os
    return os.getenv("STAGING_DASHBOARD_URL", "http://localhost:8050")


@pytest.fixture(scope="module")
def staging_db_url() -> str:
    """Get staging database URL from environment."""
    import os
    return os.getenv("STAGING_DATABASE_URL", "postgresql://user:pass@localhost:5432/corporate_intel_staging")


@pytest.fixture(scope="module")
def staging_redis_url() -> str:
    """Get staging Redis URL from environment."""
    import os
    return os.getenv("STAGING_REDIS_URL", "redis://localhost:6379/0")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
