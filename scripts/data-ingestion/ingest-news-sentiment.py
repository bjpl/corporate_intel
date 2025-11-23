#!/usr/bin/env python3
"""
NewsAPI Data Ingestion Script with Sentiment Analysis
=====================================================

Fetches news articles from NewsAPI, performs sentiment analysis,
and stores the results in the corporate intelligence database.

Usage:
    python ingest-news-sentiment.py --ticker AAPL
    python ingest-news-sentiment.py --ticker CHGG --days 7
    python ingest-news-sentiment.py --keyword "earnings report" --days 30
    python ingest-news-sentiment.py --all-watchlist
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import time

# Third-party imports
try:
    from newsapi import NewsApiClient
    from textblob import TextBlob
    import yaml
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError as e:
    print(f"Error: Missing required package: {e}")
    print("Install with: pip install newsapi-python textblob pyyaml psycopg2-binary")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NewsAPIIngestionPipeline:
    """Pipeline for ingesting news data from NewsAPI with sentiment analysis."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the NewsAPI ingestion pipeline.

        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.api_key = os.getenv('NEWSAPI_KEY')

        if not self.api_key:
            raise ValueError("NEWSAPI_KEY environment variable not set")

        self.client = NewsApiClient(api_key=self.api_key)
        self.db_conn = None
        self.stats = {
            'articles_fetched': 0,
            'articles_stored': 0,
            'articles_failed': 0,
            'sentiment_analyzed': 0,
            'api_calls': 0
        }

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if config_path is None:
            # Default config path
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            config_path = os.path.join(
                base_dir,
                'config',
                'production',
                'data-sources',
                'newsapi-config.yml'
            )

        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}. Using defaults.")
            return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            'search': {
                'language': 'en',
                'sort_by': 'publishedAt',
                'page_size': 100,
                'default_lookback_days': 7
            },
            'sentiment': {
                'enabled': True,
                'engine': 'textblob',
                'analyze_fields': ['title', 'description']
            },
            'rate_limits': {
                'requests_per_minute': 5,
                'retry_delay': 5
            }
        }

    def connect_db(self):
        """Establish database connection."""
        try:
            self.db_conn = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=os.getenv('POSTGRES_PORT', '5432'),
                database=os.getenv('POSTGRES_DB', 'corporate_intel'),
                user=os.getenv('POSTGRES_USER', 'intel_user'),
                password=os.getenv('POSTGRES_PASSWORD')
            )
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def fetch_news_by_ticker(
        self,
        ticker: str,
        days: int = 7,
        company_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch news articles for a specific company ticker.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            days: Number of days to look back
            company_name: Optional company name for better search

        Returns:
            List of article dictionaries
        """
        # Build search query
        query = f'"{ticker}"'
        if company_name:
            query += f' OR "{company_name}"'

        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        try:
            logger.info(f"Fetching news for {ticker} from {from_date}")
            self.stats['api_calls'] += 1

            response = self.client.get_everything(
                q=query,
                from_param=from_date,
                language=self.config['search']['language'],
                sort_by=self.config['search']['sort_by'],
                page_size=self.config['search']['page_size']
            )

            articles = response.get('articles', [])
            self.stats['articles_fetched'] += len(articles)
            logger.info(f"Fetched {len(articles)} articles for {ticker}")

            # Rate limiting
            time.sleep(60 / self.config['rate_limits']['requests_per_minute'])

            return articles

        except Exception as e:
            logger.error(f"Error fetching news for {ticker}: {e}")
            self.stats['articles_failed'] += 1
            return []

    def fetch_news_by_keyword(
        self,
        keyword: str,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Fetch news articles by keyword search.

        Args:
            keyword: Search keyword or phrase
            days: Number of days to look back

        Returns:
            List of article dictionaries
        """
        from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        try:
            logger.info(f"Fetching news for keyword: {keyword}")
            self.stats['api_calls'] += 1

            response = self.client.get_everything(
                q=keyword,
                from_param=from_date,
                language=self.config['search']['language'],
                sort_by=self.config['search']['sort_by'],
                page_size=self.config['search']['page_size']
            )

            articles = response.get('articles', [])
            self.stats['articles_fetched'] += len(articles)
            logger.info(f"Fetched {len(articles)} articles for '{keyword}'")

            # Rate limiting
            time.sleep(60 / self.config['rate_limits']['requests_per_minute'])

            return articles

        except Exception as e:
            logger.error(f"Error fetching news for keyword '{keyword}': {e}")
            return []

    def fetch_top_headlines(
        self,
        category: str = 'business',
        country: str = 'us'
    ) -> List[Dict[str, Any]]:
        """
        Fetch top headlines.

        Args:
            category: News category
            country: Country code (e.g., 'us')

        Returns:
            List of article dictionaries
        """
        try:
            logger.info(f"Fetching top {category} headlines for {country}")
            self.stats['api_calls'] += 1

            response = self.client.get_top_headlines(
                category=category,
                country=country,
                page_size=self.config['search']['page_size']
            )

            articles = response.get('articles', [])
            self.stats['articles_fetched'] += len(articles)
            logger.info(f"Fetched {len(articles)} top headlines")

            # Rate limiting
            time.sleep(60 / self.config['rate_limits']['requests_per_minute'])

            return articles

        except Exception as e:
            logger.error(f"Error fetching top headlines: {e}")
            return []

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text using TextBlob.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment scores
        """
        if not text:
            return {
                'polarity': 0.0,
                'subjectivity': 0.0,
                'category': 'neutral'
            }

        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity

            # Categorize sentiment
            if polarity <= -0.6:
                category = 'very_negative'
            elif polarity <= -0.2:
                category = 'negative'
            elif polarity <= 0.2:
                category = 'neutral'
            elif polarity <= 0.6:
                category = 'positive'
            else:
                category = 'very_positive'

            self.stats['sentiment_analyzed'] += 1

            return {
                'polarity': polarity,
                'subjectivity': subjectivity,
                'category': category
            }

        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {
                'polarity': 0.0,
                'subjectivity': 0.0,
                'category': 'neutral'
            }

    def process_articles(
        self,
        articles: List[Dict[str, Any]],
        ticker: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Process articles with sentiment analysis.

        Args:
            articles: List of raw article dictionaries
            ticker: Optional ticker symbol to associate

        Returns:
            List of processed articles
        """
        processed = []

        for article in articles:
            try:
                # Combine title and description for sentiment analysis
                text_for_sentiment = f"{article.get('title', '')} {article.get('description', '')}"
                sentiment = self.analyze_sentiment(text_for_sentiment)

                processed_article = {
                    'ticker': ticker,
                    'source_name': article.get('source', {}).get('name'),
                    'author': article.get('author'),
                    'title': article.get('title'),
                    'description': article.get('description'),
                    'url': article.get('url'),
                    'url_to_image': article.get('urlToImage'),
                    'published_at': article.get('publishedAt'),
                    'content': article.get('content'),
                    'sentiment_polarity': sentiment['polarity'],
                    'sentiment_subjectivity': sentiment['subjectivity'],
                    'sentiment_category': sentiment['category'],
                    'fetched_at': datetime.now().isoformat()
                }

                processed.append(processed_article)

            except Exception as e:
                logger.error(f"Error processing article: {e}")
                self.stats['articles_failed'] += 1

        return processed

    def store_articles(self, articles: List[Dict[str, Any]]):
        """
        Store processed articles in database.

        Args:
            articles: List of processed article dictionaries
        """
        if not articles:
            logger.info("No articles to store")
            return

        if not self.db_conn:
            self.connect_db()

        # Create table if not exists
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS news_articles (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(10),
            source_name VARCHAR(255),
            author VARCHAR(255),
            title TEXT NOT NULL,
            description TEXT,
            url TEXT UNIQUE NOT NULL,
            url_to_image TEXT,
            published_at TIMESTAMP,
            content TEXT,
            sentiment_polarity FLOAT,
            sentiment_subjectivity FLOAT,
            sentiment_category VARCHAR(20),
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_news_ticker ON news_articles(ticker);
        CREATE INDEX IF NOT EXISTS idx_news_published ON news_articles(published_at);
        CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news_articles(sentiment_category);
        """

        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute(create_table_sql)
                self.db_conn.commit()

                # Insert articles
                insert_sql = """
                INSERT INTO news_articles (
                    ticker, source_name, author, title, description, url,
                    url_to_image, published_at, content, sentiment_polarity,
                    sentiment_subjectivity, sentiment_category, fetched_at
                ) VALUES %s
                ON CONFLICT (url) DO UPDATE SET
                    sentiment_polarity = EXCLUDED.sentiment_polarity,
                    sentiment_subjectivity = EXCLUDED.sentiment_subjectivity,
                    sentiment_category = EXCLUDED.sentiment_category,
                    fetched_at = EXCLUDED.fetched_at
                """

                values = [
                    (
                        article['ticker'],
                        article['source_name'],
                        article['author'],
                        article['title'],
                        article['description'],
                        article['url'],
                        article['url_to_image'],
                        article['published_at'],
                        article['content'],
                        article['sentiment_polarity'],
                        article['sentiment_subjectivity'],
                        article['sentiment_category'],
                        article['fetched_at']
                    )
                    for article in articles
                ]

                execute_values(cursor, insert_sql, values)
                self.db_conn.commit()

                self.stats['articles_stored'] += len(articles)
                logger.info(f"Stored {len(articles)} articles in database")

        except Exception as e:
            logger.error(f"Error storing articles: {e}")
            if self.db_conn:
                self.db_conn.rollback()
            raise

    def run_ticker_ingestion(self, ticker: str, days: int = 7):
        """Run complete ingestion pipeline for a ticker."""
        logger.info(f"Starting news ingestion for {ticker}")

        # Fetch articles
        articles = self.fetch_news_by_ticker(ticker, days)

        if not articles:
            logger.warning(f"No articles found for {ticker}")
            return

        # Process with sentiment analysis
        processed = self.process_articles(articles, ticker)

        # Store in database
        self.store_articles(processed)

        logger.info(f"Completed news ingestion for {ticker}")

    def run_watchlist_ingestion(self, days: int = 7):
        """Run ingestion for all tickers in watchlist."""
        watchlist = [
            'CHGG', 'COUR', 'DUOL', 'TWOU',
            'ARCE', 'LAUR', 'INST', 'POWL'
        ]

        logger.info(f"Starting watchlist ingestion for {len(watchlist)} tickers")

        for ticker in watchlist:
            try:
                self.run_ticker_ingestion(ticker, days)
            except Exception as e:
                logger.error(f"Failed to ingest {ticker}: {e}")

        logger.info("Completed watchlist ingestion")

    def print_stats(self):
        """Print ingestion statistics."""
        print("\n" + "="*50)
        print("NewsAPI Ingestion Statistics")
        print("="*50)
        print(f"API Calls:           {self.stats['api_calls']}")
        print(f"Articles Fetched:    {self.stats['articles_fetched']}")
        print(f"Articles Stored:     {self.stats['articles_stored']}")
        print(f"Articles Failed:     {self.stats['articles_failed']}")
        print(f"Sentiment Analyzed:  {self.stats['sentiment_analyzed']}")
        print("="*50 + "\n")

    def close(self):
        """Clean up resources."""
        if self.db_conn:
            self.db_conn.close()
            logger.info("Database connection closed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Ingest news articles from NewsAPI with sentiment analysis'
    )
    parser.add_argument(
        '--ticker',
        help='Stock ticker symbol to fetch news for'
    )
    parser.add_argument(
        '--keyword',
        help='Keyword to search for'
    )
    parser.add_argument(
        '--all-watchlist',
        action='store_true',
        help='Fetch news for all watchlist tickers'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to look back (default: 7)'
    )
    parser.add_argument(
        '--config',
        help='Path to configuration file'
    )

    args = parser.parse_args()

    # Initialize pipeline
    try:
        pipeline = NewsAPIIngestionPipeline(config_path=args.config)

        # Run appropriate ingestion
        if args.all_watchlist:
            pipeline.run_watchlist_ingestion(args.days)
        elif args.ticker:
            pipeline.run_ticker_ingestion(args.ticker, args.days)
        elif args.keyword:
            articles = pipeline.fetch_news_by_keyword(args.keyword, args.days)
            processed = pipeline.process_articles(articles)
            pipeline.store_articles(processed)
        else:
            parser.print_help()
            return

        # Print statistics
        pipeline.print_stats()

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        sys.exit(1)
    finally:
        pipeline.close()


if __name__ == '__main__':
    main()
