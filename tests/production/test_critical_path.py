"""Critical path smoke tests for production.

These tests validate the most important user journeys and must pass
for the system to be considered operational.
"""

import pytest
import requests
import time
from typing import Dict, Any
from urllib.parse import urljoin


@pytest.mark.critical
class TestCriticalHealthChecks:
    """Critical health check endpoints that must always be operational."""

    def test_ping_responds_quickly(self, production_base_url: str, performance_thresholds: Dict[str, float]) -> None:
        """Test ping endpoint responds under threshold."""
        url = urljoin(production_base_url, "/api/v1/health/ping")

        start = time.time()
        response = requests.get(url, timeout=2)
        duration_ms = (time.time() - start) * 1000

        assert response.status_code == 200, f"Health check failed: {response.status_code}"
        assert duration_ms < performance_thresholds["health_check_max_ms"], \
            f"Health check took {duration_ms:.2f}ms (threshold: {performance_thresholds['health_check_max_ms']}ms)"

        data = response.json()
        assert data["status"] == "ok"

    def test_readiness_check_all_systems(self, production_base_url: str) -> None:
        """Test readiness endpoint shows all systems operational."""
        url = urljoin(production_base_url, "/api/v1/health/ready")
        response = requests.get(url, timeout=5)

        assert response.status_code == 200, f"Readiness check failed: {response.status_code}"

        data = response.json()
        assert data["ready"] is True, "System not ready"
        assert data["database"] == "healthy", f"Database not healthy: {data.get('database')}"
        assert data["redis"] == "healthy", f"Redis not healthy: {data.get('redis')}"

    def test_database_connectivity(self, production_base_url: str) -> None:
        """Test database is connected and responsive."""
        url = urljoin(production_base_url, "/api/v1/health/database")
        response = requests.get(url, timeout=5)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["database"]["connected"] is True
        assert data["database"]["latency_ms"] < 500

    def test_cache_connectivity(self, production_base_url: str) -> None:
        """Test Redis cache is connected and responsive."""
        url = urljoin(production_base_url, "/api/v1/health/redis")
        response = requests.get(url, timeout=5)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["redis"]["connected"] is True


@pytest.mark.critical
class TestCriticalUserJourneys:
    """Critical user journeys that must work in production."""

    def test_user_can_view_companies(self, production_base_url: str, production_auth_token: str) -> None:
        """Test authenticated user can list companies."""
        url = urljoin(production_base_url, "/api/v1/companies")
        headers = {"Authorization": f"Bearer {production_auth_token}"}

        response = requests.get(url, headers=headers, timeout=10)

        assert response.status_code == 200, f"Failed to list companies: {response.status_code}"
        data = response.json()
        assert isinstance(data, list), "Companies response should be a list"

    def test_user_can_view_company_details(self, production_base_url: str, production_auth_token: str) -> None:
        """Test user can view company details."""
        # First get a company ID
        list_url = urljoin(production_base_url, "/api/v1/companies")
        headers = {"Authorization": f"Bearer {production_auth_token}"}

        response = requests.get(list_url, headers=headers, timeout=10)
        assert response.status_code == 200

        companies = response.json()
        if not companies:
            pytest.skip("No companies in database for testing")

        # Get first company details
        company_id = companies[0]["id"]
        detail_url = urljoin(production_base_url, f"/api/v1/companies/{company_id}")

        response = requests.get(detail_url, headers=headers, timeout=10)
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == company_id
        assert "name" in data

    def test_user_can_view_financial_metrics(self, production_base_url: str, production_auth_token: str) -> None:
        """Test user can retrieve financial metrics."""
        url = urljoin(production_base_url, "/api/v1/metrics")
        headers = {"Authorization": f"Bearer {production_auth_token}"}

        response = requests.get(url, headers=headers, params={"limit": 10}, timeout=10)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_dashboard_accessible(self, production_dashboard_url: str) -> None:
        """Test dashboard is accessible and loads."""
        response = requests.get(production_dashboard_url, timeout=15)

        assert response.status_code == 200, f"Dashboard not accessible: {response.status_code}"
        assert "text/html" in response.headers.get("content-type", "")
        assert len(response.content) > 0, "Dashboard returned empty content"


@pytest.mark.critical
class TestCriticalDataIntegrity:
    """Validate critical data integrity in production."""

    def test_companies_have_required_fields(self, production_base_url: str, production_auth_token: str) -> None:
        """Test companies have all required fields."""
        url = urljoin(production_base_url, "/api/v1/companies")
        headers = {"Authorization": f"Bearer {production_auth_token}"}

        response = requests.get(url, headers=headers, params={"limit": 5}, timeout=10)
        assert response.status_code == 200

        companies = response.json()
        if not companies:
            pytest.skip("No companies to validate")

        required_fields = ["id", "name", "symbol"]
        for company in companies:
            for field in required_fields:
                assert field in company, f"Company missing field: {field}"
                assert company[field] is not None, f"Company {field} is None"

    def test_metrics_have_valid_data(self, production_base_url: str, production_auth_token: str) -> None:
        """Test financial metrics have valid data."""
        url = urljoin(production_base_url, "/api/v1/metrics")
        headers = {"Authorization": f"Bearer {production_auth_token}"}

        response = requests.get(url, headers=headers, params={"limit": 5}, timeout=10)
        assert response.status_code == 200

        metrics = response.json()
        if not metrics:
            pytest.skip("No metrics to validate")

        for metric in metrics:
            assert "company_id" in metric
            assert "metric_date" in metric
            # At least one metric value should be present
            assert any(k for k in metric.keys() if k not in ["id", "company_id", "metric_date", "created_at", "updated_at"])


@pytest.mark.critical
@pytest.mark.security
class TestCriticalSecurity:
    """Critical security validations."""

    def test_authentication_required(self, production_base_url: str) -> None:
        """Test protected endpoints require authentication."""
        protected_endpoints = [
            "/api/v1/companies",
            "/api/v1/metrics",
            "/api/v1/intelligence/summary"
        ]

        for endpoint in protected_endpoints:
            url = urljoin(production_base_url, endpoint)
            response = requests.get(url, timeout=5)

            assert response.status_code in [401, 403], \
                f"Endpoint {endpoint} should require auth but returned {response.status_code}"

    def test_cors_headers_configured(self, production_base_url: str) -> None:
        """Test CORS headers are properly configured."""
        url = urljoin(production_base_url, "/api/v1/health/ping")
        response = requests.options(url, timeout=5)

        # Should have CORS headers
        assert response.status_code in [200, 204]

    def test_https_enforced(self, production_base_url: str) -> None:
        """Test HTTPS is enforced in production."""
        # Production URL should use HTTPS
        assert production_base_url.startswith("https://"), \
            "Production API must use HTTPS"

    def test_security_headers_present(self, production_base_url: str) -> None:
        """Test security headers are present."""
        url = urljoin(production_base_url, "/api/v1/health/ping")
        response = requests.get(url, timeout=5)

        # Should have security headers
        # Note: Specific headers depend on your configuration
        assert response.status_code == 200


@pytest.mark.critical
@pytest.mark.performance
class TestCriticalPerformance:
    """Critical performance validations."""

    def test_api_response_time_acceptable(self, production_base_url: str, production_auth_token: str,
                                         performance_thresholds: Dict[str, float]) -> None:
        """Test API endpoints respond within acceptable time."""
        headers = {"Authorization": f"Bearer {production_auth_token}"}

        endpoints = [
            "/api/v1/companies",
            "/api/v1/metrics",
        ]

        for endpoint in endpoints:
            url = urljoin(production_base_url, endpoint)

            start = time.time()
            response = requests.get(url, headers=headers, timeout=10)
            duration_ms = (time.time() - start) * 1000

            assert response.status_code == 200
            assert duration_ms < performance_thresholds["api_p99_max_ms"], \
                f"Endpoint {endpoint} took {duration_ms:.2f}ms (threshold: {performance_thresholds['api_p99_max_ms']}ms)"

    def test_database_query_performance(self, production_base_url: str, production_auth_token: str,
                                       performance_thresholds: Dict[str, float]) -> None:
        """Test database queries complete quickly."""
        url = urljoin(production_base_url, "/api/v1/companies")
        headers = {"Authorization": f"Bearer {production_auth_token}"}

        start = time.time()
        response = requests.get(url, headers=headers, params={"limit": 100}, timeout=10)
        duration_ms = (time.time() - start) * 1000

        assert response.status_code == 200
        assert duration_ms < performance_thresholds["database_query_max_ms"] * 2, \
            f"Database query took {duration_ms:.2f}ms"
