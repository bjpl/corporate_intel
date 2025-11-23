"""Pytest configuration for production smoke tests."""

import pytest
import os
from typing import Dict


@pytest.fixture(scope="session")
def production_base_url() -> str:
    """Get production API base URL from environment."""
    url = os.getenv("PRODUCTION_API_URL")
    if not url:
        pytest.skip("PRODUCTION_API_URL not set - skipping production tests")
    return url


@pytest.fixture(scope="session")
def production_dashboard_url() -> str:
    """Get production dashboard URL from environment."""
    url = os.getenv("PRODUCTION_DASHBOARD_URL")
    if not url:
        pytest.skip("PRODUCTION_DASHBOARD_URL not set - skipping production tests")
    return url


@pytest.fixture(scope="session")
def production_db_url() -> str:
    """Get production database URL from environment (read-only recommended)."""
    url = os.getenv("PRODUCTION_DATABASE_URL")
    if not url:
        pytest.skip("PRODUCTION_DATABASE_URL not set - skipping production tests")
    return url


@pytest.fixture(scope="session")
def production_monitoring_url() -> str:
    """Get production monitoring URL (Grafana/Prometheus)."""
    return os.getenv("PRODUCTION_MONITORING_URL", "")


@pytest.fixture(scope="session")
def production_auth_token() -> str:
    """Get production authentication token for API testing."""
    token = os.getenv("PRODUCTION_AUTH_TOKEN")
    if not token:
        pytest.skip("PRODUCTION_AUTH_TOKEN not set - skipping authenticated tests")
    return token


@pytest.fixture(scope="session")
def performance_thresholds() -> Dict[str, float]:
    """Define performance thresholds for production."""
    return {
        "health_check_max_ms": 100,
        "api_p95_max_ms": 500,
        "api_p99_max_ms": 1000,
        "database_query_max_ms": 200,
        "cache_hit_min_ratio": 0.7,
        "error_rate_max": 0.01,  # 1%
        "uptime_min": 0.999,  # 99.9%
    }


@pytest.fixture(scope="session")
def alert_webhook() -> str:
    """Webhook URL for test failure alerts."""
    return os.getenv("ALERT_WEBHOOK_URL", "")


def pytest_configure(config):
    """Configure pytest for production tests."""
    config.addinivalue_line(
        "markers", "critical: mark test as critical path (must pass)"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as performance validation"
    )
    config.addinivalue_line(
        "markers", "security: mark test as security validation"
    )


def pytest_collection_modifyitems(config, items):
    """Add markers to tests based on their names."""
    for item in items:
        if "critical" in item.nodeid:
            item.add_marker(pytest.mark.critical)
        if "performance" in item.nodeid:
            item.add_marker(pytest.mark.performance)
        if "security" in item.nodeid:
            item.add_marker(pytest.mark.security)
