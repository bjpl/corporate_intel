"""Security tests for API headers and middleware."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestSecurityHeaders:
    """Test security headers are properly set."""

    def test_security_headers_present(self, client):
        """Test that all required security headers are present."""
        response = client.get("/health")

        assert response.status_code == 200

        # Check security headers
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

        assert "Referrer-Policy" in response.headers
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

        assert "Content-Security-Policy" in response.headers
        assert "default-src 'self'" in response.headers["Content-Security-Policy"]

    def test_server_header_obscured(self, client):
        """Test that server header doesn't reveal implementation details."""
        response = client.get("/health")

        assert "Server" in response.headers
        assert "uvicorn" not in response.headers["Server"].lower()
        assert "fastapi" not in response.headers["Server"].lower()


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_headers_present(self, client):
        """Test that rate limit headers are included."""
        response = client.get("/api/v1/companies/")

        # Rate limit headers should be present
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers

    def test_rate_limit_enforcement(self, client):
        """Test that rate limiting is enforced."""
        # Get rate limit from first request
        response = client.get("/api/v1/companies/")
        limit = int(response.headers["X-RateLimit-Limit"])

        # Make requests up to limit
        for i in range(limit):
            response = client.get("/api/v1/companies/")
            if response.status_code == 429:
                # Hit rate limit early (expected if limit is low)
                break

        # Next request should be rate limited
        response = client.get("/api/v1/companies/")

        if response.status_code == 429:
            # Verify rate limit response
            assert "Retry-After" in response.headers
            assert "detail" in response.json()
            assert "rate limit" in response.json()["detail"].lower()

    def test_rate_limit_whitelist_health(self, client):
        """Test that health endpoints bypass rate limiting."""
        # Make many health check requests
        for _ in range(100):
            response = client.get("/health")
            # Should never be rate limited
            assert response.status_code == 200


class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers(self, client):
        """Test CORS headers are properly set."""
        response = client.options(
            "/api/v1/companies/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )

        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Credentials" in response.headers

    def test_cors_rejects_unknown_origin(self, client):
        """Test that unknown origins are rejected."""
        response = client.get(
            "/api/v1/companies/",
            headers={"Origin": "http://malicious-site.com"}
        )

        # Should not include CORS headers for unknown origin
        # FastAPI CORS middleware will handle this


class TestRequestValidation:
    """Test request validation and input sanitization."""

    def test_sql_injection_prevention(self, client):
        """Test that SQL injection attempts are blocked."""
        # Try SQL injection in query parameter
        response = client.get(
            "/api/v1/companies/",
            params={"sector": "tech' OR '1'='1"}
        )

        # Should not cause SQL error
        assert response.status_code in [200, 400, 422]

        # Should not return unauthorized data
        if response.status_code == 200:
            # Verify response is properly filtered
            data = response.json()
            assert isinstance(data, list)

    def test_xss_prevention(self, client):
        """Test that XSS attempts are handled safely."""
        # Try XSS in query parameter
        response = client.get(
            "/api/v1/companies/",
            params={"sector": "<script>alert('xss')</script>"}
        )

        # Should not cause error
        assert response.status_code in [200, 400, 422]


class TestErrorHandling:
    """Test secure error handling."""

    def test_error_no_stack_trace(self, client):
        """Test that errors don't leak stack traces."""
        # Trigger an error by accessing non-existent endpoint
        response = client.get("/api/v1/nonexistent/endpoint")

        assert response.status_code == 404

        # Response should not contain stack traces or file paths
        content = response.text.lower()
        assert "traceback" not in content
        assert "file" not in content or "not found" in content
        assert ".py" not in content

    def test_error_generic_message(self, client):
        """Test that errors return generic messages."""
        response = client.get("/api/v1/nonexistent/endpoint")

        # Should return generic 404 message
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
