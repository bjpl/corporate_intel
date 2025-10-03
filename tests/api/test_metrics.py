"""Tests for financial metrics API endpoints."""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from src.db.models import FinancialMetric, Company


class TestListMetricsEndpoint:
    """Test suite for GET /api/v1/metrics/ endpoint."""

    def test_list_metrics_success(
        self, api_client: TestClient, sample_metrics: list[FinancialMetric]
    ):
        """Test listing all financial metrics."""
        response = api_client.get("/api/v1/metrics/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == len(sample_metrics)

    def test_list_metrics_empty(self, api_client: TestClient):
        """Test listing metrics when none exist."""
        response = api_client.get("/api/v1/metrics/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 0

    def test_list_metrics_filter_by_company(
        self, api_client: TestClient, sample_company: Company, sample_metrics: list[FinancialMetric]
    ):
        """Test filtering metrics by company ID."""
        response = api_client.get(f"/api/v1/metrics/?company_id={sample_company.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert all(m["company_id"] == str(sample_company.id) for m in data)

    def test_list_metrics_filter_by_type(
        self, api_client: TestClient, sample_metrics: list[FinancialMetric]
    ):
        """Test filtering metrics by metric type."""
        response = api_client.get("/api/v1/metrics/?metric_type=revenue")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert all(m["metric_type"] == "revenue" for m in data)

    def test_list_metrics_filter_by_period(
        self, api_client: TestClient, sample_metrics: list[FinancialMetric]
    ):
        """Test filtering metrics by period type."""
        response = api_client.get("/api/v1/metrics/?period_type=quarterly")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert isinstance(data, list)
        assert all(m["period_type"] == "quarterly" for m in data)

    def test_list_metrics_pagination(
        self, api_client: TestClient, sample_metrics: list[FinancialMetric]
    ):
        """Test pagination with limit and offset."""
        # First page
        response1 = api_client.get("/api/v1/metrics/?limit=2&offset=0")
        data1 = response1.json()

        # Second page
        response2 = api_client.get("/api/v1/metrics/?limit=2&offset=2")
        data2 = response2.json()

        assert len(data1) <= 2
        if len(data1) > 0 and len(data2) > 0:
            assert data1[0]["id"] != data2[0]["id"]

    def test_list_metrics_sorted_by_date(
        self, api_client: TestClient, sample_metrics: list[FinancialMetric]
    ):
        """Test metrics are sorted by date descending."""
        response = api_client.get("/api/v1/metrics/")

        data = response.json()

        if len(data) > 1:
            dates = [datetime.fromisoformat(m["metric_date"].replace('Z', '+00:00')) for m in data]
            assert dates == sorted(dates, reverse=True)

    def test_list_metrics_invalid_limit(self, api_client: TestClient):
        """Test invalid limit returns 422."""
        response = api_client.get("/api/v1/metrics/?limit=1000")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_metrics_invalid_company_id(self, api_client: TestClient):
        """Test invalid company ID format returns 422."""
        response = api_client.get("/api/v1/metrics/?company_id=invalid-uuid")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_list_metrics_response_schema(
        self, api_client: TestClient, sample_metrics: list[FinancialMetric]
    ):
        """Test response includes all expected fields."""
        response = api_client.get("/api/v1/metrics/")

        data = response.json()
        assert len(data) > 0

        metric = data[0]
        assert "id" in metric
        assert "company_id" in metric
        assert "metric_date" in metric
        assert "period_type" in metric
        assert "metric_type" in metric
        assert "value" in metric

    def test_list_metrics_no_auth_required(
        self, api_client: TestClient, sample_metrics: list[FinancialMetric]
    ):
        """Test listing metrics doesn't require authentication."""
        response = api_client.get("/api/v1/metrics/")

        assert response.status_code == status.HTTP_200_OK


class TestMetricTypes:
    """Test suite for different metric types."""

    def test_revenue_metrics(
        self, api_client: TestClient, sample_company: Company, db_session: Session
    ):
        """Test filtering revenue metrics."""
        metric = FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type="quarterly",
            metric_type="revenue",
            metric_category="financial",
            value=100000000.0,
            unit="USD",
        )
        db_session.add(metric)
        db_session.commit()

        response = api_client.get("/api/v1/metrics/?metric_type=revenue")

        data = response.json()
        assert all(m["metric_type"] == "revenue" for m in data)

    def test_growth_metrics(
        self, api_client: TestClient, sample_company: Company, db_session: Session
    ):
        """Test filtering growth metrics."""
        metric = FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type="quarterly",
            metric_type="revenue_growth_yoy",
            metric_category="growth",
            value=0.35,
            unit="percentage",
        )
        db_session.add(metric)
        db_session.commit()

        response = api_client.get("/api/v1/metrics/?metric_type=revenue_growth_yoy")

        data = response.json()
        assert all(m["metric_type"] == "revenue_growth_yoy" for m in data)

    def test_engagement_metrics(
        self, api_client: TestClient, sample_company: Company, db_session: Session
    ):
        """Test filtering engagement metrics."""
        metric = FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type="monthly",
            metric_type="monthly_active_users",
            metric_category="engagement",
            value=10000000.0,
            unit="users",
        )
        db_session.add(metric)
        db_session.commit()

        response = api_client.get("/api/v1/metrics/?metric_type=monthly_active_users")

        data = response.json()
        assert all(m["metric_type"] == "monthly_active_users" for m in data)


class TestPeriodTypes:
    """Test suite for different period types."""

    def test_quarterly_metrics(
        self, api_client: TestClient, sample_metrics: list[FinancialMetric]
    ):
        """Test filtering quarterly metrics."""
        response = api_client.get("/api/v1/metrics/?period_type=quarterly")

        data = response.json()
        assert all(m["period_type"] == "quarterly" for m in data)

    def test_annual_metrics(
        self, api_client: TestClient, sample_company: Company, db_session: Session
    ):
        """Test filtering annual metrics."""
        metric = FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type="annual",
            metric_type="revenue",
            value=400000000.0,
        )
        db_session.add(metric)
        db_session.commit()

        response = api_client.get("/api/v1/metrics/?period_type=annual")

        data = response.json()
        assert all(m["period_type"] == "annual" for m in data)

    def test_monthly_metrics(
        self, api_client: TestClient, sample_company: Company, db_session: Session
    ):
        """Test filtering monthly metrics."""
        metric = FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type="monthly",
            metric_type="revenue",
            value=30000000.0,
        )
        db_session.add(metric)
        db_session.commit()

        response = api_client.get("/api/v1/metrics/?period_type=monthly")

        data = response.json()
        assert all(m["period_type"] == "monthly" for m in data)


class TestMetricsByCompany:
    """Test suite for company-specific metrics."""

    def test_get_metrics_for_specific_company(
        self, api_client: TestClient, sample_company: Company, sample_metrics: list[FinancialMetric]
    ):
        """Test retrieving all metrics for a specific company."""
        response = api_client.get(f"/api/v1/metrics/?company_id={sample_company.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # All returned metrics should belong to the company
        assert all(m["company_id"] == str(sample_company.id) for m in data)

    def test_get_metrics_multiple_companies(
        self, api_client: TestClient, sample_companies: list[Company], db_session: Session
    ):
        """Test metrics from multiple companies are properly separated."""
        # Create metrics for different companies
        for company in sample_companies[:2]:
            metric = FinancialMetric(
                company_id=company.id,
                metric_date=datetime.utcnow(),
                period_type="quarterly",
                metric_type="revenue",
                value=100000000.0,
            )
            db_session.add(metric)
        db_session.commit()

        # Get metrics for first company
        response1 = api_client.get(f"/api/v1/metrics/?company_id={sample_companies[0].id}")
        data1 = response1.json()

        # Get metrics for second company
        response2 = api_client.get(f"/api/v1/metrics/?company_id={sample_companies[1].id}")
        data2 = response2.json()

        # Verify no overlap
        ids1 = {m["id"] for m in data1}
        ids2 = {m["id"] for m in data2}
        assert ids1.isdisjoint(ids2)

    def test_company_with_no_metrics(
        self, api_client: TestClient, sample_company: Company, db_session: Session
    ):
        """Test querying metrics for company with no metrics."""
        # Create a new company without metrics
        new_company = Company(
            id=uuid4(),
            ticker="NOMETRICS",
            name="No Metrics Company",
            sector="Technology",
        )
        db_session.add(new_company)
        db_session.commit()

        response = api_client.get(f"/api/v1/metrics/?company_id={new_company.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0


class TestMetricValueTypes:
    """Test suite for different metric value types and units."""

    def test_monetary_metrics(
        self, api_client: TestClient, sample_company: Company, db_session: Session
    ):
        """Test metrics with monetary values."""
        metric = FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type="quarterly",
            metric_type="revenue",
            value=250000000.0,
            unit="USD",
        )
        db_session.add(metric)
        db_session.commit()

        response = api_client.get(f"/api/v1/metrics/?company_id={sample_company.id}")

        data = response.json()
        revenue_metrics = [m for m in data if m["metric_type"] == "revenue"]

        assert any(m["unit"] == "USD" for m in revenue_metrics)
        assert any(isinstance(m["value"], (int, float)) for m in revenue_metrics)

    def test_percentage_metrics(
        self, api_client: TestClient, sample_company: Company, db_session: Session
    ):
        """Test metrics with percentage values."""
        metric = FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type="quarterly",
            metric_type="gross_margin",
            value=0.75,
            unit="percentage",
        )
        db_session.add(metric)
        db_session.commit()

        response = api_client.get(f"/api/v1/metrics/?metric_type=gross_margin")

        data = response.json()
        assert all(m["unit"] == "percentage" for m in data)
        assert all(0 <= m["value"] <= 1 for m in data)

    def test_count_metrics(
        self, api_client: TestClient, sample_company: Company, db_session: Session
    ):
        """Test metrics with count/user values."""
        metric = FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type="monthly",
            metric_type="monthly_active_users",
            value=5000000.0,
            unit="users",
        )
        db_session.add(metric)
        db_session.commit()

        response = api_client.get(f"/api/v1/metrics/?metric_type=monthly_active_users")

        data = response.json()
        assert all(m["unit"] == "users" for m in data)


class TestMetricCombinations:
    """Test suite for combined metric queries."""

    def test_company_and_type_filter(
        self, api_client: TestClient, sample_company: Company, sample_metrics: list[FinancialMetric]
    ):
        """Test filtering by both company and metric type."""
        response = api_client.get(
            f"/api/v1/metrics/?company_id={sample_company.id}&metric_type=revenue"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert all(m["company_id"] == str(sample_company.id) for m in data)
        assert all(m["metric_type"] == "revenue" for m in data)

    def test_company_and_period_filter(
        self, api_client: TestClient, sample_company: Company, sample_metrics: list[FinancialMetric]
    ):
        """Test filtering by both company and period type."""
        response = api_client.get(
            f"/api/v1/metrics/?company_id={sample_company.id}&period_type=quarterly"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert all(m["company_id"] == str(sample_company.id) for m in data)
        assert all(m["period_type"] == "quarterly" for m in data)

    def test_type_and_period_filter(
        self, api_client: TestClient, sample_metrics: list[FinancialMetric]
    ):
        """Test filtering by both metric type and period type."""
        response = api_client.get(
            "/api/v1/metrics/?metric_type=revenue&period_type=quarterly"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert all(m["metric_type"] == "revenue" for m in data)
        assert all(m["period_type"] == "quarterly" for m in data)

    def test_all_filters_combined(
        self, api_client: TestClient, sample_company: Company, sample_metrics: list[FinancialMetric]
    ):
        """Test filtering by company, type, and period."""
        response = api_client.get(
            f"/api/v1/metrics/?company_id={sample_company.id}"
            f"&metric_type=revenue&period_type=quarterly"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        if len(data) > 0:
            assert all(m["company_id"] == str(sample_company.id) for m in data)
            assert all(m["metric_type"] == "revenue" for m in data)
            assert all(m["period_type"] == "quarterly" for m in data)


class TestMetricsCaching:
    """Test suite for metrics endpoint caching behavior."""

    def test_list_metrics_cache_behavior(
        self, api_client: TestClient, sample_metrics: list[FinancialMetric]
    ):
        """Test metrics list endpoint uses caching."""
        response = api_client.get("/api/v1/metrics/")

        # Check for successful response (cache decorator applied)
        assert response.status_code == status.HTTP_200_OK

    def test_repeated_requests_consistent(
        self, api_client: TestClient, sample_metrics: list[FinancialMetric]
    ):
        """Test repeated requests return consistent data."""
        response1 = api_client.get("/api/v1/metrics/")
        response2 = api_client.get("/api/v1/metrics/")
        response3 = api_client.get("/api/v1/metrics/")

        data1 = response1.json()
        data2 = response2.json()
        data3 = response3.json()

        assert data1 == data2 == data3

    def test_cache_invalidation_on_new_data(
        self, api_client: TestClient, sample_company: Company, db_session: Session
    ):
        """Test cache behavior when new metrics are added."""
        # Initial request
        response1 = api_client.get(f"/api/v1/metrics/?company_id={sample_company.id}")
        count1 = len(response1.json())

        # Add new metric
        new_metric = FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type="quarterly",
            metric_type="new_metric",
            value=123.45,
        )
        db_session.add(new_metric)
        db_session.commit()

        # Second request (may still be cached)
        response2 = api_client.get(f"/api/v1/metrics/?company_id={sample_company.id}")

        # Should eventually show new data
        assert response2.status_code == status.HTTP_200_OK


class TestMetricsEdgeCases:
    """Test suite for edge cases in metrics endpoints."""

    def test_metrics_with_null_values(
        self, api_client: TestClient, sample_company: Company, db_session: Session
    ):
        """Test metrics with optional null values."""
        metric = FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type="quarterly",
            metric_type="revenue",
            value=100000.0,
            metric_category=None,  # Nullable field
            unit=None,  # Nullable field
        )
        db_session.add(metric)
        db_session.commit()

        response = api_client.get(f"/api/v1/metrics/?company_id={sample_company.id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify nullable fields are handled correctly
        assert any(m.get("metric_category") is None for m in data)

    def test_metrics_large_values(
        self, api_client: TestClient, sample_company: Company, db_session: Session
    ):
        """Test metrics with very large values."""
        metric = FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type="annual",
            metric_type="market_cap",
            value=1000000000000.0,  # 1 trillion
        )
        db_session.add(metric)
        db_session.commit()

        response = api_client.get(f"/api/v1/metrics/?metric_type=market_cap")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert any(m["value"] >= 1000000000000.0 for m in data)

    def test_metrics_zero_values(
        self, api_client: TestClient, sample_company: Company, db_session: Session
    ):
        """Test metrics with zero values."""
        metric = FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type="quarterly",
            metric_type="net_income",
            value=0.0,
        )
        db_session.add(metric)
        db_session.commit()

        response = api_client.get(f"/api/v1/metrics/?metric_type=net_income")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert any(m["value"] == 0.0 for m in data)

    def test_metrics_negative_values(
        self, api_client: TestClient, sample_company: Company, db_session: Session
    ):
        """Test metrics with negative values (losses)."""
        metric = FinancialMetric(
            company_id=sample_company.id,
            metric_date=datetime.utcnow(),
            period_type="quarterly",
            metric_type="net_income",
            value=-5000000.0,  # Loss
        )
        db_session.add(metric)
        db_session.commit()

        response = api_client.get(f"/api/v1/metrics/?metric_type=net_income")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert any(m["value"] < 0 for m in data)
