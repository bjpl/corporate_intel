#!/usr/bin/env python3
"""
NewsAPI Connectivity Test
=========================

Tests NewsAPI connectivity and data retrieval without database dependency.
"""

import os
import sys
from datetime import datetime, timedelta

try:
    from newsapi import NewsApiClient
    from textblob import TextBlob
except ImportError as e:
    print(f"Error: {e}")
    print("Install with: pip install newsapi-python textblob")
    sys.exit(1)


def test_newsapi_connectivity():
    """Test NewsAPI connectivity and basic functionality."""
    print("="*60)
    print("NewsAPI Connectivity Test")
    print("="*60)

    # Check for API key
    api_key = os.getenv('NEWSAPI_KEY')
    if not api_key:
        print("❌ NEWSAPI_KEY environment variable not set")
        print("\nTo set the API key:")
        print("  export NEWSAPI_KEY='your-api-key-here'")
        print("\nGet a free API key at: https://newsapi.org/register")
        return False

    print(f"✓ API Key found: {api_key[:10]}...")

    # Initialize client
    try:
        client = NewsApiClient(api_key=api_key)
        print("✓ NewsAPI client initialized")
    except Exception as e:
        print(f"❌ Failed to initialize client: {e}")
        return False

    # Test 1: Fetch top business headlines
    print("\n" + "-"*60)
    print("Test 1: Top Business Headlines")
    print("-"*60)
    try:
        response = client.get_top_headlines(
            category='business',
            country='us',
            page_size=5
        )

        if response['status'] == 'ok':
            articles = response.get('articles', [])
            print(f"✓ Fetched {len(articles)} headlines")

            for i, article in enumerate(articles[:3], 1):
                print(f"\n  {i}. {article.get('title')}")
                print(f"     Source: {article.get('source', {}).get('name')}")
                print(f"     Published: {article.get('publishedAt')}")
        else:
            print(f"❌ API returned status: {response['status']}")
            return False

    except Exception as e:
        print(f"❌ Error fetching headlines: {e}")
        return False

    # Test 2: Search for company news
    print("\n" + "-"*60)
    print("Test 2: Company News Search (CHGG - Chegg)")
    print("-"*60)
    try:
        from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        response = client.get_everything(
            q='CHGG OR Chegg',
            from_param=from_date,
            language='en',
            sort_by='publishedAt',
            page_size=5
        )

        if response['status'] == 'ok':
            articles = response.get('articles', [])
            print(f"✓ Found {len(articles)} articles about Chegg (CHGG)")

            if articles:
                for i, article in enumerate(articles[:2], 1):
                    print(f"\n  {i}. {article.get('title')}")
                    print(f"     URL: {article.get('url')}")
                    print(f"     Published: {article.get('publishedAt')}")
            else:
                print("  No recent articles found")
        else:
            print(f"❌ API returned status: {response['status']}")
            return False

    except Exception as e:
        print(f"❌ Error searching news: {e}")
        return False

    # Test 3: Sentiment Analysis
    print("\n" + "-"*60)
    print("Test 3: Sentiment Analysis")
    print("-"*60)
    try:
        test_texts = [
            "The company reported record quarterly earnings and strong growth.",
            "Stock prices plummeted after disappointing earnings report.",
            "The company announced a new product launch next month."
        ]

        for i, text in enumerate(test_texts, 1):
            blob = TextBlob(text)
            sentiment = blob.sentiment

            if sentiment.polarity > 0.2:
                category = "Positive"
            elif sentiment.polarity < -0.2:
                category = "Negative"
            else:
                category = "Neutral"

            print(f"\n  {i}. Text: {text}")
            print(f"     Sentiment: {category}")
            print(f"     Polarity: {sentiment.polarity:.3f}")
            print(f"     Subjectivity: {sentiment.subjectivity:.3f}")

        print("\n✓ Sentiment analysis working")

    except Exception as e:
        print(f"❌ Error in sentiment analysis: {e}")
        return False

    # Test 4: Check API limits
    print("\n" + "-"*60)
    print("Test 4: API Information")
    print("-"*60)
    print("  Rate Limits (Free Tier):")
    print("    - 1,000 requests per day")
    print("    - 100 requests per hour")
    print("  ")
    print("  Available Endpoints:")
    print("    - Top Headlines: /v2/top-headlines")
    print("    - Everything: /v2/everything")
    print("  ")
    print("  Upgrade Options:")
    print("    - Developer: 100,000 requests/day")
    print("    - Business: Unlimited requests")

    print("\n" + "="*60)
    print("✓ All NewsAPI tests passed successfully!")
    print("="*60)
    return True


if __name__ == '__main__':
    success = test_newsapi_connectivity()
    sys.exit(0 if success else 1)
