"""Pipeline Common Utilities Module.

This module contains shared utilities and helper functions used across all
data ingestion pipelines (Yahoo Finance, Alpha Vantage, SEC).

Exports:
    - get_or_create_company: Get existing or create new company record
    - upsert_financial_metric: Insert or update financial metric with conflict resolution
    - retry_with_backoff: Retry decorator with exponential backoff
    - run_coordination_hook: Execute coordination hooks with error handling
    - notify_progress: Send progress notifications
"""

from .utilities import (
    get_or_create_company,
    upsert_financial_metric,
    retry_with_backoff,
    run_coordination_hook,
    notify_progress,
)

__all__ = [
    "get_or_create_company",
    "upsert_financial_metric",
    "retry_with_backoff",
    "run_coordination_hook",
    "notify_progress",
]
