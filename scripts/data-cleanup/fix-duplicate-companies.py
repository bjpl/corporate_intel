#!/usr/bin/env python3
"""
Fix Duplicate "Company CIK" Records

This script:
1. Maps CIK numbers to proper company names/tickers via SEC mappings
2. Creates UPDATE statements to reassign SEC filings to proper companies
3. Generates DELETE statements to remove duplicate "Company CIK" records
4. Validates the fix with transaction safety

Author: Corporate Intel Data Team
Date: 2025-10-17
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import psycopg2
import requests
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scripts/data-cleanup/fix-duplicates.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5434,  # corporate-intel-postgres mapped port
    'database': 'corporate_intel',
    'user': 'intel_user',
    'password': 'lsZXGgU92KhK5VqR'
}

# CIKs to map (duplicate "Company CIK" records)
DUPLICATE_CIKS = [
    '0000730464',
    '0001013934',
    '0001157408',
    '0001364954',  # Likely Chegg
    '0001434588',
    '0001562088',  # Likely Duolingo
    '0001607939',
    '0001651562',  # Likely Coursera
]

# SEC mappings URL
SEC_TICKER_URL = 'https://www.sec.gov/files/company_tickers.json'

# User agent for SEC requests
SEC_HEADERS = {
    'User-Agent': 'Corporate Intel Data Cleanup Script admin@corporateintel.com'
}


class DuplicateCompanyFixer:
    """Fix duplicate company records and reassign SEC filings."""

    def __init__(self, db_config: Dict[str, str]):
        """Initialize fixer with database configuration."""
        self.db_config = db_config
        self.conn = None
        self.cik_mappings: Dict[str, Dict[str, str]] = {}
        self.duplicate_company_ids: Dict[str, int] = {}
        self.proper_company_ids: Dict[str, int] = {}
        self.filing_counts: Dict[str, int] = {}

    def connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def disconnect(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

    def fetch_sec_mappings(self) -> Dict[str, Dict[str, str]]:
        """
        Fetch SEC ticker mappings from official SEC source.

        Returns:
            Dictionary mapping CIK (normalized) to company info
        """
        logger.info("Fetching SEC ticker mappings...")

        try:
            response = requests.get(SEC_TICKER_URL, headers=SEC_HEADERS, timeout=30)
            response.raise_for_status()
            data = response.json()

            # Normalize CIK numbers and create mapping
            mappings = {}
            for item in data.values():
                cik = str(item['cik_str']).zfill(10)  # Normalize to 10 digits
                mappings[cik] = {
                    'ticker': item['ticker'],
                    'title': item['title'],
                    'cik': cik
                }

            logger.info(f"Fetched {len(mappings)} company mappings from SEC")
            return mappings

        except Exception as e:
            logger.error(f"Failed to fetch SEC mappings: {e}")
            raise

    def lookup_cik_info(self, cik: str) -> Optional[Dict[str, str]]:
        """
        Look up company information for a CIK.

        Args:
            cik: CIK number (any format)

        Returns:
            Company info dict or None if not found
        """
        normalized_cik = cik.zfill(10)
        return self.cik_mappings.get(normalized_cik)

    def find_duplicate_records(self) -> Dict[str, int]:
        """
        Find the duplicate "Company CIK" records in the database.

        Returns:
            Dictionary mapping CIK to company_id
        """
        logger.info("Finding duplicate 'Company CIK' records...")

        cursor = self.conn.cursor()

        # Find records with name = "Company CIK {cik}"
        placeholders = ', '.join(['%s'] * len(DUPLICATE_CIKS))
        query = f"""
            SELECT id, name, cik
            FROM companies
            WHERE cik IN ({placeholders})
            AND name LIKE 'Company CIK %'
            ORDER BY cik
        """

        cursor.execute(query, DUPLICATE_CIKS)
        results = cursor.fetchall()

        duplicate_map = {}
        for company_id, name, cik in results:
            duplicate_map[cik] = company_id
            logger.info(f"Found duplicate: {name} (ID: {company_id}, CIK: {cik})")

        cursor.close()
        return duplicate_map

    def find_proper_companies(self) -> Dict[str, int]:
        """
        Find or create proper company records for each CIK.

        Returns:
            Dictionary mapping CIK to proper company_id
        """
        logger.info("Finding/creating proper company records...")

        cursor = self.conn.cursor()
        proper_map = {}

        for cik in DUPLICATE_CIKS:
            # Look up company info from SEC
            info = self.lookup_cik_info(cik)

            if not info:
                logger.warning(f"No SEC mapping found for CIK {cik}, skipping")
                continue

            ticker = info['ticker']
            title = info['title']

            # Check if proper company record exists
            cursor.execute("""
                SELECT id FROM companies
                WHERE cik = %s
                AND name != 'Company CIK ' || %s
                LIMIT 1
            """, (cik, cik))

            result = cursor.fetchone()

            if result:
                # Proper record exists
                proper_id = result[0]
                logger.info(f"Found existing proper record for {ticker}: ID {proper_id}")
            else:
                # Create proper record
                cursor.execute("""
                    INSERT INTO companies (name, ticker, cik, industry, sector, created_at)
                    VALUES (%s, %s, %s, 'Unknown', 'Unknown', NOW())
                    RETURNING id
                """, (title, ticker, cik))

                proper_id = cursor.fetchone()[0]
                logger.info(f"Created new proper record for {ticker}: ID {proper_id}")

            proper_map[cik] = proper_id

        self.conn.commit()
        cursor.close()
        return proper_map

    def count_filings_per_duplicate(self) -> Dict[str, int]:
        """
        Count SEC filings associated with each duplicate record.

        Returns:
            Dictionary mapping CIK to filing count
        """
        logger.info("Counting SEC filings per duplicate...")

        cursor = self.conn.cursor()
        filing_counts = {}

        for cik, dup_id in self.duplicate_company_ids.items():
            cursor.execute("""
                SELECT COUNT(*)
                FROM sec_filings
                WHERE company_id = %s
            """, (dup_id,))

            count = cursor.fetchone()[0]
            filing_counts[cik] = count

            if count > 0:
                logger.info(f"CIK {cik}: {count} filings to reassign")

        cursor.close()
        return filing_counts

    def reassign_filings(self) -> Dict[str, int]:
        """
        Reassign SEC filings from duplicate records to proper companies.

        Returns:
            Dictionary mapping CIK to number of filings reassigned
        """
        logger.info("Reassigning SEC filings to proper companies...")

        cursor = self.conn.cursor()
        reassigned_counts = {}

        for cik in DUPLICATE_CIKS:
            dup_id = self.duplicate_company_ids.get(cik)
            proper_id = self.proper_company_ids.get(cik)

            if not dup_id or not proper_id:
                logger.warning(f"Skipping CIK {cik}: missing duplicate or proper ID")
                continue

            # Update filings
            cursor.execute("""
                UPDATE sec_filings
                SET company_id = %s, updated_at = NOW()
                WHERE company_id = %s
            """, (proper_id, dup_id))

            reassigned = cursor.rowcount
            reassigned_counts[cik] = reassigned

            info = self.lookup_cik_info(cik)
            ticker = info['ticker'] if info else 'UNKNOWN'

            logger.info(f"Reassigned {reassigned} filings from duplicate to {ticker} (ID: {proper_id})")

        self.conn.commit()
        cursor.close()
        return reassigned_counts

    def delete_duplicates(self) -> int:
        """
        Delete duplicate "Company CIK" records after filings are reassigned.

        Returns:
            Number of records deleted
        """
        logger.info("Deleting duplicate company records...")

        cursor = self.conn.cursor()

        duplicate_ids = list(self.duplicate_company_ids.values())

        if not duplicate_ids:
            logger.warning("No duplicate IDs to delete")
            return 0

        # Verify no filings remain
        placeholders = ', '.join(['%s'] * len(duplicate_ids))
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM sec_filings
            WHERE company_id IN ({placeholders})
        """, duplicate_ids)

        remaining = cursor.fetchone()[0]

        if remaining > 0:
            logger.error(f"Cannot delete: {remaining} filings still reference duplicate records!")
            raise Exception(f"Safety check failed: {remaining} filings still reference duplicates")

        # Safe to delete
        cursor.execute(f"""
            DELETE FROM companies
            WHERE id IN ({placeholders})
        """, duplicate_ids)

        deleted = cursor.rowcount
        logger.info(f"Deleted {deleted} duplicate company records")

        self.conn.commit()
        cursor.close()
        return deleted

    def validate_fix(self) -> bool:
        """
        Validate that the fix was successful.

        Returns:
            True if validation passes, False otherwise
        """
        logger.info("Validating fix...")

        cursor = self.conn.cursor()
        issues = []

        # Check 1: No duplicate "Company CIK" records remain
        cursor.execute("""
            SELECT COUNT(*)
            FROM companies
            WHERE name LIKE 'Company CIK %'
            AND cik IN %s
        """, (tuple(DUPLICATE_CIKS),))

        dup_count = cursor.fetchone()[0]
        if dup_count > 0:
            issues.append(f"{dup_count} duplicate 'Company CIK' records still exist")

        # Check 2: All CIKs have proper company records
        cursor.execute("""
            SELECT COUNT(*)
            FROM companies
            WHERE cik IN %s
            AND name NOT LIKE 'Company CIK %'
        """, (tuple(DUPLICATE_CIKS),))

        proper_count = cursor.fetchone()[0]
        if proper_count != len(DUPLICATE_CIKS):
            issues.append(f"Expected {len(DUPLICATE_CIKS)} proper records, found {proper_count}")

        # Check 3: All SEC filings have valid company references
        cursor.execute("""
            SELECT COUNT(*)
            FROM sec_filings sf
            LEFT JOIN companies c ON sf.company_id = c.id
            WHERE c.id IS NULL
        """)

        orphaned = cursor.fetchone()[0]
        if orphaned > 0:
            issues.append(f"{orphaned} SEC filings have invalid company references")

        cursor.close()

        if issues:
            logger.error("Validation failed:")
            for issue in issues:
                logger.error(f"  - {issue}")
            return False

        logger.info("Validation passed: All checks successful!")
        return True

    def generate_report(self) -> str:
        """
        Generate a summary report of the fix operation.

        Returns:
            Report as formatted string
        """
        report_lines = [
            "=" * 80,
            "DUPLICATE COMPANY FIX REPORT",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 80,
            "",
            "CIK MAPPINGS:",
            "-" * 80,
        ]

        for cik in sorted(DUPLICATE_CIKS):
            info = self.lookup_cik_info(cik)
            if info:
                report_lines.append(f"  {cik}: {info['ticker']:6s} - {info['title']}")
            else:
                report_lines.append(f"  {cik}: NOT FOUND IN SEC MAPPINGS")

        report_lines.extend([
            "",
            "FILING REASSIGNMENTS:",
            "-" * 80,
        ])

        total_reassigned = 0
        for cik in sorted(DUPLICATE_CIKS):
            count = self.filing_counts.get(cik, 0)
            total_reassigned += count
            info = self.lookup_cik_info(cik)
            ticker = info['ticker'] if info else 'UNKNOWN'

            dup_id = self.duplicate_company_ids.get(cik, 'N/A')
            proper_id = self.proper_company_ids.get(cik, 'N/A')

            report_lines.append(
                f"  {cik} ({ticker:6s}): {count:4d} filings "
                f"(Dup ID: {dup_id} -> Proper ID: {proper_id})"
            )

        report_lines.extend([
            "",
            f"TOTAL FILINGS REASSIGNED: {total_reassigned}",
            f"DUPLICATE RECORDS DELETED: {len(self.duplicate_company_ids)}",
            "",
            "=" * 80,
        ])

        return "\n".join(report_lines)

    def run(self, dry_run: bool = False) -> bool:
        """
        Execute the complete fix process.

        Args:
            dry_run: If True, don't commit changes

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Starting duplicate company fix process...")
            logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")

            # Connect to database
            self.connect()

            if not dry_run:
                # Start transaction
                self.conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                cursor = self.conn.cursor()
                cursor.execute("BEGIN")
                cursor.close()

            # Step 1: Fetch SEC mappings
            self.cik_mappings = self.fetch_sec_mappings()

            # Step 2: Find duplicate records
            self.duplicate_company_ids = self.find_duplicate_records()

            if not self.duplicate_company_ids:
                logger.warning("No duplicate records found!")
                return False

            # Step 3: Find/create proper company records
            self.proper_company_ids = self.find_proper_companies()

            # Step 4: Count filings to reassign
            self.filing_counts = self.count_filings_per_duplicate()

            if dry_run:
                logger.info("DRY RUN: Would reassign filings and delete duplicates")
                logger.info(f"Total filings to reassign: {sum(self.filing_counts.values())}")
                logger.info(f"Duplicate records to delete: {len(self.duplicate_company_ids)}")
            else:
                # Step 5: Reassign filings
                reassigned_counts = self.reassign_filings()

                # Step 6: Delete duplicates
                deleted_count = self.delete_duplicates()

                # Step 7: Validate
                if not self.validate_fix():
                    logger.error("Validation failed - rolling back!")
                    self.conn.rollback()
                    return False

                # Commit transaction
                self.conn.commit()
                logger.info("All changes committed successfully!")

            # Generate report
            report = self.generate_report()
            print("\n" + report)

            # Save report to file
            report_path = Path('scripts/data-cleanup') / f'fix-report-{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt'
            report_path.write_text(report)
            logger.info(f"Report saved to: {report_path}")

            return True

        except Exception as e:
            logger.error(f"Error during fix process: {e}", exc_info=True)
            if self.conn and not dry_run:
                self.conn.rollback()
                logger.info("Transaction rolled back")
            return False

        finally:
            self.disconnect()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Fix duplicate "Company CIK" records and reassign SEC filings'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without committing to database'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create fixer and run
    fixer = DuplicateCompanyFixer(DB_CONFIG)

    if args.dry_run:
        print("\n" + "=" * 80)
        print("DRY RUN MODE - No changes will be committed")
        print("=" * 80 + "\n")

    success = fixer.run(dry_run=args.dry_run)

    if success:
        logger.info("Fix process completed successfully!")
        sys.exit(0)
    else:
        logger.error("Fix process failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()
