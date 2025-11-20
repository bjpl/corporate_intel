"""Yahoo Finance pipeline module - modular Yahoo Finance data ingestion.

This module provides a clean interface for Yahoo Finance data ingestion while
maintaining backward compatibility with the monolithic yahoo_finance_ingestion.py module.
"""

from src.pipeline.yahoo.client import YahooFinanceClient
from src.pipeline.yahoo.constants import EDTECH_COMPANIES
from src.pipeline.yahoo.parser import extract_financial_metrics, parse_company_data
from src.pipeline.yahoo.processor import upsert_company, ingest_quarterly_financials
from src.pipeline.yahoo.orchestrator import (
    YahooFinanceIngestionError,
    YahooFinanceIngestionPipeline,
    run_ingestion,
)

__all__ = [
    # Client
    "YahooFinanceClient",
    # Constants
    "EDTECH_COMPANIES",
    # Parser
    "extract_financial_metrics",
    "parse_company_data",
    # Processor
    "upsert_company",
    "ingest_quarterly_financials",
    # Orchestrator
    "YahooFinanceIngestionError",
    "YahooFinanceIngestionPipeline",
    "run_ingestion",
]
