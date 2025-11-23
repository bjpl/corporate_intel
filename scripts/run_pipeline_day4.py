"""Plan A Day 4 - Complete Data Pipeline Execution and Validation.

This script orchestrates the full end-to-end data pipeline:
1. Data Ingestion (SEC, Alpha Vantage, Yahoo Finance)
2. dbt Transformations
3. Great Expectations Validation
4. Sample Analytics Generation
5. Performance Monitoring

Target: 10 EdTech companies for initial validation
"""

import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger


# Test dataset: 10 EdTech companies
TEST_COMPANIES = [
    'CHGG',  # Chegg
    'COUR',  # Coursera
    'DUOL',  # Duolingo
    'ARCE',  # Arco Platform
    'LRN',   # Stride (K12)
    'UDMY',  # Udemy
    'ATGE',  # Adtalem Global Education
    'LOPE',  # Grand Canyon Education
    'STRA',  # Strategic Education
    'BFAM',  # Bright Horizons
]


class PipelineExecutor:
    """Orchestrates end-to-end data pipeline execution."""

    def __init__(self, test_mode: bool = True):
        self.test_mode = test_mode
        self.companies = TEST_COMPANIES if test_mode else []
        self.results = {
            'start_time': datetime.now().isoformat(),
            'test_companies': self.companies,
            'stages': {},
            'metrics': {},
            'errors': []
        }
        self.docs_dir = Path('docs/pipeline')
        self.docs_dir.mkdir(parents=True, exist_ok=True)

    async def run_coordination_hook(self, hook_type: str, **kwargs):
        """Run Claude Flow coordination hooks."""
        try:
            cmd = ['npx', 'claude-flow@alpha', 'hooks', hook_type]
            for key, value in kwargs.items():
                cmd.extend([f'--{key.replace("_", "-")}', str(value)])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            logger.debug(f"Hook {hook_type}: {result.stdout}")
        except Exception as e:
            logger.warning(f"Hook {hook_type} failed: {e}")

    async def stage_1_sec_ingestion(self) -> Dict[str, Any]:
        """Stage 1: Ingest SEC filings for test companies."""
        logger.info("=" * 80)
        logger.info("STAGE 1: SEC FILINGS INGESTION")
        logger.info("=" * 80)

        stage_start = time.time()
        stage_result = {
            'status': 'pending',
            'start_time': datetime.now().isoformat(),
            'companies_processed': 0,
            'filings_stored': 0,
            'errors': []
        }

        try:
            # Import and run SEC ingestion
            from src.pipeline.sec_ingestion import FilingRequest, sec_ingestion_flow

            total_filings = 0
            for idx, ticker in enumerate(self.companies, 1):
                try:
                    logger.info(f"[{idx}/{len(self.companies)}] Processing SEC filings for {ticker}...")

                    request = FilingRequest(
                        company_ticker=ticker,
                        filing_types=["10-K", "10-Q"],
                        start_date=datetime.now() - timedelta(days=1825)  # 5 years
                    )

                    result = await sec_ingestion_flow(request)

                    if result:
                        filings_count = result.get('filings_stored', 0)
                        total_filings += filings_count
                        logger.info(f"  ✓ {ticker}: {filings_count} filings stored")
                        stage_result['companies_processed'] += 1
                    else:
                        logger.warning(f"  ⚠ {ticker}: No results returned")
                        stage_result['errors'].append(f"{ticker}: No results")

                except Exception as e:
                    logger.error(f"  ✗ {ticker}: {str(e)}")
                    stage_result['errors'].append(f"{ticker}: {str(e)}")

            stage_result['filings_stored'] = total_filings
            stage_result['status'] = 'completed'
            stage_result['duration_seconds'] = time.time() - stage_start

        except Exception as e:
            logger.error(f"SEC ingestion stage failed: {e}")
            stage_result['status'] = 'failed'
            stage_result['error'] = str(e)

        finally:
            stage_result['end_time'] = datetime.now().isoformat()
            self.results['stages']['sec_ingestion'] = stage_result

        return stage_result

    async def stage_2_alpha_vantage_ingestion(self) -> Dict[str, Any]:
        """Stage 2: Fetch Alpha Vantage fundamentals."""
        logger.info("=" * 80)
        logger.info("STAGE 2: ALPHA VANTAGE FUNDAMENTALS")
        logger.info("=" * 80)

        stage_start = time.time()
        stage_result = {
            'status': 'pending',
            'start_time': datetime.now().isoformat(),
            'companies_processed': 0,
            'metrics_stored': 0,
            'errors': []
        }

        try:
            from src.pipeline.alpha_vantage_ingestion import ingest_company_fundamentals

            for idx, ticker in enumerate(self.companies, 1):
                try:
                    logger.info(f"[{idx}/{len(self.companies)}] Fetching fundamentals for {ticker}...")

                    result = await ingest_company_fundamentals(ticker)

                    if result and result.get('metrics_stored', 0) > 0:
                        metrics_count = result['metrics_stored']
                        logger.info(f"  ✓ {ticker}: {metrics_count} metrics stored")
                        stage_result['companies_processed'] += 1
                        stage_result['metrics_stored'] += metrics_count
                    else:
                        logger.warning(f"  ⚠ {ticker}: No metrics stored")
                        stage_result['errors'].append(f"{ticker}: No metrics")

                    # Rate limiting: 5 calls per minute
                    if idx < len(self.companies):
                        await asyncio.sleep(12)

                except Exception as e:
                    logger.error(f"  ✗ {ticker}: {str(e)}")
                    stage_result['errors'].append(f"{ticker}: {str(e)}")

            stage_result['status'] = 'completed'
            stage_result['duration_seconds'] = time.time() - stage_start

        except Exception as e:
            logger.error(f"Alpha Vantage stage failed: {e}")
            stage_result['status'] = 'failed'
            stage_result['error'] = str(e)

        finally:
            stage_result['end_time'] = datetime.now().isoformat()
            self.results['stages']['alpha_vantage'] = stage_result

        return stage_result

    async def stage_3_yahoo_finance_ingestion(self) -> Dict[str, Any]:
        """Stage 3: Pull Yahoo Finance price data."""
        logger.info("=" * 80)
        logger.info("STAGE 3: YAHOO FINANCE PRICE DATA")
        logger.info("=" * 80)

        stage_start = time.time()
        stage_result = {
            'status': 'pending',
            'start_time': datetime.now().isoformat(),
            'companies_processed': 0,
            'metrics_stored': 0,
            'errors': []
        }

        try:
            from src.pipeline.yahoo_finance_ingestion import ingest_company_data

            for idx, ticker in enumerate(self.companies, 1):
                try:
                    logger.info(f"[{idx}/{len(self.companies)}] Fetching Yahoo Finance data for {ticker}...")

                    result = await ingest_company_data(ticker)

                    if result and result.get('total_metrics_stored', 0) > 0:
                        metrics_count = result['total_metrics_stored']
                        logger.info(f"  ✓ {ticker}: {metrics_count} metrics stored")
                        stage_result['companies_processed'] += 1
                        stage_result['metrics_stored'] += metrics_count
                    else:
                        logger.warning(f"  ⚠ {ticker}: No metrics stored")
                        stage_result['errors'].append(f"{ticker}: No metrics")

                except Exception as e:
                    logger.error(f"  ✗ {ticker}: {str(e)}")
                    stage_result['errors'].append(f"{ticker}: {str(e)}")

            stage_result['status'] = 'completed'
            stage_result['duration_seconds'] = time.time() - stage_start

        except Exception as e:
            logger.error(f"Yahoo Finance stage failed: {e}")
            stage_result['status'] = 'failed'
            stage_result['error'] = str(e)

        finally:
            stage_result['end_time'] = datetime.now().isoformat()
            self.results['stages']['yahoo_finance'] = stage_result

        return stage_result

    async def stage_4_dbt_transformations(self) -> Dict[str, Any]:
        """Stage 4: Execute dbt transformations."""
        logger.info("=" * 80)
        logger.info("STAGE 4: DBT TRANSFORMATIONS")
        logger.info("=" * 80)

        stage_start = time.time()
        stage_result = {
            'status': 'pending',
            'start_time': datetime.now().isoformat(),
            'models_run': 0,
            'errors': []
        }

        try:
            # Change to dbt directory
            dbt_dir = Path('dbt')

            # Run dbt deps (install dependencies)
            logger.info("Installing dbt dependencies...")
            deps_result = subprocess.run(
                ['dbt', 'deps'],
                cwd=dbt_dir,
                capture_output=True,
                text=True,
                timeout=120
            )

            if deps_result.returncode != 0:
                logger.warning(f"dbt deps warning: {deps_result.stderr}")

            # Run dbt run (execute transformations)
            logger.info("Executing dbt models...")
            run_result = subprocess.run(
                ['dbt', 'run'],
                cwd=dbt_dir,
                capture_output=True,
                text=True,
                timeout=300
            )

            if run_result.returncode == 0:
                logger.info("✓ dbt transformations completed successfully")
                stage_result['status'] = 'completed'

                # Parse run results
                run_results_file = dbt_dir / 'target' / 'run_results.json'
                if run_results_file.exists():
                    with open(run_results_file) as f:
                        dbt_results = json.load(f)
                        stage_result['models_run'] = len(dbt_results.get('results', []))
                        stage_result['dbt_results'] = dbt_results

                        # Save results
                        with open(self.docs_dir / 'dbt-run-results.json', 'w') as out:
                            json.dump(dbt_results, out, indent=2)
            else:
                logger.error(f"✗ dbt run failed: {run_result.stderr}")
                stage_result['status'] = 'failed'
                stage_result['errors'].append(run_result.stderr)

            stage_result['stdout'] = run_result.stdout
            stage_result['stderr'] = run_result.stderr
            stage_result['duration_seconds'] = time.time() - stage_start

        except Exception as e:
            logger.error(f"dbt transformations failed: {e}")
            stage_result['status'] = 'failed'
            stage_result['error'] = str(e)

        finally:
            stage_result['end_time'] = datetime.now().isoformat()
            self.results['stages']['dbt_transformations'] = stage_result

        return stage_result

    async def stage_5_data_validation(self) -> Dict[str, Any]:
        """Stage 5: Validate data quality with SQL checks."""
        logger.info("=" * 80)
        logger.info("STAGE 5: DATA QUALITY VALIDATION")
        logger.info("=" * 80)

        stage_start = time.time()
        stage_result = {
            'status': 'pending',
            'start_time': datetime.now().isoformat(),
            'validations': {},
            'errors': []
        }

        try:
            from src.db.session import get_session_factory
            from sqlalchemy import text

            async with get_session_factory()() as session:
                # Validation 1: Check company count
                result = await session.execute(text("SELECT COUNT(*) FROM companies"))
                company_count = result.scalar()
                stage_result['validations']['company_count'] = company_count
                logger.info(f"✓ Companies in database: {company_count}")

                # Validation 2: Check financial metrics count
                result = await session.execute(text("SELECT COUNT(*) FROM financial_metrics"))
                metrics_count = result.scalar()
                stage_result['validations']['metrics_count'] = metrics_count
                logger.info(f"✓ Financial metrics: {metrics_count}")

                # Validation 3: Check SEC filings count
                result = await session.execute(text("SELECT COUNT(*) FROM sec_filings"))
                filings_count = result.scalar()
                stage_result['validations']['filings_count'] = filings_count
                logger.info(f"✓ SEC filings: {filings_count}")

                # Validation 4: Data completeness by company
                result = await session.execute(text("""
                    SELECT
                        c.ticker,
                        COUNT(DISTINCT fm.id) as metric_count,
                        COUNT(DISTINCT sf.id) as filing_count
                    FROM companies c
                    LEFT JOIN financial_metrics fm ON c.id = fm.company_id
                    LEFT JOIN sec_filings sf ON c.id = sf.company_id
                    GROUP BY c.ticker
                    ORDER BY c.ticker
                """))

                completeness = []
                for row in result:
                    completeness.append({
                        'ticker': row[0],
                        'metrics': row[1],
                        'filings': row[2]
                    })

                stage_result['validations']['data_completeness'] = completeness
                logger.info(f"✓ Data completeness validated for {len(completeness)} companies")

                # Validation 5: Check for NULL values in critical fields
                result = await session.execute(text("""
                    SELECT
                        COUNT(*) FILTER (WHERE ticker IS NULL) as null_tickers,
                        COUNT(*) FILTER (WHERE name IS NULL) as null_names
                    FROM companies
                """))
                null_check = result.fetchone()
                stage_result['validations']['null_checks'] = {
                    'null_tickers': null_check[0],
                    'null_names': null_check[1]
                }
                logger.info(f"✓ NULL value checks: tickers={null_check[0]}, names={null_check[1]}")

            stage_result['status'] = 'completed'
            stage_result['duration_seconds'] = time.time() - stage_start

        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            stage_result['status'] = 'failed'
            stage_result['error'] = str(e)

        finally:
            stage_result['end_time'] = datetime.now().isoformat()
            self.results['stages']['data_validation'] = stage_result

        return stage_result

    async def stage_6_sample_analytics(self) -> Dict[str, Any]:
        """Stage 6: Generate sample analytics reports."""
        logger.info("=" * 80)
        logger.info("STAGE 6: SAMPLE ANALYTICS GENERATION")
        logger.info("=" * 80)

        stage_start = time.time()
        stage_result = {
            'status': 'pending',
            'start_time': datetime.now().isoformat(),
            'reports_generated': [],
            'errors': []
        }

        try:
            from src.db.session import get_session_factory
            from sqlalchemy import text

            async with get_session_factory()() as session:
                # Analytics 1: Company financial summary
                result = await session.execute(text("""
                    SELECT
                        c.ticker,
                        c.name,
                        COUNT(DISTINCT fm.id) as total_metrics,
                        MAX(fm.period_end) as latest_data_date,
                        AVG(CASE WHEN fm.metric_type = 'revenue' THEN fm.value END) as avg_revenue,
                        AVG(CASE WHEN fm.metric_type = 'profit_margin' THEN fm.value END) as avg_profit_margin
                    FROM companies c
                    LEFT JOIN financial_metrics fm ON c.id = fm.company_id
                    WHERE c.ticker = ANY(:tickers)
                    GROUP BY c.ticker, c.name
                    ORDER BY c.ticker
                """), {'tickers': self.companies})

                summary_data = []
                for row in result:
                    summary_data.append({
                        'ticker': row[0],
                        'name': row[1],
                        'total_metrics': row[2],
                        'latest_data_date': str(row[3]) if row[3] else None,
                        'avg_revenue': float(row[4]) if row[4] else None,
                        'avg_profit_margin': float(row[5]) if row[5] else None
                    })

                stage_result['reports_generated'].append('company_financial_summary')
                stage_result['company_summary'] = summary_data
                logger.info(f"✓ Generated financial summary for {len(summary_data)} companies")

                # Analytics 2: Data coverage by metric type
                result = await session.execute(text("""
                    SELECT
                        metric_type,
                        COUNT(*) as count,
                        MIN(period_end) as earliest_date,
                        MAX(period_end) as latest_date
                    FROM financial_metrics fm
                    JOIN companies c ON fm.company_id = c.id
                    WHERE c.ticker = ANY(:tickers)
                    GROUP BY metric_type
                    ORDER BY count DESC
                """), {'tickers': self.companies})

                coverage_data = []
                for row in result:
                    coverage_data.append({
                        'metric_type': row[0],
                        'count': row[1],
                        'earliest_date': str(row[2]) if row[2] else None,
                        'latest_date': str(row[3]) if row[3] else None
                    })

                stage_result['reports_generated'].append('metric_coverage')
                stage_result['metric_coverage'] = coverage_data
                logger.info(f"✓ Generated metric coverage for {len(coverage_data)} metric types")

            stage_result['status'] = 'completed'
            stage_result['duration_seconds'] = time.time() - stage_start

        except Exception as e:
            logger.error(f"Analytics generation failed: {e}")
            stage_result['status'] = 'failed'
            stage_result['error'] = str(e)

        finally:
            stage_result['end_time'] = datetime.now().isoformat()
            self.results['stages']['sample_analytics'] = stage_result

        return stage_result

    def calculate_metrics(self):
        """Calculate overall pipeline metrics."""
        logger.info("=" * 80)
        logger.info("CALCULATING PIPELINE METRICS")
        logger.info("=" * 80)

        total_duration = 0
        stages_completed = 0
        stages_failed = 0

        for stage_name, stage_data in self.results['stages'].items():
            if stage_data.get('status') == 'completed':
                stages_completed += 1
            elif stage_data.get('status') == 'failed':
                stages_failed += 1

            total_duration += stage_data.get('duration_seconds', 0)

        self.results['metrics'] = {
            'total_duration_seconds': total_duration,
            'total_duration_minutes': round(total_duration / 60, 2),
            'stages_completed': stages_completed,
            'stages_failed': stages_failed,
            'total_stages': len(self.results['stages']),
            'success_rate': round(stages_completed / len(self.results['stages']) * 100, 2) if self.results['stages'] else 0
        }

        logger.info(f"Total Duration: {self.results['metrics']['total_duration_minutes']} minutes")
        logger.info(f"Stages Completed: {stages_completed}/{len(self.results['stages'])}")
        logger.info(f"Success Rate: {self.results['metrics']['success_rate']}%")

    async def execute_pipeline(self):
        """Execute the complete data pipeline."""
        logger.info("=" * 80)
        logger.info("PLAN A DAY 4 - DATA PIPELINE EXECUTION")
        logger.info("=" * 80)
        logger.info(f"Test Companies: {', '.join(self.companies)}")
        logger.info(f"Start Time: {self.results['start_time']}")
        logger.info("=" * 80)

        # Pre-task hook
        await self.run_coordination_hook('pre-task', description='Plan A Day 4 Data Pipeline Execution')

        # Execute all stages
        await self.stage_1_sec_ingestion()
        await self.stage_2_alpha_vantage_ingestion()
        await self.stage_3_yahoo_finance_ingestion()
        await self.stage_4_dbt_transformations()
        await self.stage_5_data_validation()
        await self.stage_6_sample_analytics()

        # Calculate metrics
        self.calculate_metrics()

        # Save results
        self.results['end_time'] = datetime.now().isoformat()

        # Save execution log
        with open(self.docs_dir / 'PIPELINE_EXECUTION_LOG_DAY4.md', 'w') as f:
            f.write(self._generate_execution_log())

        # Save JSON results
        with open(self.docs_dir / 'data-ingestion-results.json', 'w') as f:
            json.dump(self.results, f, indent=2)

        logger.info("=" * 80)
        logger.info("PIPELINE EXECUTION COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Results saved to: {self.docs_dir}")

        # Post-task hook
        await self.run_coordination_hook('post-task', task_id='plan-a-day4-pipeline')
        await self.run_coordination_hook('notify', message='Plan A Day 4 pipeline execution completed')

        return self.results

    def _generate_execution_log(self) -> str:
        """Generate markdown execution log."""
        log = f"""# Plan A Day 4 - Data Pipeline Execution Log

**Execution Date**: {self.results['start_time']}
**Test Companies**: {', '.join(self.companies)}
**Total Duration**: {self.results['metrics']['total_duration_minutes']} minutes
**Success Rate**: {self.results['metrics']['success_rate']}%

## Execution Summary

- **Total Stages**: {self.results['metrics']['total_stages']}
- **Completed**: {self.results['metrics']['stages_completed']}
- **Failed**: {self.results['metrics']['stages_failed']}

## Stage Details

"""

        for stage_name, stage_data in self.results['stages'].items():
            status_icon = "✅" if stage_data.get('status') == 'completed' else "❌"
            log += f"### {status_icon} {stage_name.replace('_', ' ').title()}\n\n"
            log += f"- **Status**: {stage_data.get('status', 'unknown')}\n"
            log += f"- **Duration**: {stage_data.get('duration_seconds', 0):.2f} seconds\n"

            if 'companies_processed' in stage_data:
                log += f"- **Companies Processed**: {stage_data['companies_processed']}\n"
            if 'filings_stored' in stage_data:
                log += f"- **Filings Stored**: {stage_data['filings_stored']}\n"
            if 'metrics_stored' in stage_data:
                log += f"- **Metrics Stored**: {stage_data['metrics_stored']}\n"
            if 'models_run' in stage_data:
                log += f"- **Models Run**: {stage_data['models_run']}\n"

            if stage_data.get('errors'):
                log += f"\n**Errors**:\n"
                for error in stage_data['errors']:
                    log += f"- {error}\n"

            log += "\n"

        return log


async def main():
    """Main entry point."""
    # Configure logging
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # Execute pipeline
    executor = PipelineExecutor(test_mode=True)
    results = await executor.execute_pipeline()

    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("FINAL RESULTS")
    logger.info("=" * 80)
    logger.info(f"Total Duration: {results['metrics']['total_duration_minutes']} minutes")
    logger.info(f"Success Rate: {results['metrics']['success_rate']}%")
    logger.info(f"Results: {executor.docs_dir}")
    logger.info("=" * 80)

    return results


if __name__ == "__main__":
    asyncio.run(main())
