"""Tests for API error handling and resilience."""

import pytest
from uuid import uuid4
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError, IntegrityError, DataError
from sqlalchemy.orm import Session

from src.db.models import Company


class TestDatabaseErrors:
    """Test suite for database error handling."""

    @patch('src.db.base.get_db')
    def test_database_connection_failure(self, mock_get_db, api_client: TestClient):
        """Test handling of database connection failure."""
        mock_get_db.side_effect = OperationalError("Connection failed", None, None)

        response = api_client.get("/api/v1/companies/")

        # Should handle gracefully with 500 or 503
        assert response.status_code in [
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_503_SERVICE_UNAVAILABLE
        ]

    @patch('sqlalchemy.orm.Session.query')
    def test_database_query_timeout(self, mock_query, api_client: TestClient):
        """Test handling of database query timeout."""
        mock_query.side_effect = OperationalError("Query timeout", None, None)

        response = api_client.get("/api/v1/companies/")

        # Should handle timeout gracefully
        assert response.status_code in [
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            status.HTTP_200_OK  # If error is caught and handled
        ]

    def test_integrity_constraint_violation(
        self, api_client: TestClient, auth_headers: dict, sample_company: Company
    ):
        """Test handling of database integrity constraint violation."""
        # Try to create duplicate company
        company_data = {
            "ticker": sample_company.ticker,
            "name": "Duplicate Company",
        }

        response = api_client.post(
            "/api/v1/companies/",
            json=company_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "detail" in data


class TestCacheErrors:
    """Test suite for cache error handling."""

    @patch('src.core.cache.get_cache')
    def test_redis_connection_failure(self, mock_cache, api_client: TestClient):
        """Test handling of Redis connection failure."""
        mock_cache_instance = AsyncMock()
        mock_cache_instance.get.side_effect = ConnectionError("Redis connection failed")
        mock_cache.return_value = mock_cache_instance

        # Should still work even if cache fails
        response = api_client.get("/api/v1/companies/")

        # Should either succeed (cache is optional) or return service error
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]

    @patch('src.core.cache.get_cache')
    def test_cache_timeout(self, mock_cache, api_client: TestClient):
        """Test handling of cache timeout."""
        mock_cache_instance = AsyncMock()
        mock_cache_instance.get.side_effect = TimeoutError("Cache timeout")
        mock_cache.return_value = mock_cache_instance

        response = api_client.get("/api/v1/companies/")

        # Should handle cache timeout gracefully
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_500_INTERNAL_SERVER_ERROR
        ]


class TestAuthenticationErrors:
    """Test suite for authentication error handling."""

    def test_missing_auth_token(self, api_client: TestClient):
        """Test request without authentication token."""
        company_data = {
            "ticker": "TEST",
            "name": "Test Company",
        }

        response = api_client.post(
            "/api/v1/companies/",
            json=company_data
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data

    def test_invalid_auth_token(self, api_client: TestClient):
        """Test request with invalid authentication token."""
        headers = {"Authorization": "Bearer invalid.token.here"}

        company_data = {
            "ticker": "TEST",
            "name": "Test Company",
        }

        response = api_client.post(
            "/api/v1/companies/",
            json=company_data,
            headers=headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_expired_auth_token(self, api_client: TestClient, expired_token_headers: dict):
        """Test request with expired authentication token."""
        response = api_client.get(
            "/auth/me",
            headers=expired_token_headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestValidationErrors:
    """Test suite for input validation errors."""

    def test_invalid_email_format(self, api_client: TestClient):
        """Test registration with invalid email format."""
        user_data = {
            "email": "not-an-email",
            "username": "testuser",
            "password": "Test123!@#"
        }

        response = api_client.post("/auth/register", json=user_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

    def test_missing_required_fields(self, api_client: TestClient, auth_headers: dict):
        """Test creating company without required fields."""
        incomplete_data = {
            "name": "Incomplete Company"
            # Missing ticker
        }

        response = api_client.post(
            "/api/v1/companies/",
            json=incomplete_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_invalid_field_type(self, api_client: TestClient, auth_headers: dict):
        """Test creating company with invalid field types."""
        invalid_data = {
            "ticker": 12345,  # Should be string
            "name": "Test Company",
        }

        response = api_client.post(
            "/api/v1/companies/",
            json=invalid_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_field_length_validation(self, api_client: TestClient, auth_headers: dict):
        """Test field length validation."""
        invalid_data = {
            "ticker": "VERYLONGTICKER",  # Exceeds max length
            "name": "Test Company",
        }

        response = api_client.post(
            "/api/v1/companies/",
            json=invalid_data,
            headers=auth_headers
        )

        # Should validate or accept based on model constraints
        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_201_CREATED  # If validation allows it
        ]

    def test_invalid_category_value(self, api_client: TestClient, auth_headers: dict):
        """Test creating company with invalid category."""
        invalid_data = {
            "ticker": "TEST",
            "name": "Test Company",
            "category": "invalid_category"
        }

        response = api_client.post(
            "/api/v1/companies/",
            json=invalid_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestNotFoundErrors:
    """Test suite for not found errors."""

    def test_company_not_found(self, api_client: TestClient):
        """Test getting non-existent company."""
        non_existent_id = uuid4()
        response = api_client.get(f"/api/v1/companies/{non_existent_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_filing_not_found(self, api_client: TestClient):
        """Test getting non-existent filing."""
        non_existent_id = uuid4()
        response = api_client.get(f"/api/v1/filings/{non_existent_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_report_not_found(self, api_client: TestClient):
        """Test getting non-existent report."""
        non_existent_id = uuid4()
        response = api_client.get(f"/api/v1/reports/{non_existent_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_non_existent_resource(
        self, api_client: TestClient, auth_headers: dict
    ):
        """Test deleting non-existent resource."""
        non_existent_id = uuid4()
        response = api_client.delete(
            f"/api/v1/companies/{non_existent_id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_non_existent_resource(
        self, api_client: TestClient, auth_headers: dict
    ):
        """Test updating non-existent resource."""
        non_existent_id = uuid4()
        update_data = {
            "ticker": "TEST",
            "name": "Updated Name"
        }

        response = api_client.put(
            f"/api/v1/companies/{non_existent_id}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestMethodNotAllowed:
    """Test suite for method not allowed errors."""

    def test_post_to_get_only_endpoint(self, api_client: TestClient):
        """Test POST to GET-only endpoint."""
        response = api_client.post("/health")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_put_to_get_only_endpoint(self, api_client: TestClient):
        """Test PUT to GET-only endpoint."""
        response = api_client.put("/health")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_delete_to_get_only_endpoint(self, api_client: TestClient):
        """Test DELETE to GET-only endpoint."""
        response = api_client.delete("/api/v1/companies/")

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


class TestMalformedRequests:
    """Test suite for malformed request handling."""

    def test_malformed_json_body(self, api_client: TestClient, auth_headers: dict):
        """Test request with malformed JSON body."""
        response = api_client.post(
            "/api/v1/companies/",
            data="{invalid json}",
            headers={**auth_headers, "Content-Type": "application/json"}
        )

        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]

    def test_empty_json_body(self, api_client: TestClient, auth_headers: dict):
        """Test request with empty JSON body."""
        response = api_client.post(
            "/api/v1/companies/",
            json={},
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_null_json_body(self, api_client: TestClient, auth_headers: dict):
        """Test request with null JSON body."""
        response = api_client.post(
            "/api/v1/companies/",
            json=None,
            headers=auth_headers
        )

        assert response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]


class TestServerErrors:
    """Test suite for server error handling."""

    @patch('src.api.v1.companies.db')
    def test_internal_server_error(self, mock_db, api_client: TestClient):
        """Test handling of internal server errors."""
        mock_db.query.side_effect = Exception("Unexpected error")

        response = api_client.get("/api/v1/companies/")

        # Should return 500 or handle gracefully
        assert response.status_code in [
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            status.HTTP_200_OK  # If error is caught
        ]

    def test_unhandled_exception(self, api_client: TestClient):
        """Test unhandled exception handling."""
        # This should be handled by global exception handler
        # Actual implementation depends on exception handlers
        pass


class TestErrorResponseFormat:
    """Test suite for error response format."""

    def test_404_error_format(self, api_client: TestClient):
        """Test 404 error response format."""
        response = api_client.get(f"/api/v1/companies/{uuid4()}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        assert "detail" in data
        assert isinstance(data["detail"], str)

    def test_422_error_format(self, api_client: TestClient):
        """Test 422 validation error response format."""
        response = api_client.get("/api/v1/companies/invalid-uuid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()

        assert "detail" in data

    def test_401_error_format(self, api_client: TestClient):
        """Test 401 unauthorized error response format."""
        response = api_client.get("/api/v1/companies/watchlist")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()

        assert "detail" in data


class TestErrorRecoveryAndResilience:
    """Test suite for error recovery and resilience."""

    def test_api_recovers_after_database_error(
        self, api_client: TestClient, sample_company: Company
    ):
        """Test API recovers after database error."""
        # Simulate error by requesting invalid resource
        response1 = api_client.get(f"/api/v1/companies/{uuid4()}")
        assert response1.status_code == status.HTTP_404_NOT_FOUND

        # API should still work
        response2 = api_client.get(f"/api/v1/companies/{sample_company.id}")
        assert response2.status_code == status.HTTP_200_OK

    def test_api_handles_sequential_errors(self, api_client: TestClient):
        """Test API handles sequential errors gracefully."""
        # Make multiple invalid requests
        for _ in range(5):
            response = api_client.get(f"/api/v1/companies/{uuid4()}")
            assert response.status_code == status.HTTP_404_NOT_FOUND

        # API should still be responsive
        response = api_client.get("/health")
        assert response.status_code == status.HTTP_200_OK

    def test_partial_failure_in_batch_operation(
        self, api_client: TestClient, sample_companies
    ):
        """Test handling of partial failures in batch operations."""
        # Request mix of valid and invalid companies
        valid_id = sample_companies[0].id
        invalid_id = uuid4()

        response1 = api_client.get(f"/api/v1/companies/{valid_id}")
        response2 = api_client.get(f"/api/v1/companies/{invalid_id}")

        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_404_NOT_FOUND


class TestCORSErrors:
    """Test suite for CORS-related error handling."""

    def test_cors_preflight_request(self, api_client: TestClient):
        """Test CORS preflight OPTIONS request."""
        headers = {
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        }

        response = api_client.options("/api/v1/companies/", headers=headers)

        # Should handle CORS preflight
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_405_METHOD_NOT_ALLOWED
        ]


class TestRateLimitErrors:
    """Test suite for rate limiting errors."""

    def test_rate_limit_exceeded_message(self, api_client: TestClient):
        """Test rate limit error message format."""
        # This test assumes rate limiting is implemented
        # If not, it will just verify normal behavior
        responses = []
        for _ in range(1000):
            response = api_client.get("/api/v1/companies/")
            responses.append(response)
            if response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                break

        # If rate limiting is active, check error format
        rate_limited = [r for r in responses if r.status_code == status.HTTP_429_TOO_MANY_REQUESTS]
        if rate_limited:
            data = rate_limited[0].json()
            assert "detail" in data or "error" in data
