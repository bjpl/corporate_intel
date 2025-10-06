"""SQLAlchemy models for corporate intelligence platform."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, relationship, mapped_column

if TYPE_CHECKING:
    from sqlalchemy.orm import RelationshipProperty

class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


class TimestampMixin:
    """Mixin for created/updated timestamps."""
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())


class Company(Base, TimestampMixin):
    """EdTech company entity."""
    
    __tablename__ = "companies"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    ticker = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    cik = Column(String(10), unique=True, index=True)  # SEC CIK number
    sector = Column(String(100))
    subsector = Column(String(100))
    
    # EdTech categorization
    category = Column(String(50))  # K-12, Higher Ed, Corporate, D2C, Enabling Tech
    subcategory = Column(JSON)  # Array of subcategories
    delivery_model = Column(String(50))  # B2B, B2C, B2B2C, Marketplace
    monetization_strategy = Column(JSON)  # SaaS, Transaction, Freemium, etc.
    
    # Company metadata
    founded_year = Column(Integer)
    headquarters = Column(String(255))
    website = Column(String(255))
    employee_count = Column(Integer)
    
    # Relationships
    filings: Mapped[List["SECFiling"]] = relationship("SECFiling", back_populates="company", cascade="all, delete-orphan")
    metrics: Mapped[List["FinancialMetric"]] = relationship("FinancialMetric", back_populates="company", cascade="all, delete-orphan")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="company", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_company_category", "category"),
        Index("idx_company_sector_subsector", "sector", "subsector"),
    )


class SECFiling(Base, TimestampMixin):
    """SEC filing documents."""
    
    __tablename__ = "sec_filings"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    
    # Filing information
    filing_type = Column(String(20), nullable=False)  # 10-K, 10-Q, 8-K, etc.
    filing_date = Column(DateTime(timezone=True), nullable=False, index=True)
    accession_number = Column(String(25), unique=True, nullable=False)
    filing_url = Column(Text)
    
    # Content
    raw_text = Column(Text)
    parsed_sections = Column(JSON)  # Structured sections
    
    # Processing status
    processing_status = Column(String(20), default="pending")
    processed_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    
    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="filings")
    
    __table_args__ = (
        Index("idx_filing_date", "filing_date"),
        Index("idx_filing_type_date", "filing_type", "filing_date"),
        UniqueConstraint("company_id", "accession_number", name="uq_company_filing"),
    )


class FinancialMetric(Base, TimestampMixin):
    """Time-series financial and operational metrics."""
    
    __tablename__ = "financial_metrics"
    __table_args__ = (
        Index("idx_metric_time", "metric_date", "metric_type"),
        Index("idx_company_metric", "company_id", "metric_type", "metric_date"),
        UniqueConstraint("company_id", "metric_type", "metric_date", "period_type", 
                        name="uq_company_metric_period"),
        {"timescaledb_hypertable": {"time_column": "metric_date"}},  # TimescaleDB hypertable
    )
    
    # Composite primary key (id, metric_date) required for TimescaleDB hypertables
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    company_id = Column(PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)

    # Time dimension - part of composite primary key for TimescaleDB partitioning
    metric_date = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    period_type = Column(String(20), nullable=False)  # quarterly, annual, monthly
    
    # Metric identification
    metric_type = Column(String(50), nullable=False)  # revenue, mau, arpu, cac, etc.
    metric_category = Column(String(50))  # financial, operational, edtech_specific
    
    # Values
    value = Column(Float, nullable=False)
    unit = Column(String(20))  # USD, percent, count, etc.
    
    # Metadata
    source = Column(String(50))  # sec_filing, api, manual
    source_document_id = Column(PGUUID(as_uuid=True))
    confidence_score = Column(Float)  # 0-1 confidence in extracted value
    
    # Relationships
    company: Mapped["Company"] = relationship("Company", back_populates="metrics")


class Document(Base, TimestampMixin):
    """Generic document storage with vector embeddings."""
    
    __tablename__ = "documents"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(PGUUID(as_uuid=True), ForeignKey("companies.id"))
    
    # Document metadata
    document_type = Column(String(50), nullable=False)  # earnings_transcript, presentation, etc.
    title = Column(String(500))
    document_date = Column(DateTime(timezone=True))
    source_url = Column(Text)
    
    # Storage
    storage_path = Column(Text)  # MinIO path
    file_hash = Column(String(64))  # SHA-256
    file_size = Column(BigInteger)
    mime_type = Column(String(100))
    
    # Content
    content = Column(Text)
    extracted_data = Column(JSON)  # Structured extraction
    
    # Vector embedding for semantic search
    embedding = Column(Vector(1536))  # OpenAI embedding dimension
    
    # Processing
    processing_status = Column(String(20), default="pending")
    processed_at = Column(DateTime(timezone=True))
    
    # Relationships
    company: Mapped[Optional["Company"]] = relationship("Company", back_populates="documents")
    chunks: Mapped[List["DocumentChunk"]] = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_document_type_date", "document_type", "document_date"),
        Index("idx_document_embedding", "embedding", postgresql_using="ivfflat"),
    )


class DocumentChunk(Base, TimestampMixin):
    """Document chunks for granular semantic search."""
    
    __tablename__ = "document_chunks"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id = Column(PGUUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    
    # Chunk information
    chunk_index = Column(Integer, nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_tokens = Column(Integer)
    
    # Vector embedding
    embedding = Column(Vector(1536))
    
    # Metadata
    page_number = Column(Integer)
    section_name = Column(String(255))
    
    # Relationships
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
    
    __table_args__ = (
        Index("idx_chunk_embedding", "embedding", postgresql_using="ivfflat"),
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk"),
    )


class AnalysisReport(Base, TimestampMixin):
    """Generated analysis reports."""
    
    __tablename__ = "analysis_reports"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Report metadata
    report_type = Column(String(50), nullable=False)  # competitor, segment, opportunity
    title = Column(String(500), nullable=False)
    description = Column(Text)
    
    # Scope
    companies = Column(JSON)  # Array of company IDs
    date_range_start = Column(DateTime(timezone=True))
    date_range_end = Column(DateTime(timezone=True))
    
    # Content
    executive_summary = Column(Text)
    findings = Column(JSON)  # Structured findings
    recommendations = Column(JSON)
    
    # Storage
    report_url = Column(Text)  # Generated report location
    format = Column(String(20))  # pdf, html, json
    
    # Cache control
    cache_key = Column(String(255), unique=True)
    expires_at = Column(DateTime(timezone=True))
    
    __table_args__ = (
        Index("idx_report_type_date", "report_type", "created_at"),
        Index("idx_report_cache", "cache_key", "expires_at"),
    )


class MarketIntelligence(Base, TimestampMixin):
    """Market intelligence and competitive insights."""
    
    __tablename__ = "market_intelligence"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Intelligence type
    intel_type = Column(String(50), nullable=False)  # funding, acquisition, partnership, etc.
    category = Column(String(50))  # EdTech segment
    
    # Content
    title = Column(String(500), nullable=False)
    summary = Column(Text)
    full_content = Column(Text)
    
    # Entities involved
    primary_company_id = Column(PGUUID(as_uuid=True), ForeignKey("companies.id"))
    related_companies = Column(JSON)  # Array of company IDs
    
    # Metadata
    event_date = Column(DateTime(timezone=True))
    source = Column(String(255))
    source_url = Column(Text)
    confidence_score = Column(Float)
    
    # Impact assessment
    impact_assessment = Column(JSON)
    sentiment_score = Column(Float)  # -1 to 1
    
    __table_args__ = (
        Index("idx_intel_type_date", "intel_type", "event_date"),
        Index("idx_intel_company", "primary_company_id", "event_date"),
    )