"""Database session management and initialization."""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool

from src.core.config import get_settings

# Define Base here so it can be imported by models
class Base(DeclarativeBase):
    """Base class for all database models."""
    pass

settings = get_settings()

# Create synchronous engine for FastAPI
engine = create_engine(
    settings.sync_database_url,
    poolclass=NullPool,
    echo=settings.DEBUG,
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
