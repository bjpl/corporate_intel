@echo off
REM Alpha Vantage Daily Ingestion Scheduler
REM Run this daily to fetch valuation metrics for all companies
REM Rate Limit: 25 API calls per day (free tier)

echo ===================================================
echo Alpha Vantage Daily Ingestion
echo ===================================================
echo.
echo This script fetches valuation metrics (P/E, EPS, ROE, etc.)
echo for EdTech companies. Rate limited to 25 calls/day.
echo.
echo Starting ingestion...
echo.

cd /d "%~dp0.."
python -m src.pipeline.alpha_vantage_ingestion

echo.
echo ===================================================
echo Ingestion Complete!
echo ===================================================
echo.
echo Next: Run 'dbt run' to refresh marts with new data
echo.
pause
