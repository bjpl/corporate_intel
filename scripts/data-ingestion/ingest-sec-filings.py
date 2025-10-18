#!/usr/bin/env python3
"""SEC EDGAR Filing Ingestion Script

This script provides a command-line interface for ingesting SEC EDGAR filings
for EdTech companies into the Corporate Intelligence Platform.

Features:
- Single company or batch processing
- Configurable filing types and date ranges
- Rate limiting (10 requests/second)
- Retry logic with exponential backoff
- Data validation using Great Expectations
- Progress tracking and metrics reporting

Usage:
    # Single company
    python ingest-sec-filings.py --ticker DUOL

    # Batch processing
    python ingest-sec-filings.py --batch --watchlist

    # Custom date range
    python ingest-sec-filings.py --ticker CHGG --start-date 2023-01-01 --end-date 2024-12-31

    # Specific filing types
    python ingest-sec-filings.py --ticker COUR --filing-types 10-K 10-Q

Author: Corporate Intelligence Platform Team
Created: 2025-10-17
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import yaml
from loguru import logger
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.core.config import get_settings
from src.pipeline.sec_ingestion import (
    FilingRequest,
    batch_sec_ingestion_flow,
    sec_ingestion_flow,
)

console = Console()


class SECIngestionCLI:
    """Command-line interface for SEC filing ingestion."""

    def __init__(self):
        self.settings = get_settings()
        self.config = self.load_production_config()

    def load_production_config(self) -> dict:
        """Load production SEC API configuration."""
        config_path = project_root / "config" / "production" / "sec-api-config.yml"

        if not config_path.exists():
            logger.warning(f"Production config not found at {config_path}, using defaults")
            return {}

        with open(config_path, "r") as f:
            return yaml.safe_load(f)

    async def ingest_single_company(
        self,
        ticker: str,
        filing_types: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Ingest SEC filings for a single company.

        Args:
            ticker: Company ticker symbol (e.g., 'DUOL')
            filing_types: List of filing types to collect (default: 10-K, 10-Q, 8-K)
            start_date: Start date for filings (default: 2 years ago)
            end_date: End date for filings (default: today)

        Returns:
            Dictionary with ingestion results
        """
        # Default filing types from config
        if not filing_types:
            filing_types = self.config.get("ingestion", {}).get(
                "filing_types", ["10-K", "10-Q", "8-K"]
            )

        # Default date range
        if not start_date:
            lookback_days = self.config.get("ingestion", {}).get("lookback_days", 730)
            start_date = datetime.now() - timedelta(days=lookback_days)

        # Create filing request
        request = FilingRequest(
            company_ticker=ticker.upper(),
            filing_types=filing_types,
            start_date=start_date,
            end_date=end_date,
        )

        logger.info(f"Starting SEC ingestion for {ticker}")
        console.print(f"\n[bold cyan]Ingesting SEC filings for {ticker}[/bold cyan]")
        console.print(f"Filing types: {', '.join(filing_types)}")
        console.print(f"Date range: {start_date.date()} to {end_date.date() if end_date else 'today'}")

        # Execute ingestion flow
        try:
            result = await sec_ingestion_flow(request)

            if result:
                console.print(f"\n[bold green]✓ Success![/bold green]")
                console.print(f"  CIK: {result.get('cik', 'N/A')}")
                console.print(f"  Filings found: {result.get('filings_found', 0)}")
                console.print(f"  Filings stored: {result.get('filings_stored', 0)}")
                return result
            else:
                console.print(f"\n[bold red]✗ Failed to ingest filings for {ticker}[/bold red]")
                return {}

        except Exception as e:
            logger.error(f"Error ingesting {ticker}: {e}", exc_info=True)
            console.print(f"\n[bold red]✗ Error: {str(e)}[/bold red]")
            return {}

    async def ingest_batch(
        self,
        tickers: List[str],
        filing_types: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
    ) -> List[dict]:
        """Ingest SEC filings for multiple companies.

        Args:
            tickers: List of company ticker symbols
            filing_types: List of filing types to collect
            start_date: Start date for filings

        Returns:
            List of ingestion results
        """
        console.print(f"\n[bold cyan]Batch ingestion for {len(tickers)} companies[/bold cyan]")

        # Progress tracking
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:

            task = progress.add_task(
                f"Processing {len(tickers)} companies...",
                total=len(tickers)
            )

            results = []
            for ticker in tickers:
                try:
                    result = await self.ingest_single_company(
                        ticker, filing_types, start_date
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to process {ticker}: {e}")
                    results.append({})

                progress.advance(task)

        # Summary table
        self.print_batch_summary(results)
        return results

    def print_batch_summary(self, results: List[dict]):
        """Print summary table of batch ingestion results."""
        table = Table(title="\nBatch Ingestion Summary")

        table.add_column("Ticker", style="cyan", no_wrap=True)
        table.add_column("CIK", style="magenta")
        table.add_column("Found", justify="right", style="yellow")
        table.add_column("Stored", justify="right", style="green")
        table.add_column("Status", justify="center")

        total_found = 0
        total_stored = 0
        success_count = 0

        for result in results:
            if result:
                ticker = result.get("ticker", "N/A")
                cik = result.get("cik", "N/A")
                found = result.get("filings_found", 0)
                stored = result.get("filings_stored", 0)
                status = "✓" if stored > 0 else "⚠"

                table.add_row(ticker, cik, str(found), str(stored), status)

                total_found += found
                total_stored += stored
                if stored > 0:
                    success_count += 1

        # Add summary row
        table.add_row(
            "[bold]TOTAL[/bold]",
            "",
            f"[bold]{total_found}[/bold]",
            f"[bold]{total_stored}[/bold]",
            f"[bold]{success_count}/{len(results)}[/bold]",
        )

        console.print(table)
        console.print(f"\n[bold green]Successfully processed {success_count}/{len(results)} companies[/bold green]")

    async def test_connectivity(self) -> bool:
        """Test SEC EDGAR API connectivity and configuration.

        Returns:
            True if connectivity test passed
        """
        from src.pipeline.sec_ingestion import SECAPIClient

        console.print("\n[bold cyan]Testing SEC EDGAR API Connectivity[/bold cyan]")

        client = SECAPIClient()

        # Test 1: User-Agent configuration
        console.print("\n1. User-Agent Configuration")
        console.print(f"   User-Agent: {client.headers['User-Agent']}")

        if not client.headers['User-Agent'] or 'example.com' in client.headers['User-Agent']:
            console.print("   [bold red]✗ Invalid User-Agent - update SEC_USER_AGENT in .env[/bold red]")
            return False
        console.print("   [green]✓ User-Agent configured correctly[/green]")

        # Test 2: Rate limiter
        console.print("\n2. Rate Limiter")
        console.print(f"   Rate limit: {client.rate_limiter.calls_per_second} requests/second")
        console.print(f"   Min interval: {client.rate_limiter.min_interval:.3f} seconds")
        console.print("   [green]✓ Rate limiter initialized[/green]")

        # Test 3: Ticker-to-CIK mapping
        console.print("\n3. Ticker-to-CIK Mapping")
        try:
            mapping = await client.get_ticker_to_cik_mapping()
            console.print(f"   Loaded {len(mapping)} ticker mappings")
            console.print("   [green]✓ Ticker mapping loaded successfully[/green]")
        except Exception as e:
            console.print(f"   [bold red]✗ Failed to load ticker mapping: {e}[/bold red]")
            return False

        # Test 4: Company info fetch
        console.print("\n4. Company Info Fetch (DUOL)")
        try:
            company_info = await client.get_company_info("DUOL")
            if company_info:
                console.print(f"   CIK: {company_info.get('cik', 'N/A')}")
                console.print(f"   Name: {company_info.get('name', 'N/A')}")
                console.print("   [green]✓ Company info fetched successfully[/green]")
            else:
                console.print("   [bold red]✗ No company info returned[/bold red]")
                return False
        except Exception as e:
            console.print(f"   [bold red]✗ Failed to fetch company info: {e}[/bold red]")
            return False

        # Test 5: Filing list fetch
        console.print("\n5. Filing List Fetch")
        try:
            filings = await client.get_filings("0001364612", ["10-K"], datetime(2024, 1, 1))
            console.print(f"   Found {len(filings)} filings")
            if filings:
                console.print(f"   Latest: {filings[0].get('form')} on {filings[0].get('filingDate')}")
            console.print("   [green]✓ Filing list fetched successfully[/green]")
        except Exception as e:
            console.print(f"   [bold red]✗ Failed to fetch filings: {e}[/bold red]")
            return False

        console.print("\n[bold green]✓ All connectivity tests passed![/bold green]")
        return True


def parse_date(date_str: str) -> datetime:
    """Parse date string in YYYY-MM-DD format."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: {date_str} (use YYYY-MM-DD)")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Ingest SEC EDGAR filings for EdTech companies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single company
  python ingest-sec-filings.py --ticker DUOL

  # Batch processing with EdTech watchlist
  python ingest-sec-filings.py --batch --watchlist

  # Custom date range and filing types
  python ingest-sec-filings.py --ticker CHGG --start-date 2023-01-01 --filing-types 10-K 10-Q

  # Test API connectivity
  python ingest-sec-filings.py --test-connectivity
        """,
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--ticker", type=str, help="Single company ticker symbol")
    mode_group.add_argument("--batch", action="store_true", help="Batch processing mode")
    mode_group.add_argument("--test-connectivity", action="store_true", help="Test API connectivity")

    # Batch options
    parser.add_argument("--watchlist", action="store_true", help="Use EdTech watchlist for batch")
    parser.add_argument("--tickers", nargs="+", help="List of tickers for batch processing")

    # Filing options
    parser.add_argument(
        "--filing-types",
        nargs="+",
        choices=["10-K", "10-Q", "8-K", "10-K/A", "10-Q/A", "S-1", "S-4", "DEF 14A"],
        help="Filing types to collect (default: 10-K, 10-Q, 8-K)",
    )
    parser.add_argument("--start-date", type=parse_date, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=parse_date, help="End date (YYYY-MM-DD)")

    # Output options
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode (errors only)")

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    elif args.quiet:
        logger.remove()
        logger.add(sys.stderr, level="ERROR")

    # Initialize CLI
    cli = SECIngestionCLI()

    # Test connectivity mode
    if args.test_connectivity:
        success = asyncio.run(cli.test_connectivity())
        sys.exit(0 if success else 1)

    # Single company mode
    if args.ticker:
        result = asyncio.run(
            cli.ingest_single_company(
                ticker=args.ticker,
                filing_types=args.filing_types,
                start_date=args.start_date,
                end_date=args.end_date,
            )
        )
        sys.exit(0 if result else 1)

    # Batch mode
    if args.batch:
        if args.watchlist:
            tickers = cli.settings.EDTECH_COMPANIES_WATCHLIST
            console.print(f"Using EdTech watchlist: {len(tickers)} companies")
        elif args.tickers:
            tickers = args.tickers
        else:
            console.print("[bold red]Error: --batch requires either --watchlist or --tickers[/bold red]")
            sys.exit(1)

        results = asyncio.run(
            cli.ingest_batch(
                tickers=tickers,
                filing_types=args.filing_types,
                start_date=args.start_date,
            )
        )

        success_count = sum(1 for r in results if r and r.get("filings_stored", 0) > 0)
        sys.exit(0 if success_count > 0 else 1)


if __name__ == "__main__":
    main()
