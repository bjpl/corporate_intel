"""Tests for company API endpoints."""

import pytest
from uuid import uuid4
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.db.models import Company


class TestCompanyListEndpoint:
    """Test suite for GET /api/v1/companies endpoint."""

    def test_list_companies_success(self, api_client: TestClient, sample_companies: list[Company]):
        """Test listing companies returns all companies."""
        response = api_client.get("/api/v1/companies/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == len(sample_companies)

    def test_list_companies_empty(self, api_client: TestClient):
        """Test listing companies when none exist."""
        response = api_client.get("/api/v1/companies/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_companies_filter_by_category(
        self, api_client: TestClient, sample_companies: list[Company]
    ):
        """Test filtering companies by category."""
        response = api_client.get("/api/v1/companies/?category=higher_education")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert all(c["category"] == "higher_education" for c in data)

    def test_list_companies_filter_by_sector(
        self, api_client: TestClient, sample_companies: list[Company]
    ):
        """Test filtering companies by sector."""
        response = api_client.get("/api/v1/companies/?sector=Technology")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert all(c["sector"] == "Technology" for c in data)

    def test_list_companies_pagination_limit(
        self, api_client: TestClient, sample_companies: list[Company]
    ):
        """Test pagination with limit parameter."""
        response = api_client.get("/api/v1/companies/?limit=2")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data) <= 2

    def test_list_companies_pagination_offset(
        self, api_client: TestClient, sample_companies: list[Company]
    ):
        """Test pagination with offset parameter."""
        # Get first page
        response1 = api_client.get("/api/v1/companies/?limit=2&offset=0")
        data1 = response1.json()

        # Get second page
        response2 = api_client.get("/api/v1/companies/?limit=2&offset=2")
        data2 = response2.json()

        # Ensure different results
        if len(data1) > 0 and len(data2) > 0:
            assert data1[0]["id"] != data2[0]["id"]

    def test_list_companies_invalid_limit(self, api_client: TestClient):
        """Test invalid limit parameter returns 422."""
        response = api_client.get("/api/v1/companies/?limit=1000")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_companies_negative_offset(self, api_client: TestClient):
        """Test negative offset returns 422."""
        response = api_client.get("/api/v1/companies/?offset=-1")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_companies_response_schema(
        self, api_client: TestClient, sample_company: Company
    ):
        """Test response includes all expected fields."""
        response = api_client.get("/api/v1/companies/")

        data = response.json()
        assert len(data) > 0

        company = data[0]
        assert "id" in company
        assert "ticker" in company
        assert "name" in company
        assert "sector" in company


class TestGetCompanyEndpoint:
    """Test suite for GET /api/v1/companies/{company_id} endpoint."""

    def test_get_company_success(
        self, api_client: TestClient, sample_company: Company
    ):
        """Test getting a specific company by ID."""
        response = api_client.get(f"/api/v1/companies/{sample_company.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == str(sample_company.id)
        assert data["ticker"] == sample_company.ticker
        assert data["name"] == sample_company.name

    def test_get_company_not_found(self, api_client: TestClient):
        """Test getting non-existent company returns 404."""
        non_existent_id = uuid4()
        response = api_client.get(f"/api/v1/companies/{non_existent_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_get_company_invalid_uuid(self, api_client: TestClient):
        """Test invalid UUID returns 422."""
        response = api_client.get("/api/v1/companies/invalid-uuid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestGetCompanyMetricsEndpoint:
    """Test suite for GET /api/v1/companies/{company_id}/metrics endpoint."""

    def test_get_company_metrics_success(
        self, api_client: TestClient, sample_company: Company, sample_metrics
    ):
        """Test getting company metrics."""
        response = api_client.get(f"/api/v1/companies/{sample_company.id}/metrics")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["company_id"] == str(sample_company.id)
        assert data["ticker"] == sample_company.ticker
        assert "latest_revenue" in data
        assert "last_updated" in data

    def test_get_metrics_company_not_found(self, api_client: TestClient):
        """Test getting metrics for non-existent company returns 404."""
        non_existent_id = uuid4()
        response = api_client.get(f"/api/v1/companies/{non_existent_id}/metrics")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestWatchlistEndpoint:
    """Test suite for GET /api/v1/companies/watchlist endpoint."""

    def test_get_watchlist_requires_auth(
        self, api_client: TestClient, unauthorized_headers
    ):
        """Test watchlist endpoint requires authentication."""
        response = api_client.get(
            "/api/v1/companies/watchlist",
            headers=unauthorized_headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_watchlist_success(
        self, api_client: TestClient, auth_headers, sample_companies
    ):
        """Test getting watchlist with authentication."""
        response = api_client.get(
            "/api/v1/companies/watchlist",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)


class TestCreateCompanyEndpoint:
    """Test suite for POST /api/v1/companies/ endpoint."""

    def test_create_company_requires_auth(
        self, api_client: TestClient, unauthorized_headers
    ):
        """Test creating company requires authentication."""
        company_data = {
            "ticker": "TEST",
            "name": "Test Company",
        }

        response = api_client.post(
            "/api/v1/companies/",
            json=company_data,
            headers=unauthorized_headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_company_success(
        self, api_client: TestClient, auth_headers, db_session: Session
    ):
        """Test creating a new company."""
        company_data = {
            "ticker": "NEWCO",
            "name": "New Company Inc.",
            "cik": "0001234567",
            "sector": "Technology",
            "category": "k12",
        }

        response = api_client.post(
            "/api/v1/companies/",
            json=company_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()

        assert data["ticker"] == "NEWCO"
        assert data["name"] == "New Company Inc."
        assert "id" in data

    def test_create_company_duplicate_ticker(
        self, api_client: TestClient, auth_headers, sample_company: Company
    ):
        """Test creating company with duplicate ticker returns 409."""
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
        assert "already exists" in data["detail"].lower()

    def test_create_company_invalid_category(
        self, api_client: TestClient, auth_headers
    ):
        """Test creating company with invalid category returns 422."""
        company_data = {
            "ticker": "TEST",
            "name": "Test Company",
            "category": "invalid_category",
        }

        response = api_client.post(
            "/api/v1/companies/",
            json=company_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_company_missing_required_fields(
        self, api_client: TestClient, auth_headers
    ):
        """Test creating company without required fields returns 422."""
        company_data = {
            "name": "Incomplete Company",
            # Missing ticker
        }

        response = api_client.post(
            "/api/v1/companies/",
            json=company_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestUpdateCompanyEndpoint:
    """Test suite for PUT /api/v1/companies/{company_id} endpoint."""

    def test_update_company_requires_auth(
        self, api_client: TestClient, sample_company: Company, unauthorized_headers
    ):
        """Test updating company requires authentication."""
        update_data = {"name": "Updated Name"}

        response = api_client.put(
            f"/api/v1/companies/{sample_company.id}",
            json=update_data,
            headers=unauthorized_headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_company_success(
        self, api_client: TestClient, sample_company: Company, auth_headers
    ):
        """Test updating company information."""
        update_data = {
            "ticker": sample_company.ticker,
            "name": "Updated Company Name",
            "sector": "Education",
        }

        response = api_client.put(
            f"/api/v1/companies/{sample_company.id}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["name"] == "Updated Company Name"
        assert data["sector"] == "Education"

    def test_update_company_not_found(
        self, api_client: TestClient, auth_headers
    ):
        """Test updating non-existent company returns 404."""
        non_existent_id = uuid4()
        update_data = {"name": "Updated Name"}

        response = api_client.put(
            f"/api/v1/companies/{non_existent_id}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestDeleteCompanyEndpoint:
    """Test suite for DELETE /api/v1/companies/{company_id} endpoint."""

    def test_delete_company_requires_auth(
        self, api_client: TestClient, sample_company: Company, unauthorized_headers
    ):
        """Test deleting company requires authentication."""
        response = api_client.delete(
            f"/api/v1/companies/{sample_company.id}",
            headers=unauthorized_headers
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_company_success(
        self, api_client: TestClient, sample_company: Company, auth_headers, db_session: Session
    ):
        """Test deleting a company."""
        company_id = sample_company.id

        response = api_client.delete(
            f"/api/v1/companies/{company_id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify company is deleted
        deleted_company = db_session.query(Company).filter(Company.id == company_id).first()
        assert deleted_company is None

    def test_delete_company_not_found(
        self, api_client: TestClient, auth_headers
    ):
        """Test deleting non-existent company returns 404."""
        non_existent_id = uuid4()

        response = api_client.delete(
            f"/api/v1/companies/{non_existent_id}",
            headers=auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
