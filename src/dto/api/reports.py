"""Analysis reports DTOs for API endpoints.

This module provides DTOs for analysis report generation and retrieval:
- Report generation requests
- Report listings and details
- Report metadata and status
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from src.dto.base import BaseDTO, IDMixin, TimestampedDTO


class ReportBaseDTO(BaseDTO):
    """Base report model with common fields."""

    report_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Type of report (competitive_landscape, company_performance, market_trends, segment_analysis)",
        examples=["competitive_landscape", "company_performance", "market_trends"]
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Report title",
        examples=["Q4 2025 EdTech Competitive Analysis", "K-12 Market Overview"]
    )
    description: Optional[str] = Field(
        None,
        description="Detailed report description"
    )
    date_range_start: Optional[datetime] = Field(
        None,
        description="Start of analysis period"
    )
    date_range_end: Optional[datetime] = Field(
        None,
        description="End of analysis period"
    )


class ReportGenerationRequestDTO(BaseDTO):
    """Request DTO for generating a new analysis report."""

    report_type: str = Field(
        ...,
        pattern="^(competitive_landscape|company_performance|market_trends|segment_analysis|opportunity_analysis)$",
        description="Type of report to generate"
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Report title"
    )
    description: Optional[str] = Field(
        None,
        description="Report description"
    )
    category_filter: Optional[str] = Field(
        None,
        pattern="^(k12|higher_education|corporate_learning|direct_to_consumer|enabling_technology)$",
        description="EdTech category filter"
    )
    company_ids: Optional[List[UUID]] = Field(
        None,
        max_length=50,
        description="Specific companies to include in analysis (max 50)"
    )
    date_range_days: int = Field(
        default=90,
        ge=1,
        le=365,
        description="Number of days to include in analysis (1-365)"
    )
    include_visualizations: bool = Field(
        default=True,
        description="Include charts and graphs in report"
    )
    include_recommendations: bool = Field(
        default=True,
        description="Include strategic recommendations"
    )
    format: str = Field(
        default="json",
        pattern="^(json|pdf|html|excel)$",
        description="Output format for the report"
    )

    @field_validator("company_ids")
    @classmethod
    def validate_company_limit(cls, v: Optional[List[UUID]]) -> Optional[List[UUID]]:
        """Ensure company list is not too large."""
        if v and len(v) > 50:
            raise ValueError("Cannot analyze more than 50 companies in a single report")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "report_type": "competitive_landscape",
                "title": "Q4 2025 K-12 EdTech Competitive Analysis",
                "description": "Comprehensive competitive landscape analysis for K-12 education technology sector",
                "category_filter": "k12",
                "date_range_days": 90,
                "include_visualizations": True,
                "include_recommendations": True,
                "format": "pdf"
            }
        }
    }


class ReportGenerationResponseDTO(BaseDTO):
    """Response DTO for report generation request."""

    report_id: UUID = Field(
        ...,
        description="UUID of the generated report"
    )
    status: str = Field(
        ...,
        pattern="^(completed|processing|failed|queued)$",
        description="Report generation status"
    )
    title: str = Field(
        ...,
        description="Report title"
    )
    report_type: str = Field(
        ...,
        description="Report type"
    )
    companies_analyzed: int = Field(
        ...,
        ge=0,
        description="Number of companies included in analysis"
    )
    metrics_included: int = Field(
        ...,
        ge=0,
        description="Number of metrics analyzed"
    )
    created_at: datetime = Field(
        ...,
        description="When the report was created"
    )
    report_url: Optional[str] = Field(
        None,
        description="URL to download/access the report"
    )
    estimated_completion: Optional[datetime] = Field(
        None,
        description="Estimated completion time for processing reports"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "report_id": "789e0123-e45f-67g8-h901-234567890123",
                "status": "completed",
                "title": "Q4 2025 K-12 EdTech Competitive Analysis",
                "report_type": "competitive_landscape",
                "companies_analyzed": 15,
                "metrics_included": 450,
                "created_at": "2025-11-20T10:00:00Z",
                "report_url": "https://s3.amazonaws.com/reports/789e0123.pdf"
            }
        }
    }


class ReportDTO(ReportBaseDTO, IDMixin, TimestampedDTO):
    """Full report response DTO.

    Includes all report fields, content, and metadata.
    """

    companies: Optional[List[UUID]] = Field(
        None,
        description="List of company UUIDs included in the report"
    )
    format: Optional[str] = Field(
        None,
        description="Report output format"
    )
    report_url: Optional[str] = Field(
        None,
        description="URL to the generated report file"
    )
    cache_key: Optional[str] = Field(
        None,
        description="Cache key for report caching"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="When the cached report expires"
    )

    # Large content fields
    executive_summary: Optional[str] = Field(
        None,
        description="Executive summary of key findings"
    )
    findings: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured findings and insights"
    )
    recommendations: Optional[Dict[str, Any]] = Field(
        None,
        description="Strategic recommendations based on analysis"
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "789e0123-e45f-67g8-h901-234567890123",
                "report_type": "market_trends",
                "title": "EdTech Market Trends Q4 2025",
                "description": "Analysis of market trends across all EdTech segments",
                "date_range_start": "2025-07-01T00:00:00Z",
                "date_range_end": "2025-09-30T00:00:00Z",
                "companies": [
                    "123e4567-e89b-12d3-a456-426614174000",
                    "456e7890-e12b-34d5-a678-901234567890"
                ],
                "format": "pdf",
                "report_url": "https://s3.amazonaws.com/reports/789e0123.pdf",
                "executive_summary": "Key findings from Q4 2025 analysis...",
                "findings": {
                    "market_size": "$30B",
                    "growth_rate": "15%",
                    "top_segments": ["k12", "corporate_learning"]
                },
                "recommendations": {
                    "investment_opportunities": ["AI tutoring", "corporate upskilling"],
                    "risk_factors": ["regulatory changes", "market consolidation"]
                },
                "created_at": "2025-11-20T10:00:00Z",
                "updated_at": "2025-11-20T10:00:00Z"
            }
        }
    }


class ReportListItemDTO(ReportBaseDTO, IDMixin):
    """Lightweight report DTO for list responses.

    Excludes large content fields to optimize performance.
    """

    format: Optional[str] = Field(
        None,
        description="Report output format"
    )
    report_url: Optional[str] = Field(
        None,
        description="URL to the generated report"
    )
    created_at: datetime = Field(
        ...,
        description="When the report was created"
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "789e0123-e45f-67g8-h901-234567890123",
                "report_type": "competitive_landscape",
                "title": "Q4 2025 EdTech Competitive Analysis",
                "description": "Competitive landscape for Q4 2025",
                "date_range_start": "2025-07-01T00:00:00Z",
                "date_range_end": "2025-09-30T00:00:00Z",
                "format": "pdf",
                "report_url": "https://s3.amazonaws.com/reports/789e0123.pdf",
                "created_at": "2025-11-20T10:00:00Z"
            }
        }
    }


class ReportListDTO(BaseDTO):
    """Response DTO for paginated report listings."""

    reports: List[ReportListItemDTO] = Field(
        ...,
        description="List of reports"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of reports matching filters"
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
                "reports": [
                    {
                        "id": "789e0123-e45f-67g8-h901-234567890123",
                        "report_type": "market_trends",
                        "title": "EdTech Market Trends Q3 2025",
                        "format": "pdf",
                        "created_at": "2025-10-15T10:00:00Z"
                    }
                ],
                "total": 45,
                "limit": 100,
                "offset": 0
            }
        }
    }


class ReportFilterDTO(BaseDTO):
    """DTO for filtering reports in list requests."""

    report_type: Optional[str] = Field(
        None,
        description="Filter by report type"
    )
    created_after: Optional[datetime] = Field(
        None,
        description="Filter reports created after this date"
    )
    created_before: Optional[datetime] = Field(
        None,
        description="Filter reports created before this date"
    )
    format: Optional[str] = Field(
        None,
        pattern="^(json|pdf|html|excel)$",
        description="Filter by report format"
    )

    @field_validator("created_before")
    @classmethod
    def validate_date_range(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Ensure end date is after start date."""
        if v and info.data.get("created_after"):
            if v < info.data["created_after"]:
                raise ValueError("created_before must be after created_after")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "report_type": "competitive_landscape",
                "created_after": "2025-01-01T00:00:00Z",
                "created_before": "2025-12-31T23:59:59Z",
                "format": "pdf"
            }
        }
    }
