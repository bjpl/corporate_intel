"""Database session management with connection pooling."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from src.core.config import get_settings


# Global engine and session factory
_async_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_async_engine() -> AsyncEngine:
    """Get or create the async database engine with connection pooling.

    Returns:
        AsyncEngine: SQLAlchemy async engine instance

    Configuration:
        - Pool size: 5-20 connections
        - Max overflow: 10 additional connections
        - Pool recycle: 3600 seconds (1 hour)
        - Pool pre-ping: True (validates connections)
        - Echo: True in DEBUG mode
    """
    global _async_engine

    if _async_engine is None:
        settings = get_settings()

        # Connection pool configuration
        pool_size = 5 if settings.DEBUG else 20
        max_overflow = 10
        pool_recycle = 3600  # Recycle connections after 1 hour
        pool_pre_ping = True  # Test connections before using

        _async_engine = create_async_engine(
            settings.database_url,
            echo=settings.DEBUG,
            # Async engines use AsyncAdaptedQueuePool by default - don't specify poolclass
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_recycle=pool_recycle,
            pool_pre_ping=pool_pre_ping,
            # Connection arguments
            connect_args={
                "server_settings": {
                    "application_name": "corporate_intel_api",
                    "jit": "off",  # Disable JIT for faster simple queries
                },
                "command_timeout": 60,  # 60 second query timeout
                "timeout": 10,  # 10 second connection timeout
            },
        )

    return _async_engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory.

    Returns:
        async_sessionmaker: Factory for creating database sessions
    """
    global _async_session_factory

    if _async_session_factory is None:
        engine = get_async_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Don't expire objects after commit
            autoflush=False,  # Manual control over flushing
            autocommit=False,  # Manual transaction control
        )

    return _async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database sessions.

    Yields:
        AsyncSession: Database session for request handling

    Example:
        @app.get("/companies")
        async def get_companies(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Company))
            return result.scalars().all()
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db_connections():
    """Close all database connections and dispose of the engine.

    Call this during application shutdown to ensure clean cleanup.
    """
    global _async_engine, _async_session_factory

    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None

    _async_session_factory = None


# For testing - create engine without connection pooling
def get_test_engine(database_url: str) -> AsyncEngine:
    """Create a test database engine without connection pooling.

    Args:
        database_url: Database connection URL for testing

    Returns:
        AsyncEngine: Engine configured for testing
    """
    return create_async_engine(
        database_url,
        echo=True,
        poolclass=NullPool,  # No pooling for tests
        connect_args={
            "server_settings": {
                "application_name": "corporate_intel_test",
            }
        },
    )
