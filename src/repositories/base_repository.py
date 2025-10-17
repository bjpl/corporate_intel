"""Base repository pattern implementation.

This module provides the abstract base repository class with common CRUD operations,
transaction management, error handling, and connection pooling support.
"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from uuid import UUID

from loguru import logger
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Base

# Generic type for model classes
ModelType = TypeVar("ModelType", bound=Base)


class RepositoryError(Exception):
    """Base exception for repository operations."""
    pass


class DuplicateRecordError(RepositoryError):
    """Raised when attempting to create a duplicate record."""
    pass


class RecordNotFoundError(RepositoryError):
    """Raised when a requested record is not found."""
    pass


class TransactionError(RepositoryError):
    """Raised when a database transaction fails."""
    pass


class BaseRepository(ABC, Generic[ModelType]):
    """Abstract base repository with common database operations.

    This class provides a reusable pattern for database access that:
    - Decouples business logic from data access
    - Provides consistent error handling
    - Supports transaction management
    - Enables easier testing with mock repositories

    Attributes:
        model_class: SQLAlchemy model class this repository manages
        session: Async database session for queries

    Example:
        ```python
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession):
                super().__init__(User, session)

            async def find_by_email(self, email: str) -> Optional[User]:
                stmt = select(self.model_class).where(
                    self.model_class.email == email
                )
                result = await self.session.execute(stmt)
                return result.scalar_one_or_none()
        ```
    """

    def __init__(self, model_class: Type[ModelType], session: AsyncSession):
        """Initialize repository.

        Args:
            model_class: SQLAlchemy model class
            session: Async database session
        """
        self.model_class = model_class
        self.session = session

    async def create(self, **attributes) -> ModelType:
        """Create a new record.

        Args:
            **attributes: Model attributes as keyword arguments

        Returns:
            Created model instance

        Raises:
            DuplicateRecordError: If unique constraint is violated
            TransactionError: If database operation fails

        Example:
            ```python
            company = await repo.create(
                ticker="DUOL",
                name="Duolingo Inc.",
                sector="Education Technology"
            )
            ```
        """
        try:
            instance = self.model_class(**attributes)
            self.session.add(instance)
            await self.session.flush()
            await self.session.refresh(instance)

            logger.debug(
                f"Created {self.model_class.__name__} with attributes: {attributes}"
            )
            return instance

        except IntegrityError as e:
            await self.session.rollback()
            logger.warning(
                f"Duplicate {self.model_class.__name__}: {e.orig}"
            )
            raise DuplicateRecordError(
                f"Record with these attributes already exists: {attributes}"
            ) from e

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(
                f"Failed to create {self.model_class.__name__}: {e}"
            )
            raise TransactionError(
                f"Database error during create: {str(e)}"
            ) from e

    async def get_by_id(self, id: Union[UUID, int, str]) -> Optional[ModelType]:
        """Get a record by its primary key.

        Args:
            id: Primary key value (UUID, int, or str)

        Returns:
            Model instance or None if not found

        Example:
            ```python
            company = await repo.get_by_id(company_id)
            if company:
                print(f"Found: {company.name}")
            ```
        """
        try:
            result = await self.session.get(self.model_class, id)

            if result:
                logger.debug(f"Found {self.model_class.__name__} with id={id}")
            else:
                logger.debug(f"No {self.model_class.__name__} found with id={id}")

            return result

        except SQLAlchemyError as e:
            logger.error(f"Error fetching {self.model_class.__name__} by id={id}: {e}")
            raise TransactionError(f"Database error during fetch: {str(e)}") from e

    async def get_all(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None
    ) -> List[ModelType]:
        """Get all records with optional pagination.

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            order_by: Column name to sort by (default: id)

        Returns:
            List of model instances

        Example:
            ```python
            # Get first 100 companies ordered by name
            companies = await repo.get_all(limit=100, order_by="name")
            ```
        """
        try:
            stmt = select(self.model_class)

            # Apply ordering
            if order_by:
                order_column = getattr(self.model_class, order_by, None)
                if order_column is not None:
                    stmt = stmt.order_by(order_column)

            # Apply pagination
            if offset:
                stmt = stmt.offset(offset)
            if limit:
                stmt = stmt.limit(limit)

            result = await self.session.execute(stmt)
            records = result.scalars().all()

            logger.debug(
                f"Fetched {len(records)} {self.model_class.__name__} records "
                f"(limit={limit}, offset={offset})"
            )

            return list(records)

        except SQLAlchemyError as e:
            logger.error(f"Error fetching all {self.model_class.__name__}: {e}")
            raise TransactionError(f"Database error during fetch: {str(e)}") from e

    async def update(self, id: Union[UUID, int, str], **attributes) -> Optional[ModelType]:
        """Update a record by ID.

        Args:
            id: Primary key value
            **attributes: Attributes to update

        Returns:
            Updated model instance or None if not found

        Raises:
            RecordNotFoundError: If record doesn't exist
            TransactionError: If database operation fails

        Example:
            ```python
            updated = await repo.update(
                company_id,
                name="New Name",
                employee_count=500
            )
            ```
        """
        try:
            # Fetch the record first
            instance = await self.get_by_id(id)

            if not instance:
                raise RecordNotFoundError(
                    f"{self.model_class.__name__} with id={id} not found"
                )

            # Update attributes
            for key, value in attributes.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

            # Update timestamp if model has updated_at
            if hasattr(instance, 'updated_at'):
                instance.updated_at = datetime.utcnow()

            await self.session.flush()
            await self.session.refresh(instance)

            logger.debug(
                f"Updated {self.model_class.__name__} id={id} with: {attributes}"
            )

            return instance

        except RecordNotFoundError:
            raise

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Error updating {self.model_class.__name__} id={id}: {e}")
            raise TransactionError(f"Database error during update: {str(e)}") from e

    async def delete(self, id: Union[UUID, int, str]) -> bool:
        """Delete a record by ID.

        Args:
            id: Primary key value

        Returns:
            True if deleted, False if not found

        Raises:
            TransactionError: If database operation fails

        Example:
            ```python
            deleted = await repo.delete(company_id)
            if deleted:
                print("Company deleted successfully")
            ```
        """
        try:
            stmt = delete(self.model_class).where(
                self.model_class.id == id
            )

            result = await self.session.execute(stmt)
            await self.session.flush()

            deleted = result.rowcount > 0

            if deleted:
                logger.info(f"Deleted {self.model_class.__name__} id={id}")
            else:
                logger.debug(f"No {self.model_class.__name__} found with id={id}")

            return deleted

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Error deleting {self.model_class.__name__} id={id}: {e}")
            raise TransactionError(f"Database error during delete: {str(e)}") from e

    async def exists(self, id: Union[UUID, int, str]) -> bool:
        """Check if a record exists by ID.

        Args:
            id: Primary key value

        Returns:
            True if record exists, False otherwise

        Example:
            ```python
            if await repo.exists(company_id):
                print("Company exists")
            ```
        """
        try:
            result = await self.session.get(self.model_class, id)
            return result is not None

        except SQLAlchemyError as e:
            logger.error(f"Error checking existence of {self.model_class.__name__}: {e}")
            return False

    async def count(self, **filters) -> int:
        """Count records matching filters.

        Args:
            **filters: Filter conditions as keyword arguments

        Returns:
            Number of matching records

        Example:
            ```python
            # Count companies in EdTech sector
            count = await repo.count(sector="Education Technology")
            ```
        """
        try:
            stmt = select(self.model_class)

            # Apply filters
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    stmt = stmt.where(getattr(self.model_class, key) == value)

            result = await self.session.execute(stmt)
            records = result.scalars().all()

            return len(records)

        except SQLAlchemyError as e:
            logger.error(f"Error counting {self.model_class.__name__}: {e}")
            return 0

    async def find_by(self, **filters) -> List[ModelType]:
        """Find records matching filters.

        Args:
            **filters: Filter conditions as keyword arguments

        Returns:
            List of matching model instances

        Example:
            ```python
            # Find all companies in K-12 category
            companies = await repo.find_by(category="k12")
            ```
        """
        try:
            stmt = select(self.model_class)

            # Apply filters
            for key, value in filters.items():
                if hasattr(self.model_class, key):
                    stmt = stmt.where(getattr(self.model_class, key) == value)

            result = await self.session.execute(stmt)
            records = result.scalars().all()

            logger.debug(
                f"Found {len(records)} {self.model_class.__name__} records "
                f"matching filters: {filters}"
            )

            return list(records)

        except SQLAlchemyError as e:
            logger.error(f"Error finding {self.model_class.__name__}: {e}")
            raise TransactionError(f"Database error during search: {str(e)}") from e

    async def find_one_by(self, **filters) -> Optional[ModelType]:
        """Find a single record matching filters.

        Args:
            **filters: Filter conditions as keyword arguments

        Returns:
            First matching model instance or None

        Example:
            ```python
            # Find company by ticker
            company = await repo.find_one_by(ticker="DUOL")
            ```
        """
        records = await self.find_by(**filters)
        return records[0] if records else None

    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions.

        Automatically commits on success or rolls back on error.

        Example:
            ```python
            async with repo.transaction():
                await repo.create(name="Company 1")
                await repo.create(name="Company 2")
                # Both are committed together
            ```
        """
        try:
            yield self.session
            await self.session.commit()
            logger.debug(f"Transaction committed for {self.model_class.__name__}")

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Transaction rolled back for {self.model_class.__name__}: {e}")
            raise TransactionError(f"Transaction failed: {str(e)}") from e

    async def bulk_create(self, records: List[Dict[str, Any]]) -> List[ModelType]:
        """Bulk create multiple records.

        Args:
            records: List of attribute dictionaries

        Returns:
            List of created model instances

        Raises:
            TransactionError: If bulk operation fails

        Example:
            ```python
            companies = await repo.bulk_create([
                {"ticker": "DUOL", "name": "Duolingo"},
                {"ticker": "CHGG", "name": "Chegg"}
            ])
            ```
        """
        try:
            instances = [self.model_class(**record) for record in records]
            self.session.add_all(instances)
            await self.session.flush()

            for instance in instances:
                await self.session.refresh(instance)

            logger.info(
                f"Bulk created {len(instances)} {self.model_class.__name__} records"
            )

            return instances

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Bulk create failed for {self.model_class.__name__}: {e}")
            raise TransactionError(f"Bulk create failed: {str(e)}") from e

    async def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """Bulk update multiple records.

        Each update dict must include 'id' field.

        Args:
            updates: List of update dictionaries with 'id' and attributes

        Returns:
            Number of records updated

        Raises:
            TransactionError: If bulk operation fails

        Example:
            ```python
            count = await repo.bulk_update([
                {"id": id1, "employee_count": 500},
                {"id": id2, "employee_count": 1000}
            ])
            ```
        """
        try:
            count = 0

            for update_data in updates:
                record_id = update_data.pop('id')
                stmt = update(self.model_class).where(
                    self.model_class.id == record_id
                ).values(**update_data)

                result = await self.session.execute(stmt)
                count += result.rowcount

            await self.session.flush()

            logger.info(
                f"Bulk updated {count} {self.model_class.__name__} records"
            )

            return count

        except SQLAlchemyError as e:
            await self.session.rollback()
            logger.error(f"Bulk update failed for {self.model_class.__name__}: {e}")
            raise TransactionError(f"Bulk update failed: {str(e)}") from e
