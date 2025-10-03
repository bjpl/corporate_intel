"""Tests for health check endpoints."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test suite for health check endpoints."""

    def test_basic_health_check(self, api_client: TestClient):
        """Test basic health check endpoint returns healthy status."""
        response = api_client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data

    def test_health_check_no_auth_required(self, api_client: TestClient):
        """Test health check is accessible without authentication."""
        response = api_client.get("/health")

        assert response.status_code == status.HTTP_200_OK

    def test_health_check_returns_version(self, api_client: TestClient):
        """Test health check includes application version."""
        response = api_client.get("/health")

        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

    def test_health_check_returns_environment(self, api_client: TestClient):
        """Test health check includes environment info."""
        response = api_client.get("/health")

        data = response.json()
        assert "environment" in data
        assert data["environment"] in ["development", "testing", "staging", "production"]

    @pytest.mark.asyncio
    async def test_database_health_check(self, api_client: TestClient):
        """Test database health check endpoint."""
        response = api_client.get("/health/database")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "status" in data
        assert "connection_pool" in data or "database" in data

    @pytest.mark.asyncio
    async def test_cache_health_check(self, api_client: TestClient):
        """Test Redis cache health check endpoint."""
        response = api_client.get("/health/cache")

        # Cache may not be available in test environment
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_503_SERVICE_UNAVAILABLE
        ]

        data = response.json()
        assert "status" in data

    def test_health_endpoints_cors_headers(self, api_client: TestClient):
        """Test health check endpoints return proper CORS headers."""
        response = api_client.get("/health")

        # Check CORS headers are present
        assert "access-control-allow-origin" in [h.lower() for h in response.headers.keys()]

    def test_health_check_response_time(self, api_client: TestClient):
        """Test health check responds quickly."""
        import time

        start = time.time()
        response = api_client.get("/health")
        elapsed = time.time() - start

        assert response.status_code == status.HTTP_200_OK
        assert elapsed < 0.5  # Should respond in under 500ms

    def test_metrics_endpoint_available(self, api_client: TestClient):
        """Test Prometheus metrics endpoint is available."""
        response = api_client.get("/metrics")

        # Metrics endpoint should return Prometheus format
        assert response.status_code == status.HTTP_200_OK
        assert "text/plain" in response.headers.get("content-type", "")

    def test_health_check_json_content_type(self, api_client: TestClient):
        """Test health check returns JSON content type."""
        response = api_client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        assert "application/json" in response.headers.get("content-type", "")

    def test_database_health_when_connected(self, api_client: TestClient, db_session):
        """Test database health check shows healthy when DB is connected."""
        response = api_client.get("/health/database")

        data = response.json()

        # Should indicate healthy connection
        assert data.get("status") in ["healthy", "ok", "connected"]

    def test_multiple_health_checks_consistent(self, api_client: TestClient):
        """Test multiple health checks return consistent results."""
        response1 = api_client.get("/health")
        response2 = api_client.get("/health")
        response3 = api_client.get("/health")

        assert response1.status_code == response2.status_code == response3.status_code

        data1 = response1.json()
        data2 = response2.json()
        data3 = response3.json()

        assert data1["status"] == data2["status"] == data3["status"]
        assert data1["version"] == data2["version"] == data3["version"]
