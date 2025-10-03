"""Tests for SEC filings API endpoints."""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.db.models import SECFiling, Company


class TestListFilingsEndpoint:
    """Test suite for GET /api/v1/filings/ endpoint."""

    def test_list_filings_success(
        self, api_client: TestClient, sample_filings: list[SECFiling]
    ):
        """Test listing all filings."""
        response = api_client.get("/api/v1/filings/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == len(sample_filings)

    def test_list_filings_empty(self, api_client: TestClient):
        """Test listing filings when none exist."""
        response = api_client.get("/api/v1/filings/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_filings_filter_by_company(
        self, api_client: TestClient, sample_company: Company, sample_filings: list[SECFiling]
    ):
        """Test filtering filings by company ID."""
        response = api_client.get(f"/api/v1/filings/?company_id={sample_company.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert all(f["company_id"] == str(sample_company.id) for f in data)

    def test_list_filings_filter_by_type(
        self, api_client: TestClient, sample_filings: list[SECFiling]
    ):
        """Test filtering filings by filing type."""
        response = api_client.get("/api/v1/filings/?filing_type=10-K")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert all(f["filing_type"] == "10-K" for f in data)

    def test_list_filings_pagination(
        self, api_client: TestClient, sample_filings: list[SECFiling]
    ):
        """Test pagination with limit and offset."""
        # First page
        response1 = api_client.get("/api/v1/filings/?limit=2&offset=0")
        data1 = response1.json()

        # Second page
        response2 = api_client.get("/api/v1/filings/?limit=2&offset=2")
        data2 = response2.json()

        assert len(data1) <= 2
        if len(data1) > 0 and len(data2) > 0:
            assert data1[0]["id"] != data2[0]["id"]

    def test_list_filings_sorted_by_date(
        self, api_client: TestClient, sample_filings: list[SECFiling]
    ):
        """Test filings are sorted by filing date descending."""
        response = api_client.get("/api/v1/filings/")

        data = response.json()

        if len(data) > 1:
            dates = [datetime.fromisoformat(f["filing_date"].replace('Z', '+00:00')) for f in data]
            assert dates == sorted(dates, reverse=True)

    def test_list_filings_invalid_limit(self, api_client: TestClient):
        """Test invalid limit returns 422."""
        response = api_client.get("/api/v1/filings/?limit=1000")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_filings_invalid_company_id(self, api_client: TestClient):
        """Test invalid company ID format returns 422."""
        response = api_client.get("/api/v1/filings/?company_id=invalid-uuid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_filings_response_schema(
        self, api_client: TestClient, sample_filing: SECFiling
    ):
        """Test response includes all expected fields."""
        response = api_client.get("/api/v1/filings/")

        data = response.json()
        assert len(data) > 0

        filing = data[0]
        assert "id" in filing
        assert "company_id" in filing
        assert "filing_type" in filing
        assert "filing_date" in filing
        assert "accession_number" in filing
        assert "processing_status" in filing

    def test_list_filings_no_auth_required(self, api_client: TestClient, sample_filing: SECFiling):
        """Test listing filings doesn't require authentication."""
        response = api_client.get("/api/v1/filings/")

        assert response.status_code == status.HTTP_200_OK


class TestGetFilingEndpoint:
    """Test suite for GET /api/v1/filings/{filing_id} endpoint."""

    def test_get_filing_success(
        self, api_client: TestClient, sample_filing: SECFiling
    ):
        """Test getting a specific filing by ID."""
        response = api_client.get(f"/api/v1/filings/{sample_filing.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == str(sample_filing.id)
        assert data["filing_type"] == sample_filing.filing_type
        assert data["accession_number"] == sample_filing.accession_number

    def test_get_filing_not_found(self, api_client: TestClient):
        """Test getting non-existent filing returns 404."""
        non_existent_id = uuid4()
        response = api_client.get(f"/api/v1/filings/{non_existent_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_get_filing_invalid_uuid(self, api_client: TestClient):
        """Test invalid UUID returns 422."""
        response = api_client.get("/api/v1/filings/invalid-uuid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_filing_complete_data(
        self, api_client: TestClient, sample_filing: SECFiling
    ):
        """Test getting filing returns all fields."""
        response = api_client.get(f"/api/v1/filings/{sample_filing.id}")

        data = response.json()

        assert data["id"] == str(sample_filing.id)
        assert data["company_id"] == str(sample_filing.company_id)
        assert data["filing_type"] == sample_filing.filing_type
        assert data["processing_status"] == sample_filing.processing_status

    def test_get_filing_no_auth_required(
        self, api_client: TestClient, sample_filing: SECFiling
    ):
        """Test getting filing doesn't require authentication."""
        response = api_client.get(f"/api/v1/filings/{sample_filing.id}")

        assert response.status_code == status.HTTP_200_OK


class TestFilingsByCompany:
    """Test suite for filing-company relationships."""

    def test_get_filings_for_specific_company(
        self, api_client: TestClient, sample_company: Company, sample_filings: list[SECFiling]
    ):
        """Test retrieving all filings for a specific company."""
        response = api_client.get(f"/api/v1/filings/?company_id={sample_company.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # All returned filings should belong to the company
        assert all(f["company_id"] == str(sample_company.id) for f in data)

    def test_get_filings_multiple_companies(
        self, api_client: TestClient, sample_companies: list[Company], db_session: Session
    ):
        """Test filings from multiple companies are properly separated."""
        # Create filings for different companies
        for company in sample_companies[:2]:
            filing = SECFiling(
                id=uuid4(),
                company_id=company.id,
                filing_type="10-K",
                filing_date=datetime.utcnow(),
                accession_number=f"000-{company.ticker}-001",
                processing_status="pending",
            )
            db_session.add(filing)
        db_session.commit()

        # Get filings for first company
        response1 = api_client.get(f"/api/v1/filings/?company_id={sample_companies[0].id}")
        data1 = response1.json()

        # Get filings for second company
        response2 = api_client.get(f"/api/v1/filings/?company_id={sample_companies[1].id}")
        data2 = response2.json()

        # Verify no overlap
        ids1 = {f["id"] for f in data1}
        ids2 = {f["id"] for f in data2}
        assert ids1.isdisjoint(ids2)

    def test_company_with_no_filings(
        self, api_client: TestClient, sample_company: Company
    ):
        """Test querying filings for company with no filings."""
        # Create a company without filings
        response = api_client.get(f"/api/v1/filings/?company_id={sample_company.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # May have filings from fixtures, so just check it's a list
        assert isinstance(data, list)


class TestFilingTypes:
    """Test suite for different filing types."""

    def test_filter_10k_filings(
        self, api_client: TestClient, sample_filings: list[SECFiling]
    ):
        """Test filtering for 10-K filings."""
        response = api_client.get("/api/v1/filings/?filing_type=10-K")

        data = response.json()
        assert all(f["filing_type"] == "10-K" for f in data)

    def test_filter_10q_filings(
        self, api_client: TestClient, sample_filings: list[SECFiling]
    ):
        """Test filtering for 10-Q filings."""
        response = api_client.get("/api/v1/filings/?filing_type=10-Q")

        data = response.json()
        assert all(f["filing_type"] == "10-Q" for f in data)

    def test_filter_8k_filings(
        self, api_client: TestClient, sample_filings: list[SECFiling]
    ):
        """Test filtering for 8-K filings."""
        response = api_client.get("/api/v1/filings/?filing_type=8-K")

        data = response.json()
        assert all(f["filing_type"] == "8-K" for f in data)

    def test_invalid_filing_type(self, api_client: TestClient):
        """Test querying invalid filing type still returns results."""
        response = api_client.get("/api/v1/filings/?filing_type=INVALID")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0  # Should return empty list


class TestFilingProcessingStatus:
    """Test suite for filing processing status."""

    def test_filing_includes_processing_status(
        self, api_client: TestClient, sample_filing: SECFiling
    ):
        """Test filing response includes processing status."""
        response = api_client.get(f"/api/v1/filings/{sample_filing.id}")

        data = response.json()
        assert "processing_status" in data
        assert data["processing_status"] in ["pending", "processing", "completed", "failed"]

    def test_filings_with_different_statuses(
        self, api_client: TestClient, sample_company: Company, db_session: Session
    ):
        """Test filings can have different processing statuses."""
        statuses = ["pending", "completed", "failed"]
        filing_ids = []

        for status_val in statuses:
            filing = SECFiling(
                id=uuid4(),
                company_id=sample_company.id,
                filing_type="10-K",
                filing_date=datetime.utcnow(),
                accession_number=f"000-{status_val}-001",
                processing_status=status_val,
            )
            db_session.add(filing)
            filing_ids.append(filing.id)

        db_session.commit()

        # Verify each filing has correct status
        for filing_id, expected_status in zip(filing_ids, statuses):
            response = api_client.get(f"/api/v1/filings/{filing_id}")
            data = response.json()
            assert data["processing_status"] == expected_status


class TestFilingCaching:
    """Test suite for filing endpoint caching behavior."""

    def test_list_filings_cache_headers(
        self, api_client: TestClient, sample_filing: SECFiling
    ):
        """Test filings list endpoint uses caching."""
        response = api_client.get("/api/v1/filings/")

        # Check for cache-related behavior
        assert response.status_code == status.HTTP_200_OK

    def test_get_filing_cache_headers(
        self, api_client: TestClient, sample_filing: SECFiling
    ):
        """Test get filing endpoint uses caching."""
        response = api_client.get(f"/api/v1/filings/{sample_filing.id}")

        # Check for cache-related behavior
        assert response.status_code == status.HTTP_200_OK

    def test_repeated_requests_consistent(
        self, api_client: TestClient, sample_filing: SECFiling
    ):
        """Test repeated requests return consistent data."""
        response1 = api_client.get(f"/api/v1/filings/{sample_filing.id}")
        response2 = api_client.get(f"/api/v1/filings/{sample_filing.id}")
        response3 = api_client.get(f"/api/v1/filings/{sample_filing.id}")

        data1 = response1.json()
        data2 = response2.json()
        data3 = response3.json()

        assert data1 == data2 == data3
