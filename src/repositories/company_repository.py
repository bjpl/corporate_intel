"""Company repository for company-specific database operations.

This repository provides specialized methods for managing company data,
including ticker lookups, CIK lookups, and EdTech categorization queries.
"""

from typing import List, Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models import Company
from src.repositories.base_repository import (
    BaseRepository,
    DuplicateRecordError,
    RecordNotFoundError,
    TransactionError,
)


class CompanyRepository(BaseRepository[Company]):
    """Repository for Company model with specialized company operations.

    Extends BaseRepository with company-specific queries including:
    - Get or create by ticker
    - Find by ticker or CIK
    - Search by category/sector
    - EdTech categorization queries

    Example:
        ```python
        async with get_db_session() as session:
            repo = CompanyRepository(session)

            # Get or create company
            company = await repo.get_or_create_by_ticker("DUOL")

            # Find by category
            k12_companies = await repo.find_by_category("k12")

            # Search by name
            results = await repo.search_by_name("education")
        ```
    """

    def __init__(self, session: AsyncSession):
        """Initialize company repository.

        Args:
            session: Async database session
        """
        super().__init__(Company, session)

    async def get_or_create_by_ticker(
        self,
        ticker: str,
        defaults: Optional[dict] = None
    ) -> tuple[Company, bool]:
        """Get existing company by ticker or create if doesn't exist.

        Args:
            ticker: Company stock ticker symbol (case-insensitive)
            defaults: Optional default values for creation

        Returns:
            Tuple of (company instance, created flag)
            - created=True if new company was created
            - created=False if existing company was returned

        Example:
            ```python
            company, created = await repo.get_or_create_by_ticker(
                "DUOL",
                defaults={"name": "Duolingo Inc.", "sector": "EdTech"}
            )
            if created:
                print("Created new company")
            ```
        """
        ticker = ticker.upper()

        try:
            # Try to find existing company
            existing = await self.find_by_ticker(ticker)

            if existing:
                logger.debug(f"Found existing company: {ticker} (ID: {existing.id})")
                return existing, False

            # Create new company
            create_data = defaults or {}
            create_data['ticker'] = ticker

            # Set default name if not provided
            if 'name' not in create_data:
                create_data['name'] = f"{ticker} (Auto-created)"

            company = await self.create(**create_data)

            logger.info(f"Created new company: {ticker} (ID: {company.id})")
            return company, True

        except DuplicateRecordError:
            # Race condition: another process created it between our check and create
            existing = await self.find_by_ticker(ticker)
            if existing:
                return existing, False
            raise

    async def find_by_ticker(self, ticker: str) -> Optional[Company]:
        """Find company by ticker symbol.

        Args:
            ticker: Company stock ticker (case-insensitive)

        Returns:
            Company instance or None if not found

        Example:
            ```python
            company = await repo.find_by_ticker("DUOL")
            if company:
                print(f"Found: {company.name}")
            ```
        """
        ticker = ticker.upper()

        stmt = select(Company).where(Company.ticker == ticker)
        result = await self.session.execute(stmt)
        company = result.scalar_one_or_none()

        if company:
            logger.debug(f"Found company by ticker: {ticker} (ID: {company.id})")
        else:
            logger.debug(f"No company found with ticker: {ticker}")

        return company

    async def find_by_cik(self, cik: str) -> Optional[Company]:
        """Find company by SEC CIK number.

        Args:
            cik: SEC Central Index Key (CIK) number

        Returns:
            Company instance or None if not found

        Example:
            ```python
            company = await repo.find_by_cik("0001364612")
            ```
        """
        # Normalize CIK (remove leading zeros, pad to 10 digits)
        cik = cik.lstrip('0').zfill(10)

        stmt = select(Company).where(Company.cik == cik)
        result = await self.session.execute(stmt)
        company = result.scalar_one_or_none()

        if company:
            logger.debug(f"Found company by CIK: {cik} (ID: {company.id})")
        else:
            logger.debug(f"No company found with CIK: {cik}")

        return company

    async def find_by_ticker_or_cik(
        self,
        ticker: Optional[str] = None,
        cik: Optional[str] = None
    ) -> Optional[Company]:
        """Find company by ticker or CIK.

        Args:
            ticker: Optional company ticker
            cik: Optional SEC CIK number

        Returns:
            Company instance or None if not found

        Raises:
            ValueError: If neither ticker nor CIK provided

        Example:
            ```python
            # Find by either identifier
            company = await repo.find_by_ticker_or_cik(ticker="DUOL")
            company = await repo.find_by_ticker_or_cik(cik="0001364612")
            ```
        """
        if not ticker and not cik:
            raise ValueError("Must provide either ticker or cik")

        conditions = []

        if ticker:
            conditions.append(Company.ticker == ticker.upper())

        if cik:
            cik = cik.lstrip('0').zfill(10)
            conditions.append(Company.cik == cik)

        stmt = select(Company).where(or_(*conditions))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_category(
        self,
        category: str,
        limit: Optional[int] = None
    ) -> List[Company]:
        """Find companies by EdTech category.

        Args:
            category: EdTech category (k12, higher_education, corporate, etc.)
            limit: Optional maximum number of results

        Returns:
            List of companies in the category

        Example:
            ```python
            # Get all K-12 companies
            k12_companies = await repo.find_by_category("k12", limit=50)
            ```
        """
        stmt = select(Company).where(Company.category == category)

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        companies = result.scalars().all()

        logger.debug(f"Found {len(companies)} companies in category: {category}")

        return list(companies)

    async def find_by_sector(
        self,
        sector: str,
        subsector: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Company]:
        """Find companies by sector and optional subsector.

        Args:
            sector: Company sector
            subsector: Optional subsector filter
            limit: Optional maximum number of results

        Returns:
            List of matching companies

        Example:
            ```python
            # Get all EdTech companies
            edtech = await repo.find_by_sector("Education Technology")

            # Get specific subsector
            online_learning = await repo.find_by_sector(
                "Education Technology",
                subsector="Online Learning"
            )
            ```
        """
        stmt = select(Company).where(Company.sector == sector)

        if subsector:
            stmt = stmt.where(Company.subsector == subsector)

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        companies = result.scalars().all()

        logger.debug(
            f"Found {len(companies)} companies in sector: {sector}"
            + (f", subsector: {subsector}" if subsector else "")
        )

        return list(companies)

    async def search_by_name(
        self,
        name_query: str,
        limit: int = 50
    ) -> List[Company]:
        """Search companies by name (case-insensitive partial match).

        Args:
            name_query: Name search string
            limit: Maximum number of results (default: 50)

        Returns:
            List of matching companies

        Example:
            ```python
            # Find companies with "education" in name
            results = await repo.search_by_name("education")
            ```
        """
        search_pattern = f"%{name_query}%"

        stmt = select(Company).where(
            Company.name.ilike(search_pattern)
        ).limit(limit)

        result = await self.session.execute(stmt)
        companies = result.scalars().all()

        logger.debug(
            f"Found {len(companies)} companies matching name query: '{name_query}'"
        )

        return list(companies)

    async def get_all_tickers(self) -> List[str]:
        """Get list of all company tickers.

        Returns:
            List of ticker symbols

        Example:
            ```python
            tickers = await repo.get_all_tickers()
            print(f"Tracking {len(tickers)} companies")
            ```
        """
        stmt = select(Company.ticker).order_by(Company.ticker)
        result = await self.session.execute(stmt)
        tickers = [row[0] for row in result.fetchall()]

        logger.debug(f"Retrieved {len(tickers)} company tickers")

        return tickers

    async def get_companies_by_delivery_model(
        self,
        delivery_model: str,
        limit: Optional[int] = None
    ) -> List[Company]:
        """Find companies by delivery model.

        Args:
            delivery_model: Delivery model (B2B, B2C, B2B2C, Marketplace)
            limit: Optional maximum number of results

        Returns:
            List of companies with matching delivery model

        Example:
            ```python
            # Get all B2B companies
            b2b_companies = await repo.get_companies_by_delivery_model("B2B")
            ```
        """
        stmt = select(Company).where(Company.delivery_model == delivery_model)

        if limit:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        companies = result.scalars().all()

        logger.debug(
            f"Found {len(companies)} companies with delivery model: {delivery_model}"
        )

        return list(companies)

    async def get_companies_with_metrics(self) -> List[Company]:
        """Get companies that have financial metrics data.

        Returns:
            List of companies with at least one metric record

        Example:
            ```python
            # Get companies with data for dashboard
            companies = await repo.get_companies_with_metrics()
            ```
        """
        # Eager load relationships to prevent N+1 queries
        stmt = select(Company).options(
            selectinload(Company.metrics),
            selectinload(Company.filings)
        ).where(
            Company.metrics.any()
        ).order_by(Company.name)

        result = await self.session.execute(stmt)
        companies = result.scalars().all()

        logger.debug(
            f"Found {len(companies)} companies with financial metrics"
        )

        return list(companies)

    async def update_company_metadata(
        self,
        company_id: UUID,
        **metadata
    ) -> Company:
        """Update company metadata fields.

        Args:
            company_id: Company UUID
            **metadata: Metadata fields to update (founded_year, headquarters, etc.)

        Returns:
            Updated company instance

        Raises:
            RecordNotFoundError: If company doesn't exist

        Example:
            ```python
            company = await repo.update_company_metadata(
                company_id,
                founded_year=2011,
                headquarters="Pittsburgh, PA",
                website="https://duolingo.com",
                employee_count=700
            )
            ```
        """
        return await self.update(company_id, **metadata)

    async def count_by_category(self) -> dict[str, int]:
        """Count companies grouped by EdTech category.

        Returns:
            Dictionary mapping category to count

        Example:
            ```python
            category_counts = await repo.count_by_category()
            # {"k12": 15, "higher_education": 23, ...}
            ```
        """
        stmt = select(Company)
        result = await self.session.execute(stmt)
        companies = result.scalars().all()

        # Group by category
        counts = {}
        for company in companies:
            category = company.category or "uncategorized"
            counts[category] = counts.get(category, 0) + 1

        logger.debug(f"Company counts by category: {counts}")

        return counts

    async def get_recently_added(self, days: int = 7) -> List[Company]:
        """Get companies added within the last N days.

        Args:
            days: Number of days to look back (default: 7)

        Returns:
            List of recently added companies

        Example:
            ```python
            # Get companies added in last 7 days
            recent = await repo.get_recently_added(days=7)
            ```
        """
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        stmt = select(Company).where(
            Company.created_at >= cutoff_date
        ).order_by(Company.created_at.desc())

        result = await self.session.execute(stmt)
        companies = result.scalars().all()

        logger.debug(
            f"Found {len(companies)} companies added in last {days} days"
        )

        return list(companies)
