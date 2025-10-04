"""SEC filings API endpoints."""

from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from src.core.cache import cache_key_wrapper
from src.core.dependencies import get_current_user
from src.db.base import get_db
from src.db.models import SECFiling, Company
from src.auth.models import User

router = APIRouter()


class FilingResponse(BaseModel):
    """SEC filing response model."""

    id: UUID
    company_id: UUID
    filing_type: str
    filing_date: datetime
    accession_number: str
    filing_url: Optional[str] = None
    processing_status: str

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=List[FilingResponse])
@cache_key_wrapper(prefix="filings", expire=3600)
async def list_filings(
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    filing_type: Optional[str] = Query(None, description="Filter by filing type"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[FilingResponse]:
    """List SEC filings with optional filtering."""
    query = db.query(SECFiling)

    if company_id:
        query = query.filter(SECFiling.company_id == company_id)
    if filing_type:
        query = query.filter(SECFiling.filing_type == filing_type)

    filings = query.order_by(SECFiling.filing_date.desc()).offset(offset).limit(limit).all()

    return filings


@router.get("/{filing_id}", response_model=FilingResponse)
@cache_key_wrapper(prefix="filing", expire=3600)
async def get_filing(
    filing_id: UUID,
    db: Session = Depends(get_db),
) -> FilingResponse:
    """Get a specific SEC filing by ID."""
    filing = db.query(SECFiling).filter(SECFiling.id == filing_id).first()

    if not filing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Filing with ID {filing_id} not found",
        )

    return filing
