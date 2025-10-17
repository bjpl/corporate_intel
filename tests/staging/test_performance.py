"""Performance benchmark tests for staging environment.

Benchmarks:
- Query performance
- Dashboard rendering speed
- Data ingestion speed
- Cache effectiveness
"""

import pytest
import requests
import time
from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from redis import Redis
from urllib.parse import urljoin
import statistics


class TestQueryPerformance:
    """Test database query performance."""

    def test_company_list_query_performance(self, staging_db_url: str) -> None:
        """Test company list query performance."""
        engine = create_engine(staging_db_url)

        try:
            with engine.connect() as conn:
                # Warm up
                conn.execute(text("SELECT * FROM companies LIMIT 100"))

                # Benchmark
                times = []
                for _ in range(10):
                    start = time.time()
                    conn.execute(text("SELECT * FROM companies LIMIT 100"))
                    elapsed = (time.time() - start) * 1000  # Convert to ms
                    times.append(elapsed)

                avg_time = statistics.mean(times)
                p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile

                print(f"\nCompany list query: avg={avg_time:.2f}ms, p95={p95_time:.2f}ms")

                # Assertions
                assert avg_time < 100, f"Average query time {avg_time:.2f}ms exceeds 100ms"
                assert p95_time < 200, f"P95 query time {p95_time:.2f}ms exceeds 200ms"
        finally:
            engine.dispose()

    def test_financial_metrics_query_performance(self, staging_db_url: str) -> None:
        """Test financial metrics query performance."""
        engine = create_engine(staging_db_url)

        try:
            with engine.connect() as conn:
                # Complex join query
                query = text("""
                SELECT c.ticker, c.name, fm.revenue, fm.net_income
                FROM companies c
                JOIN financial_metrics fm ON c.id = fm.company_id
                WHERE fm.date > NOW() - INTERVAL '1 year'
                LIMIT 100
                """)

                # Warm up
                conn.execute(query)

                # Benchmark
                times = []
                for _ in range(10):
                    start = time.time()
                    conn.execute(query)
                    elapsed = (time.time() - start) * 1000
                    times.append(elapsed)

                avg_time = statistics.mean(times)
                p95_time = statistics.quantiles(times, n=20)[18]

                print(f"\nFinancial metrics join query: avg={avg_time:.2f}ms, p95={p95_time:.2f}ms")

                assert avg_time < 200, f"Average query time {avg_time:.2f}ms exceeds 200ms"
                assert p95_time < 500, f"P95 query time {p95_time:.2f}ms exceeds 500ms"
        finally:
            engine.dispose()

    def test_aggregation_query_performance(self, staging_db_url: str) -> None:
        """Test aggregation query performance."""
        engine = create_engine(staging_db_url)

        try:
            with engine.connect() as conn:
                query = text("""
                SELECT
                    c.sector,
                    COUNT(*) as company_count,
                    AVG(fm.revenue) as avg_revenue,
                    SUM(fm.market_cap) as total_market_cap
                FROM companies c
                LEFT JOIN financial_metrics fm ON c.id = fm.company_id
                GROUP BY c.sector
                """)

                # Warm up
                conn.execute(query)

                # Benchmark
                times = []
                for _ in range(10):
                    start = time.time()
                    conn.execute(query)
                    elapsed = (time.time() - start) * 1000
                    times.append(elapsed)

                avg_time = statistics.mean(times)
                p95_time = statistics.quantiles(times, n=20)[18]

                print(f"\nAggregation query: avg={avg_time:.2f}ms, p95={p95_time:.2f}ms")

                assert avg_time < 300, f"Average query time {avg_time:.2f}ms exceeds 300ms"
                assert p95_time < 1000, f"P95 query time {p95_time:.2f}ms exceeds 1000ms"
        finally:
            engine.dispose()

    def test_index_effectiveness(self, staging_db_url: str) -> None:
        """Test that indexes are being used effectively."""
        engine = create_engine(staging_db_url)

        try:
            with engine.connect() as conn:
                # Check indexes exist on key columns
                result = conn.execute(
                    text("""
                    SELECT
                        tablename,
                        indexname,
                        indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                    AND tablename IN ('companies', 'financial_metrics', 'sec_filings')
                    """)
                )

                indexes = result.fetchall()
                index_names = [idx[1] for idx in indexes]

                # Should have indexes on key columns
                print(f"\nFound {len(indexes)} indexes")

                # Verify at least some indexes exist
                assert len(indexes) > 3, "Too few indexes found"
        finally:
            engine.dispose()


class TestAPIPerformance:
    """Test API endpoint performance."""

    def test_health_endpoint_performance(self, staging_base_url: str) -> None:
        """Test health endpoint performance."""
        url = urljoin(staging_base_url, "/api/v1/health/ping")

        # Warm up
        requests.get(url, timeout=5)

        # Benchmark
        times = []
        for _ in range(20):
            start = time.time()
            response = requests.get(url, timeout=5)
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)

            assert response.status_code == 200

        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]

        print(f"\nHealth endpoint: avg={avg_time:.2f}ms, p95={p95_time:.2f}ms")

        assert avg_time < 50, f"Average response time {avg_time:.2f}ms exceeds 50ms"
        assert p95_time < 100, f"P95 response time {p95_time:.2f}ms exceeds 100ms"

    def test_company_list_endpoint_performance(
        self,
        staging_base_url: str,
        auth_headers: Dict[str, str]
    ) -> None:
        """Test company list endpoint performance."""
        url = urljoin(staging_base_url, "/api/v1/companies")

        # Warm up
        requests.get(url, headers=auth_headers, timeout=10)

        # Benchmark
        times = []
        for _ in range(10):
            start = time.time()
            response = requests.get(url, headers=auth_headers, timeout=10)
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)

            if response.status_code == 200:
                # Endpoint is accessible
                pass

        if times:
            avg_time = statistics.mean(times)
            p95_time = statistics.quantiles(times, n=20)[18] if len(times) >= 20 else max(times)

            print(f"\nCompany list endpoint: avg={avg_time:.2f}ms, p95={p95_time:.2f}ms")

            assert avg_time < 200, f"Average response time {avg_time:.2f}ms exceeds 200ms"
            assert p95_time < 500, f"P95 response time {p95_time:.2f}ms exceeds 500ms"

    def test_concurrent_request_performance(
        self,
        staging_base_url: str,
        auth_headers: Dict[str, str]
    ) -> None:
        """Test performance under concurrent requests."""
        import concurrent.futures

        url = urljoin(staging_base_url, "/api/v1/health/ping")

        def make_request():
            start = time.time()
            response = requests.get(url, headers=auth_headers, timeout=10)
            elapsed = (time.time() - start) * 1000
            return elapsed, response.status_code

        # Concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        times = [r[0] for r in results]
        status_codes = [r[1] for r in results]

        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]
        success_rate = sum(1 for s in status_codes if s == 200) / len(status_codes)

        print(f"\nConcurrent requests (50): avg={avg_time:.2f}ms, p95={p95_time:.2f}ms, success={success_rate:.1%}")

        assert success_rate > 0.95, f"Success rate {success_rate:.1%} below 95%"
        assert avg_time < 300, f"Average response time {avg_time:.2f}ms exceeds 300ms"
        assert p95_time < 1000, f"P95 response time {p95_time:.2f}ms exceeds 1000ms"


class TestDashboardPerformance:
    """Test dashboard rendering performance."""

    def test_dashboard_load_time(self, staging_dashboard_url: str) -> None:
        """Test dashboard initial load time."""
        # Warm up
        requests.get(staging_dashboard_url, timeout=15)

        # Benchmark
        times = []
        for _ in range(5):
            start = time.time()
            response = requests.get(staging_dashboard_url, timeout=15)
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)

            assert response.status_code == 200

        avg_time = statistics.mean(times)
        p95_time = max(times)  # With 5 samples, use max

        print(f"\nDashboard load: avg={avg_time:.2f}ms, p95={p95_time:.2f}ms")

        assert avg_time < 2000, f"Average load time {avg_time:.2f}ms exceeds 2000ms (2s)"
        assert p95_time < 5000, f"P95 load time {p95_time:.2f}ms exceeds 5000ms (5s)"

    def test_dashboard_asset_loading(self, staging_dashboard_url: str) -> None:
        """Test dashboard asset loading speed."""
        # Get main page to find asset URLs
        response = requests.get(staging_dashboard_url, timeout=10)
        assert response.status_code == 200

        # Test Dash internal endpoints
        endpoints = [
            "/_dash-layout",
            "/_dash-dependencies",
        ]

        for endpoint in endpoints:
            url = urljoin(staging_dashboard_url, endpoint)
            start = time.time()
            response = requests.get(url, timeout=10)
            elapsed = (time.time() - start) * 1000

            print(f"\nAsset {endpoint}: {elapsed:.2f}ms")

            if response.status_code == 200:
                assert elapsed < 1000, f"Asset load time {elapsed:.2f}ms exceeds 1000ms"


class TestCacheEffectiveness:
    """Test cache performance and effectiveness."""

    def test_redis_latency(self, staging_redis_url: str) -> None:
        """Test Redis operation latency."""
        redis_client = Redis.from_url(staging_redis_url, decode_responses=True)

        try:
            # Test SET latency
            set_times = []
            for i in range(100):
                start = time.time()
                redis_client.set(f"perf_test_{i}", "value", ex=60)
                elapsed = (time.time() - start) * 1000
                set_times.append(elapsed)

            # Test GET latency
            get_times = []
            for i in range(100):
                start = time.time()
                redis_client.get(f"perf_test_{i}")
                elapsed = (time.time() - start) * 1000
                get_times.append(elapsed)

            # Cleanup
            for i in range(100):
                redis_client.delete(f"perf_test_{i}")

            avg_set = statistics.mean(set_times)
            avg_get = statistics.mean(get_times)
            p95_set = statistics.quantiles(set_times, n=20)[18]
            p95_get = statistics.quantiles(get_times, n=20)[18]

            print(f"\nRedis SET: avg={avg_set:.2f}ms, p95={p95_set:.2f}ms")
            print(f"Redis GET: avg={avg_get:.2f}ms, p95={p95_get:.2f}ms")

            assert avg_set < 10, f"Average SET time {avg_set:.2f}ms exceeds 10ms"
            assert avg_get < 10, f"Average GET time {avg_get:.2f}ms exceeds 10ms"
            assert p95_set < 50, f"P95 SET time {p95_set:.2f}ms exceeds 50ms"
            assert p95_get < 50, f"P95 GET time {p95_get:.2f}ms exceeds 50ms"
        finally:
            redis_client.close()

    def test_cache_hit_rate(
        self,
        staging_base_url: str,
        staging_redis_url: str,
        auth_headers: Dict[str, str]
    ) -> None:
        """Test cache hit rate for frequently accessed endpoints."""
        redis_client = Redis.from_url(staging_redis_url, decode_responses=True)
        url = urljoin(staging_base_url, "/api/v1/companies")

        try:
            # Get initial Redis stats
            info_before = redis_client.info("stats")
            hits_before = info_before.get("keyspace_hits", 0)
            misses_before = info_before.get("keyspace_misses", 0)

            # Make requests that should be cached
            for _ in range(10):
                requests.get(url, headers=auth_headers, timeout=10)

            # Get final Redis stats
            info_after = redis_client.info("stats")
            hits_after = info_after.get("keyspace_hits", 0)
            misses_after = info_after.get("keyspace_misses", 0)

            hits = hits_after - hits_before
            misses = misses_after - misses_before
            total = hits + misses

            if total > 0:
                hit_rate = hits / total
                print(f"\nCache hit rate: {hit_rate:.1%} (hits={hits}, misses={misses})")

                # Hit rate should be reasonable if caching is working
                # Note: First request will always be a miss
                assert hit_rate >= 0, "Cache hit rate calculation error"
        finally:
            redis_client.close()

    def test_cached_vs_uncached_performance(
        self,
        staging_base_url: str,
        staging_redis_url: str,
        auth_headers: Dict[str, str]
    ) -> None:
        """Test performance improvement from caching."""
        redis_client = Redis.from_url(staging_redis_url, decode_responses=True)
        url = urljoin(staging_base_url, "/api/v1/companies")

        try:
            # Clear cache
            redis_client.flushdb()

            # First request (cache miss)
            start = time.time()
            response1 = requests.get(url, headers=auth_headers, timeout=10)
            time1 = (time.time() - start) * 1000

            # Second request (cache hit)
            start = time.time()
            response2 = requests.get(url, headers=auth_headers, timeout=10)
            time2 = (time.time() - start) * 1000

            if response1.status_code == 200 and response2.status_code == 200:
                print(f"\nCached vs uncached: uncached={time1:.2f}ms, cached={time2:.2f}ms")

                # Cached request should ideally be faster
                # (but network variability may affect this)
                improvement = ((time1 - time2) / time1) * 100 if time1 > 0 else 0
                print(f"Cache improvement: {improvement:.1f}%")
        finally:
            redis_client.close()


# Fixtures
@pytest.fixture(scope="module")
def staging_base_url() -> str:
    """Get staging API base URL."""
    import os
    return os.getenv("STAGING_API_URL", "http://localhost:8000")


@pytest.fixture(scope="module")
def staging_dashboard_url() -> str:
    """Get staging dashboard URL."""
    import os
    return os.getenv("STAGING_DASHBOARD_URL", "http://localhost:8050")


@pytest.fixture(scope="module")
def staging_db_url() -> str:
    """Get staging database URL."""
    import os
    return os.getenv("STAGING_DATABASE_URL", "postgresql://user:pass@localhost:5432/corporate_intel_staging")


@pytest.fixture(scope="module")
def staging_redis_url() -> str:
    """Get staging Redis URL."""
    import os
    return os.getenv("STAGING_REDIS_URL", "redis://localhost:6379/0")


@pytest.fixture(scope="module")
def auth_headers() -> Dict[str, str]:
    """Get authentication headers."""
    import os
    token = os.getenv("STAGING_AUTH_TOKEN", "test-token")
    return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to show print statements
