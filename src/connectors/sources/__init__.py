"""Data source connectors - modular connectors for various financial and data APIs.

This module provides a clean interface for all data source connectors while
maintaining backward compatibility with the monolithic data_sources.py module.
"""

from src.connectors.sources.base import RateLimiter, safe_float
from src.connectors.sources.sec import SECEdgarConnector
from src.connectors.sources.yahoo import YahooFinanceConnector
from src.connectors.sources.alpha_vantage import AlphaVantageConnector
from src.connectors.sources.news import NewsAPIConnector
from src.connectors.sources.crunchbase import CrunchbaseConnector
from src.connectors.sources.github import GitHubConnector
from src.connectors.sources.aggregator import DataAggregator

__all__ = [
    # Base utilities
    "RateLimiter",
    "safe_float",
    # Connectors
    "SECEdgarConnector",
    "YahooFinanceConnector",
    "AlphaVantageConnector",
    "NewsAPIConnector",
    "CrunchbaseConnector",
    "GitHubConnector",
    # Aggregator
    "DataAggregator",
]
