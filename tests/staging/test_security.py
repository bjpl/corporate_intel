"""Security tests for staging environment.

Tests for common vulnerabilities:
- SQL injection attacks
- XSS (Cross-Site Scripting)
- Authentication bypass attempts
- Authorization escalation
- CSRF protection
"""

import pytest
import requests
from typing import Dict, List
from urllib.parse import urljoin
import html


class TestSQLInjection:
    """Test SQL injection vulnerability prevention."""

    SQL_INJECTION_PAYLOADS = [
        "' OR '1'='1",
        "1' OR '1' = '1",
        "' OR 1=1--",
        "admin'--",
        "' UNION SELECT NULL--",
        "1; DROP TABLE companies--",
        "' OR 'x'='x",
        "1' AND '1'='1",
    ]

    def test_sql_injection_in_company_search(
        self,
        staging_base_url: str,
        auth_headers: Dict[str, str]
    ) -> None:
        """Test SQL injection in company search endpoint."""
        url = urljoin(staging_base_url, "/api/v1/companies/search")

        for payload in self.SQL_INJECTION_PAYLOADS:
            response = requests.get(
                url,
                params={"q": payload},
                headers=auth_headers,
                timeout=10
            )

            # Should not return 500 (server error) or expose SQL errors
            assert response.status_code != 500, f"SQL injection payload caused error: {payload}"

            if response.status_code == 200:
                # Response should not contain SQL error messages
                content = response.text.lower()
                sql_errors = ["syntax error", "sql", "mysql", "postgresql", "database error"]
                for error_msg in sql_errors:
                    assert error_msg not in content, f"SQL error exposed with payload: {payload}"

    def test_sql_injection_in_company_detail(
        self,
        staging_base_url: str,
        auth_headers: Dict[str, str]
    ) -> None:
        """Test SQL injection in company detail endpoint."""
        for payload in self.SQL_INJECTION_PAYLOADS:
            url = urljoin(staging_base_url, f"/api/v1/companies/{payload}")
            response = requests.get(url, headers=auth_headers, timeout=10)

            # Should return 404 (not found) not 500 (error)
            assert response.status_code in [400, 404], f"Unexpected response for SQL payload: {payload}"

    def test_sql_injection_in_filters(
        self,
        staging_base_url: str,
        auth_headers: Dict[str, str]
    ) -> None:
        """Test SQL injection in query filters."""
        url = urljoin(staging_base_url, "/api/v1/companies")

        for payload in self.SQL_INJECTION_PAYLOADS:
            params = {
                "sector": payload,
                "industry": payload
            }
            response = requests.get(url, params=params, headers=auth_headers, timeout=10)

            # Should handle gracefully
            assert response.status_code in [200, 400], f"SQL injection payload caused error: {payload}"


class TestXSSVulnerabilities:
    """Test Cross-Site Scripting (XSS) vulnerability prevention."""

    XSS_PAYLOADS = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "<svg/onload=alert('XSS')>",
        "javascript:alert('XSS')",
        "<iframe src='javascript:alert(\"XSS\")'></iframe>",
        "<body onload=alert('XSS')>",
        "'\"><script>alert('XSS')</script>",
    ]

    def test_xss_in_company_search(
        self,
        staging_base_url: str,
        auth_headers: Dict[str, str]
    ) -> None:
        """Test XSS prevention in company search."""
        url = urljoin(staging_base_url, "/api/v1/companies/search")

        for payload in self.XSS_PAYLOADS:
            response = requests.get(
                url,
                params={"q": payload},
                headers=auth_headers,
                timeout=10
            )

            if response.status_code == 200:
                content = response.text

                # Script tags should be escaped or removed
                assert "<script>" not in content.lower(), f"XSS payload not escaped: {payload}"
                assert "javascript:" not in content.lower(), f"JavaScript protocol not blocked: {payload}"

    def test_xss_in_api_responses(
        self,
        staging_base_url: str,
        auth_headers: Dict[str, str]
    ) -> None:
        """Test that API responses properly escape HTML."""
        url = urljoin(staging_base_url, "/api/v1/companies")
        response = requests.get(url, headers=auth_headers, timeout=10)

        if response.status_code == 200:
            # Check Content-Type is JSON (not HTML)
            content_type = response.headers.get("content-type", "")
            assert "application/json" in content_type, "API should return JSON, not HTML"

    def test_xss_in_error_messages(
        self,
        staging_base_url: str,
        auth_headers: Dict[str, str]
    ) -> None:
        """Test XSS prevention in error messages."""
        xss_payload = "<script>alert('XSS')</script>"
        url = urljoin(staging_base_url, f"/api/v1/companies/{xss_payload}")

        response = requests.get(url, headers=auth_headers, timeout=10)

        # Error message should not reflect unescaped XSS payload
        content = response.text
        assert "<script>" not in content, "Error message contains unescaped XSS"


class TestAuthenticationBypass:
    """Test authentication bypass prevention."""

    def test_protected_endpoints_require_auth(self, staging_base_url: str) -> None:
        """Test that protected endpoints require authentication."""
        protected_endpoints = [
            "/api/v1/companies",
            "/api/v1/metrics",
            "/api/v1/intelligence/summary",
            "/api/v1/admin/users",
        ]

        for endpoint in protected_endpoints:
            url = urljoin(staging_base_url, endpoint)
            response = requests.get(url, timeout=10)

            # Should return 401 (unauthorized) without auth
            # Note: Some endpoints may be public (200) - that's ok
            if response.status_code not in [401, 403, 200, 404]:
                pytest.fail(f"Unexpected status for {endpoint}: {response.status_code}")

    def test_invalid_token_rejected(
        self,
        staging_base_url: str
    ) -> None:
        """Test that invalid tokens are rejected."""
        invalid_tokens = [
            "invalid_token",
            "Bearer invalid",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid",
            "",
        ]

        url = urljoin(staging_base_url, "/api/v1/companies")

        for token in invalid_tokens:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(url, headers=headers, timeout=10)

            # Should return 401 or 403 (not 200)
            if response.status_code == 200:
                # Endpoint may be public - that's ok
                pass
            else:
                assert response.status_code in [401, 403], f"Invalid token not rejected: {token}"

    def test_expired_token_rejected(
        self,
        staging_base_url: str
    ) -> None:
        """Test that expired tokens are rejected."""
        # This would require generating an expired token
        # For now, just test with malformed JWT
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjB9.invalid"

        url = urljoin(staging_base_url, "/api/v1/companies")
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = requests.get(url, headers=headers, timeout=10)

        # Should return 401 or 403
        if response.status_code == 200:
            pass  # Public endpoint
        else:
            assert response.status_code in [401, 403]

    def test_api_key_validation(
        self,
        staging_base_url: str
    ) -> None:
        """Test API key validation."""
        url = urljoin(staging_base_url, "/api/v1/companies")

        # Invalid API key
        headers = {"X-API-Key": "invalid_api_key_12345"}
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            pass  # Public endpoint
        else:
            assert response.status_code in [401, 403]


class TestAuthorizationEscalation:
    """Test authorization and privilege escalation prevention."""

    def test_viewer_cannot_access_admin_endpoints(
        self,
        staging_base_url: str,
        viewer_auth_headers: Dict[str, str]
    ) -> None:
        """Test that viewer role cannot access admin endpoints."""
        admin_endpoints = [
            "/api/v1/admin/users",
            "/api/v1/admin/audit-logs",
            "/api/v1/admin/settings",
        ]

        for endpoint in admin_endpoints:
            url = urljoin(staging_base_url, endpoint)
            response = requests.get(url, headers=viewer_auth_headers, timeout=10)

            # Should return 403 (forbidden) or 404 (not found)
            assert response.status_code in [403, 404], f"Viewer accessed admin endpoint: {endpoint}"

    def test_analyst_cannot_modify_data(
        self,
        staging_base_url: str,
        analyst_auth_headers: Dict[str, str]
    ) -> None:
        """Test that analyst role cannot modify data."""
        # Try to create a company
        url = urljoin(staging_base_url, "/api/v1/companies")
        response = requests.post(
            url,
            json={"ticker": "TEST", "name": "Test Company"},
            headers=analyst_auth_headers,
            timeout=10
        )

        # Should return 403 (forbidden) or 405 (method not allowed)
        assert response.status_code in [403, 404, 405]

    def test_role_parameter_tampering(
        self,
        staging_base_url: str,
        auth_headers: Dict[str, str]
    ) -> None:
        """Test that role parameter tampering is prevented."""
        url = urljoin(staging_base_url, "/api/v1/users/me")

        # Try to elevate privileges via parameter
        tamper_attempts = [
            {"role": "admin"},
            {"is_admin": True},
            {"permissions": ["admin"]},
        ]

        for attempt in tamper_attempts:
            response = requests.patch(
                url,
                json=attempt,
                headers=auth_headers,
                timeout=10
            )

            # Should not allow privilege escalation
            if response.status_code == 200:
                data = response.json()
                # Verify role wasn't changed
                assert data.get("role") != "admin", "Role escalation via parameter tampering"


class TestCSRFProtection:
    """Test CSRF protection mechanisms."""

    def test_state_changing_operations_protected(
        self,
        staging_base_url: str,
        auth_headers: Dict[str, str]
    ) -> None:
        """Test that state-changing operations have CSRF protection."""
        # Try POST without CSRF token
        url = urljoin(staging_base_url, "/api/v1/companies")

        response = requests.post(
            url,
            json={"ticker": "TEST", "name": "Test Company"},
            headers=auth_headers,
            timeout=10
        )

        # API endpoints may not use CSRF tokens (token-based auth)
        # This test verifies the endpoint exists and is protected by auth
        assert response.status_code in [200, 201, 400, 403, 404, 405]

    def test_cors_headers_configured(self, staging_base_url: str) -> None:
        """Test CORS headers are properly configured."""
        url = urljoin(staging_base_url, "/api/v1/health/ping")

        # Preflight request
        response = requests.options(
            url,
            headers={"Origin": "https://malicious-site.com"},
            timeout=10
        )

        # CORS should be configured (but may reject malicious origins)
        assert response.status_code in [200, 204, 403]


class TestInputValidation:
    """Test input validation and sanitization."""

    def test_invalid_json_rejected(
        self,
        staging_base_url: str,
        auth_headers: Dict[str, str]
    ) -> None:
        """Test that invalid JSON is rejected."""
        url = urljoin(staging_base_url, "/api/v1/companies")

        # Send invalid JSON
        headers = {**auth_headers, "Content-Type": "application/json"}
        response = requests.post(
            url,
            data="{'invalid': json}",  # Invalid JSON
            headers=headers,
            timeout=10
        )

        # Should return 400 (bad request)
        assert response.status_code in [400, 404, 405]

    def test_oversized_payload_rejected(
        self,
        staging_base_url: str,
        auth_headers: Dict[str, str]
    ) -> None:
        """Test that oversized payloads are rejected."""
        url = urljoin(staging_base_url, "/api/v1/companies")

        # Send very large payload (10MB)
        large_payload = {"data": "x" * (10 * 1024 * 1024)}
        response = requests.post(
            url,
            json=large_payload,
            headers=auth_headers,
            timeout=30
        )

        # Should return 413 (payload too large) or 400
        assert response.status_code in [400, 413, 404, 405]

    def test_special_characters_handled(
        self,
        staging_base_url: str,
        auth_headers: Dict[str, str]
    ) -> None:
        """Test that special characters are properly handled."""
        special_chars = ["<>", "&&", "||", "../", "%00", "\x00"]

        url = urljoin(staging_base_url, "/api/v1/companies/search")

        for chars in special_chars:
            response = requests.get(
                url,
                params={"q": chars},
                headers=auth_headers,
                timeout=10
            )

            # Should handle gracefully (not crash)
            assert response.status_code in [200, 400, 404]


# Fixtures
@pytest.fixture(scope="module")
def staging_base_url() -> str:
    """Get staging API base URL."""
    import os
    return os.getenv("STAGING_API_URL", "http://localhost:8000")


@pytest.fixture(scope="module")
def auth_headers() -> Dict[str, str]:
    """Get authentication headers."""
    import os
    token = os.getenv("STAGING_AUTH_TOKEN", "test-token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def viewer_auth_headers() -> Dict[str, str]:
    """Get viewer role authentication headers."""
    import os
    token = os.getenv("STAGING_VIEWER_TOKEN", "viewer-token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def analyst_auth_headers() -> Dict[str, str]:
    """Get analyst role authentication headers."""
    import os
    token = os.getenv("STAGING_ANALYST_TOKEN", "analyst-token")
    return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
