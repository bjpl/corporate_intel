"""SEC filings DTOs for API endpoints.

This module provides DTOs for SEC filing-related endpoints:
- Filing retrieval and listing
- Filing creation and updates
- Filing processing status
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field, field_validator

from src.dto.base import BaseDTO, IDMixin, TimestampedDTO


class FilingBaseDTO(BaseDTO):
    """Base filing model with common fields."""

    filing_type: str = Field(
        ...,
        min_length=1,
        max_length=20,
        pattern="^(10-K|10-Q|8-K|S-1|20-F|6-K|DEF 14A)$",
        description="SEC filing type",
        examples=["10-K", "10-Q", "8-K"]
    )
    filing_date: datetime = Field(
        ...,
        description="Date the filing was submitted to SEC",
        examples=["2025-03-31T00:00:00Z"]
    )
    accession_number: str = Field(
        ...,
        min_length=20,
        max_length=25,
        pattern="^[0-9]{10}-[0-9]{2}-[0-9]{6}$",
        description="SEC accession number (format: 0000000000-00-000000)",
        examples=["0001193125-25-123456"]
    )
    filing_url: Optional[str] = Field(
        None,
        max_length=500,
        description="URL to the filing on SEC EDGAR",
        examples=["https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001318605"]
    )


class FilingCreateDTO(FilingBaseDTO):
    """DTO for creating a new SEC filing record.

    Used when ingesting new filings from SEC EDGAR.
    """

    company_id: UUID = Field(
        ...,
        description="Company UUID that filed this document"
    )
    raw_text: Optional[str] = Field(
        None,
        description="Full text content of the filing"
    )
    parsed_sections: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured sections extracted from filing (e.g., Item 1, Item 7, etc.)"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "company_id": "123e4567-e89b-12d3-a456-426614174000",
                "filing_type": "10-K",
                "filing_date": "2025-03-31T00:00:00Z",
                "accession_number": "0001193125-25-123456",
                "filing_url": "https://www.sec.gov/Archives/edgar/data/1318605/000119312525123456/d12345d10k.htm",
                "parsed_sections": {
                    "item_1": "Business description...",
                    "item_7": "Management's Discussion and Analysis..."
                }
            }
        }
    }


class FilingDTO(FilingBaseDTO, IDMixin, TimestampedDTO):
    """Full filing response DTO.

    Includes all filing fields plus processing status and metadata.
    """

    company_id: UUID = Field(
        ...,
        description="Company UUID that filed this document"
    )
    processing_status: str = Field(
        ...,
        pattern="^(pending|processing|completed|failed)$",
        description="Processing status of the filing",
        examples=["completed", "processing", "pending"]
    )
    processed_at: Optional[datetime] = Field(
        None,
        description="When the filing was successfully processed"
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if processing failed"
    )

    # Optional detailed data (not included in list responses)
    raw_text: Optional[str] = Field(
        None,
        description="Full text content of the filing (large field, excluded from lists)",
        exclude=True
    )
    parsed_sections: Optional[Dict[str, Any]] = Field(
        None,
        description="Structured sections extracted from filing"
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "987e6543-e21b-12d3-a456-426614174999",
                "company_id": "123e4567-e89b-12d3-a456-426614174000",
                "filing_type": "10-K",
                "filing_date": "2025-03-31T00:00:00Z",
                "accession_number": "0001193125-25-123456",
                "filing_url": "https://www.sec.gov/Archives/edgar/data/1318605/000119312525123456/d12345d10k.htm",
                "processing_status": "completed",
                "processed_at": "2025-04-01T12:00:00Z",
                "error_message": None,
                "parsed_sections": {
                    "item_1": "Business overview...",
                    "item_7": "MD&A..."
                },
                "created_at": "2025-04-01T10:00:00Z",
                "updated_at": "2025-04-01T12:00:00Z"
            }
        }
    }


class FilingListItemDTO(FilingBaseDTO, IDMixin):
    """Lightweight filing DTO for list responses.

    Excludes large fields like raw_text to optimize list endpoint performance.
    """

    company_id: UUID = Field(
        ...,
        description="Company UUID that filed this document"
    )
    processing_status: str = Field(
        ...,
        description="Processing status of the filing"
    )
    created_at: datetime = Field(
        ...,
        description="When the filing record was created"
    )

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "987e6543-e21b-12d3-a456-426614174999",
                "company_id": "123e4567-e89b-12d3-a456-426614174000",
                "filing_type": "10-Q",
                "filing_date": "2025-09-30T00:00:00Z",
                "accession_number": "0001193125-25-987654",
                "filing_url": "https://www.sec.gov/Archives/edgar/data/1318605/000119312525987654/d98765d10q.htm",
                "processing_status": "completed",
                "created_at": "2025-10-01T10:00:00Z"
            }
        }
    }


class FilingListDTO(BaseDTO):
    """Response DTO for paginated filing listings."""

    filings: List[FilingListItemDTO] = Field(
        ...,
        description="List of filings"
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of filings matching filters"
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
                "filings": [
                    {
                        "id": "987e6543-e21b-12d3-a456-426614174999",
                        "company_id": "123e4567-e89b-12d3-a456-426614174000",
                        "filing_type": "10-K",
                        "filing_date": "2025-03-31T00:00:00Z",
                        "accession_number": "0001193125-25-123456",
                        "processing_status": "completed",
                        "created_at": "2025-04-01T10:00:00Z"
                    }
                ],
                "total": 156,
                "limit": 100,
                "offset": 0
            }
        }
    }


class FilingFilterDTO(BaseDTO):
    """DTO for filtering filings in list requests."""

    company_id: Optional[UUID] = Field(
        None,
        description="Filter by company ID"
    )
    filing_type: Optional[str] = Field(
        None,
        pattern="^(10-K|10-Q|8-K|S-1|20-F|6-K|DEF 14A)$",
        description="Filter by filing type"
    )
    filing_date_start: Optional[datetime] = Field(
        None,
        description="Filter filings after this date"
    )
    filing_date_end: Optional[datetime] = Field(
        None,
        description="Filter filings before this date"
    )
    processing_status: Optional[str] = Field(
        None,
        pattern="^(pending|processing|completed|failed)$",
        description="Filter by processing status"
    )

    @field_validator("filing_date_end")
    @classmethod
    def validate_date_range(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Ensure end date is after start date."""
        if v and info.data.get("filing_date_start"):
            if v < info.data["filing_date_start"]:
                raise ValueError("filing_date_end must be after filing_date_start")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "company_id": "123e4567-e89b-12d3-a456-426614174000",
                "filing_type": "10-K",
                "filing_date_start": "2024-01-01T00:00:00Z",
                "filing_date_end": "2025-12-31T23:59:59Z",
                "processing_status": "completed"
            }
        }
    }
