"""Analysis reports API endpoints."""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from sqlalchemy import text

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


class ReportGenerationRequest(BaseModel):
    """Request model for generating a new report."""

    report_type: str = Field(..., description="Type of report to generate (competitive_landscape, company_performance, market_trends)")
    title: str = Field(..., max_length=200, description="Report title")
    description: Optional[str] = Field(None, description="Report description")
    category_filter: Optional[str] = Field(None, description="EdTech category filter")
    date_range_days: int = Field(90, ge=1, le=365, description="Number of days to include in analysis")
    include_visualizations: bool = Field(True, description="Include charts and graphs")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "report_type": "competitive_landscape",
            "title": "Q4 2025 EdTech Competitive Analysis",
            "description": "Comprehensive competitive landscape analysis for Q4 2025",
            "category_filter": "k12",
            "date_range_days": 90,
            "include_visualizations": True
        }
    })


class ReportGenerationResponse(BaseModel):
    """Response model for report generation."""

    report_id: UUID
    status: str
    title: str
    report_type: str
    companies_analyzed: int
    metrics_included: int
    created_at: datetime
    report_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


@router.post("/generate", response_model=ReportGenerationResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    request: ReportGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReportGenerationResponse:
    """Generate a new analysis report based on current data.

    This endpoint creates an on-demand analysis report by querying the data warehouse
    and generating insights based on the specified parameters.

    Supported report types:
    - competitive_landscape: Market positioning and competitive dynamics
    - company_performance: Individual company financial performance
    - market_trends: Market-wide trends and patterns
    """
    logger.info(f"Generating {request.report_type} report: {request.title}")

    try:
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=request.date_range_days)

        # Query data warehouse for analysis
        analysis_data = await _analyze_market_data(
            db=db,
            report_type=request.report_type,
            category_filter=request.category_filter,
            start_date=start_date,
            end_date=end_date,
        )

        # Create report record
        report = AnalysisReport(
            report_type=request.report_type,
            title=request.title,
            description=request.description or f"Auto-generated {request.report_type} report",
            date_range_start=start_date,
            date_range_end=end_date,
            format="json",  # Could be extended to PDF, Excel, etc.
            report_url=None,  # Could be S3/MinIO URL in production
            metadata_=analysis_data.get("metadata", {}),
        )

        db.add(report)
        db.commit()
        db.refresh(report)

        logger.info(f"Report generated successfully: {report.id}")

        return ReportGenerationResponse(
            report_id=report.id,
            status="completed",
            title=report.title,
            report_type=report.report_type,
            companies_analyzed=analysis_data.get("companies_count", 0),
            metrics_included=analysis_data.get("metrics_count", 0),
            created_at=report.created_at,
            report_url=report.report_url,
        )

    except Exception as e:
        logger.error(f"Error generating report: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )


async def _analyze_market_data(
    db: Session,
    report_type: str,
    category_filter: Optional[str],
    start_date: datetime,
    end_date: datetime,
) -> Dict[str, Any]:
    """Analyze market data from the data warehouse.

    Queries mart_company_performance and other data marts to generate insights.
    """
    try:
        # Query company performance data
        query = text("""
            SELECT
                COUNT(DISTINCT ticker) as companies_count,
                COUNT(*) as metrics_count,
                AVG(latest_revenue) as avg_revenue,
                AVG(latest_gross_margin) as avg_gross_margin,
                AVG(latest_operating_margin) as avg_operating_margin,
                AVG(revenue_yoy_growth) as avg_growth,
                SUM(latest_revenue) as total_revenue
            FROM public_marts.mart_company_performance
            WHERE (:category IS NULL OR edtech_category = :category)
                AND latest_data_date >= :start_date
                AND latest_data_date <= :end_date
        """)

        result = db.execute(
            query,
            {
                "category": category_filter,
                "start_date": start_date,
                "end_date": end_date,
            }
        )

        row = result.fetchone()

        if not row:
            return {
                "companies_count": 0,
                "metrics_count": 0,
                "metadata": {"status": "no_data"},
            }

        return {
            "companies_count": row[0] or 0,
            "metrics_count": row[1] or 0,
            "metadata": {
                "avg_revenue": float(row[2]) if row[2] else 0,
                "avg_gross_margin": float(row[3]) if row[3] else 0,
                "avg_operating_margin": float(row[4]) if row[4] else 0,
                "avg_growth": float(row[5]) if row[5] else 0,
                "total_revenue": float(row[6]) if row[6] else 0,
                "report_type": report_type,
                "category_filter": category_filter,
                "date_range": f"{start_date.date()} to {end_date.date()}",
            },
        }

    except Exception as e:
        logger.error(f"Error analyzing market data: {str(e)}", exc_info=True)
        return {
            "companies_count": 0,
            "metrics_count": 0,
            "metadata": {"status": "error", "error": str(e)},
        }
