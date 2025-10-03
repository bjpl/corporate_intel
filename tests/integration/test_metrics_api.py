"""
Integration tests for Financial Metrics API endpoints.
Tests time-series queries, bulk operations, and TimescaleDB integration.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, List

from app.main import app
from app.models.company import Company, CompanyStatus
from app.models.metrics import FinancialMetric, MetricType


class TestMetricsAPI:
    """Integration tests for financial metrics endpoints."""

    @pytest.fixture(autouse=True)
    def setup(self, client: TestClient, db: Session, auth_headers: Dict[str, str]):
        """Setup test fixtures."""
        self.client = client
        self.db = db
        self.headers = auth_headers

        # Create test company
        self.company = Company(
            name="MetricTest Corp",
            ticker="MTST",
            industry="Technology",
            sector="Software",
            status=CompanyStatus.ACTIVE
        )
        self.db.add(self.company)
        self.db.commit()

        # Create time-series metrics
        base_date = datetime(2024, 1, 1)
        self.test_metrics = []

        for i in range(12):  # 12 months of data
            metric_date = base_date + timedelta(days=30 * i)

            metrics = [
                FinancialMetric(
                    company_id=self.company.id,
                    metric_type=MetricType.REVENUE,
                    value=1000000 + (i * 50000),
                    period_start=metric_date,
                    period_end=metric_date + timedelta(days=30),
                    currency="USD"
                ),
                FinancialMetric(
                    company_id=self.company.id,
                    metric_type=MetricType.PROFIT,
                    value=100000 + (i * 5000),
                    period_start=metric_date,
                    period_end=metric_date + timedelta(days=30),
                    currency="USD"
                ),
                FinancialMetric(
                    company_id=self.company.id,
                    metric_type=MetricType.EXPENSES,
                    value=900000 + (i * 45000),
                    period_start=metric_date,
                    period_end=metric_date + timedelta(days=30),
                    currency="USD"
                )
            ]
            self.test_metrics.extend(metrics)

        for metric in self.test_metrics:
            self.db.add(metric)
        self.db.commit()

        yield

        # Cleanup
        self.db.query(FinancialMetric).delete()
        self.db.query(Company).delete()
        self.db.commit()

    def test_get_metrics_success(self):
        """Test GET /metrics - successful retrieval."""
        response = self.client.get(
            f"/api/v1/metrics?company_id={self.company.id}",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 36  # 12 months * 3 metric types

    def test_get_metrics_time_range(self):
        """Test GET /metrics with time range filter."""
        start_date = "2024-01-01"
        end_date = "2024-03-31"

        response = self.client.get(
            f"/api/v1/metrics?company_id={self.company.id}"
            f"&start_date={start_date}&end_date={end_date}",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()

        # Should return metrics for Q1 only
        for item in data["items"]:
            period_start = datetime.fromisoformat(
                item["period_start"].replace("Z", "+00:00")
            )
            assert period_start >= datetime(2024, 1, 1)
            assert period_start <= datetime(2024, 3, 31)

    def test_get_metrics_by_type(self):
        """Test GET /metrics filtered by metric type."""
        response = self.client.get(
            f"/api/v1/metrics?company_id={self.company.id}"
            f"&metric_type=revenue",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert all(
            item["metric_type"] == "revenue"
            for item in data["items"]
        )
        assert data["total"] >= 12  # 12 months of revenue data

    def test_get_metrics_pagination(self):
        """Test GET /metrics with pagination."""
        response = self.client.get(
            f"/api/v1/metrics?company_id={self.company.id}"
            f"&skip=10&limit=5",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 5

    def test_get_metrics_sort_by_date(self):
        """Test GET /metrics sorted by date."""
        response = self.client.get(
            f"/api/v1/metrics?company_id={self.company.id}"
            f"&sort_by=period_start&sort_order=desc",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        dates = [
            datetime.fromisoformat(item["period_start"].replace("Z", "+00:00"))
            for item in data["items"]
        ]
        assert dates == sorted(dates, reverse=True)

    def test_get_metrics_unauthorized(self):
        """Test GET /metrics without authentication."""
        response = self.client.get(
            f"/api/v1/metrics?company_id={self.company.id}"
        )
        assert response.status_code == 401

    def test_post_metrics_bulk_success(self):
        """Test POST /metrics - bulk insert."""
        payload = {
            "metrics": [
                {
                    "company_id": self.company.id,
                    "metric_type": "revenue",
                    "value": 2000000,
                    "period_start": "2024-12-01T00:00:00Z",
                    "period_end": "2024-12-31T23:59:59Z",
                    "currency": "USD"
                },
                {
                    "company_id": self.company.id,
                    "metric_type": "profit",
                    "value": 200000,
                    "period_start": "2024-12-01T00:00:00Z",
                    "period_end": "2024-12-31T23:59:59Z",
                    "currency": "USD"
                }
            ]
        }

        response = self.client.post(
            "/api/v1/metrics/bulk",
            json=payload,
            headers=self.headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["inserted"] == 2
        assert "metrics" in data

        # Verify in database
        metrics = self.db.query(FinancialMetric).filter(
            FinancialMetric.period_start >= datetime(2024, 12, 1)
        ).all()
        assert len(metrics) >= 2

    def test_post_metrics_bulk_validation_error(self):
        """Test POST /metrics with validation errors."""
        payload = {
            "metrics": [
                {
                    "company_id": self.company.id,
                    "metric_type": "revenue",
                    "value": -1000,  # Negative value
                    "period_start": "2024-12-01T00:00:00Z",
                    "period_end": "2024-12-31T23:59:59Z"
                }
            ]
        }

        response = self.client.post(
            "/api/v1/metrics/bulk",
            json=payload,
            headers=self.headers
        )
        assert response.status_code == 422

    def test_post_metrics_bulk_unauthorized(self):
        """Test POST /metrics without authentication."""
        payload = {"metrics": []}
        response = self.client.post("/api/v1/metrics/bulk", json=payload)
        assert response.status_code == 401

    def test_get_metrics_aggregations_sum(self):
        """Test GET /metrics/aggregations - sum aggregation."""
        response = self.client.get(
            f"/api/v1/metrics/aggregations"
            f"?company_id={self.company.id}"
            f"&metric_type=revenue"
            f"&aggregation=sum",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "aggregation" in data
        assert data["aggregation"] == "sum"
        assert "value" in data
        assert data["value"] > 0

    def test_get_metrics_aggregations_avg(self):
        """Test GET /metrics/aggregations - average aggregation."""
        response = self.client.get(
            f"/api/v1/metrics/aggregations"
            f"?company_id={self.company.id}"
            f"&metric_type=profit"
            f"&aggregation=avg",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["aggregation"] == "avg"
        assert "value" in data

    def test_get_metrics_aggregations_time_bucket(self):
        """Test GET /metrics/aggregations with time buckets."""
        response = self.client.get(
            f"/api/v1/metrics/aggregations"
            f"?company_id={self.company.id}"
            f"&metric_type=revenue"
            f"&aggregation=sum"
            f"&bucket=month",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "buckets" in data
        assert len(data["buckets"]) > 0

        # Verify bucket structure
        bucket = data["buckets"][0]
        assert "time_bucket" in bucket
        assert "value" in bucket

    def test_get_metrics_aggregations_multiple_metrics(self):
        """Test GET /metrics/aggregations for multiple metric types."""
        response = self.client.get(
            f"/api/v1/metrics/aggregations"
            f"?company_id={self.company.id}"
            f"&metric_types=revenue,profit,expenses"
            f"&aggregation=avg",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 3

    def test_timescaledb_hypertable_query(self):
        """Test TimescaleDB hypertable optimized queries."""
        # Query with time_bucket function (TimescaleDB-specific)
        response = self.client.get(
            f"/api/v1/metrics/timeseries"
            f"?company_id={self.company.id}"
            f"&metric_type=revenue"
            f"&interval=1 month",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "timeseries" in data
        assert len(data["timeseries"]) > 0

    def test_metrics_continuous_aggregates(self):
        """Test continuous aggregates materialized views."""
        response = self.client.get(
            f"/api/v1/metrics/continuous-agg"
            f"?company_id={self.company.id}"
            f"&view=monthly_revenue",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_metrics_performance_large_dataset(self):
        """Test query performance with large dataset."""
        import time

        start_time = time.time()
        response = self.client.get(
            f"/api/v1/metrics?company_id={self.company.id}&limit=1000",
            headers=self.headers
        )
        elapsed = time.time() - start_time

        assert response.status_code == 200
        assert elapsed < 2.0  # Should complete in less than 2 seconds

    def test_metrics_currency_conversion(self):
        """Test metrics with currency conversion."""
        response = self.client.get(
            f"/api/v1/metrics?company_id={self.company.id}"
            f"&metric_type=revenue"
            f"&convert_to=EUR",
            headers=self.headers
        )

        assert response.status_code == 200
        data = response.json()
        assert all(
            item.get("converted_currency") == "EUR"
            for item in data["items"]
            if "converted_currency" in item
        )
