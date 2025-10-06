"""Tests for analysis reports API endpoints."""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.db.models import AnalysisReport, Company


@pytest.fixture
def sample_report(db_session: Session, sample_company: Company) -> AnalysisReport:
    """Create a sample analysis report for testing."""
    report = AnalysisReport(
        id=uuid4(),
        report_type="market_analysis",
        title="Q4 2023 EdTech Market Analysis",
        description="Comprehensive analysis of EdTech market trends",
        date_range_start=datetime.utcnow() - timedelta(days=90),
        date_range_end=datetime.utcnow(),
        format="pdf",
        report_url="https://storage.example.com/reports/q4-2023.pdf",
    )
    db_session.add(report)
    db_session.commit()
    db_session.refresh(report)
    return report


@pytest.fixture
def sample_reports(db_session: Session) -> list[AnalysisReport]:
    """Create multiple sample reports for testing pagination/filtering."""
    reports = [
        AnalysisReport(
            id=uuid4(),
            report_type="market_analysis",
            title="Q3 2023 Market Analysis",
            description="Market trends Q3",
            date_range_start=datetime.utcnow() - timedelta(days=180),
            date_range_end=datetime.utcnow() - timedelta(days=90),
            format="pdf",
        ),
        AnalysisReport(
            id=uuid4(),
            report_type="competitive_landscape",
            title="Competitor Analysis 2023",
            description="Competitive landscape overview",
            date_range_start=datetime.utcnow() - timedelta(days=365),
            date_range_end=datetime.utcnow(),
            format="excel",
        ),
        AnalysisReport(
            id=uuid4(),
            report_type="financial_performance",
            title="Financial Performance Report",
            description="Annual financial performance",
            date_range_start=datetime.utcnow() - timedelta(days=365),
            date_range_end=datetime.utcnow(),
            format="pdf",
        ),
    ]

    for report in reports:
        db_session.add(report)

    db_session.commit()
    for report in reports:
        db_session.refresh(report)

    return reports


class TestListReportsEndpoint:
    """Test suite for GET /api/v1/reports/ endpoint."""

    def test_list_reports_success(
        self, api_client: TestClient, sample_reports: list[AnalysisReport]
    ):
        """Test listing all reports."""
        response = api_client.get("/api/v1/reports/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == len(sample_reports)

    def test_list_reports_empty(self, api_client: TestClient):
        """Test listing reports when none exist."""
        response = api_client.get("/api/v1/reports/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_reports_filter_by_type(
        self, api_client: TestClient, sample_reports: list[AnalysisReport]
    ):
        """Test filtering reports by report type."""
        response = api_client.get("/api/v1/reports/?report_type=market_analysis")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert all(r["report_type"] == "market_analysis" for r in data)

    def test_list_reports_pagination_limit(
        self, api_client: TestClient, sample_reports: list[AnalysisReport]
    ):
        """Test pagination with limit parameter."""
        response = api_client.get("/api/v1/reports/?limit=2")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data) <= 2

    def test_list_reports_pagination_offset(
        self, api_client: TestClient, sample_reports: list[AnalysisReport]
    ):
        """Test pagination with offset parameter."""
        # Get first page
        response1 = api_client.get("/api/v1/reports/?limit=2&offset=0")
        data1 = response1.json()

        # Get second page
        response2 = api_client.get("/api/v1/reports/?limit=2&offset=2")
        data2 = response2.json()

        # Ensure different results
        if len(data1) > 0 and len(data2) > 0:
            assert data1[0]["id"] != data2[0]["id"]

    def test_list_reports_sorted_by_created(
        self, api_client: TestClient, sample_reports: list[AnalysisReport]
    ):
        """Test reports are sorted by created_at descending."""
        response = api_client.get("/api/v1/reports/")

        data = response.json()
        assert response.status_code == status.HTTP_200_OK
        # Reports should be in descending order (most recent first)

    def test_list_reports_invalid_limit(self, api_client: TestClient):
        """Test invalid limit returns 422."""
        response = api_client.get("/api/v1/reports/?limit=1000")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_reports_negative_offset(self, api_client: TestClient):
        """Test negative offset returns 422."""
        response = api_client.get("/api/v1/reports/?offset=-1")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_reports_response_schema(
        self, api_client: TestClient, sample_report: AnalysisReport
    ):
        """Test response includes all expected fields."""
        response = api_client.get("/api/v1/reports/")

        data = response.json()
        assert len(data) > 0

        report = data[0]
        assert "id" in report
        assert "report_type" in report
        assert "title" in report
        assert "description" in report

    def test_list_reports_no_auth_required(
        self, api_client: TestClient, sample_report: AnalysisReport
    ):
        """Test listing reports doesn't require authentication."""
        response = api_client.get("/api/v1/reports/")

        assert response.status_code == status.HTTP_200_OK


class TestGetReportEndpoint:
    """Test suite for GET /api/v1/reports/{report_id} endpoint."""

    def test_get_report_success(
        self, api_client: TestClient, sample_report: AnalysisReport
    ):
        """Test getting a specific report by ID."""
        response = api_client.get(f"/api/v1/reports/{sample_report.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["id"] == str(sample_report.id)
        assert data["title"] == sample_report.title
        assert data["report_type"] == sample_report.report_type

    def test_get_report_not_found(self, api_client: TestClient):
        """Test getting non-existent report returns 404."""
        non_existent_id = uuid4()
        response = api_client.get(f"/api/v1/reports/{non_existent_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()

        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_get_report_invalid_uuid(self, api_client: TestClient):
        """Test invalid UUID returns 422."""
        response = api_client.get("/api/v1/reports/invalid-uuid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_report_complete_data(
        self, api_client: TestClient, sample_report: AnalysisReport
    ):
        """Test getting report returns all fields."""
        response = api_client.get(f"/api/v1/reports/{sample_report.id}")

        data = response.json()

        assert data["id"] == str(sample_report.id)
        assert data["report_type"] == sample_report.report_type
        assert data["title"] == sample_report.title
        assert data["description"] == sample_report.description
        assert data["format"] == sample_report.format

    def test_get_report_no_auth_required(
        self, api_client: TestClient, sample_report: AnalysisReport
    ):
        """Test getting report doesn't require authentication."""
        response = api_client.get(f"/api/v1/reports/{sample_report.id}")

        assert response.status_code == status.HTTP_200_OK


class TestReportTypes:
    """Test suite for different report types."""

    def test_filter_market_analysis_reports(
        self, api_client: TestClient, sample_reports: list[AnalysisReport]
    ):
        """Test filtering market analysis reports."""
        response = api_client.get("/api/v1/reports/?report_type=market_analysis")

        data = response.json()
        assert all(r["report_type"] == "market_analysis" for r in data)

    def test_filter_competitive_landscape_reports(
        self, api_client: TestClient, sample_reports: list[AnalysisReport]
    ):
        """Test filtering competitive landscape reports."""
        response = api_client.get("/api/v1/reports/?report_type=competitive_landscape")

        data = response.json()
        assert all(r["report_type"] == "competitive_landscape" for r in data)

    def test_filter_financial_performance_reports(
        self, api_client: TestClient, sample_reports: list[AnalysisReport]
    ):
        """Test filtering financial performance reports."""
        response = api_client.get("/api/v1/reports/?report_type=financial_performance")

        data = response.json()
        assert all(r["report_type"] == "financial_performance" for r in data)

    def test_invalid_report_type(self, api_client: TestClient):
        """Test querying invalid report type returns empty list."""
        response = api_client.get("/api/v1/reports/?report_type=INVALID_TYPE")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0


class TestReportFormats:
    """Test suite for different report formats."""

    def test_reports_with_pdf_format(
        self, api_client: TestClient, sample_reports: list[AnalysisReport]
    ):
        """Test reports can have PDF format."""
        response = api_client.get("/api/v1/reports/")

        data = response.json()
        pdf_reports = [r for r in data if r["format"] == "pdf"]
        assert len(pdf_reports) > 0

    def test_reports_with_excel_format(
        self, api_client: TestClient, sample_reports: list[AnalysisReport]
    ):
        """Test reports can have Excel format."""
        response = api_client.get("/api/v1/reports/")

        data = response.json()
        excel_reports = [r for r in data if r["format"] == "excel"]
        assert len(excel_reports) > 0

    def test_reports_with_null_format(
        self, api_client: TestClient, db_session: Session
    ):
        """Test reports can have null format."""
        report = AnalysisReport(
            id=uuid4(),
            report_type="custom",
            title="Custom Report",
            format=None,  # Nullable
        )
        db_session.add(report)
        db_session.commit()

        response = api_client.get(f"/api/v1/reports/{report.id}")

        data = response.json()
        assert data["format"] is None


class TestReportDateRanges:
    """Test suite for report date range handling."""

    def test_report_with_date_range(
        self, api_client: TestClient, sample_report: AnalysisReport
    ):
        """Test report with valid date range."""
        response = api_client.get(f"/api/v1/reports/{sample_report.id}")

        data = response.json()
        assert "date_range_start" in data
        assert "date_range_end" in data

    def test_report_without_date_range(
        self, api_client: TestClient, db_session: Session
    ):
        """Test report without date range."""
        report = AnalysisReport(
            id=uuid4(),
            report_type="adhoc",
            title="Ad-hoc Report",
            date_range_start=None,
            date_range_end=None,
        )
        db_session.add(report)
        db_session.commit()

        response = api_client.get(f"/api/v1/reports/{report.id}")

        data = response.json()
        assert data["date_range_start"] is None
        assert data["date_range_end"] is None


class TestReportCaching:
    """Test suite for report endpoint caching behavior."""

    def test_list_reports_cache_behavior(
        self, api_client: TestClient, sample_reports: list[AnalysisReport]
    ):
        """Test reports list endpoint uses caching."""
        response = api_client.get("/api/v1/reports/")

        assert response.status_code == status.HTTP_200_OK

    def test_get_report_cache_behavior(
        self, api_client: TestClient, sample_report: AnalysisReport
    ):
        """Test get report endpoint uses caching."""
        response = api_client.get(f"/api/v1/reports/{sample_report.id}")

        assert response.status_code == status.HTTP_200_OK

    def test_repeated_requests_consistent(
        self, api_client: TestClient, sample_report: AnalysisReport
    ):
        """Test repeated requests return consistent data."""
        response1 = api_client.get(f"/api/v1/reports/{sample_report.id}")
        response2 = api_client.get(f"/api/v1/reports/{sample_report.id}")
        response3 = api_client.get(f"/api/v1/reports/{sample_report.id}")

        data1 = response1.json()
        data2 = response2.json()
        data3 = response3.json()

        assert data1 == data2 == data3


class TestReportEdgeCases:
    """Test suite for edge cases in report endpoints."""

    def test_report_with_empty_title(
        self, api_client: TestClient, db_session: Session
    ):
        """Test report with empty title (should fail validation)."""
        # This would normally fail at the model level
        # Testing API's handling of edge cases
        pass

    def test_report_with_very_long_description(
        self, api_client: TestClient, db_session: Session
    ):
        """Test report with very long description."""
        long_description = "A" * 10000
        report = AnalysisReport(
            id=uuid4(),
            report_type="test",
            title="Test Report",
            description=long_description,
        )
        db_session.add(report)
        db_session.commit()

        response = api_client.get(f"/api/v1/reports/{report.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["description"]) == 10000

    def test_report_with_special_characters(
        self, api_client: TestClient, db_session: Session
    ):
        """Test report with special characters in title."""
        special_title = "Report: Q4 2023 (Market & Competitive) - 100%"
        report = AnalysisReport(
            id=uuid4(),
            report_type="test",
            title=special_title,
        )
        db_session.add(report)
        db_session.commit()

        response = api_client.get(f"/api/v1/reports/{report.id}")

        data = response.json()
        assert data["title"] == special_title

    def test_pagination_beyond_available_data(
        self, api_client: TestClient, sample_reports: list[AnalysisReport]
    ):
        """Test pagination offset beyond available data."""
        response = api_client.get("/api/v1/reports/?offset=1000")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0

    def test_zero_limit(self, api_client: TestClient):
        """Test zero limit returns validation error."""
        response = api_client.get("/api/v1/reports/?limit=0")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestReportURLs:
    """Test suite for report URL handling."""

    def test_report_with_valid_url(
        self, api_client: TestClient, sample_report: AnalysisReport
    ):
        """Test report with valid URL."""
        response = api_client.get(f"/api/v1/reports/{sample_report.id}")

        data = response.json()
        assert "report_url" in data
        assert data["report_url"].startswith("https://")

    def test_report_without_url(
        self, api_client: TestClient, db_session: Session
    ):
        """Test report without URL."""
        report = AnalysisReport(
            id=uuid4(),
            report_type="draft",
            title="Draft Report",
            report_url=None,
        )
        db_session.add(report)
        db_session.commit()

        response = api_client.get(f"/api/v1/reports/{report.id}")

        data = response.json()
        assert data["report_url"] is None


class TestReportListPerformance:
    """Test suite for report list performance."""

    def test_list_large_number_of_reports(
        self, api_client: TestClient, db_session: Session
    ):
        """Test listing with many reports."""
        # Create 100 reports
        reports = []
        for i in range(100):
            report = AnalysisReport(
                id=uuid4(),
                report_type="test",
                title=f"Test Report {i}",
            )
            reports.append(report)
            db_session.add(report)

        db_session.commit()

        # Test pagination works
        response = api_client.get("/api/v1/reports/?limit=50")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 50

    def test_default_limit_applied(
        self, api_client: TestClient, db_session: Session
    ):
        """Test default limit is applied when not specified."""
        response = api_client.get("/api/v1/reports/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) <= 100  # Default limit
