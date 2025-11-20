"""
Data Source Connectors for Corporate Intelligence Platform
==========================================================

SPARC SPECIFICATION:
-------------------
Purpose: Connect to multiple financial data sources for EdTech intelligence
Data Sources:
  1. SEC EDGAR API - Financial filings (10-K, 10-Q, 8-K)
  2. Yahoo Finance - Real-time stock data and metrics
  3. Alpha Vantage - Financial statements and indicators
  4. NewsAPI - Market news and sentiment
  5. Crunchbase API - Funding rounds and company data
  6. GitHub API - Open source activity metrics
  7. SimilarWeb API - Web traffic analytics
  8. Glassdoor API - Employee sentiment and reviews

ARCHITECTURE:
- Async/await for concurrent API calls
- Rate limiting per API requirements
- Retry logic with exponential backoff
- Response caching to minimize API costs
"""

import asyncio
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import aiohttp
import pandas as pd
import yfinance as yf
from alpha_vantage.fundamentaldata import FundamentalData
from loguru import logger
from sec_edgar_api import EdgarClient

from src.core.cache import cache_key_wrapper, get_cache
from src.core.config import get_settings
from src.core.circuit_breaker import (
    alpha_vantage_breaker,
    alpha_vantage_fallback,
)


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


class SECEdgarConnector:
    """
    SEC EDGAR API connector for financial filings.
    Free API with 10 requests/second limit.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.client = EdgarClient(user_agent=self.settings.SEC_USER_AGENT)
        self.rate_limiter = RateLimiter(10)  # 10 requests/second
    
    async def get_company_filings(
        self,
        ticker: str,
        filing_types: List[str] = ["10-K", "10-Q", "8-K"],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Fetch recent filings for a company."""
        await self.rate_limiter.acquire()
        
        try:
            # Get company CIK
            submissions = self.client.get_submissions(ticker=ticker)
            
            if not submissions:
                logger.warning(f"No submissions found for {ticker}")
                return []
            
            filings = []
            recent_filings = submissions['filings']['recent']
            
            for i in range(min(limit, len(recent_filings['form']))):
                if recent_filings['form'][i] in filing_types:
                    filings.append({
                        'ticker': ticker,
                        'form': recent_filings['form'][i],
                        'filing_date': recent_filings['filingDate'][i],
                        'accession_number': recent_filings['accessionNumber'][i],
                        'primary_document': recent_filings['primaryDocument'][i],
                        'description': recent_filings['primaryDocDescription'][i],
                    })
            
            return filings
            
        except Exception as e:
            logger.error(f"Error fetching SEC filings for {ticker}: {e}")
            return []
    
    async def get_filing_content(self, accession_number: str, ticker: str) -> str:
        """Download actual filing content."""
        await self.rate_limiter.acquire()
        
        try:
            # Get filing details
            filing = self.client.get_filing(accession_number)
            return filing.get('content', '')
            
        except Exception as e:
            logger.error(f"Error downloading filing {accession_number}: {e}")
            return ""


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


class NewsAPIConnector:
    """
    NewsAPI connector for market sentiment and news.
    Free tier: 100 requests/day.
    """

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.NEWSAPI_KEY if hasattr(self.settings, 'NEWSAPI_KEY') else None
        self.base_url = "https://newsapi.org/v2"
        self.rate_limiter = RateLimiter(100/86400)  # 100 per day

        if not self.api_key:
            logger.warning("NewsAPI key not configured")
    
    async def get_company_news(
        self,
        company_name: str,
        days_back: int = 7
    ) -> List[Dict[str, Any]]:
        """Fetch recent news about a company."""
        if not self.api_key:
            logger.warning("NewsAPI key not configured, skipping news fetch")
            return []

        await self.rate_limiter.acquire()

        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        params = {
            'q': f'"{company_name}" AND (education OR edtech OR learning)',
            'from': from_date,
            'sortBy': 'relevancy',
            'apiKey': self.api_key,
            'language': 'en',
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/everything",
                    params=params
                ) as response:
                    data = await response.json()
                    
                    if data.get('status') == 'ok':
                        articles = data.get('articles', [])
                        
                        # Process articles
                        processed = []
                        for article in articles[:10]:  # Limit to 10
                            processed.append({
                                'title': article.get('title'),
                                'description': article.get('description'),
                                'url': article.get('url'),
                                'published_at': article.get('publishedAt'),
                                'source': article.get('source', {}).get('name'),
                                'sentiment': self._analyze_sentiment(
                                    article.get('title', '') + ' ' + 
                                    article.get('description', '')
                                ),
                            })
                        
                        return processed
                    
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching news for {company_name}: {e}")
            return []
    
    def _analyze_sentiment(self, text: str) -> float:
        """Simple sentiment analysis (would use NLP model in production)."""
        positive_words = ['growth', 'success', 'profit', 'gain', 'rise', 'up', 'positive']
        negative_words = ['loss', 'decline', 'fall', 'down', 'negative', 'concern', 'risk']
        
        text_lower = text.lower()
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        if pos_count + neg_count == 0:
            return 0  # Neutral
        
        return (pos_count - neg_count) / (pos_count + neg_count)


class CrunchbaseConnector:
    """
    Crunchbase connector for funding and company data.
    Requires paid API key.
    """

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.CRUNCHBASE_API_KEY if hasattr(self.settings, 'CRUNCHBASE_API_KEY') else None
        self.base_url = "https://api.crunchbase.com/v4"
        self.rate_limiter = RateLimiter(1)  # Conservative rate limit

        if not self.api_key:
            logger.warning("Crunchbase API key not configured")
    
    async def get_company_funding(self, company_name: str) -> Dict[str, Any]:
        """Get funding history for a company."""
        if not self.api_key:
            logger.warning("Crunchbase API key not configured, skipping funding fetch")
            return {}

        await self.rate_limiter.acquire()

        headers = {
            'X-cb-user-key': self.api_key,
        }
        
        params = {
            'field_ids': 'name,funding_total,num_funding_rounds,last_funding_at',
            'q': company_name,
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/searches/organizations",
                    headers=headers,
                    params=params
                ) as response:
                    data = await response.json()
                    
                    if data.get('entities'):
                        company = data['entities'][0]['properties']
                        return {
                            'name': company.get('name'),
                            'funding_total': company.get('funding_total', {}).get('value', 0),
                            'num_funding_rounds': company.get('num_funding_rounds', 0),
                            'last_funding_date': company.get('last_funding_at'),
                        }
                    
                    return {}
                    
        except Exception as e:
            logger.error(f"Error fetching Crunchbase data for {company_name}: {e}")
            return {}


class GitHubConnector:
    """
    GitHub connector for open source activity metrics.
    Useful for EdTech companies with open source tools.
    """
    
    def __init__(self):
        self.base_url = "https://api.github.com"
        self.rate_limiter = RateLimiter(60/3600)  # 60 requests per hour
    
    async def get_repo_metrics(self, org: str, repo: str) -> Dict[str, Any]:
        """Get repository metrics for EdTech open source projects."""
        await self.rate_limiter.acquire()
        
        try:
            async with aiohttp.ClientSession() as session:
                # Get repo info
                async with session.get(f"{self.base_url}/repos/{org}/{repo}") as response:
                    repo_data = await response.json()
                
                # Get recent commits
                async with session.get(
                    f"{self.base_url}/repos/{org}/{repo}/commits",
                    params={'per_page': 100}
                ) as response:
                    commits = await response.json()
                
                # Get contributors
                async with session.get(
                    f"{self.base_url}/repos/{org}/{repo}/contributors",
                    params={'per_page': 100}
                ) as response:
                    contributors = await response.json()
                
                return {
                    'stars': repo_data.get('stargazers_count', 0),
                    'forks': repo_data.get('forks_count', 0),
                    'watchers': repo_data.get('watchers_count', 0),
                    'open_issues': repo_data.get('open_issues_count', 0),
                    'recent_commits': len(commits) if isinstance(commits, list) else 0,
                    'contributors': len(contributors) if isinstance(contributors, list) else 0,
                    'created_at': repo_data.get('created_at'),
                    'updated_at': repo_data.get('updated_at'),
                    'language': repo_data.get('language'),
                    'license': repo_data.get('license', {}).get('name'),
                }
                
        except Exception as e:
            logger.error(f"Error fetching GitHub data for {org}/{repo}: {e}")
            return {}


class DataAggregator:
    """
    Aggregates data from multiple sources for comprehensive analysis.
    """
    
    def __init__(self):
        self.sec = SECEdgarConnector()
        self.yahoo = YahooFinanceConnector()
        self.alpha = AlphaVantageConnector()
        self.news = NewsAPIConnector()
        self.crunchbase = CrunchbaseConnector()
        self.github = GitHubConnector()
    
    async def get_comprehensive_company_data(
        self,
        ticker: str,
        company_name: str,
        github_repo: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Aggregate data from all available sources.
        
        This creates a complete picture of an EdTech company by combining:
        - Financial data (SEC, Yahoo, Alpha Vantage)
        - Market sentiment (News)
        - Funding history (Crunchbase)
        - Developer activity (GitHub)
        """
        
        # Run all API calls concurrently
        tasks = [
            self.sec.get_company_filings(ticker),
            self.yahoo.get_stock_info(ticker),
            self.alpha.get_company_overview(ticker),
            self.news.get_company_news(company_name),
            self.crunchbase.get_company_funding(company_name),
        ]
        
        if github_repo:
            org, repo = github_repo.split('/')
            tasks.append(self.github.get_repo_metrics(org, repo))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        aggregated = {
            'ticker': ticker,
            'company_name': company_name,
            'timestamp': datetime.utcnow().isoformat(),
            'sec_filings': results[0] if not isinstance(results[0], Exception) else [],
            'yahoo_finance': results[1] if not isinstance(results[1], Exception) else {},
            'alpha_vantage': results[2] if not isinstance(results[2], Exception) else {},
            'news_sentiment': results[3] if not isinstance(results[3], Exception) else [],
            'crunchbase': results[4] if not isinstance(results[4], Exception) else {},
        }
        
        if github_repo and len(results) > 5:
            aggregated['github_metrics'] = results[5] if not isinstance(results[5], Exception) else {}
        
        # Calculate composite metrics
        aggregated['composite_score'] = self._calculate_composite_score(aggregated)
        
        return aggregated
    
    def _calculate_composite_score(self, data: Dict[str, Any]) -> float:
        """
        Calculate a composite health score for the company.
        
        Factors:
        - Financial performance (40%)
        - Growth metrics (30%)
        - Market sentiment (20%)
        - Developer activity (10%)
        """
        score = 0
        
        # Financial performance
        yahoo = data.get('yahoo_finance', {})
        if yahoo:
            margin_score = min(yahoo.get('profit_margins', 0) * 100, 40)
            score += margin_score * 0.4
        
        # Growth metrics
        alpha = data.get('alpha_vantage', {})
        if alpha:
            growth_score = min(alpha.get('quarterly_revenue_growth_yoy', 0), 40)
            score += growth_score * 0.3
        
        # Market sentiment
        news = data.get('news_sentiment', [])
        if news:
            avg_sentiment = sum(n['sentiment'] for n in news) / len(news)
            sentiment_score = (avg_sentiment + 1) * 50  # Convert -1,1 to 0,100
            score += sentiment_score * 0.2
        
        # Developer activity (if applicable)
        github = data.get('github_metrics', {})
        if github:
            activity_score = min(github.get('recent_commits', 0) / 100 * 100, 100)
            score += activity_score * 0.1
        
        return round(score, 2)