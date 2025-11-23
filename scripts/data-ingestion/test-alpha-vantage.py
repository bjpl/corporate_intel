#!/usr/bin/env python3
"""Test Alpha Vantage API connectivity and validation."""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.connectors.data_sources import AlphaVantageConnector


async def comprehensive_test():
    print()
    print('ALPHA VANTAGE PRODUCTION VALIDATION')
    print('=' * 70)
    print(f'Timestamp: {datetime.now().isoformat()}')
    print()

    connector = AlphaVantageConnector()
    test_tickers = ['CHGG', 'COUR', 'DUOL']

    print(f'Testing {len(test_tickers)} EdTech companies...')
    print('-' * 70)

    results = []
    for ticker in test_tickers:
        try:
            data = await connector.get_company_overview(ticker)

            if data and 'ticker' in data:
                # Count metrics
                metrics_count = len([v for k, v in data.items() if isinstance(v, (int, float)) and v != 0])

                results.append({
                    'ticker': ticker,
                    'status': 'SUCCESS',
                    'metrics': metrics_count,
                    'market_cap': data.get('market_cap', 0),
                    'pe_ratio': data.get('pe_ratio', 0)
                })

                print(f'{ticker:6} | SUCCESS | Metrics: {metrics_count:2} | MarketCap: ${data.get("market_cap", 0):,.0f}')
            else:
                results.append({'ticker': ticker, 'status': 'NO_DATA', 'metrics': 0})
                print(f'{ticker:6} | NO_DATA')

            # Rate limit delay
            if ticker != test_tickers[-1]:
                print(f'         | Rate limit: waiting 12s...')
                await asyncio.sleep(12)

        except Exception as e:
            results.append({'ticker': ticker, 'status': 'ERROR', 'error': str(e)})
            print(f'{ticker:6} | ERROR: {str(e)}')

    print('-' * 70)
    print()
    print('SUMMARY:')
    successful = [r for r in results if r['status'] == 'SUCCESS']
    print(f'  Total Tested: {len(results)}')
    print(f'  Successful: {len(successful)}')
    print(f'  Success Rate: {len(successful)/len(results)*100:.1f}%')

    if successful:
        avg_metrics = sum(r['metrics'] for r in successful) / len(successful)
        print(f'  Avg Metrics per Company: {avg_metrics:.1f}')

    print()
    print('✓ Production validation COMPLETE')

    return results


if __name__ == "__main__":
    asyncio.run(comprehensive_test())
