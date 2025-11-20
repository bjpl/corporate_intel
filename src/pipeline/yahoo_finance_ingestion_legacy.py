"""Legacy Yahoo Finance ingestion module - DEPRECATED.

This file is deprecated and maintained only for backward compatibility.
All new code should import from src.pipeline.yahoo instead.

Migration guide:
- from src.pipeline.yahoo_finance_ingestion import YahooFinanceIngestionPipeline
  → from src.pipeline.yahoo import YahooFinanceIngestionPipeline

- from src.pipeline.yahoo_finance_ingestion import run_ingestion
  → from src.pipeline.yahoo import run_ingestion
"""

import warnings

warnings.warn(
    "src.pipeline.yahoo_finance_ingestion is deprecated. "
    "Please import from src.pipeline.yahoo instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from the new modular structure for backward compatibility
from src.pipeline.yahoo import (
    YahooFinanceClient,
    EDTECH_COMPANIES,
    extract_financial_metrics,
    parse_company_data,
    upsert_company,
    ingest_quarterly_financials,
    YahooFinanceIngestionError,
    YahooFinanceIngestionPipeline,
    run_ingestion,
)

__all__ = [
    "YahooFinanceClient",
    "EDTECH_COMPANIES",
    "extract_financial_metrics",
    "parse_company_data",
    "upsert_company",
    "ingest_quarterly_financials",
    "YahooFinanceIngestionError",
    "YahooFinanceIngestionPipeline",
    "run_ingestion",
]
