"""Repository layer for data access abstraction.

This package provides the repository pattern implementation that decouples
business logic from database operations, improving testability and maintainability.

Repositories:
    BaseRepository: Abstract base class with common CRUD operations
    CompanyRepository: Company-specific queries and operations
    MetricsRepository: Financial metrics time-series operations

Exceptions:
    RepositoryError: Base exception for all repository errors
    DuplicateRecordError: Unique constraint violation
    RecordNotFoundError: Record not found
    TransactionError: Database transaction failure

Example:
    ```python
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.repositories import CompanyRepository, MetricsRepository

    async def example(session: AsyncSession):
        # Company operations
        company_repo = CompanyRepository(session)
        company, created = await company_repo.get_or_create_by_ticker("DUOL")

        # Metrics operations
        metrics_repo = MetricsRepository(session)
        metric = await metrics_repo.upsert_metric(
            company_id=company.id,
            metric_type="revenue",
            metric_date=datetime(2024, 3, 31),
            period_type="quarterly",
            value=50000000.0,
            unit="USD"
        )

        # Transaction management
        async with company_repo.transaction():
            await company_repo.create(ticker="NEW", name="New Company")
            await company_repo.create(ticker="TEST", name="Test Company")
            # Both committed together
    ```
"""

from src.repositories.base_repository import (
    BaseRepository,
    DuplicateRecordError,
    RecordNotFoundError,
    RepositoryError,
    TransactionError,
)
from src.repositories.company_repository import CompanyRepository
from src.repositories.metrics_repository import MetricsRepository

__all__ = [
    # Base
    "BaseRepository",
    # Exceptions
    "RepositoryError",
    "DuplicateRecordError",
    "RecordNotFoundError",
    "TransactionError",
    # Specialized repositories
    "CompanyRepository",
    "MetricsRepository",
]
