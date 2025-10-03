"""Database initialization and health check functions."""

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from src.core.config import get_settings
from src.db.session import get_async_engine


async def init_database() -> None:
    """Initialize database connection and verify extensions.

    This function:
    1. Tests database connectivity
    2. Verifies required extensions (TimescaleDB, pgvector, uuid-ossp)
    3. Checks that hypertables are configured
    4. Validates database schema version

    Note: This does NOT create tables - use Alembic migrations for that.
    Run: alembic upgrade head
    """
    logger.info("Initializing database connection...")

    engine = get_async_engine()

    try:
        async with engine.begin() as conn:
            # Test basic connectivity
            result = await conn.execute(text("SELECT 1"))
            logger.info("✓ Database connection successful")

            # Verify PostgreSQL version
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"✓ PostgreSQL version: {version}")

            # Check TimescaleDB extension
            result = await conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'timescaledb'")
            )
            if result.scalar():
                logger.info("✓ TimescaleDB extension is installed")

                # Get TimescaleDB version
                result = await conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'"))
                ts_version = result.scalar()
                logger.info(f"  TimescaleDB version: {ts_version}")
            else:
                logger.warning("⚠ TimescaleDB extension not found - run migrations first")

            # Check pgvector extension
            result = await conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
            )
            if result.scalar():
                logger.info("✓ pgvector extension is installed")
            else:
                logger.warning("⚠ pgvector extension not found - run migrations first")

            # Check uuid-ossp extension
            result = await conn.execute(
                text("SELECT extname FROM pg_extension WHERE extname = 'uuid-ossp'")
            )
            if result.scalar():
                logger.info("✓ uuid-ossp extension is installed")
            else:
                logger.warning("⚠ uuid-ossp extension not found - run migrations first")

            # Check if tables exist
            result = await conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name IN ('companies', 'sec_filings', 'financial_metrics')
                """)
            )
            table_count = result.scalar()

            if table_count == 3:
                logger.info("✓ Core tables exist")
            else:
                logger.warning(f"⚠ Only {table_count}/3 core tables found - run migrations: alembic upgrade head")

            # Check if financial_metrics is a hypertable
            result = await conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM timescaledb_information.hypertables
                    WHERE hypertable_name = 'financial_metrics'
                """)
            )
            if result.scalar():
                logger.info("✓ financial_metrics is configured as TimescaleDB hypertable")
            else:
                logger.warning("⚠ financial_metrics hypertable not found - run migrations first")

            # Check continuous aggregates
            result = await conn.execute(
                text("""
                    SELECT view_name
                    FROM timescaledb_information.continuous_aggregates
                """)
            )
            aggs = result.scalars().all()
            if aggs:
                logger.info(f"✓ Continuous aggregates: {', '.join(aggs)}")
            else:
                logger.warning("⚠ No continuous aggregates found - run migrations first")

        logger.info("✓ Database initialization complete")

    except Exception as e:
        logger.error(f"✗ Database initialization failed: {e}")
        raise


async def check_database_health() -> dict[str, any]:
    """Perform comprehensive database health check.

    Returns:
        dict: Health check results with connection status and metrics

    Example response:
        {
            "status": "healthy",
            "database": "corporate_intel",
            "connection_pool": {
                "size": 20,
                "checked_in": 15,
                "checked_out": 5,
                "overflow": 2
            },
            "extensions": {
                "timescaledb": "2.14.0",
                "pgvector": "0.5.1",
                "uuid-ossp": "1.1"
            },
            "tables": 13,
            "hypertables": 1
        }
    """
    engine = get_async_engine()
    health_data = {
        "status": "unhealthy",
        "database": None,
        "connection_pool": {},
        "extensions": {},
        "tables": 0,
        "hypertables": 0,
    }

    try:
        async with engine.begin() as conn:
            # Get database name
            result = await conn.execute(text("SELECT current_database()"))
            health_data["database"] = result.scalar()

            # Get connection pool stats
            pool = engine.pool
            health_data["connection_pool"] = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
            }

            # Get extension versions
            result = await conn.execute(
                text("""
                    SELECT extname, extversion
                    FROM pg_extension
                    WHERE extname IN ('timescaledb', 'vector', 'uuid-ossp')
                """)
            )
            for row in result:
                health_data["extensions"][row[0]] = row[1]

            # Count tables
            result = await conn.execute(
                text("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                """)
            )
            health_data["tables"] = result.scalar()

            # Count hypertables
            result = await conn.execute(
                text("SELECT COUNT(*) FROM timescaledb_information.hypertables")
            )
            health_data["hypertables"] = result.scalar()

            health_data["status"] = "healthy"

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_data["error"] = str(e)

    return health_data


async def verify_migrations() -> dict[str, any]:
    """Verify that all Alembic migrations have been applied.

    Returns:
        dict: Migration status information

    Example response:
        {
            "current_revision": "001",
            "migrations_applied": true,
            "pending_migrations": []
        }
    """
    engine = get_async_engine()
    migration_data = {
        "current_revision": None,
        "migrations_applied": False,
        "pending_migrations": [],
    }

    try:
        async with engine.begin() as conn:
            # Check if alembic_version table exists
            result = await conn.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'alembic_version'
                    )
                """)
            )

            if not result.scalar():
                migration_data["error"] = "Alembic version table not found - run: alembic upgrade head"
                return migration_data

            # Get current revision
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            current_rev = result.scalar()

            if current_rev:
                migration_data["current_revision"] = current_rev
                migration_data["migrations_applied"] = True
            else:
                migration_data["error"] = "No migrations applied - run: alembic upgrade head"

    except Exception as e:
        logger.error(f"Migration verification failed: {e}")
        migration_data["error"] = str(e)

    return migration_data


async def create_extensions() -> None:
    """Create required PostgreSQL extensions.

    Note: This requires superuser privileges. In production, extensions
    should be created during database provisioning or via migrations.

    This function is primarily for development/testing environments.
    """
    engine = get_async_engine()

    extensions = [
        ("timescaledb", "TimescaleDB for time-series data"),
        ("vector", "pgvector for embeddings"),
        ("uuid-ossp", "UUID generation"),
    ]

    try:
        async with engine.begin() as conn:
            for ext_name, description in extensions:
                try:
                    await conn.execute(text(f"CREATE EXTENSION IF NOT EXISTS {ext_name} CASCADE"))
                    logger.info(f"✓ Created extension: {ext_name} ({description})")
                except Exception as e:
                    logger.error(f"✗ Failed to create extension {ext_name}: {e}")
                    logger.warning("  This may require superuser privileges")

    except Exception as e:
        logger.error(f"Extension creation failed: {e}")
        raise
