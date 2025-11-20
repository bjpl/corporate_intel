"""Legacy SEC ingestion module - DEPRECATED.

This file is deprecated and maintained only for backward compatibility.
All new code should import from src.pipeline.sec instead.

Migration guide:
- from src.pipeline.sec_ingestion import SECAPIClient
  → from src.pipeline.sec import SECAPIClient

- from src.pipeline.sec_ingestion import sec_ingestion_flow
  → from src.pipeline.sec import sec_ingestion_flow
"""

import warnings

warnings.warn(
    "src.pipeline.sec_ingestion is deprecated. "
    "Please import from src.pipeline.sec instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from the new modular structure for backward compatibility
from src.pipeline.sec import (
    SECAPIClient,
    RateLimiter,
    validate_filing_data,
    classify_edtech_company,
    get_or_create_company,
    store_filing,
    FilingRequest,
    fetch_company_data,
    fetch_filings,
    download_filing,
    sec_ingestion_flow,
    batch_sec_ingestion_flow,
)

__all__ = [
    "SECAPIClient",
    "RateLimiter",
    "validate_filing_data",
    "classify_edtech_company",
    "get_or_create_company",
    "store_filing",
    "FilingRequest",
    "fetch_company_data",
    "fetch_filings",
    "download_filing",
    "sec_ingestion_flow",
    "batch_sec_ingestion_flow",
]
