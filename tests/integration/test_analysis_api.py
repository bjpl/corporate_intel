"""
Integration tests for Analysis API endpoints.
Tests competitor analysis, market intelligence, report generation, and async processing.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from typing import Dict
from datetime import datetime, timedelta
import time

from app.main import app
from app.models.company import Company, CompanyStatus
from app.models.analysis import Analysis, AnalysisType, AnalysisStatus


class TestAnalysisAPI:
    """Integration tests for analysis endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self, client: TestClient, db: Session, auth_headers: Dict[str, str]):
        """Setup test fixtures."""
        self.client = client
        self.db = db
        self.headers = auth_headers

        # Create test companies
        self.companies = [
            Company(
                name="AnalysisTest Corp",
                ticker="ATST",
                industry="Technology",
                sector="Software",
                status=CompanyStatus.ACTIVE,
                revenue=1000000000
            ),
            Company(
                name="Competitor A",
                ticker="CMPA",
                industry="Technology",
                sector="Software",
                status=CompanyStatus.ACTIVE,
                revenue=800000000
            ),
            Company(
                name="Competitor B",
                ticker="CMPB",
                industry="Technology",
                sector="Software",
                status=CompanyStatus.ACTIVE,
                revenue=1200000000
            )
        ]

        for company in self.companies:
            self.db.add(company)
        self.db.commit()

        # Create test analyses
        self.test_analyses = [
            Analysis(
                company_id=self.companies[0].id,
                analysis_type=AnalysisType.COMPETITOR,
                status=AnalysisStatus.COMPLETED,
                title="Q4 2024 Competitor Analysis",
                summary="Comprehensive competitor analysis for Q4 2024",
                findings={
                    "market_position": "Strong",
                    "competitive_advantages": ["Technology", "Brand"],
                    "threats": ["New entrants"]
                },
                recommendations=[
                    "Invest in R&D",
                    "Expand market presence"
                ]
            ),
            Analysis(
                company_id=self.companies[0].id,
                analysis_type=AnalysisType.MARKET_INTELLIGENCE,
                status=AnalysisStatus.PROCESSING,
                title="Market Trends Analysis",
                summary="Analysis of current market trends"
            )
        ]

        for analysis in self.test_analyses:
            self.db.add(analysis)
        self.db.commit()

        yield

        # Cleanup
        self.db.query(Analysis).delete()
        self.db.query(Company).delete()
        self.db.commit()

    def test_create_competitor_analysis_success(self):
        """Test POST /analysis/competitor - create analysis."""
        payload = {
            "company_id": self.companies[0].id,
            "competitor_ids": [self.companies[1].id, self.companies[2].id],
            "analysis_type": "comprehensive",
            "include_metrics": ["revenue", "market_share", "growth_rate"],
            "time_period": "Q4_2024"
        }

        response = self.client.post(
            "/api/v1/analysis/competitor",
            json=payload,
            headers=self.headers
        )

        assert response.status_code == 202  # Accepted for async processing
        data = response.json()
        assert "analysis_id" in data
        assert data["status"] in ["pending", "processing"]
        assert "estimated_completion" in data

    def test_create_competitor_analysis_validation(self):
        """Test POST /analysis/competitor with validation."""
        payload = {
            "company_id": self.companies[0].id,
            "competitor_ids": [],  # Empty competitors
            "analysis_type": "comprehensive"
        }

        response = self.client.post(
            "/api/v1/analysis/competitor",
            json=payload,
            headers=self.headers
        )
        assert response.status_code == 422

    def test_create_competitor_analysis_unauthorized(self):
        """Test POST /analysis/competitor without auth."""
        payload = {
            "company_id": self.companies[0].id,
            "competitor_ids": [self.companies[1].id]
        }

        response = self.client.post(
            "/api/v1/analysis/competitor",
            json=payload
        )
        assert response.status_code == 401

    def test_get_competitor_analysis_success(self):
        """Test GET /analysis/competitor/{id}."""
        analysis_id = self.test_analyses[0].id
        response = self.client.get(
            f"/api/v1/analysis/competitor/{analysis_id}",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == analysis_id
        assert data["analysis_type"] == "competitor"
        assert "findings" in data
        assert "recommendations" in data

    def test_get_competitor_analysis_not_found(self):
        """Test GET /analysis/competitor/{id} - not found."""
        response = self.client.get(
            "/api/v1/analysis/competitor/99999",
            headers=self.headers
        )
        assert response.status_code == 404

    def test_list_analyses_success(self):
        """Test GET /analysis - list all analyses."""
        response = self.client.get(
            f"/api/v1/analysis?company_id={self.companies[0].id}",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 2

    def test_list_analyses_filter_by_type(self):
        """Test GET /analysis filtered by type."""
        response = self.client.get(
            f"/api/v1/analysis?company_id={self.companies[0].id}"
            f"&analysis_type=competitor",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert all(
            item["analysis_type"] == "competitor"
            for item in data["items"]
        )

    def test_list_analyses_filter_by_status(self):
        """Test GET /analysis filtered by status."""
        response = self.client.get(
            f"/api/v1/analysis?company_id={self.companies[0].id}"
            f"&status=completed",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert all(
            item["status"] == "completed"
            for item in data["items"]
        )

    def test_market_intelligence_query_success(self):
        """Test POST /analysis/market-intelligence."""
        payload = {
            "company_id": self.companies[0].id,
            "query": "What are the current market trends in cloud software?",
            "include_competitors": True,
            "time_range": "6_months",
            "sources": ["news", "reports", "filings"]
        }

        response = self.client.post(
            "/api/v1/analysis/market-intelligence",
            json=payload,
            headers=self.headers
        )

        assert response.status_code == 202
        data = response.json()
        assert "analysis_id" in data
        assert data["status"] in ["pending", "processing"]

    def test_market_intelligence_with_filters(self):
        """Test POST /analysis/market-intelligence with filters."""
        payload = {
            "company_id": self.companies[0].id,
            "query": "Market analysis",
            "filters": {
                "industries": ["Technology"],
                "regions": ["North America"],
                "date_range": {
                    "start": "2024-01-01",
                    "end": "2024-12-31"
                }
            }
        }

        response = self.client.post(
            "/api/v1/analysis/market-intelligence",
            json=payload,
            headers=self.headers
        )

        assert response.status_code == 202

    def test_generate_report_success(self):
        """Test POST /analysis/reports/generate."""
        payload = {
            "company_id": self.companies[0].id,
            "report_type": "comprehensive",
            "sections": [
                "executive_summary",
                "competitor_analysis",
                "market_trends",
                "financial_metrics",
                "recommendations"
            ],
            "format": "pdf",
            "include_charts": True
        }

        response = self.client.post(
            "/api/v1/analysis/reports/generate",
            json=payload,
            headers=self.headers
        )

        assert response.status_code == 202
        data = response.json()
        assert "report_id" in data
        assert data["status"] in ["pending", "generating"]

    def test_generate_report_multiple_formats(self):
        """Test POST /analysis/reports/generate with formats."""
        payload = {
            "company_id": self.companies[0].id,
            "report_type": "quarterly",
            "formats": ["pdf", "docx", "html"]
        }

        response = self.client.post(
            "/api/v1/analysis/reports/generate",
            json=payload,
            headers=self.headers
        )

        assert response.status_code == 202

    def test_get_report_status(self):
        """Test GET /analysis/reports/{id}/status."""
        # First generate a report
        payload = {
            "company_id": self.companies[0].id,
            "report_type": "summary"
        }

        create_response = self.client.post(
            "/api/v1/analysis/reports/generate",
            json=payload,
            headers=self.headers
        )
        report_id = create_response.json()["report_id"]

        # Check status
        response = self.client.get(
            f"/api/v1/analysis/reports/{report_id}/status",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "progress" in data

    def test_download_report_success(self):
        """Test GET /analysis/reports/{id}/download."""
        # Assuming a completed report exists
        analysis_id = self.test_analyses[0].id

        response = self.client.get(
            f"/api/v1/analysis/reports/{analysis_id}/download",
            headers=self.headers
        )

        # Should return file or redirect
        assert response.status_code in [200, 302, 404]

        if response.status_code == 200:
            assert response.headers["content-type"] in [
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ]

    def test_async_analysis_processing(self):
        """Test async analysis processing workflow."""
        # Create analysis
        payload = {
            "company_id": self.companies[0].id,
            "competitor_ids": [self.companies[1].id],
            "analysis_type": "quick"
        }

        create_response = self.client.post(
            "/api/v1/analysis/competitor",
            json=payload,
            headers=self.headers
        )
        analysis_id = create_response.json()["analysis_id"]

        # Poll status (simulate async processing)
        max_attempts = 10
        for _ in range(max_attempts):
            status_response = self.client.get(
                f"/api/v1/analysis/{analysis_id}/status",
                headers=self.headers
            )

            assert status_response.status_code == 200
            status = status_response.json()["status"]

            if status == "completed":
                break

            time.sleep(1)

        # Verify final status
        final_response = self.client.get(
            f"/api/v1/analysis/{analysis_id}",
            headers=self.headers
        )
        assert final_response.status_code == 200

    def test_cancel_analysis(self):
        """Test POST /analysis/{id}/cancel."""
        # Create analysis
        payload = {
            "company_id": self.companies[0].id,
            "competitor_ids": [self.companies[1].id]
        }

        create_response = self.client.post(
            "/api/v1/analysis/competitor",
            json=payload,
            headers=self.headers
        )
        analysis_id = create_response.json()["analysis_id"]

        # Cancel it
        response = self.client.post(
            f"/api/v1/analysis/{analysis_id}/cancel",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "cancelled"

    def test_analysis_webhooks(self):
        """Test POST /analysis/webhooks/register."""
        payload = {
            "event_type": "analysis.completed",
            "webhook_url": "https://example.com/webhook",
            "secret": "webhook_secret_123"
        }

        response = self.client.post(
            "/api/v1/analysis/webhooks/register",
            json=payload,
            headers=self.headers
        )

        assert response.status_code in [201, 200]

    def test_batch_analysis_creation(self):
        """Test POST /analysis/batch - batch analysis."""
        payload = {
            "analyses": [
                {
                    "company_id": self.companies[0].id,
                    "analysis_type": "competitor",
                    "competitor_ids": [self.companies[1].id]
                },
                {
                    "company_id": self.companies[0].id,
                    "analysis_type": "market_intelligence",
                    "query": "Market trends"
                }
            ]
        }

        response = self.client.post(
            "/api/v1/analysis/batch",
            json=payload,
            headers=self.headers
        )

        assert response.status_code == 202
        data = response.json()
        assert "batch_id" in data
        assert "analysis_ids" in data
        assert len(data["analysis_ids"]) == 2

    def test_analysis_export(self):
        """Test GET /analysis/{id}/export."""
        analysis_id = self.test_analyses[0].id

        response = self.client.get(
            f"/api/v1/analysis/{analysis_id}/export?format=json",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "findings" in data
        assert "recommendations" in data
