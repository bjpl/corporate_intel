#!/usr/bin/env python3
"""
Dependency Import Verification Script
Verifies that all critical dependencies can be imported successfully.
"""

import sys
from typing import List, Tuple

def test_imports() -> Tuple[List[str], List[str]]:
    """Test all critical imports and return success/failure lists."""
    success = []
    failures = []

    # Core Framework
    imports_to_test = [
        ("fastapi", "FastAPI framework"),
        ("uvicorn", "ASGI server"),
        ("pydantic", "Data validation"),
        ("pydantic_settings", "Settings management"),

        # Database
        ("sqlalchemy", "SQLAlchemy ORM"),
        ("asyncpg", "Async PostgreSQL"),
        ("psycopg2", "PostgreSQL adapter"),
        ("alembic", "Database migrations"),
        ("pgvector", "Vector extensions"),

        # Data Processing
        ("pandas", "Data manipulation"),
        ("numpy", "Numerical computing"),
        ("pandera", "Data validation"),
        ("great_expectations", "Data quality"),
        ("dbt.cli", "dbt CLI"),

        # Orchestration
        ("prefect", "Workflow orchestration"),
        ("prefect_dask", "Dask integration"),
        ("ray", "Distributed computing"),

        # Caching & Storage
        ("redis", "Redis client"),
        ("aiocache", "Async caching"),
        ("minio", "Object storage"),

        # Observability
        ("opentelemetry.api", "OpenTelemetry API"),
        ("opentelemetry.sdk", "OpenTelemetry SDK"),
        ("opentelemetry.instrumentation.fastapi", "FastAPI instrumentation"),
        ("prometheus_client", "Prometheus metrics"),
        ("loguru", "Logging"),
        ("sentry_sdk", "Error tracking"),

        # Document Processing
        ("pypdf", "PDF parsing"),
        ("pdfplumber", "PDF extraction"),
        ("docx", "Word documents"),
        ("bs4", "HTML parsing"),

        # Financial Data
        ("yfinance", "Yahoo Finance"),
        ("alpha_vantage", "Alpha Vantage"),

        # Visualization
        ("plotly", "Plotly charts"),
        ("dash", "Dash framework"),

        # Testing
        ("pytest", "Testing framework"),
        ("pytest_asyncio", "Async testing"),
        ("pytest_cov", "Coverage testing"),
        ("httpx", "HTTP client"),
    ]

    print("=" * 70)
    print("DEPENDENCY IMPORT VERIFICATION")
    print("=" * 70)
    print()

    for module_name, description in imports_to_test:
        try:
            __import__(module_name)
            success.append(f"✓ {module_name:40} - {description}")
            print(f"✓ {module_name:40} - {description}")
        except ImportError as e:
            failures.append(f"✗ {module_name:40} - {description}: {str(e)}")
            print(f"✗ {module_name:40} - {description}")
            print(f"  Error: {str(e)}")

    return success, failures


def main():
    """Main execution function."""
    success, failures = test_imports()

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✓ Successful imports: {len(success)}")
    print(f"✗ Failed imports: {len(failures)}")
    print()

    if failures:
        print("FAILED IMPORTS:")
        for failure in failures:
            print(f"  {failure}")
        print()
        sys.exit(1)
    else:
        print("✓ All critical dependencies imported successfully!")
        sys.exit(0)


if __name__ == "__main__":
    main()
