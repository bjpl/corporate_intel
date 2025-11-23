#!/usr/bin/env python3
"""
Yahoo Finance Data Ingestion Script
===================================

Fetches financial data from Yahoo Finance using yfinance library
and stores it in the corporate intelligence database.

Usage:
    python ingest-yahoo-finance.py --ticker AAPL
    python ingest-yahoo-finance.py --ticker CHGG --period 1y
    python ingest-yahoo-finance.py --all-watchlist
    python ingest-yahoo-finance.py --ticker AAPL --full  # Fetch all data types
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
    import yfinance as yf
    import yaml
    import psycopg2
    from psycopg2.extras import execute_values, Json
    import pandas as pd
except ImportError as e:
    print(f"Error: Missing required package: {e}")
    print("Install with: pip install yfinance pyyaml psycopg2-binary pandas")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YahooFinanceIngestionPipeline:
    """Pipeline for ingesting financial data from Yahoo Finance."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the Yahoo Finance ingestion pipeline.

        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.db_conn = None
        self.stats = {
            'tickers_processed': 0,
            'quotes_stored': 0,
            'historical_records': 0,
            'info_stored': 0,
            'financials_stored': 0,
            'failed_tickers': 0
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
                'yahoo-finance-config.yml'
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
            'data_types': {
                'quotes': {'enabled': True},
                'historical': {'enabled': True, 'default_period': '1y', 'default_interval': '1d'},
                'info': {'enabled': True},
                'financials': {'enabled': True}
            },
            'api': {
                'request_delay': 1,
                'max_retries': 3,
                'timeout': 30
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

    def fetch_quote(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch current quote data for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with quote data
        """
        try:
            logger.info(f"Fetching quote for {ticker}")
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info or 'regularMarketPrice' not in info:
                logger.warning(f"No quote data found for {ticker}")
                return None

            quote = {
                'ticker': ticker,
                'regular_market_price': info.get('regularMarketPrice'),
                'regular_market_change': info.get('regularMarketChange'),
                'regular_market_change_percent': info.get('regularMarketChangePercent'),
                'regular_market_volume': info.get('regularMarketVolume'),
                'market_cap': info.get('marketCap'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_day_average': info.get('fiftyDayAverage'),
                'two_hundred_day_average': info.get('twoHundredDayAverage'),
                'trailing_pe': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'dividend_yield': info.get('dividendYield'),
                'beta': info.get('beta'),
                'fetched_at': datetime.now()
            }

            self.stats['quotes_stored'] += 1
            time.sleep(self.config['api']['request_delay'])
            return quote

        except Exception as e:
            logger.error(f"Error fetching quote for {ticker}: {e}")
            self.stats['failed_tickers'] += 1
            return None

    def fetch_historical(
        self,
        ticker: str,
        period: str = '1y',
        interval: str = '1d'
    ) -> Optional[pd.DataFrame]:
        """
        Fetch historical price data.

        Args:
            ticker: Stock ticker symbol
            period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: Data interval (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            DataFrame with historical data
        """
        try:
            logger.info(f"Fetching historical data for {ticker} (period={period}, interval={interval})")
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period, interval=interval)

            if hist.empty:
                logger.warning(f"No historical data found for {ticker}")
                return None

            # Add ticker column
            hist['ticker'] = ticker
            hist['fetched_at'] = datetime.now()

            self.stats['historical_records'] += len(hist)
            time.sleep(self.config['api']['request_delay'])
            return hist

        except Exception as e:
            logger.error(f"Error fetching historical data for {ticker}: {e}")
            return None

    def fetch_company_info(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch company information.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with company info
        """
        try:
            logger.info(f"Fetching company info for {ticker}")
            stock = yf.Ticker(ticker)
            info = stock.info

            if not info:
                logger.warning(f"No company info found for {ticker}")
                return None

            company_info = {
                'ticker': ticker,
                'short_name': info.get('shortName'),
                'long_name': info.get('longName'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'full_time_employees': info.get('fullTimeEmployees'),
                'city': info.get('city'),
                'state': info.get('state'),
                'country': info.get('country'),
                'website': info.get('website'),
                'business_summary': info.get('longBusinessSummary'),
                'market_cap': info.get('marketCap'),
                'beta': info.get('beta'),
                'trailing_pe': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'dividend_rate': info.get('dividendRate'),
                'dividend_yield': info.get('dividendYield'),
                'recommendation_key': info.get('recommendationKey'),
                'fetched_at': datetime.now()
            }

            self.stats['info_stored'] += 1
            time.sleep(self.config['api']['request_delay'])
            return company_info

        except Exception as e:
            logger.error(f"Error fetching company info for {ticker}: {e}")
            return None

    def fetch_financials(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch financial statements.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with financial data
        """
        try:
            logger.info(f"Fetching financials for {ticker}")
            stock = yf.Ticker(ticker)

            financials = {
                'ticker': ticker,
                'income_stmt': None,
                'balance_sheet': None,
                'cashflow': None,
                'fetched_at': datetime.now()
            }

            # Income statement
            try:
                income_stmt = stock.financials
                if not income_stmt.empty:
                    financials['income_stmt'] = income_stmt.to_dict()
            except Exception as e:
                logger.warning(f"Could not fetch income statement for {ticker}: {e}")

            # Balance sheet
            try:
                balance_sheet = stock.balance_sheet
                if not balance_sheet.empty:
                    financials['balance_sheet'] = balance_sheet.to_dict()
            except Exception as e:
                logger.warning(f"Could not fetch balance sheet for {ticker}: {e}")

            # Cash flow
            try:
                cashflow = stock.cashflow
                if not cashflow.empty:
                    financials['cashflow'] = cashflow.to_dict()
            except Exception as e:
                logger.warning(f"Could not fetch cashflow for {ticker}: {e}")

            if any([financials['income_stmt'], financials['balance_sheet'], financials['cashflow']]):
                self.stats['financials_stored'] += 1
                time.sleep(self.config['api']['request_delay'])
                return financials
            else:
                return None

        except Exception as e:
            logger.error(f"Error fetching financials for {ticker}: {e}")
            return None

    def store_quote(self, quote: Dict[str, Any]):
        """Store quote data in database."""
        if not quote:
            return

        if not self.db_conn:
            self.connect_db()

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS yahoo_quotes (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(10) NOT NULL,
            regular_market_price NUMERIC,
            regular_market_change NUMERIC,
            regular_market_change_percent NUMERIC,
            regular_market_volume BIGINT,
            market_cap BIGINT,
            fifty_two_week_low NUMERIC,
            fifty_two_week_high NUMERIC,
            fifty_day_average NUMERIC,
            two_hundred_day_average NUMERIC,
            trailing_pe NUMERIC,
            forward_pe NUMERIC,
            dividend_yield NUMERIC,
            beta NUMERIC,
            fetched_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_yahoo_quotes_ticker ON yahoo_quotes(ticker);
        CREATE INDEX IF NOT EXISTS idx_yahoo_quotes_fetched ON yahoo_quotes(fetched_at);
        """

        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute(create_table_sql)

                insert_sql = """
                INSERT INTO yahoo_quotes (
                    ticker, regular_market_price, regular_market_change,
                    regular_market_change_percent, regular_market_volume,
                    market_cap, fifty_two_week_low, fifty_two_week_high,
                    fifty_day_average, two_hundred_day_average, trailing_pe,
                    forward_pe, dividend_yield, beta, fetched_at
                ) VALUES (
                    %(ticker)s, %(regular_market_price)s, %(regular_market_change)s,
                    %(regular_market_change_percent)s, %(regular_market_volume)s,
                    %(market_cap)s, %(fifty_two_week_low)s, %(fifty_two_week_high)s,
                    %(fifty_day_average)s, %(two_hundred_day_average)s, %(trailing_pe)s,
                    %(forward_pe)s, %(dividend_yield)s, %(beta)s, %(fetched_at)s
                )
                """

                cursor.execute(insert_sql, quote)
                self.db_conn.commit()
                logger.info(f"Stored quote for {quote['ticker']}")

        except Exception as e:
            logger.error(f"Error storing quote: {e}")
            if self.db_conn:
                self.db_conn.rollback()

    def store_historical(self, hist_data: pd.DataFrame, ticker: str):
        """Store historical data in database."""
        if hist_data is None or hist_data.empty:
            return

        if not self.db_conn:
            self.connect_db()

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS yahoo_historical (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(10) NOT NULL,
            date TIMESTAMP NOT NULL,
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            close NUMERIC,
            volume BIGINT,
            dividends NUMERIC,
            stock_splits NUMERIC,
            fetched_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(ticker, date)
        );

        CREATE INDEX IF NOT EXISTS idx_yahoo_historical_ticker ON yahoo_historical(ticker);
        CREATE INDEX IF NOT EXISTS idx_yahoo_historical_date ON yahoo_historical(date);
        """

        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute(create_table_sql)

                # Prepare data for insertion
                hist_data_reset = hist_data.reset_index()
                values = []

                for _, row in hist_data_reset.iterrows():
                    values.append((
                        ticker,
                        row.get('Date') or row.name,
                        row.get('Open'),
                        row.get('High'),
                        row.get('Low'),
                        row.get('Close'),
                        row.get('Volume'),
                        row.get('Dividends', 0),
                        row.get('Stock Splits', 0),
                        datetime.now()
                    ))

                insert_sql = """
                INSERT INTO yahoo_historical (
                    ticker, date, open, high, low, close, volume,
                    dividends, stock_splits, fetched_at
                ) VALUES %s
                ON CONFLICT (ticker, date) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    dividends = EXCLUDED.dividends,
                    stock_splits = EXCLUDED.stock_splits,
                    fetched_at = EXCLUDED.fetched_at
                """

                execute_values(cursor, insert_sql, values)
                self.db_conn.commit()
                logger.info(f"Stored {len(values)} historical records for {ticker}")

        except Exception as e:
            logger.error(f"Error storing historical data: {e}")
            if self.db_conn:
                self.db_conn.rollback()

    def store_company_info(self, info: Dict[str, Any]):
        """Store company information in database."""
        if not info:
            return

        if not self.db_conn:
            self.connect_db()

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS yahoo_company_info (
            id SERIAL PRIMARY KEY,
            ticker VARCHAR(10) UNIQUE NOT NULL,
            short_name VARCHAR(255),
            long_name VARCHAR(255),
            sector VARCHAR(100),
            industry VARCHAR(100),
            full_time_employees INTEGER,
            city VARCHAR(100),
            state VARCHAR(100),
            country VARCHAR(100),
            website VARCHAR(255),
            business_summary TEXT,
            market_cap BIGINT,
            beta NUMERIC,
            trailing_pe NUMERIC,
            forward_pe NUMERIC,
            dividend_rate NUMERIC,
            dividend_yield NUMERIC,
            recommendation_key VARCHAR(50),
            fetched_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_yahoo_info_ticker ON yahoo_company_info(ticker);
        CREATE INDEX IF NOT EXISTS idx_yahoo_info_sector ON yahoo_company_info(sector);
        CREATE INDEX IF NOT EXISTS idx_yahoo_info_industry ON yahoo_company_info(industry);
        """

        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute(create_table_sql)

                insert_sql = """
                INSERT INTO yahoo_company_info (
                    ticker, short_name, long_name, sector, industry,
                    full_time_employees, city, state, country, website,
                    business_summary, market_cap, beta, trailing_pe, forward_pe,
                    dividend_rate, dividend_yield, recommendation_key, fetched_at
                ) VALUES (
                    %(ticker)s, %(short_name)s, %(long_name)s, %(sector)s, %(industry)s,
                    %(full_time_employees)s, %(city)s, %(state)s, %(country)s, %(website)s,
                    %(business_summary)s, %(market_cap)s, %(beta)s, %(trailing_pe)s, %(forward_pe)s,
                    %(dividend_rate)s, %(dividend_yield)s, %(recommendation_key)s, %(fetched_at)s
                )
                ON CONFLICT (ticker) DO UPDATE SET
                    short_name = EXCLUDED.short_name,
                    long_name = EXCLUDED.long_name,
                    sector = EXCLUDED.sector,
                    industry = EXCLUDED.industry,
                    full_time_employees = EXCLUDED.full_time_employees,
                    city = EXCLUDED.city,
                    state = EXCLUDED.state,
                    country = EXCLUDED.country,
                    website = EXCLUDED.website,
                    business_summary = EXCLUDED.business_summary,
                    market_cap = EXCLUDED.market_cap,
                    beta = EXCLUDED.beta,
                    trailing_pe = EXCLUDED.trailing_pe,
                    forward_pe = EXCLUDED.forward_pe,
                    dividend_rate = EXCLUDED.dividend_rate,
                    dividend_yield = EXCLUDED.dividend_yield,
                    recommendation_key = EXCLUDED.recommendation_key,
                    fetched_at = EXCLUDED.fetched_at,
                    updated_at = CURRENT_TIMESTAMP
                """

                cursor.execute(insert_sql, info)
                self.db_conn.commit()
                logger.info(f"Stored company info for {info['ticker']}")

        except Exception as e:
            logger.error(f"Error storing company info: {e}")
            if self.db_conn:
                self.db_conn.rollback()

    def run_ticker_ingestion(
        self,
        ticker: str,
        fetch_all: bool = False,
        period: str = '1y'
    ):
        """
        Run complete ingestion pipeline for a ticker.

        Args:
            ticker: Stock ticker symbol
            fetch_all: Fetch all data types
            period: Historical data period
        """
        logger.info(f"Starting Yahoo Finance ingestion for {ticker}")

        try:
            # Fetch and store quote
            if fetch_all or self.config['data_types']['quotes']['enabled']:
                quote = self.fetch_quote(ticker)
                if quote:
                    self.store_quote(quote)

            # Fetch and store historical data
            if fetch_all or self.config['data_types']['historical']['enabled']:
                hist = self.fetch_historical(ticker, period=period)
                if hist is not None:
                    self.store_historical(hist, ticker)

            # Fetch and store company info
            if fetch_all or self.config['data_types']['info']['enabled']:
                info = self.fetch_company_info(ticker)
                if info:
                    self.store_company_info(info)

            self.stats['tickers_processed'] += 1
            logger.info(f"Completed ingestion for {ticker}")

        except Exception as e:
            logger.error(f"Failed to process {ticker}: {e}")
            self.stats['failed_tickers'] += 1

    def run_watchlist_ingestion(self, fetch_all: bool = False, period: str = '1y'):
        """Run ingestion for all tickers in watchlist."""
        watchlist = self.config.get('watchlist', {}).get('default_tickers', [
            'CHGG', 'COUR', 'DUOL', 'TWOU',
            'ARCE', 'LAUR', 'INST', 'POWL'
        ])

        logger.info(f"Starting watchlist ingestion for {len(watchlist)} tickers")

        for ticker in watchlist:
            try:
                self.run_ticker_ingestion(ticker, fetch_all, period)
            except Exception as e:
                logger.error(f"Failed to ingest {ticker}: {e}")

        logger.info("Completed watchlist ingestion")

    def print_stats(self):
        """Print ingestion statistics."""
        print("\n" + "="*50)
        print("Yahoo Finance Ingestion Statistics")
        print("="*50)
        print(f"Tickers Processed:    {self.stats['tickers_processed']}")
        print(f"Quotes Stored:        {self.stats['quotes_stored']}")
        print(f"Historical Records:   {self.stats['historical_records']}")
        print(f"Company Info Stored:  {self.stats['info_stored']}")
        print(f"Financials Stored:    {self.stats['financials_stored']}")
        print(f"Failed Tickers:       {self.stats['failed_tickers']}")
        print("="*50 + "\n")

    def close(self):
        """Clean up resources."""
        if self.db_conn:
            self.db_conn.close()
            logger.info("Database connection closed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Ingest financial data from Yahoo Finance'
    )
    parser.add_argument(
        '--ticker',
        help='Stock ticker symbol to fetch data for'
    )
    parser.add_argument(
        '--all-watchlist',
        action='store_true',
        help='Fetch data for all watchlist tickers'
    )
    parser.add_argument(
        '--period',
        default='1y',
        help='Historical data period (default: 1y)'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Fetch all data types (quotes, historical, info, financials)'
    )
    parser.add_argument(
        '--config',
        help='Path to configuration file'
    )

    args = parser.parse_args()

    # Initialize pipeline
    try:
        pipeline = YahooFinanceIngestionPipeline(config_path=args.config)

        # Run appropriate ingestion
        if args.all_watchlist:
            pipeline.run_watchlist_ingestion(fetch_all=args.full, period=args.period)
        elif args.ticker:
            pipeline.run_ticker_ingestion(args.ticker, fetch_all=args.full, period=args.period)
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
