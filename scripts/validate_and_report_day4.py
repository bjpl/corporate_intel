"""Plan A Day 4 - Data Pipeline Validation and Reporting.

This script validates existing data in the database and generates comprehensive reports.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger
from sqlalchemy import text

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.session import get_session_factory


class DataValidator:
    """Validates and reports on existing data pipeline."""

    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'validations': {},
            'analytics': {},
            'metrics': {}
        }
        self.docs_dir = Path('docs/pipeline')
        self.docs_dir.mkdir(parents=True, exist_ok=True)

    async def validate_database_state(self):
        """Validate current database state."""
        logger.info("=" * 80)
        logger.info("DATABASE STATE VALIDATION")
        logger.info("=" * 80)

        async with get_session_factory()() as session:
            # Count companies
            result = await session.execute(text("SELECT COUNT(*) FROM companies"))
            company_count = result.scalar()
            logger.info(f"✓ Companies: {company_count}")
            self.results['validations']['company_count'] = company_count

            # Count financial metrics
            result = await session.execute(text("SELECT COUNT(*) FROM financial_metrics"))
            metrics_count = result.scalar()
            logger.info(f"✓ Financial Metrics: {metrics_count}")
            self.results['validations']['metrics_count'] = metrics_count

            # Count SEC filings
            result = await session.execute(text("SELECT COUNT(*) FROM sec_filings"))
            filings_count = result.scalar()
            logger.info(f"✓ SEC Filings: {filings_count}")
            self.results['validations']['filings_count'] = filings_count

            # List all companies
            result = await session.execute(text("""
                SELECT ticker, name, sector, created_at
                FROM companies
                ORDER BY ticker
            """))
            companies = []
            for row in result:
                companies.append({
                    'ticker': row[0],
                    'name': row[1],
                    'sector': row[2],
                    'created_at': str(row[3])
                })
            self.results['validations']['companies'] = companies
            logger.info(f"✓ Found {len(companies)} companies in database")

            # Data completeness by company
            result = await session.execute(text("""
                SELECT
                    c.ticker,
                    c.name,
                    COUNT(DISTINCT fm.id) as metric_count,
                    COUNT(DISTINCT sf.id) as filing_count,
                    MAX(fm.period_end) as latest_metric_date,
                    MIN(fm.period_end) as earliest_metric_date
                FROM companies c
                LEFT JOIN financial_metrics fm ON c.id = fm.company_id
                LEFT JOIN sec_filings sf ON c.id = sf.company_id
                GROUP BY c.ticker, c.name
                ORDER BY metric_count DESC
            """))

            completeness = []
            for row in result:
                completeness.append({
                    'ticker': row[0],
                    'name': row[1],
                    'metric_count': row[2],
                    'filing_count': row[3],
                    'latest_date': str(row[4]) if row[4] else None,
                    'earliest_date': str(row[5]) if row[5] else None
                })

            self.results['validations']['data_completeness'] = completeness
            logger.info(f"✓ Data completeness calculated for {len(completeness)} companies")

    async def generate_analytics_reports(self):
        """Generate analytics reports from available data."""
        logger.info("=" * 80)
        logger.info("ANALYTICS REPORT GENERATION")
        logger.info("=" * 80)

        async with get_session_factory()() as session:
            # Report 1: Company Financial Summary
            result = await session.execute(text("""
                SELECT
                    c.ticker,
                    c.name,
                    COUNT(DISTINCT fm.id) as total_metrics,
                    MAX(fm.period_end) as latest_data_date,
                    AVG(CASE WHEN fm.metric_type = 'revenue' THEN fm.value END) as avg_revenue,
                    AVG(CASE WHEN fm.metric_type = 'profit_margin' THEN fm.value END) as avg_profit_margin,
                    AVG(CASE WHEN fm.metric_type = 'net_income' THEN fm.value END) as avg_net_income
                FROM companies c
                LEFT JOIN financial_metrics fm ON c.id = fm.company_id
                GROUP BY c.ticker, c.name
                ORDER BY total_metrics DESC
            """))

            summary = []
            for row in result:
                summary.append({
                    'ticker': row[0],
                    'name': row[1],
                    'total_metrics': row[2],
                    'latest_data_date': str(row[3]) if row[3] else None,
                    'avg_revenue': float(row[4]) if row[4] else None,
                    'avg_profit_margin': float(row[5]) if row[5] else None,
                    'avg_net_income': float(row[6]) if row[6] else None
                })

            self.results['analytics']['company_summary'] = summary
            logger.info(f"✓ Generated financial summary for {len(summary)} companies")

            # Report 2: Metric Type Coverage
            result = await session.execute(text("""
                SELECT
                    metric_type,
                    metric_category,
                    COUNT(*) as count,
                    MIN(period_end) as earliest_date,
                    MAX(period_end) as latest_date,
                    COUNT(DISTINCT company_id) as company_count
                FROM financial_metrics
                GROUP BY metric_type, metric_category
                ORDER BY count DESC
            """))

            metric_coverage = []
            for row in result:
                metric_coverage.append({
                    'metric_type': row[0],
                    'category': row[1],
                    'count': row[2],
                    'earliest_date': str(row[3]) if row[3] else None,
                    'latest_date': str(row[4]) if row[4] else None,
                    'company_count': row[5]
                })

            self.results['analytics']['metric_coverage'] = metric_coverage
            logger.info(f"✓ Generated metric coverage for {len(metric_coverage)} metric types")

            # Report 3: Top performers by revenue
            result = await session.execute(text("""
                SELECT
                    c.ticker,
                    c.name,
                    fm.value as latest_revenue,
                    fm.period_end
                FROM companies c
                JOIN financial_metrics fm ON c.id = fm.company_id
                WHERE fm.metric_type = 'revenue'
                    AND fm.period_end = (
                        SELECT MAX(period_end)
                        FROM financial_metrics fm2
                        WHERE fm2.company_id = c.id AND fm2.metric_type = 'revenue'
                    )
                ORDER BY fm.value DESC
                LIMIT 10
            """))

            top_revenue = []
            for row in result:
                top_revenue.append({
                    'ticker': row[0],
                    'name': row[1],
                    'latest_revenue': float(row[2]) if row[2] else None,
                    'period_end': str(row[3]) if row[3] else None
                })

            self.results['analytics']['top_revenue'] = top_revenue
            logger.info(f"✓ Identified top {len(top_revenue)} companies by revenue")

            # Report 4: Data quality metrics
            result = await session.execute(text("""
                SELECT
                    COUNT(*) FILTER (WHERE value IS NULL) as null_values,
                    COUNT(*) FILTER (WHERE value < 0) as negative_values,
                    COUNT(*) FILTER (WHERE source IS NULL) as null_sources,
                    COUNT(*) as total_records
                FROM financial_metrics
            """))

            quality = result.fetchone()
            self.results['analytics']['data_quality'] = {
                'null_values': quality[0],
                'negative_values': quality[1],
                'null_sources': quality[2],
                'total_records': quality[3],
                'completeness_rate': round((1 - quality[0] / quality[3]) * 100, 2) if quality[3] > 0 else 0
            }
            logger.info(f"✓ Data quality metrics calculated")

    def calculate_metrics(self):
        """Calculate overall pipeline metrics."""
        logger.info("=" * 80)
        logger.info("PIPELINE METRICS")
        logger.info("=" * 80)

        self.results['metrics'] = {
            'total_companies': self.results['validations']['company_count'],
            'total_metrics': self.results['validations']['metrics_count'],
            'total_filings': self.results['validations']['filings_count'],
            'data_coverage': {
                'companies_with_metrics': len([c for c in self.results['validations']['data_completeness'] if c['metric_count'] > 0]),
                'companies_with_filings': len([c for c in self.results['validations']['data_completeness'] if c['filing_count'] > 0]),
                'avg_metrics_per_company': round(self.results['validations']['metrics_count'] / max(self.results['validations']['company_count'], 1), 2)
            },
            'data_quality': self.results['analytics']['data_quality']['completeness_rate']
        }

        logger.info(f"Total Companies: {self.results['metrics']['total_companies']}")
        logger.info(f"Total Metrics: {self.results['metrics']['total_metrics']}")
        logger.info(f"Data Quality: {self.results['metrics']['data_quality']}%")

    def generate_markdown_report(self) -> str:
        """Generate markdown report."""
        report = f"""# Plan A Day 4 - Data Pipeline Validation Report

**Generated**: {self.results['timestamp']}

## Executive Summary

- **Total Companies**: {self.results['metrics']['total_companies']}
- **Total Financial Metrics**: {self.results['metrics']['total_metrics']}
- **Total SEC Filings**: {self.results['metrics']['total_filings']}
- **Data Quality Score**: {self.results['metrics']['data_quality']}%

## Database Validation

### Companies in Database

| Ticker | Company Name | Metrics | Filings | Latest Data |
|--------|-------------|---------|---------|-------------|
"""

        for company in self.results['validations']['data_completeness'][:20]:
            report += f"| {company['ticker']} | {company['name'][:40]} | {company['metric_count']} | {company['filing_count']} | {company['latest_date'] or 'N/A'} |\n"

        report += f"""
## Analytics Reports

### Top Companies by Data Coverage

"""

        top_companies = sorted(self.results['validations']['data_completeness'], key=lambda x: x['metric_count'], reverse=True)[:10]
        for idx, company in enumerate(top_companies, 1):
            report += f"{idx}. **{company['ticker']}** ({company['name']}): {company['metric_count']} metrics\n"

        report += f"""
### Metric Type Coverage

"""

        for metric in self.results['analytics']['metric_coverage'][:15]:
            report += f"- **{metric['metric_type']}** ({metric['category']}): {metric['count']} records across {metric['company_count']} companies\n"

        report += f"""
### Top Companies by Revenue

"""

        for idx, company in enumerate(self.results['analytics']['top_revenue'], 1):
            revenue = company['latest_revenue']
            revenue_str = f"${revenue/1e9:.2f}B" if revenue and revenue > 1e9 else f"${revenue/1e6:.2f}M" if revenue else "N/A"
            report += f"{idx}. **{company['ticker']}** ({company['name']}): {revenue_str} (as of {company['period_end']})\n"

        report += f"""
## Data Quality Assessment

- **Completeness Rate**: {self.results['analytics']['data_quality']['completeness_rate']}%
- **Total Records**: {self.results['analytics']['data_quality']['total_records']}
- **NULL Values**: {self.results['analytics']['data_quality']['null_values']}
- **Negative Values**: {self.results['analytics']['data_quality']['negative_values']}
- **Missing Sources**: {self.results['analytics']['data_quality']['null_sources']}

## Coverage Analysis

- **Companies with Metrics**: {self.results['metrics']['data_coverage']['companies_with_metrics']} / {self.results['metrics']['total_companies']}
- **Companies with Filings**: {self.results['metrics']['data_coverage']['companies_with_filings']} / {self.results['metrics']['total_companies']}
- **Average Metrics per Company**: {self.results['metrics']['data_coverage']['avg_metrics_per_company']}

## Recommendations

1. **SEC Filings**: Complete SEC filings ingestion - currently at {self.results['validations']['filings_count']} filings
2. **Data Quality**: Address {self.results['analytics']['data_quality']['null_values']} NULL values in metrics
3. **Coverage**: Expand data collection for companies with fewer than 20 metrics
4. **Validation**: Set up Great Expectations suite for automated data quality checks

---

*Report generated by Plan A Day 4 Data Pipeline*
"""

        return report

    async def run(self):
        """Execute validation and reporting."""
        logger.info("=" * 80)
        logger.info("PLAN A DAY 4 - DATA VALIDATION & REPORTING")
        logger.info("=" * 80)

        await self.validate_database_state()
        await self.generate_analytics_reports()
        self.calculate_metrics()

        # Save JSON results
        with open(self.docs_dir / 'data-ingestion-results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"✓ Saved JSON results: {self.docs_dir / 'data-ingestion-results.json'}")

        # Save markdown report
        markdown_report = self.generate_markdown_report()
        with open(self.docs_dir / 'PIPELINE_EXECUTION_LOG_DAY4.md', 'w') as f:
            f.write(markdown_report)
        logger.info(f"✓ Saved markdown report: {self.docs_dir / 'PIPELINE_EXECUTION_LOG_DAY4.md'}")

        # Save sample analytics
        with open(self.docs_dir / 'SAMPLE_ANALYTICS_REPORT.md', 'w') as f:
            f.write(self._generate_analytics_report())
        logger.info(f"✓ Saved analytics report: {self.docs_dir / 'SAMPLE_ANALYTICS_REPORT.md'}")

        logger.info("=" * 80)
        logger.info("VALIDATION COMPLETE")
        logger.info("=" * 80)

        return self.results

    def _generate_analytics_report(self) -> str:
        """Generate detailed analytics report."""
        return f"""# Sample Analytics Report - Plan A Day 4

**Generated**: {self.results['timestamp']}

## Financial Performance Analysis

### Revenue Leaders

"""
        + "\n".join([
            f"**{idx}. {company['ticker']}** - {company['name']}\n"
            f"   - Latest Revenue: ${company['latest_revenue']/1e9:.2f}B" if company['latest_revenue'] and company['latest_revenue'] > 1e9 else f"   - Latest Revenue: ${company['latest_revenue']/1e6:.2f}M" if company['latest_revenue'] else "   - Latest Revenue: N/A"
            f"\n   - Period: {company['period_end']}\n"
            for idx, company in enumerate(self.results['analytics']['top_revenue'], 1)
        ]) + f"""

## Data Coverage Summary

### Companies by Data Availability

"""
        + "\n".join([
            f"- **{company['ticker']}**: {company['metric_count']} metrics, {company['filing_count']} filings"
            for company in sorted(self.results['validations']['data_completeness'], key=lambda x: x['metric_count'], reverse=True)[:20]
        ]) + f"""

## Metric Type Distribution

"""
        + "\n".join([
            f"- **{metric['metric_type']}**: {metric['count']} records ({metric['company_count']} companies)"
            for metric in self.results['analytics']['metric_coverage'][:10]
        ]) + """

---

*Generated by Corporate Intel Data Pipeline*
"""


async def main():
    """Main entry point."""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    validator = DataValidator()
    await validator.run()

    logger.info("\n✓ All reports generated successfully")
    logger.info(f"✓ Check docs/pipeline/ for detailed results")


if __name__ == "__main__":
    asyncio.run(main())
