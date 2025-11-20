"""Financial metrics API endpoints."""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session, selectinload

from src.core.cache import cache_key_wrapper
from src.core.dependencies import get_current_user
from src.db.base import get_db
from src.db.models import FinancialMetric, Company
from src.auth.models import User

router = APIRouter()


class MetricResponse(BaseModel):
    """Financial metric response model."""

    id: int
    company_id: UUID
    metric_date: datetime
    period_type: str
    metric_type: str
    metric_category: Optional[str] = None
    value: float
    unit: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=List[MetricResponse])
@cache_key_wrapper(prefix="metrics", expire=900)
async def list_metrics(
    company_id: Optional[UUID] = Query(None, description="Filter by company ID"),
    metric_type: Optional[str] = Query(None, description="Filter by metric type"),
    period_type: Optional[str] = Query(None, description="Filter by period type"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[MetricResponse]:
    """List financial metrics with optional filtering."""
    # Eager load company relationship to prevent N+1 queries
    query = db.query(FinancialMetric).options(
        selectinload(FinancialMetric.company)
    )

    if company_id:
        query = query.filter(FinancialMetric.company_id == company_id)
    if metric_type:
        query = query.filter(FinancialMetric.metric_type == metric_type)
    if period_type:
        query = query.filter(FinancialMetric.period_type == period_type)

    metrics = query.order_by(FinancialMetric.metric_date.desc()).offset(offset).limit(limit).all()

    return metrics
