"""Data aggregator for combining multiple data sources."""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from src.connectors.sources.sec import SECEdgarConnector
from src.connectors.sources.yahoo import YahooFinanceConnector
from src.connectors.sources.alpha_vantage import AlphaVantageConnector
from src.connectors.sources.news import NewsAPIConnector
from src.connectors.sources.crunchbase import CrunchbaseConnector
from src.connectors.sources.github import GitHubConnector


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
