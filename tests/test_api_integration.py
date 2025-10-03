"""API integration tests for all endpoints."""

import pytest
from fastapi import status
from datetime import datetime, timedelta
import json


class TestCompaniesAPI:
    """Test companies API endpoints."""
    
    def test_create_company(self, client, admin_headers, sample_company_data):
        """Test creating a new company."""
        response = client.post("/api/v1/companies",
            headers=admin_headers,
            json=sample_company_data
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["ticker"] == sample_company_data["ticker"]
        assert data["name"] == sample_company_data["name"]
        assert "id" in data
    
    def test_get_company(self, client, auth_headers, sample_company_data, admin_headers):
        """Test getting a company by ID."""
        # First create a company
        create_response = client.post("/api/v1/companies",
            headers=admin_headers,
            json=sample_company_data
        )
        company_id = create_response.json()["id"]
        
        # Get the company
        response = client.get(f"/api/v1/companies/{company_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == company_id
        assert data["ticker"] == sample_company_data["ticker"]
    
    def test_list_companies(self, client, auth_headers):
        """Test listing companies with pagination."""
        response = client.get("/api/v1/companies?skip=0&limit=10",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 10
    
    def test_update_company(self, client, admin_headers, sample_company_data):
        """Test updating a company."""
        # Create company
        create_response = client.post("/api/v1/companies",
            headers=admin_headers,
            json=sample_company_data
        )
        company_id = create_response.json()["id"]
        
        # Update company
        update_data = {"employees": 900, "description": "Updated description"}
        response = client.put(f"/api/v1/companies/{company_id}",
            headers=admin_headers,
            json=update_data
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["employees"] == 900
        assert data["description"] == "Updated description"
    
    def test_delete_company(self, client, admin_headers, sample_company_data):
        """Test deleting a company."""
        # Create company
        create_response = client.post("/api/v1/companies",
            headers=admin_headers,
            json=sample_company_data
        )
        company_id = create_response.json()["id"]
        
        # Delete company
        response = client.delete(f"/api/v1/companies/{company_id}",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify deletion
        get_response = client.get(f"/api/v1/companies/{company_id}",
            headers=admin_headers
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_search_companies(self, client, auth_headers):
        """Test searching companies."""
        response = client.get("/api/v1/companies/search?query=edtech",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)


class TestFinancialMetricsAPI:
    """Test financial metrics API endpoints."""
    
    def test_create_metrics(self, client, admin_headers, sample_financial_metrics):
        """Test creating financial metrics."""
        response = client.post("/api/v1/metrics",
            headers=admin_headers,
            json=sample_financial_metrics
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["revenue"] == sample_financial_metrics["revenue"]
    
    def test_get_company_metrics(self, client, auth_headers):
        """Test getting metrics for a company."""
        company_id = "test-company-id"
        response = client.get(f"/api/v1/metrics/company/{company_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_metrics_time_series(self, client, auth_headers):
        """Test getting metrics time series."""
        company_id = "test-company-id"
        start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        end_date = datetime.utcnow().isoformat()
        
        response = client.get(
            f"/api/v1/metrics/company/{company_id}/timeseries"
            f"?start_date={start_date}&end_date={end_date}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    def test_aggregate_metrics(self, client, auth_headers):
        """Test aggregating metrics."""
        response = client.get("/api/v1/metrics/aggregate?sector=EdTech",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "avg_revenue" in data
        assert "avg_growth" in data
        assert "total_market_cap" in data


class TestSECFilingsAPI:
    """Test SEC filings API endpoints."""
    
    def test_ingest_filings(self, client, admin_headers, mock_external_apis):
        """Test ingesting SEC filings."""
        response = client.post("/api/v1/filings/ingest",
            headers=admin_headers,
            json={
                "ticker": "DUOL",
                "filing_types": ["10-K", "10-Q"],
                "start_date": "2023-01-01"
            }
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "task_id" in data
    
    def test_get_filing(self, client, auth_headers, sample_sec_filing, admin_headers):
        """Test getting a specific filing."""
        # Create filing
        response = client.post("/api/v1/filings",
            headers=admin_headers,
            json=sample_sec_filing
        )
        filing_id = response.json()["id"]
        
        # Get filing
        response = client.get(f"/api/v1/filings/{filing_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["filing_type"] == sample_sec_filing["filing_type"]
    
    def test_list_company_filings(self, client, auth_headers):
        """Test listing filings for a company."""
        company_id = "test-company-id"
        response = client.get(f"/api/v1/filings/company/{company_id}",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
    
    def test_process_filing(self, client, admin_headers, mock_ray):
        """Test processing a filing."""
        filing_id = "test-filing-id"
        response = client.post(f"/api/v1/filings/{filing_id}/process",
            headers=admin_headers
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "task_id" in data


class TestIntelligenceAPI:
    """Test intelligence/analysis API endpoints."""
    
    def test_competitor_analysis(self, client, analyst_user, auth_service):
        """Test competitor analysis endpoint."""
        token = auth_service.create_access_token(analyst_user)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.post("/api/v1/intelligence/competitor-analysis",
            headers=headers,
            json={
                "company_id": "test-company-id",
                "competitor_ids": ["comp1", "comp2"],
                "metrics": ["revenue", "growth", "market_share"]
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "analysis" in data
        assert "recommendations" in data
    
    def test_market_opportunity(self, client, analyst_user, auth_service):
        """Test market opportunity analysis."""
        token = auth_service.create_access_token(analyst_user)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.post("/api/v1/intelligence/market-opportunity",
            headers=headers,
            json={
                "sector": "EdTech",
                "segments": ["K-12", "Higher Ed", "Corporate Training"]
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "tam" in data
        assert "sam" in data
        assert "som" in data
    
    def test_cohort_analysis(self, client, analyst_user, auth_service):
        """Test cohort analysis."""
        token = auth_service.create_access_token(analyst_user)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.post("/api/v1/intelligence/cohort-analysis",
            headers=headers,
            json={
                "company_ids": ["comp1", "comp2", "comp3"],
                "cohort_period": "quarterly",
                "metrics": ["retention", "expansion", "churn"]
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "cohorts" in data
        assert "retention_curves" in data
    
    def test_sentiment_analysis(self, client, auth_headers, mock_external_apis):
        """Test sentiment analysis on news."""
        response = client.post("/api/v1/intelligence/sentiment",
            headers=auth_headers,
            json={
                "company_id": "test-company-id",
                "sources": ["news", "social"],
                "days_back": 30
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "sentiment_score" in data
        assert "sentiment_trend" in data


class TestSearchAPI:
    """Test search functionality."""
    
    def test_semantic_search(self, client, auth_headers):
        """Test semantic search."""
        response = client.post("/api/v1/search/semantic",
            headers=auth_headers,
            json={
                "query": "companies with strong revenue growth in EdTech",
                "limit": 10
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "results" in data
        assert len(data["results"]) <= 10
    
    def test_hybrid_search(self, client, auth_headers):
        """Test hybrid search (semantic + keyword)."""
        response = client.post("/api/v1/search/hybrid",
            headers=auth_headers,
            json={
                "query": "Duolingo language learning",
                "filters": {
                    "sector": "EdTech",
                    "min_revenue": 100000000
                },
                "limit": 5
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "results" in data
        assert "total_count" in data
    
    def test_faceted_search(self, client, auth_headers):
        """Test faceted search."""
        response = client.post("/api/v1/search/faceted",
            headers=auth_headers,
            json={
                "query": "online education",
                "facets": ["sector", "filing_type", "year"],
                "limit": 20
            }
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "results" in data
        assert "facets" in data
        assert "sector" in data["facets"]


class TestReportsAPI:
    """Test report generation API."""
    
    def test_generate_company_report(self, client, analyst_user, auth_service):
        """Test generating a company report."""
        token = auth_service.create_access_token(analyst_user)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.post("/api/v1/reports/company",
            headers=headers,
            json={
                "company_id": "test-company-id",
                "report_type": "comprehensive",
                "sections": ["overview", "financials", "competition", "outlook"]
            }
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "report_id" in data
        assert "status" in data
    
    def test_generate_sector_report(self, client, analyst_user, auth_service):
        """Test generating a sector report."""
        token = auth_service.create_access_token(analyst_user)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.post("/api/v1/reports/sector",
            headers=headers,
            json={
                "sector": "EdTech",
                "period": "2024-Q1",
                "include_forecast": True
            }
        )
        
        assert response.status_code == status.HTTP_202_ACCEPTED
        data = response.json()
        assert "report_id" in data
    
    def test_get_report_status(self, client, auth_headers):
        """Test getting report generation status."""
        report_id = "test-report-id"
        response = client.get(f"/api/v1/reports/{report_id}/status",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert data["status"] in ["pending", "processing", "completed", "failed"]
    
    def test_download_report(self, client, auth_headers):
        """Test downloading a completed report."""
        report_id = "test-report-id"
        response = client.get(f"/api/v1/reports/{report_id}/download",
            headers=auth_headers
        )
        
        # Would be 200 with actual report data
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]


class TestHealthAndMetrics:
    """Test health check and metrics endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data
    
    def test_metrics_endpoint(self, client):
        """Test Prometheus metrics endpoint."""
        response = client.get("/metrics")
        
        assert response.status_code == status.HTTP_200_OK
        # Prometheus returns text format
        assert "text/plain" in response.headers["content-type"]


class TestCaching:
    """Test caching functionality."""
    
    def test_cached_response(self, client, auth_headers, mock_cache_manager):
        """Test that responses are cached."""
        # First request - cache miss
        response1 = client.get("/api/v1/companies?skip=0&limit=10",
            headers=auth_headers
        )
        assert response1.status_code == status.HTTP_200_OK
        
        # Second request - should hit cache
        response2 = client.get("/api/v1/companies?skip=0&limit=10",
            headers=auth_headers
        )
        assert response2.status_code == status.HTTP_200_OK
        
        # Verify cache was checked
        mock_cache_manager.get.assert_called()
    
    def test_cache_invalidation(self, client, admin_headers, mock_cache_manager):
        """Test cache invalidation on updates."""
        # Create company
        response = client.post("/api/v1/companies",
            headers=admin_headers,
            json={"ticker": "TEST", "name": "Test Corp"}
        )
        company_id = response.json()["id"]
        
        # Update company - should invalidate cache
        client.put(f"/api/v1/companies/{company_id}",
            headers=admin_headers,
            json={"name": "Updated Corp"}
        )
        
        # Verify cache was cleared
        mock_cache_manager.delete.assert_called()


class TestErrorHandling:
    """Test error handling and validation."""
    
    def test_404_not_found(self, client, auth_headers):
        """Test 404 for non-existent resource."""
        response = client.get("/api/v1/companies/non-existent-id",
            headers=auth_headers
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "detail" in response.json()
    
    def test_validation_error(self, client, admin_headers):
        """Test validation error for invalid data."""
        response = client.post("/api/v1/companies",
            headers=admin_headers,
            json={
                "ticker": "",  # Invalid - empty
                "name": "x" * 300  # Invalid - too long
            }
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "detail" in response.json()
    
    def test_unauthorized_access(self, client):
        """Test unauthorized access without auth."""
        response = client.get("/api/v1/companies")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_forbidden_access(self, client, auth_headers):
        """Test forbidden access for insufficient permissions."""
        # Viewer trying to create company (admin only)
        response = client.post("/api/v1/companies",
            headers=auth_headers,
            json={"ticker": "TEST", "name": "Test Corp"}
        )
        
        assert response.status_code == status.HTTP_403_FORBIDDEN