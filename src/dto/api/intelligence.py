"""Market intelligence DTOs for API endpoints.

This module provides DTOs for market intelligence and competitive insights:
- Intelligence item retrieval and listing
- Intelligence creation and updates
- Market events and trends
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from src.dto.base import BaseDTO, IDMixin, TimestampedDTO


class IntelligenceBaseDTO(BaseDTO):
    """Base intelligence model with common fields."""

    intel_type: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Type of intelligence (funding, acquisition, partnership, product_launch, etc.)",
        examples=["funding", "acquisition", "partnership", "product_launch"]
    )
    category: Optional[str] = Field(
        None,
        max_length=50,
        description="EdTech segment/category",
        examples=["k12", "higher_education", "corporate_learning"]
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Intelligence item title",
        examples=["Duolingo raises $50M Series E", "Coursera acquires Learning Platform Inc."]
    )
    summary: Optional[str] = Field(
        None,
        description="Brief summary of the intelligence item"
    )
    event_date: Optional[datetime] = Field(
        None,
        description="Date when the event occurred",
        examples=["2025-11-15T00:00:00Z"]
    )
    source: Optional[str] = Field(
        None,
        max_length=255,
        description="Source of the intelligence (news outlet, SEC filing, etc.)",
        examples=["TechCrunch", "The Information", "SEC EDGAR"]
    )
    source_url: Optional[str] = Field(
        None,
        description="URL to the source article/document"
    )


class IntelligenceCreateDTO(IntelligenceBaseDTO):
    """DTO for creating a new intelligence item."""

    full_content: Optional[str] = Field(
        None,
        description="Full content/article text"
    )
    primary_company_id: Optional[UUID] = Field(
        None,
        description="Primary company involved in this intelligence"
    )
    related_companies: Optional[List[UUID]] = Field(
        None,
        description="List of related company UUIDs"
    )
    confidence_score: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Confidence in the intelligence accuracy (0-1)"
    )
    sentiment_score: Optional[float] = Field(
        None,
        ge=-1,
        le=1,
        description="Sentiment score (-1 to 1, where -1 is very negative, 1 is very positive)"
    )
    impact_assessment: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured impact assessment data"
    )

    @field_validator("sentiment_score")
    @classmethod
    def validate_sentiment(cls, v: Optional[float]) -> Optional[float]:
        """Ensure sentiment score is within valid range."""
        if v is not None and (v < -1 or v > 1):
            raise ValueError("sentiment_score must be between -1 and 1")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "intel_type": "funding",
                "category": "direct_to_consumer",
                "title": "Duolingo raises $50M Series E at $6.5B valuation",
                "summary": "Language learning platform Duolingo announced a $50M Series E funding round...",
                "full_content": "Full article content...",
                "primary_company_id": "123e4567-e89b-12d3-a456-426614174000",
                "related_companies": [],
                "event_date": "2025-11-15T00:00:00Z",
                "source": "TechCrunch",
                "source_url": "https://techcrunch.com/2025/11/15/duolingo-funding",
                "confidence_score": 0.95,
                "sentiment_score": 0.8,
                "impact_assessment": {
                    "market_impact": "high",
                    "competitive_threat": "medium",
                    "strategic_importance": "high"
                }
            }
        }
    }


class IntelligenceDTO(IntelligenceBaseDTO, IDMixin, TimestampedDTO):
    """Full intelligence response DTO.

    Includes all intelligence fields plus system metadata.
    """

    primary_company_id: Optional[UUID] = Field(
        None,
        description="Primary company UUID involved in this intelligence"
    )
    related_companies: Optional[List[UUID]] = Field(
        None,
        description="List of related company UUIDs"
    )
    confidence_score: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Confidence in the intelligence accuracy (0-1)"
    )
    sentiment_score: Optional[float] = Field(
        None,
        ge=-1,
        le=1,
        description="Sentiment score (-1 to 1)"
    )
    impact_assessment: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured impact assessment data"
    )

    # Full content excluded from list responses
    full_content: Optional[str] = Field(
        None,
        description="Full content/article text (large field, excluded from lists)",
        exclude=True
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "456e7890-e12b-34d5-a678-901234567890",
                "intel_type": "acquisition",
                "category": "higher_education",
                "title": "Coursera acquires Learning Platform Inc. for $200M",
                "summary": "Coursera announced the acquisition of Learning Platform Inc...",
                "primary_company_id": "123e4567-e89b-12d3-a456-426614174000",
                "related_companies": ["789e0123-e45f-67g8-h901-234567890123"],
                "event_date": "2025-11-10T00:00:00Z",
                "source": "The Information",
                "source_url": "https://www.theinformation.com/articles/coursera-acquisition",
                "confidence_score": 0.98,
                "sentiment_score": 0.6,
                "impact_assessment": {
                    "market_impact": "high",
                    "competitive_threat": "high",
                    "geographic_expansion": ["europe", "asia"]
                },
                "created_at": "2025-11-10T15:00:00Z",
                "updated_at": "2025-11-10T15:00:00Z"
            }
        }
    }


class IntelligenceListItemDTO(IntelligenceBaseDTO, IDMixin):
    """Lightweight intelligence DTO for list responses.

    Excludes large fields like full_content to optimize performance.
    """

    primary_company_id: Optional[UUID] = Field(
        None,
        description="Primary company UUID"
    )
    confidence_score: Optional[float] = Field(
        None,
        description="Confidence score"
    )
    sentiment_score: Optional[float] = Field(
        None,
        description="Sentiment score"
    )
    created_at: datetime = Field(
        ...,
        description="When the intelligence was created"
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "456e7890-e12b-34d5-a678-901234567890",
                "intel_type": "funding",
                "category": "k12",
                "title": "ClassDojo raises $35M Series D",
                "summary": "Classroom communication platform ClassDojo announced...",
                "event_date": "2025-11-01T00:00:00Z",
                "source": "EdSurge",
                "primary_company_id": "123e4567-e89b-12d3-a456-426614174000",
                "confidence_score": 0.92,
                "sentiment_score": 0.7,
                "created_at": "2025-11-01T12:00:00Z"
            }
        }
    }


class IntelligenceListDTO(BaseDTO):
    """Response DTO for paginated intelligence listings."""

    intelligence: List[IntelligenceListItemDTO] = Field(
        ...,
        description="List of intelligence items"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of intelligence items matching filters"
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
                "intelligence": [
                    {
                        "id": "456e7890-e12b-34d5-a678-901234567890",
                        "intel_type": "partnership",
                        "category": "corporate_learning",
                        "title": "LinkedIn Learning partners with Harvard University",
                        "summary": "Strategic partnership announced...",
                        "event_date": "2025-10-25T00:00:00Z",
                        "source": "LinkedIn Newsroom",
                        "created_at": "2025-10-25T14:00:00Z"
                    }
                ],
                "total": 342,
                "limit": 100,
                "offset": 0
            }
        }
    }


class IntelligenceFilterDTO(BaseDTO):
    """DTO for filtering intelligence in list requests."""

    intel_type: Optional[str] = Field(
        None,
        description="Filter by intelligence type"
    )
    category: Optional[str] = Field(
        None,
        description="Filter by EdTech category"
    )
    primary_company_id: Optional[UUID] = Field(
        None,
        description="Filter by primary company"
    )
    event_date_start: Optional[datetime] = Field(
        None,
        description="Filter events after this date"
    )
    event_date_end: Optional[datetime] = Field(
        None,
        description="Filter events before this date"
    )
    min_confidence: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Minimum confidence score"
    )
    sentiment: Optional[str] = Field(
        None,
        pattern="^(positive|neutral|negative)$",
        description="Filter by sentiment (positive: >0.3, neutral: -0.3 to 0.3, negative: <-0.3)"
    )

    @field_validator("event_date_end")
    @classmethod
    def validate_date_range(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Ensure end date is after start date."""
        if v and info.data.get("event_date_start"):
            if v < info.data["event_date_start"]:
                raise ValueError("event_date_end must be after event_date_start")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "intel_type": "funding",
                "category": "k12",
                "event_date_start": "2025-01-01T00:00:00Z",
                "event_date_end": "2025-12-31T23:59:59Z",
                "min_confidence": 0.8,
                "sentiment": "positive"
            }
        }
    }
