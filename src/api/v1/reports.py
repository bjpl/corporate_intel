"""Analysis reports API endpoints."""

from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from src.core.cache import cache_key_wrapper
from src.core.dependencies import get_current_user
from src.db.base import get_db
from src.db.models import AnalysisReport
from src.auth.models import User

router = APIRouter()


class ReportResponse(BaseModel):
    """Analysis report response model."""

    id: UUID
    report_type: str
    title: str
    description: Optional[str] = None
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    format: Optional[str] = None
    report_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


@router.get("/", response_model=List[ReportResponse])
@cache_key_wrapper(prefix="reports", expire=1800)
async def list_reports(
    report_type: Optional[str] = Query(None, description="Filter by report type"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[ReportResponse]:
    """List analysis reports with optional filtering."""
    query = db.query(AnalysisReport)

    if report_type:
        query = query.filter(AnalysisReport.report_type == report_type)

    reports = query.order_by(AnalysisReport.created_at.desc()).offset(offset).limit(limit).all()

    return reports


@router.get("/{report_id}", response_model=ReportResponse)
@cache_key_wrapper(prefix="report", expire=1800)
async def get_report(
    report_id: UUID,
    db: Session = Depends(get_db),
) -> ReportResponse:
    """Get a specific analysis report by ID."""
    report = db.query(AnalysisReport).filter(AnalysisReport.id == report_id).first()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID {report_id} not found",
        )

    return report
