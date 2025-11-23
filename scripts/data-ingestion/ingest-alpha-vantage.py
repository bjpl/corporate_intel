#!/usr/bin/env python3
"""
Production Alpha Vantage Data Ingestion Script
Corporate Intelligence Platform - Plan A Day 4

This script orchestrates Alpha Vantage data ingestion with production-grade features:
- Multi-workflow support (stock prices, fundamentals, technical indicators)
- Advanced monitoring and metrics
- Prometheus integration
- Detailed reporting
- Dry-run mode for testing
- Graceful error handling

Usage:
    # Run specific workflow
    python ingest-alpha-vantage.py --workflow=fundamentals

    # Dry-run mode (no database writes)
    python ingest-alpha-vantage.py --test-mode

    # Custom ticker list
    python ingest-alpha-vantage.py --tickers=CHGG,COUR,DUOL

    # Enable debug logging
    python ingest-alpha-vantage.py --log-level=DEBUG
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.connectors.data_sources import AlphaVantageConnector
from src.core.config import get_settings
from src.db.session import get_session_factory
from src.pipeline.alpha_vantage_ingestion import (
    EDTECH_TICKERS,
    ingest_alpha_vantage_for_company,
    AlphaVantageIngestionResult,
)


# Workflow Definitions
WORKFLOWS = {
    'stock_prices': {
        'description': 'Daily stock price ingestion (OHLCV)',
        'schedule': 'Daily at 5 PM (market close)',
        'endpoints': ['time_series_daily'],
        'target_companies': 'all',
        'delay_seconds': 12,
    },
    'fundamentals': {
        'description': 'Fundamental data (company overview, financials)',
        'schedule': 'Weekly on Saturday at 6 PM',
        'endpoints': ['company_overview', 'income_statement', 'balance_sheet', 'cash_flow'],
        'target_companies': 'edtech_only',
        'delay_seconds': 12,
    },
    'technical_indicators': {
        'description': 'Technical indicators (SMA, EMA, RSI, MACD)',
        'schedule': 'Daily at 7 PM (disabled by default)',
        'endpoints': ['sma', 'ema', 'rsi', 'macd'],
        'target_companies': 'edtech_only',
        'delay_seconds': 12,
    },
}


class ProductionMetrics:
    """Production-grade metrics collector."""

    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.api_calls = 0
        self.api_errors = 0
        self.cache_hits = 0
        self.companies_processed = 0
        self.companies_succeeded = 0
        self.companies_failed = 0
        self.metrics_fetched = 0
        self.metrics_stored = 0
        self.retries = 0
        self.rate_limit_hits = 0
        self.errors_by_category: Dict[str, int] = {}

    def record_api_call(self):
        """Record an API call."""
        self.api_calls += 1

    def record_api_error(self):
        """Record an API error."""
        self.api_errors += 1

    def record_cache_hit(self):
        """Record a cache hit."""
        self.cache_hits += 1

    def record_result(self, result: AlphaVantageIngestionResult):
        """Record ingestion result."""
        self.companies_processed += 1

        if result.success:
            self.companies_succeeded += 1
        else:
            self.companies_failed += 1

        self.metrics_fetched += result.metrics_fetched
        self.metrics_stored += result.metrics_stored
        self.retries += result.retry_count

        if result.error_category:
            self.errors_by_category[result.error_category] = \
                self.errors_by_category.get(result.error_category, 0) + 1

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        duration = (datetime.now(timezone.utc) - self.start_time).total_seconds()

        return {
            'duration_seconds': round(duration, 2),
            'api_calls': self.api_calls,
            'api_errors': self.api_errors,
            'cache_hits': self.cache_hits,
            'cache_hit_rate': round(self.cache_hits / max(self.api_calls, 1), 2),
            'companies_processed': self.companies_processed,
            'companies_succeeded': self.companies_succeeded,
            'companies_failed': self.companies_failed,
            'success_rate': round(self.companies_succeeded / max(self.companies_processed, 1), 2),
            'metrics_fetched': self.metrics_fetched,
            'metrics_stored': self.metrics_stored,
            'metrics_per_company': round(self.metrics_stored / max(self.companies_processed, 1), 2),
            'retries': self.retries,
            'rate_limit_hits': self.rate_limit_hits,
            'errors_by_category': self.errors_by_category,
        }

    def export_prometheus_metrics(self, output_file: Path):
        """Export metrics in Prometheus format."""
        summary = self.get_summary()

        metrics = [
            f'# HELP alpha_vantage_api_calls_total Total API calls made',
            f'# TYPE alpha_vantage_api_calls_total counter',
            f'alpha_vantage_api_calls_total {self.api_calls}',
            '',
            f'# HELP alpha_vantage_api_errors_total Total API errors',
            f'# TYPE alpha_vantage_api_errors_total counter',
            f'alpha_vantage_api_errors_total {self.api_errors}',
            '',
            f'# HELP alpha_vantage_cache_hits_total Total cache hits',
            f'# TYPE alpha_vantage_cache_hits_total counter',
            f'alpha_vantage_cache_hits_total {self.cache_hits}',
            '',
            f'# HELP alpha_vantage_companies_processed_total Total companies processed',
            f'# TYPE alpha_vantage_companies_processed_total counter',
            f'alpha_vantage_companies_processed_total {self.companies_processed}',
            '',
            f'# HELP alpha_vantage_metrics_stored_total Total metrics stored',
            f'# TYPE alpha_vantage_metrics_stored_total counter',
            f'alpha_vantage_metrics_stored_total {self.metrics_stored}',
            '',
            f'# HELP alpha_vantage_ingestion_duration_seconds Ingestion duration',
            f'# TYPE alpha_vantage_ingestion_duration_seconds gauge',
            f'alpha_vantage_ingestion_duration_seconds {summary["duration_seconds"]}',
            '',
        ]

        output_file.write_text('\n'.join(metrics))
        logger.info(f"Exported Prometheus metrics to {output_file}")


async def run_workflow(
    workflow_name: str,
    tickers: List[str],
    test_mode: bool = False,
    delay_seconds: int = 12
) -> Dict[str, Any]:
    """
    Run a specific ingestion workflow.

    Args:
        workflow_name: Name of workflow (stock_prices, fundamentals, etc.)
        tickers: List of ticker symbols to process
        test_mode: If True, don't write to database
        delay_seconds: Delay between companies

    Returns:
        Summary dictionary with results
    """
    workflow = WORKFLOWS.get(workflow_name)
    if not workflow:
        raise ValueError(f"Unknown workflow: {workflow_name}")

    logger.info("=" * 80)
    logger.info(f"ALPHA VANTAGE WORKFLOW: {workflow_name.upper()}")
    logger.info("=" * 80)
    logger.info(f"Description: {workflow['description']}")
    logger.info(f"Schedule: {workflow['schedule']}")
    logger.info(f"Companies: {len(tickers)}")
    logger.info(f"Test Mode: {test_mode}")
    logger.info(f"Delay: {delay_seconds}s between companies")
    logger.info("=" * 80)

    # Initialize metrics
    metrics = ProductionMetrics()

    # Initialize connector
    connector = AlphaVantageConnector()
    session_factory = get_session_factory()

    # Process companies
    results: List[AlphaVantageIngestionResult] = []

    for idx, ticker in enumerate(tickers, 1):
        logger.info(f"[{idx}/{len(tickers)}] Processing {ticker}...")

        # Create new session for each company
        async with session_factory() as session:
            # Record API call
            metrics.record_api_call()

            try:
                # Fetch and store data
                result = await ingest_alpha_vantage_for_company(
                    ticker,
                    connector,
                    session if not test_mode else None  # Skip DB in test mode
                )

                results.append(result)
                metrics.record_result(result)

                if result.success:
                    logger.info(
                        f"[{idx}/{len(tickers)}] {ticker}: SUCCESS - "
                        f"Fetched {result.metrics_fetched} fields, "
                        f"Stored {result.metrics_stored} metrics"
                    )
                else:
                    logger.warning(
                        f"[{idx}/{len(tickers)}] {ticker}: FAILED - "
                        f"{result.error_message or 'Unknown error'}"
                    )
                    metrics.record_api_error()

            except Exception as e:
                logger.error(f"[{idx}/{len(tickers)}] {ticker}: EXCEPTION - {str(e)}", exc_info=True)
                metrics.record_api_error()

                # Create error result
                error_result = AlphaVantageIngestionResult(ticker)
                error_result.error_message = str(e)
                error_result.error_category = "unexpected_error"
                results.append(error_result)
                metrics.record_result(error_result)

        # Rate limit delay
        if idx < len(tickers):
            logger.debug(f"Rate limit: Waiting {delay_seconds}s before next company...")
            await asyncio.sleep(delay_seconds)

    # Generate summary
    summary = metrics.get_summary()
    summary['workflow'] = workflow_name
    summary['test_mode'] = test_mode
    summary['tickers'] = tickers
    summary['results'] = [r.to_dict() for r in results]

    return summary


def print_summary(summary: Dict[str, Any]):
    """Print detailed summary report."""
    logger.info("=" * 80)
    logger.info("INGESTION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Workflow: {summary['workflow']}")
    logger.info(f"Test Mode: {summary['test_mode']}")
    logger.info(f"Duration: {summary['duration_seconds']}s")
    logger.info("-" * 80)

    logger.info("COMPANIES")
    logger.info(f"  Processed: {summary['companies_processed']}")
    logger.info(f"  Succeeded: {summary['companies_succeeded']}")
    logger.info(f"  Failed: {summary['companies_failed']}")
    logger.info(f"  Success Rate: {summary['success_rate'] * 100:.1f}%")
    logger.info("-" * 80)

    logger.info("API METRICS")
    logger.info(f"  API Calls: {summary['api_calls']}")
    logger.info(f"  API Errors: {summary['api_errors']}")
    logger.info(f"  Cache Hits: {summary['cache_hits']}")
    logger.info(f"  Cache Hit Rate: {summary['cache_hit_rate'] * 100:.1f}%")
    logger.info(f"  Retries: {summary['retries']}")
    logger.info("-" * 80)

    logger.info("DATA METRICS")
    logger.info(f"  Metrics Fetched: {summary['metrics_fetched']}")
    logger.info(f"  Metrics Stored: {summary['metrics_stored']}")
    logger.info(f"  Avg per Company: {summary['metrics_per_company']:.1f}")
    logger.info("-" * 80)

    if summary['errors_by_category']:
        logger.info("ERROR BREAKDOWN")
        for category, count in sorted(
            summary['errors_by_category'].items(),
            key=lambda x: x[1],
            reverse=True
        ):
            logger.info(f"  {category}: {count}")
        logger.info("-" * 80)

    # Failed companies
    failed = [r for r in summary['results'] if not r['success']]
    if failed:
        logger.warning(f"FAILED COMPANIES ({len(failed)})")
        for r in failed:
            logger.warning(f"  {r['ticker']}: {r['error_message']}")
        logger.info("-" * 80)

    logger.info("=" * 80)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Alpha Vantage Production Ingestion Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run fundamentals workflow
  python ingest-alpha-vantage.py --workflow=fundamentals

  # Test mode (no database writes)
  python ingest-alpha-vantage.py --test-mode

  # Custom tickers
  python ingest-alpha-vantage.py --tickers=CHGG,COUR,DUOL

  # Debug logging
  python ingest-alpha-vantage.py --log-level=DEBUG
        """
    )

    parser.add_argument(
        '--workflow',
        choices=list(WORKFLOWS.keys()),
        default='fundamentals',
        help='Workflow to run (default: fundamentals)'
    )

    parser.add_argument(
        '--tickers',
        type=str,
        help='Comma-separated list of tickers (default: all EdTech companies)'
    )

    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Dry-run mode: fetch data but don\'t write to database'
    )

    parser.add_argument(
        '--delay',
        type=int,
        default=12,
        help='Delay between companies in seconds (default: 12)'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )

    parser.add_argument(
        '--export-metrics',
        type=str,
        help='Export Prometheus metrics to file'
    )

    parser.add_argument(
        '--export-json',
        type=str,
        help='Export summary as JSON to file'
    )

    args = parser.parse_args()

    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=args.log_level
    )

    # Determine tickers
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(',')]
    else:
        tickers = EDTECH_TICKERS

    # Verify API key
    settings = get_settings()
    if not settings.ALPHA_VANTAGE_API_KEY:
        logger.error("Alpha Vantage API key not configured. Please set ALPHA_VANTAGE_API_KEY in .env")
        sys.exit(1)

    # Run workflow
    try:
        summary = await run_workflow(
            workflow_name=args.workflow,
            tickers=tickers,
            test_mode=args.test_mode,
            delay_seconds=args.delay
        )

        # Print summary
        print_summary(summary)

        # Export metrics
        if args.export_metrics:
            metrics = ProductionMetrics()
            for result in summary['results']:
                r = AlphaVantageIngestionResult(result['ticker'])
                r.success = result['success']
                r.metrics_fetched = result['metrics_fetched']
                r.metrics_stored = result['metrics_stored']
                r.retry_count = result['retry_count']
                r.error_category = result.get('error_category')
                metrics.record_result(r)

            metrics.export_prometheus_metrics(Path(args.export_metrics))

        # Export JSON
        if args.export_json:
            Path(args.export_json).write_text(
                json.dumps(summary, indent=2, default=str)
            )
            logger.info(f"Exported summary to {args.export_json}")

        # Exit code
        if summary['companies_failed'] > 0:
            logger.error(f"Ingestion completed with {summary['companies_failed']} failures")
            sys.exit(1)

        logger.info("Ingestion completed successfully")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Ingestion failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
