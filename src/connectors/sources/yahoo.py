"""Yahoo Finance connector for real-time market data."""

from typing import Any, Dict

import pandas as pd
import yfinance as yf
from loguru import logger

from src.core.cache import cache_key_wrapper


class YahooFinanceConnector:
    """
    Yahoo Finance connector for real-time market data.
    Free, no API key required.
    """

    @cache_key_wrapper(prefix="yfinance", expire=300)  # 5 min cache
    async def get_stock_info(self, ticker: str) -> Dict[str, Any]:
        """Get comprehensive stock information."""
        try:
            stock = yf.Ticker(ticker)

            # Get various data points
            info = stock.info

            # Extract EdTech-relevant metrics
            return {
                'ticker': ticker,
                'company_name': info.get('longName', ''),
                'market_cap': info.get('marketCap', 0),
                'enterprise_value': info.get('enterpriseValue', 0),
                'trailing_pe': info.get('trailingPE', 0),
                'forward_pe': info.get('forwardPE', 0),
                'price_to_book': info.get('priceToBook', 0),
                'revenue_growth': info.get('revenueGrowth', 0),
                'gross_margins': info.get('grossMargins', 0),
                'operating_margins': info.get('operatingMargins', 0),
                'profit_margins': info.get('profitMargins', 0),
                'return_on_equity': info.get('returnOnEquity', 0),
                'total_revenue': info.get('totalRevenue', 0),
                'revenue_per_share': info.get('revenuePerShare', 0),
                'total_cash': info.get('totalCash', 0),
                'total_debt': info.get('totalDebt', 0),
                'free_cashflow': info.get('freeCashflow', 0),
                'operating_cashflow': info.get('operatingCashflow', 0),
                'earnings_growth': info.get('earningsGrowth', 0),
                'current_price': info.get('currentPrice', 0),
                '52_week_high': info.get('fiftyTwoWeekHigh', 0),
                '52_week_low': info.get('fiftyTwoWeekLow', 0),
                'shares_outstanding': info.get('sharesOutstanding', 0),
                'employees': info.get('fullTimeEmployees', 0),
                'website': info.get('website', ''),
                'industry': info.get('industry', ''),
                'sector': info.get('sector', ''),
            }

        except Exception as e:
            logger.error(f"Error fetching Yahoo Finance data for {ticker}: {e}")
            return {}

    async def get_quarterly_financials(self, ticker: str) -> pd.DataFrame:
        """Get quarterly financial statements."""
        try:
            stock = yf.Ticker(ticker)

            # Get quarterly financials
            quarterly = stock.quarterly_financials

            if quarterly is not None and not quarterly.empty:
                # Transpose and add metadata
                df = quarterly.T
                df['ticker'] = ticker
                df['period'] = df.index
                return df

            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error fetching quarterly financials for {ticker}: {e}")
            return pd.DataFrame()
