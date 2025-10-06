"""
Database Load Testing Suite
Tests performance with applied indexes on corporate_intel database
"""

import asyncio
import asyncpg
import time
import statistics
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import json

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 5434,
    'user': 'intel_user',
    'password': 'lsZXGgU92KhK5VqR',
    'database': 'corporate_intel'
}

class LoadTestResults:
    """Store and analyze load test results"""

    def __init__(self):
        self.query_times: List[float] = []
        self.query_results: List[Dict] = []
        self.errors: List[str] = []
        self.index_usage: Dict[str, bool] = {}

    def add_query(self, query_name: str, duration: float, success: bool, error: str = None):
        """Record a query execution"""
        self.query_times.append(duration)
        self.query_results.append({
            'query': query_name,
            'duration_ms': duration * 1000,
            'success': success,
            'error': error,
            'timestamp': datetime.now().isoformat()
        })
        if error:
            self.errors.append(f"{query_name}: {error}")

    def get_stats(self) -> Dict:
        """Calculate performance statistics"""
        if not self.query_times:
            return {}

        sorted_times = sorted(self.query_times)
        return {
            'total_queries': len(self.query_times),
            'successful_queries': len([r for r in self.query_results if r['success']]),
            'failed_queries': len(self.errors),
            'avg_response_time_ms': statistics.mean(self.query_times) * 1000,
            'median_response_time_ms': statistics.median(self.query_times) * 1000,
            'min_response_time_ms': min(self.query_times) * 1000,
            'max_response_time_ms': max(self.query_times) * 1000,
            'p95_response_time_ms': sorted_times[int(len(sorted_times) * 0.95)] * 1000,
            'p99_response_time_ms': sorted_times[int(len(sorted_times) * 0.99)] * 1000,
            'throughput_qps': len(self.query_times) / sum(self.query_times) if sum(self.query_times) > 0 else 0
        }

class DatabaseLoadTester:
    """Comprehensive database load testing"""

    def __init__(self):
        self.pool = None
        self.results = LoadTestResults()

    async def initialize(self):
        """Initialize database connection pool"""
        self.pool = await asyncpg.create_pool(
            **DB_CONFIG,
            min_size=5,
            max_size=20,
            command_timeout=60
        )
        print("✓ Database connection pool initialized")

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            print("✓ Database connection pool closed")

    async def execute_timed_query(self, query: str, query_name: str, params: list = None) -> Tuple[float, any]:
        """Execute a query and measure execution time"""
        start_time = time.time()
        try:
            async with self.pool.acquire() as conn:
                if params:
                    result = await conn.fetch(query, *params)
                else:
                    result = await conn.fetch(query)
            duration = time.time() - start_time
            self.results.add_query(query_name, duration, True)
            return duration, result
        except Exception as e:
            duration = time.time() - start_time
            self.results.add_query(query_name, duration, False, str(e))
            return duration, None

    async def explain_analyze_query(self, query: str, query_name: str) -> Dict:
        """Run EXPLAIN ANALYZE to verify index usage"""
        explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
        try:
            async with self.pool.acquire() as conn:
                result = await conn.fetchval(explain_query)
                return {
                    'query_name': query_name,
                    'plan': result[0],
                    'uses_index': self._check_index_usage(result[0])
                }
        except Exception as e:
            return {
                'query_name': query_name,
                'error': str(e),
                'uses_index': False
            }

    def _check_index_usage(self, plan: Dict) -> bool:
        """Check if query plan uses index scan"""
        plan_str = json.dumps(plan).lower()
        return ('index scan' in plan_str or
                'index only scan' in plan_str or
                'bitmap index scan' in plan_str)

    # Benchmark Query Suite
    async def benchmark_ticker_lookup(self):
        """Test ticker lookup with idx_companies_ticker"""
        query = "SELECT * FROM companies WHERE ticker = $1"
        tickers = ['CHGG', 'AAPL', 'MSFT', 'GOOGL', 'AMZN']

        for ticker in tickers:
            await self.execute_timed_query(
                query,
                f"ticker_lookup_{ticker}",
                [ticker]
            )

    async def benchmark_category_filter(self):
        """Test category filter with idx_companies_category"""
        query = "SELECT * FROM companies WHERE category = $1"
        categories = ['edtech', 'technology', 'finance']

        for category in categories:
            await self.execute_timed_query(
                query,
                f"category_filter_{category}",
                [category]
            )

    async def benchmark_company_search(self):
        """Test company name search with idx_companies_name_trgm"""
        query = "SELECT * FROM companies WHERE name ILIKE $1 LIMIT 20"
        searches = ['%Chegg%', '%Apple%', '%Microsoft%', '%Google%', '%Amazon%']

        for search in searches:
            await self.execute_timed_query(
                query,
                f"company_search_{search[:10]}",
                [search]
            )

    async def benchmark_financial_metrics(self):
        """Test financial metrics with compound index"""
        query = """
        SELECT c.ticker, c.name, fm.*
        FROM companies c
        JOIN financial_metrics fm ON c.company_id = fm.company_id
        WHERE c.ticker = $1
        AND fm.report_date >= $2
        ORDER BY fm.report_date DESC
        LIMIT 10
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        tickers = ['CHGG', 'AAPL', 'MSFT']
        for ticker in tickers:
            await self.execute_timed_query(
                query,
                f"financial_metrics_{ticker}",
                [ticker, start_date]
            )

    async def benchmark_sec_filings(self):
        """Test SEC filings date range query"""
        query = """
        SELECT c.ticker, s.*
        FROM companies c
        JOIN sec_filings s ON c.company_id = s.company_id
        WHERE s.filing_date >= $1
        AND s.filing_date <= $2
        AND s.form_type = $3
        ORDER BY s.filing_date DESC
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        await self.execute_timed_query(
            query,
            "sec_filings_10Q",
            [start_date, end_date, '10-Q']
        )

    async def benchmark_earnings_analysis(self):
        """Test earnings analysis with time-series data"""
        query = """
        SELECT
            c.ticker,
            e.earnings_date,
            e.eps_estimate,
            e.eps_actual,
            e.revenue_estimate,
            e.revenue_actual
        FROM companies c
        JOIN earnings_calls e ON c.company_id = e.company_id
        WHERE c.ticker = $1
        AND e.earnings_date >= $2
        ORDER BY e.earnings_date DESC
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)  # 2 years

        await self.execute_timed_query(
            query,
            "earnings_analysis_CHGG",
            ['CHGG', start_date]
        )

    async def benchmark_complex_join(self):
        """Test complex multi-table join"""
        query = """
        SELECT
            c.ticker,
            c.name,
            c.category,
            COUNT(DISTINCT s.filing_id) as filing_count,
            COUNT(DISTINCT e.earnings_id) as earnings_count,
            AVG(fm.revenue) as avg_revenue,
            MAX(fm.report_date) as latest_report
        FROM companies c
        LEFT JOIN sec_filings s ON c.company_id = s.company_id
        LEFT JOIN earnings_calls e ON c.company_id = e.company_id
        LEFT JOIN financial_metrics fm ON c.company_id = fm.company_id
        WHERE c.category = $1
        GROUP BY c.ticker, c.name, c.category
        HAVING COUNT(DISTINCT s.filing_id) > 0
        """

        await self.execute_timed_query(
            query,
            "complex_join_edtech",
            ['edtech']
        )

    async def run_concurrent_load_test(self, num_users: int = 10, queries_per_user: int = 100):
        """Simulate concurrent users executing queries"""
        print(f"\n🔄 Running concurrent load test: {num_users} users, {queries_per_user} queries each...")

        async def user_workload(user_id: int):
            """Simulate single user workload"""
            queries = [
                ("SELECT * FROM companies WHERE ticker = 'CHGG'", f"user_{user_id}_ticker"),
                ("SELECT * FROM companies WHERE category = 'edtech' LIMIT 10", f"user_{user_id}_category"),
                ("SELECT COUNT(*) FROM sec_filings WHERE filing_date >= CURRENT_DATE - INTERVAL '30 days'", f"user_{user_id}_count"),
            ]

            for i in range(queries_per_user):
                query, name = queries[i % len(queries)]
                await self.execute_timed_query(query, f"{name}_{i}")

        # Run all users concurrently
        start_time = time.time()
        tasks = [user_workload(i) for i in range(num_users)]
        await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        print(f"✓ Concurrent load test completed in {total_time:.2f}s")
        return total_time

    async def verify_index_usage(self):
        """Verify that indexes are being used by query planner"""
        print("\n📊 Verifying index usage with EXPLAIN ANALYZE...")

        test_queries = [
            ("SELECT * FROM companies WHERE ticker = 'CHGG'", "ticker_index"),
            ("SELECT * FROM companies WHERE category = 'edtech'", "category_index"),
            ("SELECT * FROM companies WHERE name ILIKE '%Chegg%'", "name_trigram_index"),
            ("""
                SELECT c.*, fm.*
                FROM companies c
                JOIN financial_metrics fm ON c.company_id = fm.company_id
                WHERE c.ticker = 'CHGG'
            """, "join_with_indexes"),
            ("""
                SELECT * FROM sec_filings
                WHERE filing_date >= CURRENT_DATE - INTERVAL '90 days'
                AND form_type = '10-Q'
            """, "sec_filings_composite_index")
        ]

        index_reports = []
        for query, name in test_queries:
            report = await self.explain_analyze_query(query, name)
            index_reports.append(report)
            uses_index = report.get('uses_index', False)
            status = "✓ USING INDEX" if uses_index else "✗ NOT USING INDEX"
            print(f"  {status}: {name}")

        return index_reports

    async def get_database_stats(self):
        """Get database performance statistics"""
        stats_query = """
        SELECT
            schemaname,
            tablename,
            indexname,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch
        FROM pg_stat_user_indexes
        WHERE schemaname = 'public'
        ORDER BY idx_scan DESC
        """

        cache_query = """
        SELECT
            sum(heap_blks_read) as heap_read,
            sum(heap_blks_hit) as heap_hit,
            sum(idx_blks_read) as idx_read,
            sum(idx_blks_hit) as idx_hit,
            CASE
                WHEN sum(heap_blks_hit) + sum(heap_blks_read) = 0 THEN 0
                ELSE round(100.0 * sum(heap_blks_hit) /
                    nullif(sum(heap_blks_hit) + sum(heap_blks_read), 0), 2)
            END as heap_hit_ratio,
            CASE
                WHEN sum(idx_blks_hit) + sum(idx_blks_read) = 0 THEN 0
                ELSE round(100.0 * sum(idx_blks_hit) /
                    nullif(sum(idx_blks_hit) + sum(idx_blks_read), 0), 2)
            END as index_hit_ratio
        FROM pg_statio_user_tables
        """

        async with self.pool.acquire() as conn:
            index_stats = await conn.fetch(stats_query)
            cache_stats = await conn.fetchrow(cache_query)

        return {
            'index_usage': [dict(row) for row in index_stats],
            'cache_performance': dict(cache_stats) if cache_stats else {}
        }

    async def run_full_benchmark(self):
        """Run complete benchmark suite"""
        print("\n" + "="*70)
        print("DATABASE LOAD TESTING - WITH APPLIED INDEXES")
        print("="*70)

        await self.initialize()

        # 1. Run individual query benchmarks
        print("\n📊 Phase 1: Individual Query Benchmarks")
        print("-" * 70)

        benchmarks = [
            ("Ticker Lookups", self.benchmark_ticker_lookup),
            ("Category Filters", self.benchmark_category_filter),
            ("Company Search", self.benchmark_company_search),
            ("Financial Metrics", self.benchmark_financial_metrics),
            ("SEC Filings", self.benchmark_sec_filings),
            ("Earnings Analysis", self.benchmark_earnings_analysis),
            ("Complex Joins", self.benchmark_complex_join),
        ]

        for name, benchmark_func in benchmarks:
            print(f"\n  Running: {name}...")
            await benchmark_func()
            print(f"  ✓ Completed: {name}")

        # 2. Concurrent load test
        print("\n📊 Phase 2: Concurrent Load Test")
        print("-" * 70)
        concurrent_time = await self.run_concurrent_load_test(num_users=10, queries_per_user=100)

        # 3. Verify index usage
        print("\n📊 Phase 3: Index Usage Verification")
        print("-" * 70)
        index_reports = await self.verify_index_usage()

        # 4. Get database statistics
        print("\n📊 Phase 4: Database Statistics")
        print("-" * 70)
        db_stats = await self.get_database_stats()

        # Generate final report
        print("\n" + "="*70)
        print("LOAD TEST RESULTS")
        print("="*70)

        stats = self.results.get_stats()

        print(f"\n✓ Total Queries Executed: {stats.get('total_queries', 0)}")
        print(f"✓ Successful Queries: {stats.get('successful_queries', 0)}")
        print(f"✗ Failed Queries: {stats.get('failed_queries', 0)}")
        print(f"\n⏱️  Average Response Time: {stats.get('avg_response_time_ms', 0):.2f} ms")
        print(f"⏱️  Median Response Time: {stats.get('median_response_time_ms', 0):.2f} ms")
        print(f"⏱️  P95 Response Time: {stats.get('p95_response_time_ms', 0):.2f} ms")
        print(f"⏱️  P99 Response Time: {stats.get('p99_response_time_ms', 0):.2f} ms")
        print(f"⏱️  Min Response Time: {stats.get('min_response_time_ms', 0):.2f} ms")
        print(f"⏱️  Max Response Time: {stats.get('max_response_time_ms', 0):.2f} ms")
        print(f"\n🚀 Throughput: {stats.get('throughput_qps', 0):.2f} queries/second")
        print(f"🚀 Concurrent Load Test Duration: {concurrent_time:.2f} seconds")

        # Cache performance
        cache_perf = db_stats.get('cache_performance', {})
        print(f"\n💾 Heap Cache Hit Ratio: {cache_perf.get('heap_hit_ratio', 0):.2f}%")
        print(f"💾 Index Cache Hit Ratio: {cache_perf.get('index_hit_ratio', 0):.2f}%")

        # Index usage summary
        print(f"\n📈 Index Usage Summary:")
        index_usage = db_stats.get('index_usage', [])
        for idx in index_usage[:10]:  # Top 10 most used indexes
            print(f"  {idx['indexname']}: {idx['idx_scan']} scans")

        # Save detailed results
        report = {
            'timestamp': datetime.now().isoformat(),
            'performance_stats': stats,
            'cache_performance': cache_perf,
            'index_usage': index_usage,
            'index_verification': index_reports,
            'detailed_results': self.results.query_results,
            'errors': self.results.errors
        }

        await self.close()
        return report

async def main():
    """Main execution function"""
    tester = DatabaseLoadTester()
    report = await tester.run_full_benchmark()

    # Save report to file
    report_file = f"tests/load-testing/load_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n✓ Detailed report saved to: {report_file}")
    print("\n" + "="*70)

    # Print recommendations
    print("\n📋 RECOMMENDATIONS:")
    print("-" * 70)

    stats = report['performance_stats']
    cache = report['cache_performance']

    if stats.get('avg_response_time_ms', 0) > 100:
        print("⚠️  Average response time > 100ms - Consider query optimization")
    else:
        print("✓ Response times are within acceptable range")

    if cache.get('index_hit_ratio', 0) < 95:
        print("⚠️  Index cache hit ratio < 95% - Consider increasing shared_buffers")
    else:
        print("✓ Index cache performance is excellent")

    if stats.get('failed_queries', 0) > 0:
        print(f"⚠️  {stats['failed_queries']} queries failed - Review error log")
    else:
        print("✓ All queries executed successfully")

    # Check if indexes are being used
    index_verification = report.get('index_verification', [])
    not_using_index = [r for r in index_verification if not r.get('uses_index', False)]
    if not_using_index:
        print(f"⚠️  {len(not_using_index)} queries not using indexes:")
        for r in not_using_index:
            print(f"    - {r['query_name']}")
    else:
        print("✓ All critical queries are using indexes")

    print("\n" + "="*70)

if __name__ == "__main__":
    asyncio.run(main())
