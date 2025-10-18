"""Cleanup script for duplicate "Company CIK" records.

This script identifies and merges duplicate company records created by the old
SEC ingestion logic that used generic "Company CIK [number]" names.

Usage:
    python scripts/data-ingestion/cleanup_duplicate_companies.py [--dry-run] [--verbose]

Options:
    --dry-run: Show what would be done without making changes
    --verbose: Show detailed logging
"""

import argparse
import asyncio
from typing import Dict, List, Tuple

from loguru import logger
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.db.models import Company, SECFiling
from src.db.session import get_session_factory


async def find_duplicate_companies(session: AsyncSession) -> List[Dict]:
    """Find companies with generic 'Company CIK' names.

    Returns:
        List of dictionaries with duplicate company info
    """
    result = await session.execute(
        select(Company)
        .where(Company.name.like("Company CIK%"))
        .order_by(Company.cik)
    )
    duplicates = result.scalars().all()

    duplicate_info = []
    for dup in duplicates:
        # Count associated filings
        filing_count_result = await session.execute(
            select(SECFiling).where(SECFiling.company_id == dup.id)
        )
        filing_count = len(filing_count_result.scalars().all())

        duplicate_info.append({
            "id": str(dup.id),
            "cik": dup.cik,
            "ticker": dup.ticker,
            "name": dup.name,
            "filing_count": filing_count,
        })

    return duplicate_info


async def find_proper_company_by_cik(session: AsyncSession, cik: str) -> Company | None:
    """Find the proper company record for a given CIK.

    Looks for companies with the same CIK that don't have generic names.

    Args:
        session: Database session
        cik: Company CIK number

    Returns:
        Proper company record or None if not found
    """
    result = await session.execute(
        select(Company)
        .where(Company.cik == cik)
        .where(~Company.name.like("Company CIK%"))
    )
    return result.scalar_one_or_none()


async def merge_companies(
    session: AsyncSession,
    duplicate_id: str,
    target_id: str,
    dry_run: bool = False
) -> Tuple[int, int]:
    """Merge duplicate company into target company.

    Args:
        session: Database session
        duplicate_id: ID of duplicate company to merge
        target_id: ID of target company to merge into
        dry_run: If True, don't make changes

    Returns:
        Tuple of (filings_updated, companies_deleted)
    """
    # Update all filings to point to target company
    if not dry_run:
        result = await session.execute(
            update(SECFiling)
            .where(SECFiling.company_id == duplicate_id)
            .values(company_id=target_id)
        )
        filings_updated = result.rowcount
    else:
        # Count filings that would be updated
        result = await session.execute(
            select(SECFiling).where(SECFiling.company_id == duplicate_id)
        )
        filings_updated = len(result.scalars().all())

    # Delete duplicate company
    if not dry_run:
        result = await session.execute(
            delete(Company).where(Company.id == duplicate_id)
        )
        companies_deleted = result.rowcount
    else:
        companies_deleted = 1  # Would delete one company

    return filings_updated, companies_deleted


async def cleanup_duplicates(dry_run: bool = False, verbose: bool = False) -> Dict:
    """Main cleanup logic.

    Args:
        dry_run: If True, show what would be done without making changes
        verbose: If True, show detailed logging

    Returns:
        Dictionary with cleanup statistics
    """
    settings = get_settings()
    session_factory = get_session_factory()

    total_duplicates_found = 0
    total_duplicates_merged = 0
    total_duplicates_deleted = 0
    total_filings_updated = 0
    errors = []

    async with session_factory() as session:
        try:
            # Find all duplicate companies
            duplicates = await find_duplicate_companies(session)
            total_duplicates_found = len(duplicates)

            logger.info(f"Found {total_duplicates_found} duplicate 'Company CIK' records")

            if total_duplicates_found == 0:
                logger.info("No duplicates found - database is clean!")
                return {
                    "duplicates_found": 0,
                    "duplicates_merged": 0,
                    "duplicates_deleted": 0,
                    "filings_updated": 0,
                    "errors": [],
                }

            # Process each duplicate
            for dup in duplicates:
                cik = dup["cik"]
                dup_id = dup["id"]

                if verbose:
                    logger.info(f"Processing duplicate: {dup['name']} (CIK: {cik}, ID: {dup_id})")

                # Find proper company with same CIK
                proper_company = await find_proper_company_by_cik(session, cik)

                if proper_company:
                    # Merge into proper company
                    logger.info(
                        f"{'[DRY RUN] Would merge' if dry_run else 'Merging'} "
                        f"{dup['name']} -> {proper_company.name} "
                        f"({dup['filing_count']} filings)"
                    )

                    filings_updated, companies_deleted = await merge_companies(
                        session, dup_id, str(proper_company.id), dry_run
                    )

                    total_filings_updated += filings_updated
                    total_duplicates_merged += 1
                    total_duplicates_deleted += companies_deleted

                    if verbose:
                        logger.info(
                            f"  → Updated {filings_updated} filings, "
                            f"deleted {companies_deleted} companies"
                        )
                else:
                    # No proper company found - keep the duplicate for now
                    logger.warning(
                        f"No proper company found for CIK {cik} - keeping duplicate "
                        f"{dup['name']} for manual review"
                    )
                    errors.append({
                        "cik": cik,
                        "name": dup["name"],
                        "reason": "No target company found",
                    })

            # Commit changes
            if not dry_run:
                await session.commit()
                logger.info("Changes committed to database")
            else:
                logger.info("DRY RUN - no changes made to database")

        except Exception as e:
            if not dry_run:
                await session.rollback()
            logger.error(f"Error during cleanup: {str(e)}", exc_info=True)
            errors.append({"error": str(e)})
            raise

    return {
        "duplicates_found": total_duplicates_found,
        "duplicates_merged": total_duplicates_merged,
        "duplicates_deleted": total_duplicates_deleted,
        "filings_updated": total_filings_updated,
        "errors": errors,
    }


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Cleanup duplicate 'Company CIK' records"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed logging",
    )
    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logger.level("INFO")
    else:
        logger.level("WARNING")

    logger.info("Starting duplicate company cleanup...")
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")

    # Run cleanup
    results = await cleanup_duplicates(dry_run=args.dry_run, verbose=args.verbose)

    # Print summary
    logger.info("\n" + "=" * 60)
    logger.info("CLEANUP SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Duplicates found:   {results['duplicates_found']}")
    logger.info(f"Duplicates merged:  {results['duplicates_merged']}")
    logger.info(f"Duplicates deleted: {results['duplicates_deleted']}")
    logger.info(f"Filings updated:    {results['filings_updated']}")

    if results["errors"]:
        logger.warning(f"\nErrors/Warnings:    {len(results['errors'])}")
        for error in results["errors"]:
            logger.warning(f"  - {error}")

    logger.info("=" * 60)

    if args.dry_run:
        logger.info("\nTo apply these changes, run without --dry-run flag")

    return results


if __name__ == "__main__":
    asyncio.run(main())
