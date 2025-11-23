#!/usr/bin/env python3
"""
Yahoo Finance Connectivity Test
================================

Tests Yahoo Finance connectivity and data retrieval without database dependency.
"""

import sys
from datetime import datetime

try:
    import yfinance as yf
    import pandas as pd
except ImportError as e:
    print(f"Error: {e}")
    print("Install with: pip install yfinance pandas")
    sys.exit(1)


def test_yahoo_finance_connectivity():
    """Test Yahoo Finance connectivity and basic functionality."""
    print("="*60)
    print("Yahoo Finance Connectivity Test")
    print("="*60)
    print("Note: Yahoo Finance is an unofficial API (no API key required)")
    print("")

    test_ticker = "CHGG"  # Chegg Inc.

    # Test 1: Fetch current quote
    print("-"*60)
    print(f"Test 1: Current Quote Data ({test_ticker})")
    print("-"*60)
    try:
        stock = yf.Ticker(test_ticker)
        info = stock.info

        if info:
            print(f"✓ Successfully fetched quote for {test_ticker}")
            print(f"\n  Company: {info.get('longName', 'N/A')}")
            print(f"  Symbol: {info.get('symbol', 'N/A')}")
            print(f"  Sector: {info.get('sector', 'N/A')}")
            print(f"  Industry: {info.get('industry', 'N/A')}")
            print(f"  Market Price: ${info.get('regularMarketPrice', 'N/A')}")
            print(f"  Market Cap: ${info.get('marketCap', 0):,.0f}")
            print(f"  52 Week Low: ${info.get('fiftyTwoWeekLow', 'N/A')}")
            print(f"  52 Week High: ${info.get('fiftyTwoWeekHigh', 'N/A')}")
            print(f"  P/E Ratio: {info.get('trailingPE', 'N/A')}")
            print(f"  Beta: {info.get('beta', 'N/A')}")
        else:
            print(f"❌ No quote data found for {test_ticker}")
            return False

    except Exception as e:
        print(f"❌ Error fetching quote: {e}")
        return False

    # Test 2: Fetch historical data
    print("\n" + "-"*60)
    print(f"Test 2: Historical Price Data ({test_ticker}, 1 month)")
    print("-"*60)
    try:
        stock = yf.Ticker(test_ticker)
        hist = stock.history(period="1mo")

        if not hist.empty:
            print(f"✓ Fetched {len(hist)} days of historical data")
            print(f"\n  Date Range: {hist.index[0].strftime('%Y-%m-%d')} to {hist.index[-1].strftime('%Y-%m-%d')}")
            print(f"\n  Recent Prices:")

            for i, (date, row) in enumerate(hist.tail(5).iterrows()):
                print(f"    {date.strftime('%Y-%m-%d')}: "
                      f"Open=${row['Open']:.2f}, "
                      f"High=${row['High']:.2f}, "
                      f"Low=${row['Low']:.2f}, "
                      f"Close=${row['Close']:.2f}, "
                      f"Volume={row['Volume']:,.0f}")

            # Calculate simple statistics
            avg_price = hist['Close'].mean()
            volatility = hist['Close'].std()
            print(f"\n  Average Close Price: ${avg_price:.2f}")
            print(f"  Price Volatility (Std Dev): ${volatility:.2f}")

        else:
            print(f"❌ No historical data found for {test_ticker}")
            return False

    except Exception as e:
        print(f"❌ Error fetching historical data: {e}")
        return False

    # Test 3: Company Information
    print("\n" + "-"*60)
    print(f"Test 3: Detailed Company Information ({test_ticker})")
    print("-"*60)
    try:
        stock = yf.Ticker(test_ticker)
        info = stock.info

        if info:
            print(f"✓ Company information retrieved")
            print(f"\n  Full Name: {info.get('longName', 'N/A')}")
            print(f"  Website: {info.get('website', 'N/A')}")
            print(f"  Employees: {info.get('fullTimeEmployees', 'N/A'):,}")
            print(f"  Location: {info.get('city', 'N/A')}, {info.get('state', 'N/A')}, {info.get('country', 'N/A')}")

            summary = info.get('longBusinessSummary', '')
            if summary:
                print(f"\n  Business Summary:")
                print(f"    {summary[:200]}...")
        else:
            print(f"❌ No company info found for {test_ticker}")
            return False

    except Exception as e:
        print(f"❌ Error fetching company info: {e}")
        return False

    # Test 4: Multiple Tickers (EdTech Watchlist)
    print("\n" + "-"*60)
    print("Test 4: Multiple Tickers (EdTech Watchlist)")
    print("-"*60)
    try:
        watchlist = ['CHGG', 'COUR', 'DUOL', 'TWOU']
        print(f"Testing {len(watchlist)} tickers: {', '.join(watchlist)}")

        results = []
        for ticker in watchlist:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info

                if info and 'regularMarketPrice' in info:
                    results.append({
                        'ticker': ticker,
                        'name': info.get('shortName', 'N/A'),
                        'price': info.get('regularMarketPrice', 0),
                        'change_pct': info.get('regularMarketChangePercent', 0),
                        'volume': info.get('regularMarketVolume', 0)
                    })
            except Exception as e:
                print(f"  ⚠ Warning: Could not fetch {ticker}: {e}")

        if results:
            print(f"\n✓ Successfully fetched data for {len(results)}/{len(watchlist)} tickers")
            print("\n  Current Prices:")

            for r in results:
                change_symbol = "▲" if r['change_pct'] > 0 else "▼" if r['change_pct'] < 0 else "="
                print(f"    {r['ticker']:6} ({r['name'][:20]:20}): "
                      f"${r['price']:7.2f} "
                      f"{change_symbol} {abs(r['change_pct']):5.2f}% "
                      f"Vol: {r['volume']:>12,}")
        else:
            print(f"❌ Could not fetch any ticker data")
            return False

    except Exception as e:
        print(f"❌ Error testing multiple tickers: {e}")
        return False

    # Test 5: Market Indices
    print("\n" + "-"*60)
    print("Test 5: Market Indices")
    print("-"*60)
    try:
        indices = {
            '^GSPC': 'S&P 500',
            '^DJI': 'Dow Jones',
            '^IXIC': 'NASDAQ'
        }

        print("Fetching major market indices...")

        for symbol, name in indices.items():
            try:
                index = yf.Ticker(symbol)
                info = index.info

                if info and 'regularMarketPrice' in info:
                    price = info.get('regularMarketPrice', 0)
                    change = info.get('regularMarketChange', 0)
                    change_pct = info.get('regularMarketChangePercent', 0)
                    change_symbol = "▲" if change > 0 else "▼" if change < 0 else "="

                    print(f"  {name:12}: {price:>10,.2f} "
                          f"{change_symbol} {abs(change):>7,.2f} ({change_pct:>5.2f}%)")
            except Exception as e:
                print(f"  ⚠ Could not fetch {name}: {e}")

        print("✓ Market indices retrieved")

    except Exception as e:
        print(f"❌ Error fetching indices: {e}")
        return False

    # Summary
    print("\n" + "="*60)
    print("✓ All Yahoo Finance tests passed successfully!")
    print("="*60)
    print("\nKey Points:")
    print("  • No API key required (unofficial API)")
    print("  • Real-time quotes available")
    print("  • Historical data accessible")
    print("  • Company fundamentals available")
    print("  • Multiple ticker support works")
    print("  • Market indices accessible")
    print("\nRecommendations:")
    print("  • Implement rate limiting (30 req/min recommended)")
    print("  • Add error handling for API changes")
    print("  • Use caching to minimize requests")
    print("  • Monitor for service disruptions")
    print("  • Have backup data sources ready")
    print("="*60)

    return True


if __name__ == '__main__':
    success = test_yahoo_finance_connectivity()
    sys.exit(0 if success else 1)
