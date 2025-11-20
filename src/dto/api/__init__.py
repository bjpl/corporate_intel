"""API endpoint-specific DTOs.

This package contains DTOs for each API endpoint category:
- companies: Company management DTOs
- filings: SEC filing DTOs
- metrics: Financial metrics DTOs
- intelligence: Market intelligence DTOs
- reports: Analysis report DTOs
- admin: Admin and monitoring DTOs
- health: Health check DTOs
"""

# Import endpoint DTOs for easy access
from src.dto.api.companies import (
    CompanyCreateDTO,
    CompanyDTO,
    CompanyListDTO,
    CompanyMetricsDTO,
    CompanyUpdateDTO,
    TrendingCompanyDTO,
)
from src.dto.api.filings import (
    FilingCreateDTO,
    FilingDTO,
    FilingListDTO,
)
from src.dto.api.metrics import (
    MetricCreateDTO,
    MetricDTO,
    MetricsListDTO,
)
from src.dto.api.intelligence import (
    IntelligenceCreateDTO,
    IntelligenceDTO,
    IntelligenceListDTO,
)
from src.dto.api.reports import (
    ReportDTO,
    ReportGenerationRequestDTO,
    ReportGenerationResponseDTO,
    ReportListDTO,
)
from src.dto.api.admin import (
    DatabaseStatsDTO,
    IndexUsageDTO,
    QueryPerformanceDTO,
    TableStatsDTO,
)
from src.dto.api.health import (
    ComponentHealthDTO,
    DetailedHealthDTO,
    HealthDTO,
    PlatformMetricsDTO,
)

__all__ = [
    # Companies
    "CompanyDTO",
    "CompanyCreateDTO",
    "CompanyUpdateDTO",
    "CompanyListDTO",
    "CompanyMetricsDTO",
    "TrendingCompanyDTO",
    # Filings
    "FilingDTO",
    "FilingCreateDTO",
    "FilingListDTO",
    # Metrics
    "MetricDTO",
    "MetricCreateDTO",
    "MetricsListDTO",
    # Intelligence
    "IntelligenceDTO",
    "IntelligenceCreateDTO",
    "IntelligenceListDTO",
    # Reports
    "ReportDTO",
    "ReportGenerationRequestDTO",
    "ReportGenerationResponseDTO",
    "ReportListDTO",
    # Admin
    "QueryPerformanceDTO",
    "DatabaseStatsDTO",
    "TableStatsDTO",
    "IndexUsageDTO",
    # Health
    "HealthDTO",
    "DetailedHealthDTO",
    "ComponentHealthDTO",
    "PlatformMetricsDTO",
]
