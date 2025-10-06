"""Data ingestion pipelines for corporate intelligence platform."""

from src.pipeline.yahoo_finance_ingestion import (
    YahooFinanceIngestionPipeline,
    run_ingestion,
    EDTECH_COMPANIES,
)

__all__ = [
    "YahooFinanceIngestionPipeline",
    "run_ingestion",
    "EDTECH_COMPANIES",
]
