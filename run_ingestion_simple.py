#!/usr/bin/env python3
"""
Simplified data ingestion script for EdTech companies.
PATTERN: Graceful degradation - Works without full infrastructure
WHY: Allow data collection even when services are unavailable
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# EdTech companies to analyze
EDTECH_COMPANIES = [
    {
        'ticker': 'CHGG',
        'name': 'Chegg Inc.',
        'cik': '0001364954',
        'sector': 'Technology',
        'subsector': 'Education Technology'
    },
    {
        'ticker': 'COUR',
        'name': 'Coursera Inc.',
        'cik': '0001651562',
        'sector': 'Technology',
        'subsector': 'Online Learning'
    },
    {
        'ticker': 'DUOL',
        'name': 'Duolingo Inc.',
        'cik': '0001562088',
        'sector': 'Technology',
        'subsector': 'Language Learning'
    },
    {
        'ticker': 'UDMY',
        'name': 'Udemy Inc.',
        'cik': '0001607939',
        'sector': 'Technology',
        'subsector': 'Skills Development'
    },
    {
        'ticker': 'TWOU',
        'name': '2U Inc.',
        'cik': '0001459417',
        'sector': 'Technology',
        'subsector': 'Online Program Management'
    }
]

def check_dependencies():
    """Check if required packages are installed."""
    required = ['yfinance', 'pandas', 'requests']
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        logger.error(f"Missing packages: {missing}")
        logger.info(f"Install with: pip install {' '.join(missing)}")
        return False
    return True

def fetch_stock_data(ticker: str, start_date: str = None, end_date: str = None):
    """
    Fetch stock data using yfinance.
    PATTERN: Fallback data source when primary APIs unavailable
    """
    try:
        import yfinance as yf
        
        if not start_date:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"Fetching stock data for {ticker} from {start_date} to {end_date}")
        
        stock = yf.Ticker(ticker)
        
        # Get historical prices
        hist = stock.history(start=start_date, end=end_date)
        
        # Get company info
        info = stock.info
        
        # Save to CSV
        output_dir = Path('data/raw/stock_data')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        hist.to_csv(output_dir / f'{ticker}_prices.csv')
        
        with open(output_dir / f'{ticker}_info.json', 'w') as f:
            json.dump(info, f, indent=2, default=str)
        
        logger.info(f"✓ Saved {ticker} data to {output_dir}")
        
        return {
            'ticker': ticker,
            'records': len(hist),
            'latest_price': hist['Close'].iloc[-1] if not hist.empty else None,
            'market_cap': info.get('marketCap'),
            'pe_ratio': info.get('trailingPE')
        }
        
    except Exception as e:
        logger.error(f"Error fetching {ticker}: {e}")
        return None

def fetch_sec_filings(company: dict):
    """
    Fetch SEC filings using sec-edgar-api.
    CONCEPT: Regulatory data as primary source of truth
    """
    try:
        from sec_edgar_api import EdgarClient
        
        edgar = EdgarClient(user_agent="Corporate Intel Analysis")
        
        output_dir = Path('data/raw/sec_filings')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get recent 10-K and 10-Q filings
        filings = edgar.get_filings(
            cik=company['cik'],
            filing_type=['10-K', '10-Q'],
            start_date='2023-01-01'
        )
        
        # Save filings metadata
        with open(output_dir / f"{company['ticker']}_filings.json", 'w') as f:
            json.dump(filings, f, indent=2, default=str)
        
        logger.info(f"✓ Saved SEC filings for {company['ticker']}")
        return len(filings) if filings else 0
        
    except ImportError:
        logger.warning("sec-edgar-api not installed, skipping SEC data")
        return 0
    except Exception as e:
        logger.error(f"Error fetching SEC data for {company['ticker']}: {e}")
        return 0

def create_summary_report(results: list):
    """
    Create a summary report of ingested data.
    PATTERN: Always provide feedback on data collection status
    """
    output_dir = Path('data/reports')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Save to CSV
    report_path = output_dir / f'ingestion_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    df.to_csv(report_path, index=False)
    
    # Print summary
    print("\n" + "="*60)
    print("📊 DATA INGESTION SUMMARY")
    print("="*60)
    print(f"Companies processed: {len(results)}")
    print(f"Total stock records: {df['stock_records'].sum():,}")
    print(f"Total SEC filings: {df['sec_filings'].sum():,}")
    print("\nCompany Details:")
    print("-"*60)
    
    for _, row in df.iterrows():
        print(f"\n{row['name']} ({row['ticker']})")
        print(f"  • Stock records: {row['stock_records']:,}")
        print(f"  • Latest price: ${row['latest_price']:.2f}" if row['latest_price'] else "  • Latest price: N/A")
        print(f"  • Market cap: ${row['market_cap']:,.0f}" if row['market_cap'] else "  • Market cap: N/A")
        print(f"  • SEC filings: {row['sec_filings']}")
    
    print(f"\n✅ Report saved to: {report_path}")
    print("="*60)

def main():
    """Main ingestion workflow."""
    logger.info("Starting Corporate Intelligence Data Ingestion")
    
    # Check dependencies
    if not check_dependencies():
        logger.error("Missing dependencies. Please install required packages.")
        sys.exit(1)
    
    # Process each company
    results = []
    for company in EDTECH_COMPANIES:
        logger.info(f"\nProcessing {company['name']} ({company['ticker']})")
        
        # Fetch stock data
        stock_result = fetch_stock_data(company['ticker'])
        
        # Fetch SEC filings
        sec_count = fetch_sec_filings(company)
        
        # Compile results
        if stock_result:
            results.append({
                'ticker': company['ticker'],
                'name': company['name'],
                'sector': company['sector'],
                'subsector': company['subsector'],
                'stock_records': stock_result['records'],
                'latest_price': stock_result['latest_price'],
                'market_cap': stock_result['market_cap'],
                'pe_ratio': stock_result['pe_ratio'],
                'sec_filings': sec_count
            })
    
    # Create summary report
    if results:
        create_summary_report(results)
    else:
        logger.error("No data collected. Please check your network connection and API access.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️  Ingestion interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()