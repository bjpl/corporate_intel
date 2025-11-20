"""DTO factories for converting between database models and DTOs.

This module provides factory functions to convert SQLAlchemy models
into their corresponding DTO representations. This centralizes conversion
logic and ensures consistency across the application.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar
from uuid import UUID

from src.db.models import (
    AnalysisReport,
    Company,
    FinancialMetric,
    MarketIntelligence,
    SECFiling,
)
from src.dto.api.companies import (
    CompanyDTO,
    CompanyListDTO,
    CompanyMetricsDTO,
    TrendingCompanyDTO,
)
from src.dto.api.filings import FilingDTO, FilingListDTO, FilingListItemDTO
from src.dto.api.intelligence import (
    IntelligenceDTO,
    IntelligenceListDTO,
    IntelligenceListItemDTO,
)
from src.dto.api.metrics import MetricDTO, MetricListItemDTO, MetricsListDTO
from src.dto.api.reports import ReportDTO, ReportListDTO, ReportListItemDTO


T = TypeVar("T")


# ===== Company Factories =====


def company_to_dto(company: Company) -> CompanyDTO:
    """Convert Company model to CompanyDTO.

    Args:
        company: SQLAlchemy Company model instance

    Returns:
        CompanyDTO instance with all fields populated
    """
    return CompanyDTO.model_validate(company)


def companies_to_list_dto(
    companies: List[Company],
    total: int,
    limit: int,
    offset: int
) -> CompanyListDTO:
    """Convert list of Company models to CompanyListDTO.

    Args:
        companies: List of SQLAlchemy Company models
        total: Total number of companies matching query
        limit: Page size limit
        offset: Number of items skipped

    Returns:
        CompanyListDTO with paginated results
    """
    return CompanyListDTO(
        companies=[company_to_dto(c) for c in companies],
        total=total,
        limit=limit,
        offset=offset
    )


def company_metrics_to_dto(
    company: Company,
    metrics_dict: Dict[str, Any],
    last_updated: Optional[datetime] = None
) -> CompanyMetricsDTO:
    """Convert company and metrics data to CompanyMetricsDTO.

    Args:
        company: SQLAlchemy Company model instance
        metrics_dict: Dictionary of metric_type -> value
        last_updated: When metrics were last calculated

    Returns:
        CompanyMetricsDTO with aggregated metrics
    """
    return CompanyMetricsDTO(
        company_id=company.id,
        ticker=company.ticker,
        latest_revenue=metrics_dict.get("revenue"),
        revenue_growth_yoy=metrics_dict.get("revenue_growth_yoy"),
        monthly_active_users=int(metrics_dict.get("monthly_active_users", 0)) if metrics_dict.get("monthly_active_users") else None,
        arpu=metrics_dict.get("average_revenue_per_user"),
        cac=metrics_dict.get("customer_acquisition_cost"),
        nrr=metrics_dict.get("net_revenue_retention"),
        last_updated=last_updated or datetime.utcnow()
    )


def trending_company_from_dict(data: Dict[str, Any]) -> TrendingCompanyDTO:
    """Convert dictionary data to TrendingCompanyDTO.

    Used for data warehouse query results.

    Args:
        data: Dictionary with trending company data

    Returns:
        TrendingCompanyDTO instance
    """
    return TrendingCompanyDTO(
        ticker=data["ticker"],
        company_name=data["company_name"],
        edtech_category=data["edtech_category"],
        revenue_yoy_growth=data.get("revenue_yoy_growth"),
        latest_revenue=data.get("latest_revenue"),
        overall_score=data.get("overall_score"),
        growth_rank=data.get("growth_rank"),
        company_health_status=data.get("company_health_status")
    )


# ===== Filing Factories =====


def filing_to_dto(filing: SECFiling) -> FilingDTO:
    """Convert SECFiling model to FilingDTO.

    Args:
        filing: SQLAlchemy SECFiling model instance

    Returns:
        FilingDTO instance with all fields populated
    """
    return FilingDTO.model_validate(filing)


def filing_to_list_item_dto(filing: SECFiling) -> FilingListItemDTO:
    """Convert SECFiling model to lightweight FilingListItemDTO.

    Args:
        filing: SQLAlchemy SECFiling model instance

    Returns:
        FilingListItemDTO instance (excludes large fields)
    """
    return FilingListItemDTO.model_validate(filing)


def filings_to_list_dto(
    filings: List[SECFiling],
    total: int,
    limit: int,
    offset: int
) -> FilingListDTO:
    """Convert list of SECFiling models to FilingListDTO.

    Args:
        filings: List of SQLAlchemy SECFiling models
        total: Total number of filings matching query
        limit: Page size limit
        offset: Number of items skipped

    Returns:
        FilingListDTO with paginated results
    """
    return FilingListDTO(
        filings=[filing_to_list_item_dto(f) for f in filings],
        total=total,
        limit=limit,
        offset=offset
    )


# ===== Metric Factories =====


def metric_to_dto(metric: FinancialMetric) -> MetricDTO:
    """Convert FinancialMetric model to MetricDTO.

    Args:
        metric: SQLAlchemy FinancialMetric model instance

    Returns:
        MetricDTO instance with all fields populated
    """
    return MetricDTO.model_validate(metric)


def metric_to_list_item_dto(metric: FinancialMetric) -> MetricListItemDTO:
    """Convert FinancialMetric model to lightweight MetricListItemDTO.

    Args:
        metric: SQLAlchemy FinancialMetric model instance

    Returns:
        MetricListItemDTO instance (excludes metadata fields)
    """
    return MetricListItemDTO.model_validate(metric)


def metrics_to_list_dto(
    metrics: List[FinancialMetric],
    total: int,
    limit: int,
    offset: int
) -> MetricsListDTO:
    """Convert list of FinancialMetric models to MetricsListDTO.

    Args:
        metrics: List of SQLAlchemy FinancialMetric models
        total: Total number of metrics matching query
        limit: Page size limit
        offset: Number of items skipped

    Returns:
        MetricsListDTO with paginated results
    """
    return MetricsListDTO(
        metrics=[metric_to_list_item_dto(m) for m in metrics],
        total=total,
        limit=limit,
        offset=offset
    )


# ===== Intelligence Factories =====


def intelligence_to_dto(intelligence: MarketIntelligence) -> IntelligenceDTO:
    """Convert MarketIntelligence model to IntelligenceDTO.

    Args:
        intelligence: SQLAlchemy MarketIntelligence model instance

    Returns:
        IntelligenceDTO instance with all fields populated
    """
    return IntelligenceDTO.model_validate(intelligence)


def intelligence_to_list_item_dto(intelligence: MarketIntelligence) -> IntelligenceListItemDTO:
    """Convert MarketIntelligence model to lightweight IntelligenceListItemDTO.

    Args:
        intelligence: SQLAlchemy MarketIntelligence model instance

    Returns:
        IntelligenceListItemDTO instance (excludes large fields)
    """
    return IntelligenceListItemDTO.model_validate(intelligence)


def intelligence_to_list_dto(
    intelligence_items: List[MarketIntelligence],
    total: int,
    limit: int,
    offset: int
) -> IntelligenceListDTO:
    """Convert list of MarketIntelligence models to IntelligenceListDTO.

    Args:
        intelligence_items: List of SQLAlchemy MarketIntelligence models
        total: Total number of intelligence items matching query
        limit: Page size limit
        offset: Number of items skipped

    Returns:
        IntelligenceListDTO with paginated results
    """
    return IntelligenceListDTO(
        intelligence=[intelligence_to_list_item_dto(i) for i in intelligence_items],
        total=total,
        limit=limit,
        offset=offset
    )


# ===== Report Factories =====


def report_to_dto(report: AnalysisReport) -> ReportDTO:
    """Convert AnalysisReport model to ReportDTO.

    Args:
        report: SQLAlchemy AnalysisReport model instance

    Returns:
        ReportDTO instance with all fields populated
    """
    return ReportDTO.model_validate(report)


def report_to_list_item_dto(report: AnalysisReport) -> ReportListItemDTO:
    """Convert AnalysisReport model to lightweight ReportListItemDTO.

    Args:
        report: SQLAlchemy AnalysisReport model instance

    Returns:
        ReportListItemDTO instance (excludes large content fields)
    """
    return ReportListItemDTO.model_validate(report)


def reports_to_list_dto(
    reports: List[AnalysisReport],
    total: int,
    limit: int,
    offset: int
) -> ReportListDTO:
    """Convert list of AnalysisReport models to ReportListDTO.

    Args:
        reports: List of SQLAlchemy AnalysisReport models
        total: Total number of reports matching query
        limit: Page size limit
        offset: Number of items skipped

    Returns:
        ReportListDTO with paginated results
    """
    return ReportListDTO(
        reports=[report_to_list_item_dto(r) for r in reports],
        total=total,
        limit=limit,
        offset=offset
    )


# ===== Generic Factories =====


def model_to_dto(model: Any, dto_class: Type[T]) -> T:
    """Generic factory to convert any SQLAlchemy model to a DTO.

    Args:
        model: SQLAlchemy model instance
        dto_class: Target DTO class

    Returns:
        Instance of dto_class with model data

    Example:
        >>> company_dto = model_to_dto(company, CompanyDTO)
    """
    return dto_class.model_validate(model)


def models_to_dtos(models: List[Any], dto_class: Type[T]) -> List[T]:
    """Generic factory to convert a list of models to DTOs.

    Args:
        models: List of SQLAlchemy model instances
        dto_class: Target DTO class

    Returns:
        List of DTO instances

    Example:
        >>> company_dtos = models_to_dtos(companies, CompanyDTO)
    """
    return [dto_class.model_validate(m) for m in models]


def dict_to_dto(data: Dict[str, Any], dto_class: Type[T]) -> T:
    """Convert dictionary data to a DTO.

    Useful for database query results that return dictionaries
    instead of ORM objects.

    Args:
        data: Dictionary with DTO field data
        dto_class: Target DTO class

    Returns:
        Instance of dto_class with dictionary data

    Example:
        >>> trending = dict_to_dto(row._mapping, TrendingCompanyDTO)
    """
    return dto_class(**data)


def paginated_response(
    items: List[T],
    total: int,
    limit: int,
    offset: int,
    list_dto_class: Type[Any]
) -> Any:
    """Generic factory for creating paginated list responses.

    Args:
        items: List of DTO items
        total: Total count matching query
        limit: Page size limit
        offset: Number of items skipped
        list_dto_class: Target list DTO class

    Returns:
        Instance of list_dto_class with paginated data

    Example:
        >>> response = paginated_response(
        ...     items=company_dtos,
        ...     total=100,
        ...     limit=20,
        ...     offset=0,
        ...     list_dto_class=CompanyListDTO
        ... )
    """
    # Determine the field name for items based on DTO class
    field_mapping = {
        "CompanyListDTO": "companies",
        "FilingListDTO": "filings",
        "MetricsListDTO": "metrics",
        "IntelligenceListDTO": "intelligence",
        "ReportListDTO": "reports",
    }

    field_name = field_mapping.get(
        list_dto_class.__name__,
        "items"  # Default fallback
    )

    return list_dto_class(**{
        field_name: items,
        "total": total,
        "limit": limit,
        "offset": offset
    })
