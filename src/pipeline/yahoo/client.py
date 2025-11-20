"""Yahoo Finance API client with retry logic and circuit breaker protection."""

import asyncio
from typing import Any, Dict, Optional

import yfinance as yf
from loguru import logger

from src.core.circuit_breaker import yahoo_finance_breaker, yahoo_finance_fallback


class YahooFinanceClient:
    """Client for fetching data from Yahoo Finance API."""

    def __init__(self):
        """Initialize the Yahoo Finance client."""
        pass

    async def fetch_stock_info(self, ticker: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """Fetch comprehensive data from Yahoo Finance with retry logic.

        Protected by circuit breaker to prevent cascading failures when
        Yahoo Finance API is unavailable.

        Args:
            ticker: Stock ticker symbol
            max_retries: Maximum number of retry attempts

        Returns:
            Dict containing Yahoo Finance data or None if failed
        """
        for attempt in range(max_retries):
            try:
                # Run synchronous yfinance call in executor to avoid blocking
                loop = asyncio.get_event_loop()

                # Wrap API call with circuit breaker
                stock = yahoo_finance_breaker.call(yf.Ticker, ticker)
                stock_obj = await loop.run_in_executor(None, lambda: stock) if asyncio.iscoroutine(stock) else stock

                info = yahoo_finance_breaker.call(lambda: stock_obj.info)
                info_data = await loop.run_in_executor(None, lambda: info) if asyncio.iscoroutine(info) else info

                if not info_data or "regularMarketPrice" not in info_data:
                    logger.warning(f"Incomplete data for {ticker}, attempt {attempt + 1}/{max_retries}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    return None

                return info_data

            except Exception as e:
                logger.error(f"Error fetching data for {ticker} (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    # Use fallback strategy
                    return await yahoo_finance_fallback(ticker)

        return None

    async def fetch_quarterly_financials(self, ticker: str) -> Optional[Any]:
        """Fetch quarterly financial statements.

        Protected by circuit breaker to prevent cascading failures.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Quarterly financial data or None if failed
        """
        try:
            loop = asyncio.get_event_loop()

            # Wrap API calls with circuit breaker
            stock = yahoo_finance_breaker.call(yf.Ticker, ticker)
            stock_obj = await loop.run_in_executor(None, lambda: stock) if asyncio.iscoroutine(stock) else stock

            # Get quarterly income statement
            quarterly_income = yahoo_finance_breaker.call(lambda: stock_obj.quarterly_income_stmt)
            quarterly_income_data = await loop.run_in_executor(None, lambda: quarterly_income) if asyncio.iscoroutine(quarterly_income) else quarterly_income

            return quarterly_income_data

        except Exception as e:
            logger.error(f"Error fetching quarterly financials for {ticker}: {e}")
            return None

    async def fetch_quarterly_balance_sheet(self, ticker: str) -> Optional[Any]:
        """Fetch quarterly balance sheet.

        Protected by circuit breaker to prevent cascading failures.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Quarterly balance sheet data or None if failed
        """
        try:
            loop = asyncio.get_event_loop()

            # Wrap API calls with circuit breaker
            stock = yahoo_finance_breaker.call(yf.Ticker, ticker)
            stock_obj = await loop.run_in_executor(None, lambda: stock) if asyncio.iscoroutine(stock) else stock

            # Get quarterly balance sheet
            quarterly_balance = yahoo_finance_breaker.call(lambda: stock_obj.quarterly_balance_sheet)
            quarterly_balance_data = await loop.run_in_executor(None, lambda: quarterly_balance) if asyncio.iscoroutine(quarterly_balance) else quarterly_balance

            return quarterly_balance_data

        except Exception as e:
            logger.error(f"Error fetching quarterly balance sheet for {ticker}: {e}")
            return None
