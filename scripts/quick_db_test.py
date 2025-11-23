#!/usr/bin/env python3
"""Quick database connection test for staging environment."""

import psycopg2
import sys

DB_CONFIG = {
    "host": "localhost",
    "port": 5435,
    "database": "corporate_intel_staging",
    "user": "intel_staging_user",
    "password": "lsZXGgU92KhK5VqR"
}

SAMPLE_COMPANIES = [
    ("AAPL", "Apple Inc.", "Technology", "Consumer Electronics", "0000320193"),
    ("MSFT", "Microsoft Corporation", "Technology", "Software", "0000789019"),
    ("GOOGL", "Alphabet Inc.", "Technology", "Internet Services", "0001652044"),
    ("CHGG", "Chegg, Inc.", "EdTech", "Higher Education", "0001364954"),
    ("DUOL", "Duolingo, Inc.", "EdTech", "Language Learning", "0001405086")
]

def main():
    print("=" * 80)
    print("QUICK DATABASE TEST - Corporate Intel Staging")
    print("=" * 80)

    try:
        print(f"\n1. Connecting to database...")
        print(f"   Host: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
        print(f"   Database: {DB_CONFIG['database']}")

        conn = psycopg2.connect(**DB_CONFIG)
        print("   ✅ Connected successfully!")

        cursor = conn.cursor()

        # Check tables
        print(f"\n2. Checking database schema...")
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        print(f"   ✅ Found {len(tables)} tables:")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
            count = cursor.fetchone()[0]
            print(f"      - {table[0]:<25} ({count:>5} rows)")

        # Load sample companies
        print(f"\n3. Loading sample companies...")
        inserted = 0
        updated = 0

        for ticker, name, sector, category, cik in SAMPLE_COMPANIES:
            cursor.execute("SELECT id FROM companies WHERE ticker = %s", (ticker,))
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE companies
                    SET name = %s, sector = %s, category = %s, cik = %s
                    WHERE ticker = %s
                """, (name, sector, category, cik, ticker))
                updated += 1
                print(f"   ✓ Updated: {ticker} - {name}")
            else:
                cursor.execute("""
                    INSERT INTO companies (ticker, name, sector, category, cik)
                    VALUES (%s, %s, %s, %s, %s)
                """, (ticker, name, sector, category, cik))
                inserted += 1
                print(f"   ✓ Inserted: {ticker} - {name}")

        conn.commit()
        print(f"\n   ✅ Success! Inserted: {inserted}, Updated: {updated}")

        # Verify
        cursor.execute("SELECT COUNT(*) FROM companies")
        total = cursor.fetchone()[0]
        print(f"   ✅ Total companies in database: {total}")

        # Show all companies
        print(f"\n4. All companies in database:")
        cursor.execute("SELECT ticker, name, sector FROM companies ORDER BY ticker")
        for row in cursor.fetchall():
            print(f"   - {row[0]:<6} {row[1]:<30} ({row[2]})")

        cursor.close()
        conn.close()

        print(f"\n" + "=" * 80)
        print("✅ DATABASE TEST PASSED - Staging environment is operational!")
        print("=" * 80)
        return 0

    except psycopg2.OperationalError as e:
        print(f"\n❌ Connection failed: {e}")
        print(f"\nPossible issues:")
        print(f"  1. PostgreSQL container is not running")
        print(f"  2. Port 5435 is not accessible")
        print(f"  3. Wrong credentials")
        print(f"\nTo start staging environment:")
        print(f"  docker-compose -f docker-compose.staging.yml --env-file .env.staging up -d")
        return 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
