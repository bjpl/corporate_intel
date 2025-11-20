"""Alpha Vantage connector for fundamental data."""

from typing import Any, Dict

from alpha_vantage.fundamentaldata import FundamentalData
from loguru import logger

from src.core.cache import cache_key_wrapper
from src.core.circuit_breaker import alpha_vantage_breaker, alpha_vantage_fallback
from src.core.config import get_settings
from src.connectors.sources.base import RateLimiter, safe_float


class AlphaVantageConnector:
    """
    Alpha Vantage connector for fundamental data.
    Free tier: 5 API calls/minute, 500 calls/day.
    """

    def __init__(self):
        self.settings = get_settings()
        if self.settings.ALPHA_VANTAGE_API_KEY:
            self.fd = FundamentalData(
                key=self.settings.ALPHA_VANTAGE_API_KEY.get_secret_value()
            )
            self.rate_limiter = RateLimiter(5/60)  # 5 calls per minute
        else:
            self.fd = None
            logger.warning("Alpha Vantage API key not configured")

    @cache_key_wrapper(prefix="alpha_vantage", expire=3600)  # 1 hour cache
    async def get_company_overview(self, ticker: str) -> Dict[str, Any]:
        """Get company overview with fundamental data.

        Protected by circuit breaker to prevent cascading failures when
        Alpha Vantage API is unavailable or rate-limited.
        """
        if not self.fd:
            return {}

        await self.rate_limiter.acquire()

        try:
            # Wrap API call with circuit breaker
            # Circuit opens after 5 consecutive failures
            data, _ = alpha_vantage_breaker.call(self.fd.get_company_overview, ticker)

            # Extract EdTech-relevant metrics
            return {
                'ticker': ticker,
                'market_cap': safe_float(data.get('MarketCapitalization'), 0.0),
                'pe_ratio': safe_float(data.get('PERatio'), 0.0),
                'peg_ratio': safe_float(data.get('PEGRatio'), 0.0),
                'dividend_yield': safe_float(data.get('DividendYield'), 0.0),
                'eps': safe_float(data.get('EPS'), 0.0),
                'revenue_ttm': safe_float(data.get('RevenueTTM'), 0.0),
                'revenue_per_share_ttm': safe_float(data.get('RevenuePerShareTTM'), 0.0),
                'profit_margin': safe_float(data.get('ProfitMargin'), 0.0),
                'operating_margin_ttm': safe_float(data.get('OperatingMarginTTM'), 0.0),
                'return_on_assets_ttm': safe_float(data.get('ReturnOnAssetsTTM'), 0.0),
                'return_on_equity_ttm': safe_float(data.get('ReturnOnEquityTTM'), 0.0),
                'quarterly_earnings_growth_yoy': safe_float(data.get('QuarterlyEarningsGrowthYOY'), 0.0),
                'quarterly_revenue_growth_yoy': safe_float(data.get('QuarterlyRevenueGrowthYOY'), 0.0),
                'analyst_target_price': safe_float(data.get('AnalystTargetPrice'), 0.0),
                'trailing_pe': safe_float(data.get('TrailingPE'), 0.0),
                'forward_pe': safe_float(data.get('ForwardPE'), 0.0),
                'price_to_sales_ttm': safe_float(data.get('PriceToSalesRatioTTM'), 0.0),
                'price_to_book': safe_float(data.get('PriceToBookRatio'), 0.0),
                'ev_to_revenue': safe_float(data.get('EVToRevenue'), 0.0),
                'ev_to_ebitda': safe_float(data.get('EVToEBITDA'), 0.0),
                'beta': safe_float(data.get('Beta'), 0.0),
                '52_week_high': safe_float(data.get('52WeekHigh'), 0.0),
                '52_week_low': safe_float(data.get('52WeekLow'), 0.0),
            }

        except Exception as e:
            logger.error(f"Error fetching Alpha Vantage data for {ticker}: {e}")
            # Fallback to empty data - caller handles gracefully
            return await alpha_vantage_fallback(ticker)
