#!/bin/bash
# Alpha Vantage Daily Ingestion Scheduler
# Run this daily to fetch valuation metrics for all companies
# Rate Limit: 25 API calls per day (free tier)

echo "==================================================="
echo "Alpha Vantage Daily Ingestion"
echo "==================================================="
echo ""
echo "This script fetches valuation metrics (P/E, EPS, ROE, etc.)"
echo "for EdTech companies. Rate limited to 25 calls/day."
echo ""
echo "Starting ingestion..."
echo ""

cd "$(dirname "$0")/.."
python -m src.pipeline.alpha_vantage_ingestion

echo ""
echo "==================================================="
echo "Ingestion Complete!"
echo "==================================================="
echo ""
echo "Next: Run 'dbt run' to refresh marts with new data"
echo ""
