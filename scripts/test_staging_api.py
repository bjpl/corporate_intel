#!/usr/bin/env python3
"""
Test Staging API and Load Sample Data
Tests API health, loads sample companies, and verifies database operations.
"""

import sys
import json
import time
import psycopg2
from typing import Dict, List, Optional
from datetime import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configuration
API_BASE_URL = "http://localhost:8004"
DB_CONFIG = {
    "host": "localhost",
    "port": 5435,
    "database": "corporate_intel_staging",
    "user": "intel_staging_user",
    "password": None  # Will be set from args
}

# Sample companies for testing
SAMPLE_COMPANIES = [
    {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "sector": "Technology",
        "category": "Consumer Electronics",
        "description": "Designs and manufactures consumer electronics, software, and online services",
        "cik": "0000320193"
    },
    {
        "ticker": "MSFT",
        "name": "Microsoft Corporation",
        "sector": "Technology",
        "category": "Software",
        "description": "Develops and supports software, services, devices and solutions",
        "cik": "0000789019"
    },
    {
        "ticker": "GOOGL",
        "name": "Alphabet Inc.",
        "sector": "Technology",
        "category": "Internet Services",
        "description": "Technology company specializing in Internet-related services and products",
        "cik": "0001652044"
    },
    {
        "ticker": "CHGG",
        "name": "Chegg, Inc.",
        "sector": "EdTech",
        "category": "Higher Education",
        "description": "EdTech company providing digital and physical textbook rentals, online tutoring",
        "cik": "0001364954"
    },
    {
        "ticker": "DUOL",
        "name": "Duolingo, Inc.",
        "sector": "EdTech",
        "category": "Language Learning",
        "description": "Language-learning platform offering free and premium courses",
        "cik": "0001405086"
    }
]


class StagingAPITester:
    """Test staging API and load sample data."""

    def __init__(self, api_base_url: str, db_config: Dict):
        self.api_base_url = api_base_url
        self.db_config = db_config
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic."""
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def test_api_health(self) -> bool:
        """Test API health endpoint."""
        print("\n" + "="*80)
        print("TASK A: Testing API Health")
        print("="*80)

        try:
            url = f"{self.api_base_url}/health"
            print(f"\n📡 Testing: {url}")
            response = self.session.get(url, timeout=10)

            print(f"✅ Status Code: {response.status_code}")
            print(f"✅ Response: {response.text}")

            if response.status_code == 200:
                data = response.json()
                print(f"\n✅ API Health: {data.get('status', 'unknown')}")
                print(f"✅ Version: {data.get('version', 'unknown')}")
                print(f"✅ Environment: {data.get('environment', 'unknown')}")
                return True
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
                return False

        except requests.exceptions.ConnectionError as e:
            print(f"❌ Connection Error: {e}")
            print("\n⚠️  API appears to be down or not responding")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

    def test_api_docs(self) -> bool:
        """Test API documentation endpoint."""
        try:
            url = f"{self.api_base_url}/api/v1/docs"
            print(f"\n📚 Testing API Docs: {url}")
            response = self.session.get(url, timeout=10, allow_redirects=True)

            if response.status_code == 200:
                print(f"✅ API Documentation accessible")
                return True
            else:
                print(f"❌ Status: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error accessing docs: {e}")
            return False

    def connect_database(self) -> Optional[psycopg2.extensions.connection]:
        """Connect to staging database."""
        print("\n" + "="*80)
        print("Connecting to Database")
        print("="*80)

        try:
            conn = psycopg2.connect(**self.db_config)
            print(f"✅ Connected to: {self.db_config['database']}")
            print(f"✅ Host: {self.db_config['host']}:{self.db_config['port']}")
            return conn
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return None

    def load_sample_companies(self, conn: psycopg2.extensions.connection) -> bool:
        """Load sample companies into database."""
        print("\n" + "="*80)
        print("TASK A: Loading Sample Company Data")
        print("="*80)

        try:
            cursor = conn.cursor()

            # Check existing companies
            cursor.execute("SELECT COUNT(*) FROM companies")
            existing_count = cursor.fetchone()[0]
            print(f"\n📊 Existing companies: {existing_count}")

            inserted = 0
            updated = 0

            for company in SAMPLE_COMPANIES:
                # Check if company exists
                cursor.execute(
                    "SELECT id FROM companies WHERE ticker = %s",
                    (company['ticker'],)
                )
                existing = cursor.fetchone()

                if existing:
                    # Update existing
                    cursor.execute("""
                        UPDATE companies
                        SET name = %s, sector = %s, category = %s, description = %s, cik = %s
                        WHERE ticker = %s
                    """, (
                        company['name'], company['sector'], company['category'],
                        company['description'], company.get('cik'), company['ticker']
                    ))
                    updated += 1
                    print(f"✓ Updated: {company['ticker']} - {company['name']}")
                else:
                    # Insert new
                    cursor.execute("""
                        INSERT INTO companies (ticker, name, sector, category, description, cik)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        company['ticker'], company['name'], company['sector'],
                        company['category'], company['description'], company.get('cik')
                    ))
                    inserted += 1
                    print(f"✓ Inserted: {company['ticker']} - {company['name']}")

            conn.commit()
            print(f"\n✅ Successfully loaded {len(SAMPLE_COMPANIES)} companies")
            print(f"   - Inserted: {inserted}")
            print(f"   - Updated: {updated}")

            # Verify
            cursor.execute("SELECT COUNT(*) FROM companies")
            final_count = cursor.fetchone()[0]
            print(f"✅ Total companies in database: {final_count}")

            cursor.close()
            return True

        except Exception as e:
            print(f"❌ Error loading companies: {e}")
            conn.rollback()
            return False

    def verify_database_schema(self, conn: psycopg2.extensions.connection) -> bool:
        """Verify database schema and tables."""
        print("\n" + "="*80)
        print("Verifying Database Schema")
        print("="*80)

        try:
            cursor = conn.cursor()

            # List all tables
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = cursor.fetchall()

            print(f"\n📋 Database Tables ({len(tables)} total):")
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                count = cursor.fetchone()[0]
                print(f"   - {table[0]:<25} ({count:>5} rows)")

            # Check TimescaleDB hypertables
            cursor.execute("""
                SELECT hypertable_name, num_dimensions
                FROM timescaledb_information.hypertables
            """)
            hypertables = cursor.fetchall()

            if hypertables:
                print(f"\n⏱️  TimescaleDB Hypertables:")
                for ht in hypertables:
                    print(f"   - {ht[0]} ({ht[1]} dimensions)")

            cursor.close()
            return True

        except Exception as e:
            print(f"❌ Error verifying schema: {e}")
            return False

    def run_tests(self, db_password: str) -> Dict[str, bool]:
        """Run all tests."""
        self.db_config['password'] = db_password

        results = {
            "api_health": False,
            "api_docs": False,
            "database_connection": False,
            "database_schema": False,
            "sample_data_loaded": False
        }

        # Test API
        results["api_health"] = self.test_api_health()
        if results["api_health"]:
            results["api_docs"] = self.test_api_docs()

        # Test Database
        conn = self.connect_database()
        if conn:
            results["database_connection"] = True
            results["database_schema"] = self.verify_database_schema(conn)
            results["sample_data_loaded"] = self.load_sample_companies(conn)
            conn.close()

        return results


def print_summary(results: Dict[str, bool]):
    """Print test summary."""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    print(f"\nResults: {passed}/{total} tests passed\n")

    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}  {test.replace('_', ' ').title()}")

    print("\n" + "="*80)

    if passed == total:
        print("🎉 ALL TESTS PASSED - Staging environment is operational!")
    elif passed >= total * 0.7:
        print("⚠️  PARTIAL SUCCESS - Some components need attention")
    else:
        print("❌ CRITICAL - Multiple failures detected")

    print("="*80 + "\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_staging_api.py <db_password>")
        print("\nExample:")
        print("  python scripts/test_staging_api.py your_password_here")
        sys.exit(1)

    db_password = sys.argv[1]

    tester = StagingAPITester(API_BASE_URL, DB_CONFIG)
    results = tester.run_tests(db_password)
    print_summary(results)

    # Exit with appropriate code
    if all(results.values()):
        sys.exit(0)
    else:
        sys.exit(1)
