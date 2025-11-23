"""Advanced edge case tests for API endpoints."""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock
import concurrent.futures

from src.db.models import Company, FinancialMetric, SECFiling


class TestRateLimiting:
    """Test suite for rate limiting scenarios."""

    def test_rapid_successive_requests(self, api_client: TestClient):
        """Test handling of rapid successive requests."""
        # Make 50 rapid requests
        responses = []
        for _ in range(50):
            response = api_client.get("/health")
            responses.append(response)

        # Should handle all requests without errors
        assert all(r.status_code == status.HTTP_200_OK for r in responses)

    def test_burst_traffic_companies_endpoint(
        self, api_client: TestClient, sample_companies
    ):
        """Test burst traffic to companies endpoint."""
        responses = []
        for _ in range(20):
            response = api_client.get("/api/v1/companies/")
            responses.append(response)

        # All should succeed (unless rate limiting is enforced)
        success_count = sum(1 for r in responses if r.status_code == status.HTTP_200_OK)
        assert success_count >= 10  # At least half should succeed


class TestConcurrentRequests:
    """Test suite for concurrent request handling."""

    def test_concurrent_company_reads(
        self, api_client: TestClient, sample_company: Company
    ):
        """Test concurrent reads of same company."""
        def make_request():
            return api_client.get(f"/api/v1/companies/{sample_company.id}")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [f.result() for f in futures]

        # All should succeed
        assert all(r.status_code == status.HTTP_200_OK for r in responses)

        # All should return same data
        data_list = [r.json() for r in responses]
        assert all(d["id"] == str(sample_company.id) for d in data_list)

    def test_concurrent_list_requests(
        self, api_client: TestClient, sample_companies
    ):
        """Test concurrent list requests."""
        def make_request():
            return api_client.get("/api/v1/companies/")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [f.result() for f in futures]

        # All should succeed
        assert all(r.status_code == status.HTTP_200_OK for r in responses)

    def test_concurrent_mixed_operations(
        self, api_client: TestClient, sample_companies
    ):
        """Test concurrent mixed read operations."""
        def read_companies():
            return api_client.get("/api/v1/companies/")

        def read_metrics():
            return api_client.get("/api/v1/metrics/")

        def read_filings():
            return api_client.get("/api/v1/filings/")

        operations = [read_companies, read_metrics, read_filings] * 3

        with concurrent.futures.ThreadPoolExecutor(max_workers=9) as executor:
            futures = [executor.submit(op) for op in operations]
            responses = [f.result() for f in futures]

        # All should succeed
        assert all(r.status_code == status.HTTP_200_OK for r in responses)


class TestPaginationEdgeCases:
    """Test suite for pagination edge cases."""

    def test_large_offset_small_dataset(
        self, api_client: TestClient, sample_companies
    ):
        """Test large offset with small dataset."""
        response = api_client.get("/api/v1/companies/?offset=1000000")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0

    def test_maximum_limit_value(self, api_client: TestClient):
        """Test maximum allowed limit value."""
        response = api_client.get("/api/v1/companies/?limit=500")

        assert response.status_code == status.HTTP_200_OK

    def test_limit_exceeds_maximum(self, api_client: TestClient):
        """Test limit exceeding maximum returns validation error."""
        response = api_client.get("/api/v1/companies/?limit=501")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_pagination_with_filters(
        self, api_client: TestClient, sample_companies
    ):
        """Test pagination combined with filters."""
        response = api_client.get(
            "/api/v1/companies/?category=higher_education&limit=1&offset=0"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) <= 1

    def test_offset_equals_total_count(
        self, api_client: TestClient, sample_companies
    ):
        """Test offset equal to total count."""
        # Get total count first
        response1 = api_client.get("/api/v1/companies/")
        total = len(response1.json())

        # Request with offset equal to total
        response2 = api_client.get(f"/api/v1/companies/?offset={total}")

        assert response2.status_code == status.HTTP_200_OK
        data = response2.json()
        assert len(data) == 0


class TestInvalidUUIDHandling:
    """Test suite for invalid UUID handling."""

    def test_malformed_uuid_company(self, api_client: TestClient):
        """Test malformed UUID in company endpoint."""
        invalid_uuids = [
            "not-a-uuid",
            "12345",
            "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "00000000-0000-0000-0000-000000000000g",
            "",
        ]

        for invalid_uuid in invalid_uuids:
            response = api_client.get(f"/api/v1/companies/{invalid_uuid}")
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_malformed_uuid_filing(self, api_client: TestClient):
        """Test malformed UUID in filing endpoint."""
        response = api_client.get("/api/v1/filings/invalid-uuid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_malformed_uuid_in_query_param(self, api_client: TestClient):
        """Test malformed UUID in query parameter."""
        response = api_client.get("/api/v1/metrics/?company_id=invalid-uuid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestSpecialCharacterHandling:
    """Test suite for special character handling."""

    def test_query_with_special_characters(
        self, api_client: TestClient, db_session: Session
    ):
        """Test query parameters with special characters."""
        company = Company(
            id=uuid4(),
            ticker="TEST&CO",
            name="Test & Company Inc.",
            sector="Technology & Education",
        )
        db_session.add(company)
        db_session.commit()

        response = api_client.get("/api/v1/companies/?sector=Technology%20%26%20Education")

        assert response.status_code == status.HTTP_200_OK

    def test_unicode_characters(
        self, api_client: TestClient, db_session: Session
    ):
        """Test handling of unicode characters."""
        company = Company(
            id=uuid4(),
            ticker="INTL",
            name="Educación Internacional",
            sector="Education",
        )
        db_session.add(company)
        db_session.commit()

        response = api_client.get(f"/api/v1/companies/{company.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "Educación" in data["name"]


class TestEmptyAndNullValues:
    """Test suite for empty and null value handling."""

    def test_company_with_null_optional_fields(
        self, api_client: TestClient, db_session: Session
    ):
        """Test company with all optional fields null."""
        company = Company(
            id=uuid4(),
            ticker="NULL",
            name="Null Company",
            cik=None,
            sector=None,
            subsector=None,
            category=None,
            delivery_model=None,
        )
        db_session.add(company)
        db_session.commit()

        response = api_client.get(f"/api/v1/companies/{company.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["ticker"] == "NULL"

    def test_empty_string_filters(self, api_client: TestClient):
        """Test empty string in filter parameters."""
        response = api_client.get("/api/v1/companies/?sector=")

        # Should handle gracefully
        assert response.status_code == status.HTTP_200_OK

    def test_multiple_empty_filters(self, api_client: TestClient):
        """Test multiple empty filter parameters."""
        response = api_client.get("/api/v1/companies/?sector=&category=")

        assert response.status_code == status.HTTP_200_OK


class TestVeryLargeResponses:
    """Test suite for handling very large responses."""

    def test_large_number_of_companies(
        self, api_client: TestClient, db_session: Session
    ):
        """Test retrieving large number of companies."""
        # Create 200 companies
        companies = []
        for i in range(200):
            company = Company(
                id=uuid4(),
                ticker=f"TST{i:03d}",
                name=f"Test Company {i}",
                sector="Technology",
            )
            companies.append(company)
            db_session.add(company)

        db_session.commit()

        # Request with high limit
        response = api_client.get("/api/v1/companies/?limit=500")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should return up to limit (500) or all available
        assert len(data) >= 200

    def test_metrics_with_many_records(
        self, api_client: TestClient, db_session: Session, sample_company: Company
    ):
        """Test metrics endpoint with many records."""
        # Create 100 metrics
        for i in range(100):
            metric = FinancialMetric(
                company_id=sample_company.id,
                metric_date=datetime.utcnow() - timedelta(days=i),
                period_type="daily",
                metric_type=f"metric_{i % 10}",
                value=float(i * 1000),
            )
            db_session.add(metric)

        db_session.commit()

        response = api_client.get(f"/api/v1/metrics/?company_id={sample_company.id}&limit=500")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) >= 100


class TestDateTimeEdgeCases:
    """Test suite for date/time edge cases."""

    def test_very_old_dates(
        self, api_client: TestClient, db_session: Session, sample_company: Company
    ):
        """Test handling of very old dates."""
        old_metric = FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime(1990, 1, 1),
            period_type="annual",
            metric_type="revenue",
            value=1000000.0,
        )
        db_session.add(old_metric)
        db_session.commit()

        response = api_client.get(f"/api/v1/metrics/?company_id={sample_company.id}")

        assert response.status_code == status.HTTP_200_OK

    def test_future_dates(
        self, api_client: TestClient, db_session: Session, sample_company: Company
    ):
        """Test handling of future dates."""
        future_metric = FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow() + timedelta(days=365),
            period_type="quarterly",
            metric_type="forecast",
            value=5000000.0,
        )
        db_session.add(future_metric)
        db_session.commit()

        response = api_client.get(f"/api/v1/metrics/?company_id={sample_company.id}")

        assert response.status_code == status.HTTP_200_OK


class TestNumericEdgeCases:
    """Test suite for numeric value edge cases."""

    def test_very_large_metric_values(
        self, api_client: TestClient, db_session: Session, sample_company: Company
    ):
        """Test handling of very large metric values."""
        large_metric = FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type="annual",
            metric_type="market_cap",
            value=1e15,  # 1 quadrillion
        )
        db_session.add(large_metric)
        db_session.commit()

        response = api_client.get(f"/api/v1/metrics/?company_id={sample_company.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        market_cap_metrics = [m for m in data if m["metric_type"] == "market_cap"]
        assert len(market_cap_metrics) > 0

    def test_zero_values(
        self, api_client: TestClient, db_session: Session, sample_company: Company
    ):
        """Test handling of zero values."""
        zero_metric = FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type="quarterly",
            metric_type="profit",
            value=0.0,
        )
        db_session.add(zero_metric)
        db_session.commit()

        response = api_client.get(f"/api/v1/metrics/?company_id={sample_company.id}")

        assert response.status_code == status.HTTP_200_OK

    def test_negative_values(
        self, api_client: TestClient, db_session: Session, sample_company: Company
    ):
        """Test handling of negative values."""
        negative_metric = FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type="quarterly",
            metric_type="net_income",
            value=-1000000.0,
        )
        db_session.add(negative_metric)
        db_session.commit()

        response = api_client.get(f"/api/v1/metrics/?company_id={sample_company.id}")

        assert response.status_code == status.HTTP_200_OK

    def test_very_small_decimal_values(
        self, api_client: TestClient, db_session: Session, sample_company: Company
    ):
        """Test handling of very small decimal values."""
        small_metric = FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type="quarterly",
            metric_type="percentage",
            value=0.0001,
        )
        db_session.add(small_metric)
        db_session.commit()

        response = api_client.get(f"/api/v1/metrics/?company_id={sample_company.id}")

        assert response.status_code == status.HTTP_200_OK


class TestCacheEdgeCases:
    """Test suite for cache-related edge cases."""

    def test_cache_consistency_across_requests(
        self, api_client: TestClient, sample_companies
    ):
        """Test cache returns consistent data."""
        response1 = api_client.get("/api/v1/companies/")
        response2 = api_client.get("/api/v1/companies/")
        response3 = api_client.get("/api/v1/companies/")

        data1 = response1.json()
        data2 = response2.json()
        data3 = response3.json()

        # Should return identical data
        assert data1 == data2 == data3

    def test_different_query_params_different_cache(
        self, api_client: TestClient, sample_companies
    ):
        """Test different query params use different cache keys."""
        response1 = api_client.get("/api/v1/companies/?limit=10")
        response2 = api_client.get("/api/v1/companies/?limit=20")

        # Different params might return different results
        assert response1.status_code == status.HTTP_200_OK
        assert response2.status_code == status.HTTP_200_OK


class TestContentTypeHandling:
    """Test suite for content type handling."""

    def test_json_content_type_required(
        self, api_client: TestClient, auth_headers: dict
    ):
        """Test JSON content type for POST requests."""
        # Try to create company without JSON content-type
        headers = {**auth_headers, "Content-Type": "text/plain"}

        response = api_client.post(
            "/api/v1/companies/",
            data="invalid data",
            headers=headers
        )

        # Should reject or handle gracefully
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        ]

    def test_response_content_type(self, api_client: TestClient):
        """Test all responses have correct content type."""
        endpoints = [
            "/health",
            "/api/v1/companies/",
            "/api/v1/metrics/",
            "/api/v1/filings/",
        ]

        for endpoint in endpoints:
            response = api_client.get(endpoint)
            assert "application/json" in response.headers.get("content-type", "")


class TestErrorRecovery:
    """Test suite for error recovery scenarios."""

    def test_recovery_after_invalid_request(
        self, api_client: TestClient, sample_company: Company
    ):
        """Test API recovers after invalid request."""
        # Make invalid request
        response1 = api_client.get("/api/v1/companies/invalid-uuid")
        assert response1.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Make valid request - should succeed
        response2 = api_client.get(f"/api/v1/companies/{sample_company.id}")
        assert response2.status_code == status.HTTP_200_OK

    def test_recovery_after_not_found(
        self, api_client: TestClient, sample_company: Company
    ):
        """Test API recovers after 404 error."""
        # Request non-existent resource
        response1 = api_client.get(f"/api/v1/companies/{uuid4()}")
        assert response1.status_code == status.HTTP_404_NOT_FOUND

        # Make valid request - should succeed
        response2 = api_client.get(f"/api/v1/companies/{sample_company.id}")
        assert response2.status_code == status.HTTP_200_OK
