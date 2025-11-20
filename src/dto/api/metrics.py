"""Financial metrics DTOs for API endpoints.

This module provides DTOs for financial and operational metrics:
- Metric time-series data
- Metric CRUD operations
- Aggregated metrics and analytics
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from src.dto.base import BaseDTO, TimestampedDTO


class MetricBaseDTO(BaseDTO):
    """Base metric model with common fields."""

    metric_date: datetime = Field(
        ...,
        description="Date/timestamp for this metric value",
        examples=["2025-09-30T00:00:00Z"]
    )
    period_type: str = Field(
        ...,
        pattern="^(quarterly|annual|monthly|daily)$",
        description="Time period type for this metric",
        examples=["quarterly", "annual"]
    )
    metric_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Type of metric (e.g., revenue, mau, arpu, cac, nrr)",
        examples=["revenue", "monthly_active_users", "customer_acquisition_cost"]
    )
    metric_category: Optional[str] = Field(
        None,
        pattern="^(financial|operational|edtech_specific)$",
        description="Category of metric",
        examples=["financial", "operational"]
    )
    value: float = Field(
        ...,
        description="Numeric value of the metric"
    )
    unit: Optional[str] = Field(
        None,
        max_length=20,
        description="Unit of measurement (USD, percent, count, etc.)",
        examples=["USD", "percent", "count"]
    )


class MetricCreateDTO(MetricBaseDTO):
    """DTO for creating a new metric record."""

    company_id: UUID = Field(
        ...,
        description="Company UUID this metric belongs to"
    )
    source: Optional[str] = Field(
        None,
        max_length=50,
        description="Data source (sec_filing, api, manual, calculated)",
        examples=["sec_filing", "api", "manual"]
    )
    source_document_id: Optional[UUID] = Field(
        None,
        description="Source document UUID if extracted from filing"
    )
    confidence_score: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Confidence in the metric value (0-1)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "company_id": "123e4567-e89b-12d3-a456-426614174000",
                "metric_date": "2025-09-30T00:00:00Z",
                "period_type": "quarterly",
                "metric_type": "revenue",
                "metric_category": "financial",
                "value": 194500000,
                "unit": "USD",
                "source": "sec_filing",
                "source_document_id": "987e6543-e21b-12d3-a456-426614174999",
                "confidence_score": 1.0
            }
        }
    }


class MetricDTO(MetricBaseDTO, TimestampedDTO):
    """Full metric response DTO.

    Includes all metric fields plus system metadata.
    Note: Uses BigInteger ID due to TimescaleDB hypertable requirements.
    """

    id: int = Field(
        ...,
        description="Metric record ID (BigInteger for TimescaleDB)"
    )
    company_id: UUID = Field(
        ...,
        description="Company UUID this metric belongs to"
    )
    source: Optional[str] = Field(
        None,
        description="Data source"
    )
    source_document_id: Optional[UUID] = Field(
        None,
        description="Source document UUID if extracted from filing"
    )
    confidence_score: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Confidence in the metric value (0-1)"
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 123456,
                "company_id": "123e4567-e89b-12d3-a456-426614174000",
                "metric_date": "2025-09-30T00:00:00Z",
                "period_type": "quarterly",
                "metric_type": "revenue",
                "metric_category": "financial",
                "value": 194500000,
                "unit": "USD",
                "source": "sec_filing",
                "source_document_id": "987e6543-e21b-12d3-a456-426614174999",
                "confidence_score": 1.0,
                "created_at": "2025-10-01T10:00:00Z",
                "updated_at": "2025-10-01T10:00:00Z"
            }
        }
    }


class MetricListItemDTO(BaseDTO):
    """Lightweight metric DTO for list responses."""

    id: int = Field(
        ...,
        description="Metric record ID"
    )
    company_id: UUID = Field(
        ...,
        description="Company UUID"
    )
    metric_date: datetime = Field(
        ...,
        description="Metric date"
    )
    period_type: str = Field(
        ...,
        description="Period type"
    )
    metric_type: str = Field(
        ...,
        description="Metric type"
    )
    value: float = Field(
        ...,
        description="Metric value"
    )
    unit: Optional[str] = Field(
        None,
        description="Unit of measurement"
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 123456,
                "company_id": "123e4567-e89b-12d3-a456-426614174000",
                "metric_date": "2025-09-30T00:00:00Z",
                "period_type": "quarterly",
                "metric_type": "revenue",
                "value": 194500000,
                "unit": "USD"
            }
        }
    }


class MetricsListDTO(BaseDTO):
    """Response DTO for paginated metrics listings."""

    metrics: List[MetricListItemDTO] = Field(
        ...,
        description="List of metrics"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of metrics matching filters"
    )
    limit: int = Field(
        ...,
        ge=1,
        description="Maximum items per page"
    )
    offset: int = Field(
        ...,
        ge=0,
        description="Number of items skipped"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "metrics": [
                    {
                        "id": 123456,
                        "company_id": "123e4567-e89b-12d3-a456-426614174000",
                        "metric_date": "2025-09-30T00:00:00Z",
                        "period_type": "quarterly",
                        "metric_type": "revenue",
                        "value": 194500000,
                        "unit": "USD"
                    }
                ],
                "total": 1500,
                "limit": 100,
                "offset": 0
            }
        }
    }


class MetricFilterDTO(BaseDTO):
    """DTO for filtering metrics in list requests."""

    company_id: Optional[UUID] = Field(
        None,
        description="Filter by company ID"
    )
    metric_type: Optional[str] = Field(
        None,
        description="Filter by metric type"
    )
    metric_category: Optional[str] = Field(
        None,
        pattern="^(financial|operational|edtech_specific)$",
        description="Filter by metric category"
    )
    period_type: Optional[str] = Field(
        None,
        pattern="^(quarterly|annual|monthly|daily)$",
        description="Filter by period type"
    )
    date_start: Optional[datetime] = Field(
        None,
        description="Filter metrics after this date"
    )
    date_end: Optional[datetime] = Field(
        None,
        description="Filter metrics before this date"
    )

    @field_validator("date_end")
    @classmethod
    def validate_date_range(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Ensure end date is after start date."""
        if v and info.data.get("date_start"):
            if v < info.data["date_start"]:
                raise ValueError("date_end must be after date_start")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "company_id": "123e4567-e89b-12d3-a456-426614174000",
                "metric_type": "revenue",
                "metric_category": "financial",
                "period_type": "quarterly",
                "date_start": "2024-01-01T00:00:00Z",
                "date_end": "2025-12-31T23:59:59Z"
            }
        }
    }


class MetricAggregationDTO(BaseDTO):
    """DTO for aggregated metric statistics.

    Used for analytics and dashboard endpoints.
    """

    metric_type: str = Field(
        ...,
        description="Type of metric being aggregated"
    )
    company_id: Optional[UUID] = Field(
        None,
        description="Company ID if aggregating for single company"
    )
    period_start: datetime = Field(
        ...,
        description="Start of aggregation period"
    )
    period_end: datetime = Field(
        ...,
        description="End of aggregation period"
    )
    count: int = Field(
        ...,
        ge=0,
        description="Number of data points in aggregation"
    )
    min_value: Optional[float] = Field(
        None,
        description="Minimum value in period"
    )
    max_value: Optional[float] = Field(
        None,
        description="Maximum value in period"
    )
    avg_value: Optional[float] = Field(
        None,
        description="Average value in period"
    )
    latest_value: Optional[float] = Field(
        None,
        description="Most recent value in period"
    )
    growth_rate: Optional[float] = Field(
        None,
        description="Growth rate over the period (percentage)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "metric_type": "revenue",
                "company_id": "123e4567-e89b-12d3-a456-426614174000",
                "period_start": "2024-01-01T00:00:00Z",
                "period_end": "2025-12-31T23:59:59Z",
                "count": 8,
                "min_value": 180000000,
                "max_value": 205000000,
                "avg_value": 192500000,
                "latest_value": 194500000,
                "growth_rate": 5.3
            }
        }
    }
