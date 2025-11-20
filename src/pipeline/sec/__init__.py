"""SEC pipeline module - modular SEC EDGAR data ingestion.

This module provides a clean interface for SEC data ingestion while maintaining
backward compatibility with the monolithic sec_ingestion.py module.
"""

from src.pipeline.sec.client import SECAPIClient, RateLimiter
from src.pipeline.sec.parser import validate_filing_data, classify_edtech_company
from src.pipeline.sec.processor import get_or_create_company, store_filing
from src.pipeline.sec.orchestrator import (
    FilingRequest,
    fetch_company_data,
    fetch_filings,
    download_filing,
    sec_ingestion_flow,
    batch_sec_ingestion_flow,
)

__all__ = [
    # Client
    "SECAPIClient",
    "RateLimiter",
    # Parser
    "validate_filing_data",
    "classify_edtech_company",
    # Processor
    "get_or_create_company",
    "store_filing",
    # Orchestrator
    "FilingRequest",
    "fetch_company_data",
    "fetch_filings",
    "download_filing",
    "sec_ingestion_flow",
    "batch_sec_ingestion_flow",
]
