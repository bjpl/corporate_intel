"""Company management DTOs for API endpoints.

This module provides DTOs for company-related endpoints:
- Company CRUD operations
- Company listing and filtering
- Company metrics and analytics
- Trending companies
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from src.dto.base import BaseDTO, IDMixin, PaginatedResponse, TimestampedDTO


class CompanyBaseDTO(BaseDTO):
    """Base company model with common fields."""

    ticker: str = Field(
        ...,
        min_length=1,
        max_length=10,
        pattern="^[A-Z0-9]+$",
        description="Stock ticker symbol (uppercase alphanumeric)",
        examples=["AAPL", "GOOGL", "2U"]
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Company legal name",
        examples=["Apple Inc.", "Alphabet Inc.", "2U, Inc."]
    )
    cik: Optional[str] = Field(
        None,
        min_length=10,
        max_length=10,
        pattern="^[0-9]{10}$",
        description="SEC Central Index Key (CIK) - 10 digits",
        examples=["0001318605", "0001652044"]
    )
    sector: Optional[str] = Field(
        None,
        max_length=100,
        description="Business sector",
        examples=["Technology", "Education", "Software"]
    )
    subsector: Optional[str] = Field(
        None,
        max_length=100,
        description="Business subsector",
        examples=["EdTech", "SaaS", "Learning Platforms"]
    )


class CompanyCreateDTO(CompanyBaseDTO):
    """DTO for creating a new company.

    Includes all editable fields and EdTech-specific categorization.
    """

    # EdTech categorization
    category: Optional[str] = Field(
        None,
        pattern="^(k12|higher_education|corporate_learning|direct_to_consumer|enabling_technology)$",
        description="EdTech category",
        examples=["k12", "higher_education"]
    )
    subcategory: Optional[List[str]] = Field(
        None,
        description="EdTech subcategories",
        examples=[["content", "platform"], ["tutoring", "assessment"]]
    )
    delivery_model: Optional[str] = Field(
        None,
        pattern="^(b2b|b2c|b2b2c|marketplace|hybrid)$",
        description="Business delivery model",
        examples=["b2b", "b2c"]
    )
    monetization_strategy: Optional[List[str]] = Field(
        None,
        description="Revenue models",
        examples=[["saas", "subscription"], ["transaction", "freemium"]]
    )

    # Company metadata
    founded_year: Optional[int] = Field(
        None,
        ge=1800,
        le=2100,
        description="Year company was founded",
        examples=[2012, 1999]
    )
    headquarters: Optional[str] = Field(
        None,
        max_length=255,
        description="Headquarters location",
        examples=["San Francisco, CA", "New York, NY"]
    )
    website: Optional[str] = Field(
        None,
        max_length=255,
        description="Company website URL",
        examples=["https://www.example.com"]
    )
    employee_count: Optional[int] = Field(
        None,
        ge=0,
        description="Number of employees",
        examples=[500, 1200]
    )

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        """Ensure ticker is uppercase."""
        return v.upper()

    model_config = {
        "json_schema_extra": {
            "example": {
                "ticker": "2U",
                "name": "2U, Inc.",
                "cik": "0001459417",
                "sector": "Technology",
                "subsector": "EdTech",
                "category": "higher_education",
                "subcategory": ["platform", "content"],
                "delivery_model": "b2b2c",
                "monetization_strategy": ["saas", "revenue_share"],
                "founded_year": 2008,
                "headquarters": "Lanham, MD",
                "website": "https://2u.com",
                "employee_count": 4000
            }
        }
    }


class CompanyUpdateDTO(CompanyBaseDTO):
    """DTO for updating an existing company.

    All fields are optional to support partial updates.
    """

    ticker: Optional[str] = Field(
        None,
        min_length=1,
        max_length=10,
        pattern="^[A-Z0-9]+$",
        description="Stock ticker symbol (uppercase alphanumeric)"
    )
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Company legal name"
    )
    category: Optional[str] = Field(
        None,
        pattern="^(k12|higher_education|corporate_learning|direct_to_consumer|enabling_technology)$",
        description="EdTech category"
    )
    subcategory: Optional[List[str]] = Field(
        None,
        description="EdTech subcategories"
    )
    delivery_model: Optional[str] = Field(
        None,
        pattern="^(b2b|b2c|b2b2c|marketplace|hybrid)$",
        description="Business delivery model"
    )
    monetization_strategy: Optional[List[str]] = Field(
        None,
        description="Revenue models"
    )
    founded_year: Optional[int] = Field(
        None,
        ge=1800,
        le=2100,
        description="Year company was founded"
    )
    headquarters: Optional[str] = Field(
        None,
        max_length=255,
        description="Headquarters location"
    )
    website: Optional[str] = Field(
        None,
        max_length=255,
        description="Company website URL"
    )
    employee_count: Optional[int] = Field(
        None,
        ge=0,
        description="Number of employees"
    )


class CompanyDTO(CompanyBaseDTO, IDMixin, TimestampedDTO):
    """Full company response DTO.

    Includes all company fields plus system metadata.
    """

    # EdTech categorization
    category: Optional[str] = Field(
        None,
        description="EdTech category"
    )
    subcategory: Optional[List[str]] = Field(
        None,
        description="EdTech subcategories"
    )
    delivery_model: Optional[str] = Field(
        None,
        description="Business delivery model"
    )
    monetization_strategy: Optional[List[str]] = Field(
        None,
        description="Revenue models"
    )

    # Company metadata
    founded_year: Optional[int] = Field(
        None,
        description="Year company was founded"
    )
    headquarters: Optional[str] = Field(
        None,
        description="Headquarters location"
    )
    website: Optional[str] = Field(
        None,
        description="Company website URL"
    )
    employee_count: Optional[int] = Field(
        None,
        description="Number of employees"
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "ticker": "CHGG",
                "name": "Chegg, Inc.",
                "cik": "0001364954",
                "sector": "Technology",
                "subsector": "EdTech",
                "category": "higher_education",
                "subcategory": ["homework_help", "study_resources"],
                "delivery_model": "b2c",
                "monetization_strategy": ["subscription"],
                "founded_year": 2005,
                "headquarters": "Santa Clara, CA",
                "website": "https://www.chegg.com",
                "employee_count": 3200,
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-11-20T10:00:00Z"
            }
        }
    }


class CompanyListDTO(BaseDTO):
    """Response DTO for paginated company listings."""

    companies: List[CompanyDTO] = Field(
        ...,
        description="List of companies"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of companies matching filters"
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
                "companies": [
                    {
                        "id": "123e4567-e89b-12d3-a456-426614174000",
                        "ticker": "CHGG",
                        "name": "Chegg, Inc.",
                        "cik": "0001364954",
                        "sector": "Technology",
                        "subsector": "EdTech",
                        "category": "higher_education",
                        "created_at": "2025-01-15T10:00:00Z",
                        "updated_at": "2025-11-20T10:00:00Z"
                    }
                ],
                "total": 27,
                "limit": 100,
                "offset": 0
            }
        }
    }


class CompanyMetricsDTO(BaseDTO):
    """Company key performance metrics summary.

    Aggregates the most important metrics for a company.
    """

    company_id: UUID = Field(
        ...,
        description="Company unique identifier"
    )
    ticker: str = Field(
        ...,
        description="Stock ticker symbol"
    )
    latest_revenue: Optional[float] = Field(
        None,
        ge=0,
        description="Most recent revenue (USD)"
    )
    revenue_growth_yoy: Optional[float] = Field(
        None,
        description="Year-over-year revenue growth percentage"
    )
    monthly_active_users: Optional[int] = Field(
        None,
        ge=0,
        description="Monthly active users"
    )
    arpu: Optional[float] = Field(
        None,
        ge=0,
        description="Average revenue per user (USD)"
    )
    cac: Optional[float] = Field(
        None,
        ge=0,
        description="Customer acquisition cost (USD)"
    )
    nrr: Optional[float] = Field(
        None,
        ge=0,
        le=200,
        description="Net revenue retention percentage"
    )
    last_updated: datetime = Field(
        ...,
        description="When metrics were last calculated"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "company_id": "123e4567-e89b-12d3-a456-426614174000",
                "ticker": "CHGG",
                "latest_revenue": 776500000,
                "revenue_growth_yoy": -4.2,
                "monthly_active_users": 7800000,
                "arpu": 8.32,
                "cac": 45.50,
                "nrr": 95.3,
                "last_updated": "2025-11-20T10:00:00Z"
            }
        }
    }


class TrendingCompanyDTO(BaseDTO):
    """DTO for trending/top-performing companies.

    Used in analytics and dashboards to highlight notable companies.
    """

    ticker: str = Field(
        ...,
        description="Stock ticker symbol"
    )
    company_name: str = Field(
        ...,
        description="Company name"
    )
    edtech_category: str = Field(
        ...,
        description="EdTech category"
    )
    revenue_yoy_growth: Optional[float] = Field(
        None,
        description="Year-over-year revenue growth percentage"
    )
    latest_revenue: Optional[float] = Field(
        None,
        ge=0,
        description="Most recent revenue (USD)"
    )
    overall_score: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Overall performance score (0-100)"
    )
    growth_rank: Optional[int] = Field(
        None,
        ge=1,
        description="Growth ranking among all companies"
    )
    company_health_status: Optional[str] = Field(
        None,
        description="Health status: healthy, at_risk, or distressed"
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "ticker": "DUOL",
                "company_name": "Duolingo, Inc.",
                "edtech_category": "direct_to_consumer",
                "revenue_yoy_growth": 45.3,
                "latest_revenue": 531000000,
                "overall_score": 92.5,
                "growth_rank": 1,
                "company_health_status": "healthy"
            }
        }
    }
