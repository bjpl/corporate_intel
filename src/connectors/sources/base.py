"""Base classes and utilities for data source connectors."""

import asyncio
from typing import Any


def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert value to float, handling 'None' strings, None, empty strings.

    Args:
        value: The value to convert to float
        default: Default value to return if conversion fails

    Returns:
        Float value or default if conversion fails
    """
    if value is None or value == '' or value == 'None' or value == 'null':
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self, calls_per_second: float):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Wait if necessary to respect rate limit."""
        async with self.lock:
            current = asyncio.get_event_loop().time()
            time_since_last = current - self.last_call

            if time_since_last < self.min_interval:
                await asyncio.sleep(self.min_interval - time_since_last)

            self.last_call = asyncio.get_event_loop().time()
