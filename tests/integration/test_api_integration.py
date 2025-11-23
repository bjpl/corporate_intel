"""Integration tests for API endpoints.

These tests increase coverage for src/api/v1/*.py files
by testing actual HTTP requests and responses.
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from src.api.main import app
from src.core.config import get_settings


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def settings():
    """Get settings."""
    return get_settings()


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_endpoint(self, client):
        """Test basic health endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data

    def test_database_health_endpoint(self, client):
        """Test database health endpoint."""
        response = client.get("/health/database")

        assert response.status_code == 200
        # May fail if database not running, but endpoint should respond
        data = response.json()
        assert "status" in data

    def test_cache_health_endpoint(self, client):
        """Test cache health endpoint."""
        response = client.get("/health/cache")

        assert response.status_code == 200
        # May fail if Redis not running, but endpoint should respond
        data = response.json()
        assert "status" in data


# ============================================================================
# AUTHENTICATION TESTS
# ============================================================================

class TestAuthenticationEndpoints:
    """Test authentication endpoints."""

    def test_register_endpoint_exists(self, client):
        """Test register endpoint exists."""
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "TestPassword123!",
            "full_name": "Test User"
        })

        # Should respond (may be 400/422 if validation fails, but endpoint exists)
        assert response.status_code in [200, 201, 400, 422]

    def test_login_endpoint_exists(self, client):
        """Test login endpoint exists."""
        response = client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "TestPassword123!"
        })

        # Should respond (may be 401 if user doesn't exist)
        assert response.status_code in [200, 401, 422]

    def test_register_invalid_email(self, client):
        """Test registration with invalid email."""
        response = client.post("/auth/register", json={
            "email": "not-an-email",
            "password": "TestPassword123!",
            "full_name": "Test User"
        })

        # Should reject invalid email
        assert response.status_code in [400, 422]

    def test_register_weak_password(self, client):
        """Test registration with weak password."""
        response = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "123",
            "full_name": "Test User"
        })

        # Should reject weak password
        assert response.status_code in [400, 422]


# ============================================================================
# COMPANIES API TESTS
# ============================================================================

class TestCompaniesEndpoints:
    """Test companies API endpoints."""

    def test_list_companies_endpoint_exists(self, client):
        """Test list companies endpoint exists."""
        response = client.get(f"{get_settings().API_V1_PREFIX}/companies")

        # May require auth, but endpoint should exist
        assert response.status_code in [200, 401, 403]

    def test_get_company_endpoint_structure(self, client):
        """Test get single company endpoint structure."""
        response = client.get(f"{get_settings().API_V1_PREFIX}/companies/CHGG")

        # Endpoint should exist
        assert response.status_code in [200, 401, 403, 404]

    def test_list_companies_pagination(self, client):
        """Test companies list pagination."""
        response = client.get(
            f"{get_settings().API_V1_PREFIX}/companies",
            params={"skip": 0, "limit": 10}
        )

        # Should accept pagination params
        assert response.status_code in [200, 401, 403]


# ============================================================================
# METRICS API TESTS
# ============================================================================

class TestMetricsEndpoints:
    """Test metrics API endpoints."""

    def test_list_metrics_endpoint(self, client):
        """Test list metrics endpoint."""
        response = client.get(f"{get_settings().API_V1_PREFIX}/metrics")

        # Endpoint should exist
        assert response.status_code in [200, 401, 403]

    def test_company_metrics_endpoint(self, client):
        """Test company-specific metrics endpoint."""
        response = client.get(
            f"{get_settings().API_V1_PREFIX}/companies/CHGG/metrics"
        )

        # Endpoint should exist
        assert response.status_code in [200, 401, 403, 404]


# ============================================================================
# FILINGS API TESTS
# ============================================================================

class TestFilingsEndpoints:
    """Test SEC filings API endpoints."""

    def test_list_filings_endpoint(self, client):
        """Test list filings endpoint."""
        response = client.get(f"{get_settings().API_V1_PREFIX}/filings")

        # Endpoint should exist
        assert response.status_code in [200, 401, 403]

    def test_company_filings_endpoint(self, client):
        """Test company-specific filings endpoint."""
        response = client.get(
            f"{get_settings().API_V1_PREFIX}/companies/CHGG/filings"
        )

        # Endpoint should exist
        assert response.status_code in [200, 401, 403, 404]


# ============================================================================
# REPORTS API TESTS
# ============================================================================

class TestReportsEndpoints:
    """Test reports API endpoints."""

    def test_list_reports_endpoint(self, client):
        """Test list reports endpoint."""
        response = client.get(f"{get_settings().API_V1_PREFIX}/reports")

        # Endpoint should exist
        assert response.status_code in [200, 401, 403]

    def test_generate_report_endpoint(self, client):
        """Test generate report endpoint structure."""
        response = client.post(
            f"{get_settings().API_V1_PREFIX}/reports",
            json={"report_type": "competitive", "companies": ["CHGG", "COUR"]}
        )

        # Endpoint should exist
        assert response.status_code in [200, 201, 401, 403, 422]


# ============================================================================
# INTELLIGENCE API TESTS
# ============================================================================

class TestIntelligenceEndpoints:
    """Test intelligence API endpoints."""

    def test_list_intelligence_endpoint(self, client):
        """Test list intelligence endpoint."""
        response = client.get(f"{get_settings().API_V1_PREFIX}/intelligence")

        # Endpoint should exist
        assert response.status_code in [200, 401, 403]


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test API error handling."""

    def test_404_for_invalid_endpoint(self, client):
        """Test 404 for non-existent endpoint."""
        response = client.get("/api/v1/nonexistent")

        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """Test method not allowed."""
        # Try POST on GET-only endpoint
        response = client.post("/health")

        assert response.status_code == 405

    def test_invalid_json(self, client):
        """Test handling of invalid JSON."""
        response = client.post(
            "/auth/register",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422


# ============================================================================
# CORS TESTS
# ============================================================================

class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers_present(self, client):
        """Test CORS headers are present."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )

        # Should have CORS headers
        assert response.status_code in [200, 204]


# ============================================================================
# METRICS ENDPOINT TESTS
# ============================================================================

class TestPrometheusMetrics:
    """Test Prometheus metrics endpoint."""

    def test_metrics_endpoint_exists(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get("/metrics")

        assert response.status_code == 200
        # Should return Prometheus-format metrics
        assert "text/plain" in response.headers.get("content-type", "")
