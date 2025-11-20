"""Legacy data sources module - DEPRECATED.

This file is deprecated and maintained only for backward compatibility.
All new code should import from src.connectors.sources instead.

Migration guide:
- from src.connectors.data_sources import SECEdgarConnector
  → from src.connectors.sources import SECEdgarConnector

- from src.connectors.data_sources import DataAggregator
  → from src.connectors.sources import DataAggregator
"""

import warnings

warnings.warn(
    "src.connectors.data_sources is deprecated. "
    "Please import from src.connectors.sources instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export everything from the new modular structure for backward compatibility
from src.connectors.sources import (
    RateLimiter,
    safe_float,
    SECEdgarConnector,
    YahooFinanceConnector,
    AlphaVantageConnector,
    NewsAPIConnector,
    CrunchbaseConnector,
    GitHubConnector,
    DataAggregator,
)

__all__ = [
    "RateLimiter",
    "safe_float",
    "SECEdgarConnector",
    "YahooFinanceConnector",
    "AlphaVantageConnector",
    "NewsAPIConnector",
    "CrunchbaseConnector",
    "GitHubConnector",
    "DataAggregator",
]
