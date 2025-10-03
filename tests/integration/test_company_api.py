"""
Integration tests for Company API endpoints.
Tests CRUD operations, authentication, authorization, and validation.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any

from app.main import app
from app.models.company import Company, CompanyStatus
from app.core.security import create_access_token


class TestCompanyAPI:
    """Integration tests for company endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self, client: TestClient, db: Session, auth_headers: Dict[str, str]):
        """Setup test fixtures."""
        self.client = client
        self.db = db
        self.headers = auth_headers

        # Create test companies
        self.test_companies = [
            Company(
                name="TechCorp Inc",
                ticker="TECH",
                industry="Technology",
                sector="Software",
                status=CompanyStatus.ACTIVE,
                revenue=1000000000,
                employee_count=5000,
                founded_year=2010
            ),
            Company(
                name="FinServe Ltd",
                ticker="FINS",
                industry="Finance",
                sector="Banking",
                status=CompanyStatus.ACTIVE,
                revenue=500000000,
                employee_count=2000,
                founded_year=2005
            ),
            Company(
                name="RetailMax Corp",
                ticker="RETL",
                industry="Retail",
                sector="E-commerce",
                status=CompanyStatus.ARCHIVED,
                revenue=750000000,
                employee_count=3000,
                founded_year=2015
            )
        ]

        for company in self.test_companies:
            self.db.add(company)
        self.db.commit()

        yield

        # Cleanup
        self.db.query(Company).delete()
        self.db.commit()

    def test_list_companies_success(self):
        """Test GET /companies - successful list retrieval."""
        response = self.client.get("/api/v1/companies", headers=self.headers)

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 3
        assert len(data["items"]) >= 3

        # Verify company data structure
        company = data["items"][0]
        assert "id" in company
        assert "name" in company
        assert "ticker" in company
        assert "industry" in company
        assert "status" in company

    def test_list_companies_pagination(self):
        """Test GET /companies with pagination."""
        response = self.client.get(
            "/api/v1/companies?skip=1&limit=2",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] >= 3

    def test_list_companies_search(self):
        """Test GET /companies with search query."""
        response = self.client.get(
            "/api/v1/companies?search=TechCorp",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any("TechCorp" in item["name"] for item in data["items"])

    def test_list_companies_filter_industry(self):
        """Test GET /companies filtered by industry."""
        response = self.client.get(
            "/api/v1/companies?industry=Technology",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert all(item["industry"] == "Technology" for item in data["items"])

    def test_list_companies_filter_status(self):
        """Test GET /companies filtered by status."""
        response = self.client.get(
            "/api/v1/companies?status=active",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert all(item["status"] == "active" for item in data["items"])

    def test_list_companies_sort(self):
        """Test GET /companies with sorting."""
        response = self.client.get(
            "/api/v1/companies?sort_by=revenue&sort_order=desc",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        revenues = [item["revenue"] for item in data["items"]]
        assert revenues == sorted(revenues, reverse=True)

    def test_list_companies_unauthorized(self):
        """Test GET /companies without authentication."""
        response = self.client.get("/api/v1/companies")
        assert response.status_code == 401

    def test_get_company_success(self):
        """Test GET /companies/{id} - successful retrieval."""
        company_id = self.test_companies[0].id
        response = self.client.get(
            f"/api/v1/companies/{company_id}",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == company_id
        assert data["name"] == "TechCorp Inc"
        assert data["ticker"] == "TECH"
        assert data["industry"] == "Technology"

    def test_get_company_not_found(self):
        """Test GET /companies/{id} - non-existent company."""
        response = self.client.get(
            "/api/v1/companies/99999",
            headers=self.headers
        )
        assert response.status_code == 404

    def test_get_company_unauthorized(self):
        """Test GET /companies/{id} without authentication."""
        company_id = self.test_companies[0].id
        response = self.client.get(f"/api/v1/companies/{company_id}")
        assert response.status_code == 401

    def test_create_company_success(self):
        """Test POST /companies - successful creation."""
        payload = {
            "name": "NewTech Solutions",
            "ticker": "NWTS",
            "industry": "Technology",
            "sector": "Cloud Services",
            "status": "active",
            "revenue": 250000000,
            "employee_count": 1500,
            "founded_year": 2020,
            "headquarters_location": "San Francisco, CA",
            "website": "https://newtech.example.com",
            "description": "Cloud infrastructure provider"
        }

        response = self.client.post(
            "/api/v1/companies",
            json=payload,
            headers=self.headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == payload["name"]
        assert data["ticker"] == payload["ticker"]
        assert "id" in data
        assert "created_at" in data

        # Verify in database
        company = self.db.query(Company).filter(
            Company.ticker == "NWTS"
        ).first()
        assert company is not None
        assert company.name == "NewTech Solutions"

    def test_create_company_duplicate_ticker(self):
        """Test POST /companies with duplicate ticker."""
        payload = {
            "name": "Another TechCorp",
            "ticker": "TECH",  # Duplicate
            "industry": "Technology",
            "sector": "Software"
        }

        response = self.client.post(
            "/api/v1/companies",
            json=payload,
            headers=self.headers
        )
        assert response.status_code == 400

    def test_create_company_invalid_data(self):
        """Test POST /companies with invalid data."""
        payload = {
            "name": "",  # Empty name
            "ticker": "TST"
        }

        response = self.client.post(
            "/api/v1/companies",
            json=payload,
            headers=self.headers
        )
        assert response.status_code == 422

    def test_create_company_missing_required_fields(self):
        """Test POST /companies missing required fields."""
        payload = {
            "name": "Incomplete Corp"
            # Missing ticker
        }

        response = self.client.post(
            "/api/v1/companies",
            json=payload,
            headers=self.headers
        )
        assert response.status_code == 422

    def test_create_company_unauthorized(self):
        """Test POST /companies without authentication."""
        payload = {
            "name": "Unauthorized Corp",
            "ticker": "UNAU"
        }

        response = self.client.post("/api/v1/companies", json=payload)
        assert response.status_code == 401

    def test_update_company_success(self):
        """Test PUT /companies/{id} - successful update."""
        company_id = self.test_companies[0].id
        payload = {
            "name": "TechCorp Inc (Updated)",
            "revenue": 1200000000,
            "employee_count": 5500,
            "description": "Updated description"
        }

        response = self.client.put(
            f"/api/v1/companies/{company_id}",
            json=payload,
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == payload["name"]
        assert data["revenue"] == payload["revenue"]
        assert data["employee_count"] == payload["employee_count"]

        # Verify in database
        self.db.refresh(self.test_companies[0])
        assert self.test_companies[0].name == "TechCorp Inc (Updated)"

    def test_update_company_partial(self):
        """Test PUT /companies/{id} - partial update."""
        company_id = self.test_companies[0].id
        payload = {
            "revenue": 1100000000
        }

        response = self.client.put(
            f"/api/v1/companies/{company_id}",
            json=payload,
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["revenue"] == 1100000000
        assert data["name"] == "TechCorp Inc"  # Unchanged

    def test_update_company_not_found(self):
        """Test PUT /companies/{id} - non-existent company."""
        payload = {"revenue": 1000000}
        response = self.client.put(
            "/api/v1/companies/99999",
            json=payload,
            headers=self.headers
        )
        assert response.status_code == 404

    def test_update_company_unauthorized(self):
        """Test PUT /companies/{id} without authentication."""
        company_id = self.test_companies[0].id
        payload = {"revenue": 1000000}
        response = self.client.put(
            f"/api/v1/companies/{company_id}",
            json=payload
        )
        assert response.status_code == 401

    def test_delete_company_success(self):
        """Test DELETE /companies/{id} - successful deletion."""
        company_id = self.test_companies[0].id
        response = self.client.delete(
            f"/api/v1/companies/{company_id}",
            headers=self.headers
        )

        assert response.status_code == 204

        # Verify deleted from database
        company = self.db.query(Company).filter(
            Company.id == company_id
        ).first()
        assert company is None

    def test_delete_company_not_found(self):
        """Test DELETE /companies/{id} - non-existent company."""
        response = self.client.delete(
            "/api/v1/companies/99999",
            headers=self.headers
        )
        assert response.status_code == 404

    def test_delete_company_unauthorized(self):
        """Test DELETE /companies/{id} without authentication."""
        company_id = self.test_companies[0].id
        response = self.client.delete(f"/api/v1/companies/{company_id}")
        assert response.status_code == 401

    def test_authorization_role_based(self):
        """Test role-based authorization for company operations."""
        # Create read-only user token
        readonly_token = create_access_token(
            data={"sub": "readonly@example.com", "role": "reader"}
        )
        readonly_headers = {"Authorization": f"Bearer {readonly_token}"}

        # Read operations should succeed
        response = self.client.get(
            "/api/v1/companies",
            headers=readonly_headers
        )
        assert response.status_code == 200

        # Write operations should fail
        payload = {"name": "Test Corp", "ticker": "TST"}
        response = self.client.post(
            "/api/v1/companies",
            json=payload,
            headers=readonly_headers
        )
        assert response.status_code == 403
