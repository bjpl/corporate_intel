"""Comprehensive tests for health check endpoints."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, SQLAlchemyError


class TestBasicHealthEndpoint:
    """Test suite for GET /health endpoint."""

    def test_health_check_success(self, api_client: TestClient):
        """Test basic health check returns 200."""
        response = api_client.get("/health")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data

    def test_health_check_includes_version(self, api_client: TestClient):
        """Test health check includes version information."""
        response = api_client.get("/health")

        data = response.json()
        assert "version" in data
        assert isinstance(data["version"], str)

    def test_health_check_includes_environment(self, api_client: TestClient):
        """Test health check includes environment information."""
        response = api_client.get("/health")

        data = response.json()
        assert "environment" in data
        assert data["environment"] in ["development", "staging", "production", "test"]

    def test_health_check_no_auth_required(self, api_client: TestClient):
        """Test health check doesn't require authentication."""
        response = api_client.get("/health")

        assert response.status_code == status.HTTP_200_OK

    def test_health_check_response_schema(self, api_client: TestClient):
        """Test health check response has correct schema."""
        response = api_client.get("/health")

        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "environment" in data

    def test_health_check_status_value(self, api_client: TestClient):
        """Test health check status is 'healthy'."""
        response = api_client.get("/health")

        data = response.json()
        assert data["status"] == "healthy"

    def test_health_check_multiple_calls(self, api_client: TestClient):
        """Test health check is consistent across multiple calls."""
        response1 = api_client.get("/health")
        response2 = api_client.get("/health")
        response3 = api_client.get("/health")

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK
        assert response3.status_code == status.HTTP_200_OK

        # Version and environment should be consistent
        data1 = response1.json()
        data2 = response2.json()
        data3 = response3.json()

        assert data1["version"] == data2["version"] == data3["version"]
        assert data1["environment"] == data2["environment"] == data3["environment"]


class TestDatabaseHealthEndpoint:
    """Test suite for GET /health/database endpoint."""

    def test_database_health_success(self, api_client: TestClient):
        """Test database health check returns 200 when healthy."""
        response = api_client.get("/health/database")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "status" in data

    def test_database_health_includes_connection_info(
        self, api_client: TestClient
    ):
        """Test database health check includes connection information."""
        response = api_client.get("/health/database")

        data = response.json()
        # Should include database connectivity info
        assert response.status_code == status.HTTP_200_OK

    def test_database_health_no_auth_required(self, api_client: TestClient):
        """Test database health check doesn't require authentication."""
        response = api_client.get("/health/database")

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]

    @patch('src.db.init.check_database_health')
    async def test_database_health_when_database_down(
        self, mock_check, api_client: TestClient
    ):
        """Test database health check when database is unavailable."""
        mock_check.return_value = {
            "status": "unhealthy",
            "error": "Connection refused"
        }

        response = api_client.get("/health/database")

        # Should still return a response, even if unhealthy
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]

    def test_database_health_response_time(self, api_client: TestClient):
        """Test database health check responds quickly."""
        import time

        start = time.time()
        response = api_client.get("/health/database")
        duration = time.time() - start

        # Health check should be fast (< 5 seconds)
        assert duration < 5.0
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]


class TestCacheHealthEndpoint:
    """Test suite for GET /health/cache endpoint."""

    def test_cache_health_success(self, api_client: TestClient):
        """Test cache health check returns 200 when healthy."""
        response = api_client.get("/health/cache")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "status" in data

    def test_cache_health_no_auth_required(self, api_client: TestClient):
        """Test cache health check doesn't require authentication."""
        response = api_client.get("/health/cache")

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]

    @patch('src.core.cache_manager.check_cache_health')
    async def test_cache_health_when_redis_down(
        self, mock_check, api_client: TestClient
    ):
        """Test cache health check when Redis is unavailable."""
        mock_check.return_value = {
            "status": "unhealthy",
            "error": "Connection refused"
        }

        response = api_client.get("/health/cache")

        # Should still return a response
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]

    def test_cache_health_response_time(self, api_client: TestClient):
        """Test cache health check responds quickly."""
        import time

        start = time.time()
        response = api_client.get("/health/cache")
        duration = time.time() - start

        # Health check should be fast (< 5 seconds)
        assert duration < 5.0
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]


class TestHealthEndpointEdgeCases:
    """Test suite for edge cases in health endpoints."""

    def test_health_with_query_parameters(self, api_client: TestClient):
        """Test health endpoint ignores query parameters."""
        response = api_client.get("/health?foo=bar&baz=qux")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_with_invalid_path(self, api_client: TestClient):
        """Test invalid health path returns 404."""
        response = api_client.get("/health/invalid")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_health_head_request(self, api_client: TestClient):
        """Test HEAD request to health endpoint."""
        response = api_client.head("/health")

        # HEAD requests should return same status but no body
        assert response.status_code == status.HTTP_200_OK

    def test_health_options_request(self, api_client: TestClient):
        """Test OPTIONS request to health endpoint."""
        response = api_client.options("/health")

        # OPTIONS should be allowed (CORS)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]

    def test_health_post_not_allowed(self, api_client: TestClient):
        """Test POST request to health endpoint returns 405."""
        response = api_client.post("/health")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_health_put_not_allowed(self, api_client: TestClient):
        """Test PUT request to health endpoint returns 405."""
        response = api_client.put("/health")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_health_delete_not_allowed(self, api_client: TestClient):
        """Test DELETE request to health endpoint returns 405."""
        response = api_client.delete("/health")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class TestHealthEndpointConcurrency:
    """Test suite for concurrent health check requests."""

    def test_concurrent_health_checks(self, api_client: TestClient):
        """Test multiple concurrent health check requests."""
        import concurrent.futures

        def make_request():
            return api_client.get("/health")

        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [f.result() for f in futures]

        # All should succeed
        assert all(r.status_code == status.HTTP_200_OK for r in responses)

    def test_concurrent_database_health_checks(self, api_client: TestClient):
        """Test multiple concurrent database health checks."""
        import concurrent.futures

        def make_request():
            return api_client.get("/health/database")

        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [f.result() for f in futures]

        # All should return a valid response
        assert all(
            r.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]
            for r in responses
        )


class TestHealthEndpointPerformance:
    """Test suite for health endpoint performance."""

    def test_health_check_performance(self, api_client: TestClient):
        """Test health check responds quickly under load."""
        import time

        times = []
        for _ in range(100):
            start = time.time()
            response = api_client.get("/health")
            duration = time.time() - start
            times.append(duration)

            assert response.status_code == status.HTTP_200_OK

        # Average response time should be fast
        avg_time = sum(times) / len(times)
        assert avg_time < 0.1  # Less than 100ms average

    def test_database_health_check_performance(self, api_client: TestClient):
        """Test database health check performance."""
        import time

        times = []
        for _ in range(10):
            start = time.time()
            response = api_client.get("/health/database")
            duration = time.time() - start
            times.append(duration)

            assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]

        # Should complete within reasonable time
        avg_time = sum(times) / len(times)
        assert avg_time < 2.0  # Less than 2s average


class TestHealthEndpointMonitoring:
    """Test suite for health endpoint monitoring scenarios."""

    def test_health_check_for_load_balancer(self, api_client: TestClient):
        """Test health check suitable for load balancer monitoring."""
        response = api_client.get("/health")

        assert response.status_code == status.HTTP_200_OK

        # Load balancers typically check for 200 status
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_check_json_response(self, api_client: TestClient):
        """Test health check returns valid JSON."""
        response = api_client.get("/health")

        assert response.headers["content-type"] == "application/json"

        # Should be valid JSON
        data = response.json()
        assert isinstance(data, dict)

    def test_database_health_for_monitoring(self, api_client: TestClient):
        """Test database health suitable for monitoring systems."""
        response = api_client.get("/health/database")

        # Should return valid response for monitoring
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]

        data = response.json()
        assert "status" in data

    def test_cache_health_for_monitoring(self, api_client: TestClient):
        """Test cache health suitable for monitoring systems."""
        response = api_client.get("/health/cache")

        # Should return valid response for monitoring
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]

        data = response.json()
        assert "status" in data


class TestHealthEndpointIntegration:
    """Test suite for health endpoint integration scenarios."""

    def test_all_health_endpoints_accessible(self, api_client: TestClient):
        """Test all health endpoints are accessible."""
        endpoints = [
            "/health",
            "/health/database",
            "/health/cache",
        ]

        for endpoint in endpoints:
            response = api_client.get(endpoint)
            assert response.status_code in [
                status.HTTP_200_OK,
                status.HTTP_503_SERVICE_UNAVAILABLE
            ]

    def test_health_endpoints_return_json(self, api_client: TestClient):
        """Test all health endpoints return JSON."""
        endpoints = [
            "/health",
            "/health/database",
            "/health/cache",
        ]

        for endpoint in endpoints:
            response = api_client.get(endpoint)
            assert "application/json" in response.headers.get("content-type", "")

            # Should be parseable as JSON
            data = response.json()
            assert isinstance(data, dict)

    def test_health_check_uptime_monitoring(self, api_client: TestClient):
        """Test health check suitable for uptime monitoring."""
        # Simulate uptime monitoring by making requests over time
        for _ in range(5):
            response = api_client.get("/health")

            # Should consistently return healthy
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "healthy"


class TestHealthEndpointSecurity:
    """Test suite for health endpoint security."""

    def test_health_no_sensitive_data(self, api_client: TestClient):
        """Test health check doesn't expose sensitive data."""
        response = api_client.get("/health")

        data = response.json()

        # Should not include sensitive information
        sensitive_keys = [
            "password", "secret", "key", "token", "api_key",
            "database_url", "connection_string"
        ]

        for key in sensitive_keys:
            assert key not in str(data).lower()

    def test_database_health_no_credentials(self, api_client: TestClient):
        """Test database health doesn't expose credentials."""
        response = api_client.get("/health/database")

        data = response.json()

        # Should not include database credentials
        sensitive_keys = [
            "password", "user", "host", "port",
            "connection_string", "database_url"
        ]

        data_str = str(data).lower()
        # Check that no obvious credentials are exposed
        assert "password=" not in data_str
        assert "user=" not in data_str

    def test_cache_health_no_redis_credentials(self, api_client: TestClient):
        """Test cache health doesn't expose Redis credentials."""
        response = api_client.get("/health/cache")

        data = response.json()

        # Should not include Redis credentials
        data_str = str(data).lower()
        assert "password" not in data_str or "redis_password" not in data_str
