"""Company management API endpoints."""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from src.core.cache import cache_key_wrapper, get_cache
from src.core.dependencies import get_current_user
from src.db.base import get_db
from src.db.models import Company
from src.auth.models import User

router = APIRouter()


class CompanyBase(BaseModel):
    """Base company model."""
    
    ticker: str = Field(..., max_length=10)
    name: str = Field(..., max_length=255)
    cik: Optional[str] = Field(None, max_length=10)
    sector: Optional[str] = Field(None, max_length=100)
    subsector: Optional[str] = Field(None, max_length=100)
    category: Optional[str] = Field(None, pattern="^(k12|higher_education|corporate_learning|direct_to_consumer|enabling_technology)$")
    delivery_model: Optional[str] = Field(None, pattern="^(b2b|b2c|b2b2c|marketplace|hybrid)$")


class CompanyCreate(CompanyBase):
    """Company creation model."""
    
    subcategory: Optional[List[str]] = None
    monetization_strategy: Optional[List[str]] = None
    founded_year: Optional[int] = Field(None, ge=1800, le=2100)
    headquarters: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = Field(None, max_length=255)
    employee_count: Optional[int] = Field(None, ge=0)


class CompanyResponse(CompanyBase):
    """Company response model."""
    
    id: UUID
    subcategory: Optional[List[str]] = None
    monetization_strategy: Optional[List[str]] = None
    founded_year: Optional[int] = None
    headquarters: Optional[str] = None
    website: Optional[str] = None
    employee_count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class CompanyMetrics(BaseModel):
    """Company key metrics summary."""
    
    company_id: UUID
    ticker: str
    latest_revenue: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None
    monthly_active_users: Optional[int] = None
    arpu: Optional[float] = None
    cac: Optional[float] = None
    nrr: Optional[float] = None
    last_updated: str


@router.get("/", response_model=List[CompanyResponse])
@cache_key_wrapper(prefix="companies", expire=3600)
async def list_companies(
    category: Optional[str] = Query(None, description="Filter by EdTech category"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[CompanyResponse]:
    """List all companies with optional filtering."""
    logger.info(f"Listing companies: category={category}, sector={sector}, limit={limit}, offset={offset}")
    
    # Build query
    query = db.query(Company)
    
    if category:
        query = query.filter(Company.category == category)
    if sector:
        query = query.filter(Company.sector == sector)
    
    # Execute with pagination
    companies = query.offset(offset).limit(limit).all()
    
    return companies


@router.get("/watchlist", response_model=List[CompanyResponse])
@cache_key_wrapper(prefix="watchlist", expire=1800)
async def get_watchlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[CompanyResponse]:
    """Get companies on the EdTech watchlist."""
    from src.core.config import get_settings
    
    settings = get_settings()
    tickers = settings.EDTECH_COMPANIES_WATCHLIST
    
    companies = db.query(Company).filter(Company.ticker.in_(tickers)).all()
    
    return companies


@router.get("/{company_id}", response_model=CompanyResponse)
@cache_key_wrapper(prefix="company", expire=3600)
async def get_company(
    company_id: UUID,
    db: Session = Depends(get_db),
) -> CompanyResponse:
    """Get a specific company by ID."""
    company = db.query(Company).filter(Company.id == company_id).first()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found",
        )
    
    return company


@router.get("/{company_id}/metrics", response_model=CompanyMetrics)
@cache_key_wrapper(prefix="company_metrics", expire=900)
async def get_company_metrics(
    company_id: UUID,
    db: Session = Depends(get_db),
) -> CompanyMetrics:
    """Get latest metrics for a company."""
    from datetime import datetime
    
    company = db.query(Company).filter(Company.id == company_id).first()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found",
        )
    
    # Fetch latest metrics from TimescaleDB
    metrics_query = """
    WITH latest_metrics AS (
        SELECT 
            company_id,
            metric_type,
            value,
            metric_date,
            ROW_NUMBER() OVER (PARTITION BY metric_type ORDER BY metric_date DESC) as rn
        FROM financial_metrics
        WHERE company_id = :company_id
    )
    SELECT 
        metric_type,
        value,
        metric_date
    FROM latest_metrics
    WHERE rn = 1
    """
    
    metrics_result = db.execute(metrics_query, {"company_id": company_id}).fetchall()
    
    # Build metrics response
    metrics_dict = {row.metric_type: row.value for row in metrics_result}
    
    return CompanyMetrics(
        company_id=company_id,
        ticker=company.ticker,
        latest_revenue=metrics_dict.get("revenue"),
        revenue_growth_yoy=metrics_dict.get("revenue_growth_yoy"),
        monthly_active_users=int(metrics_dict.get("monthly_active_users", 0)),
        arpu=metrics_dict.get("average_revenue_per_user"),
        cac=metrics_dict.get("customer_acquisition_cost"),
        nrr=metrics_dict.get("net_revenue_retention"),
        last_updated=datetime.utcnow().isoformat(),
    )


@router.post("/", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    company: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyResponse:
    """Create a new company."""
    # Check if company already exists
    existing = db.query(Company).filter(
        (Company.ticker == company.ticker) | (Company.cik == company.cik)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Company with ticker {company.ticker} or CIK {company.cik} already exists",
        )
    
    # Create new company
    db_company = Company(**company.model_dump())
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    
    logger.info(f"Created new company: {db_company.ticker} (ID: {db_company.id})")
    
    # Invalidate cache
    cache = get_cache()
    await cache.delete("companies:*")
    
    return db_company


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID,
    company_update: CompanyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CompanyResponse:
    """Update company information."""
    company = db.query(Company).filter(Company.id == company_id).first()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found",
        )
    
    # Update fields
    for field, value in company_update.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    
    db.commit()
    db.refresh(company)
    
    logger.info(f"Updated company: {company.ticker} (ID: {company.id})")
    
    # Invalidate cache
    cache = get_cache()
    await cache.delete(f"company:{company_id}")
    await cache.delete(f"company_metrics:{company_id}")
    
    return company


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a company."""
    company = db.query(Company).filter(Company.id == company_id).first()
    
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found",
        )
    
    db.delete(company)
    db.commit()
    
    logger.info(f"Deleted company: {company.ticker} (ID: {company_id})")
    
    # Invalidate cache
    cache = get_cache()
    await cache.delete(f"company:{company_id}")
    await cache.delete("companies:*")