"""NewsAPI connector for market sentiment and news."""

import aiohttp
from datetime import datetime, timedelta
from typing import Any, Dict, List

from loguru import logger

from src.core.config import get_settings
from src.connectors.sources.base import RateLimiter


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
