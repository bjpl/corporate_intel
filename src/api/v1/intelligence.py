"""Market intelligence API endpoints."""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field

from src.core.cache import cache_key_wrapper
from src.core.dependencies import get_current_user
from src.db.base import get_db
from src.db.models import MarketIntelligence

router = APIRouter()


class IntelligenceResponse(BaseModel):
    """Market intelligence response model."""

    id: UUID
    intel_type: str
    category: Optional[str] = None
    title: str
    summary: Optional[str] = None
    event_date: Optional[datetime] = None
    source: Optional[str] = None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[IntelligenceResponse])
@cache_key_wrapper(prefix="intelligence", expire=1800)
async def list_intelligence(
    intel_type: Optional[str] = Query(None, description="Filter by intelligence type"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db=Depends(get_db),
):
    """List market intelligence items with optional filtering."""
    query = db.query(MarketIntelligence)

    if intel_type:
        query = query.filter(MarketIntelligence.intel_type == intel_type)
    if category:
        query = query.filter(MarketIntelligence.category == category)

    intelligence = query.order_by(MarketIntelligence.event_date.desc()).offset(offset).limit(limit).all()

    return intelligence
