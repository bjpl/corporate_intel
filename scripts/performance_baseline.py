#!/usr/bin/env python3
"""
Performance Baseline Measurement Script
Establishes comprehensive baseline metrics for staging environment
Part of Plan A Day 1 - Production Deployment
"""

import asyncio
import asyncpg
import aiohttp
import time
import statistics
import json
import psutil
import sys
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict


@dataclass
class PerformanceMetrics:
    """Container for performance measurements"""
    timestamp: str
    endpoint: str
    method: str
    response_time_ms: float
    status_code: int
    success: bool
    error: str = None


@dataclass
class DatabaseMetrics:
    """Container for database performance metrics"""
    timestamp: str
    query_name: str
    execution_time_ms: float
    rows_returned: int
    index_used: bool
    cache_hit: bool


@dataclass
class ResourceMetrics:
    """Container for system resource metrics"""
    timestamp: str
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_sent_mb: float
    network_recv_mb: float


class PerformanceBaseline:
    """Comprehensive performance baseline measurements"""

    def __init__(self, api_base_url: str = "http://localhost:8004", db_config: Dict = None):
        self.api_base_url = api_base_url
        self.db_config = db_config or {
            'host': 'localhost',
            'port': 5435,
            'user': 'intel_staging_user',
            'password': 'lsZXGgU92KhK5VqR',
            'database': 'corporate_intel_staging'
        }
        self.pool = None

        # Results storage
        self.api_metrics: List[PerformanceMetrics] = []
        self.db_metrics: List[DatabaseMetrics] = []
        self.resource_metrics: List[ResourceMetrics] = []

    async def initialize(self):
        """Initialize connections"""
        try:
            self.pool = await asyncpg.create_pool(
                **self.db_config,
                min_size=5,
                max_size=20,
                command_timeout=60
            )
            print("✓ Database connection pool initialized")
        except Exception as e:
            print(f"✗ Failed to initialize database pool: {e}")
            raise

    async def close(self):
        """Close connections"""
        if self.pool:
            await self.pool.close()
            print("✓ Database connection pool closed")

    # ==================== API Performance Tests ====================

    async def measure_api_endpoint(self, endpoint: str, method: str = "GET", params: Dict = None) -> PerformanceMetrics:
        """Measure API endpoint performance"""
        url = f"{self.api_base_url}{endpoint}"
        start_time = time.time()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    await response.text()
                    duration_ms = (time.time() - start_time) * 1000

                    metric = PerformanceMetrics(
                        timestamp=datetime.now().isoformat(),
                        endpoint=endpoint,
                        method=method,
                        response_time_ms=duration_ms,
                        status_code=response.status,
                        success=200 <= response.status < 300
                    )
                    self.api_metrics.append(metric)
                    return metric

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            metric = PerformanceMetrics(
                timestamp=datetime.now().isoformat(),
                endpoint=endpoint,
                method=method,
                response_time_ms=duration_ms,
                status_code=0,
                success=False,
                error=str(e)
            )
            self.api_metrics.append(metric)
            return metric

    async def benchmark_api_endpoints(self):
        """Benchmark all critical API endpoints"""
        print("\n📊 Phase 1: API Endpoint Performance")
        print("-" * 70)

        endpoints = [
            ("/health", "GET", None),
            ("/health/ping", "GET", None),
            ("/health/detailed", "GET", None),
            ("/api/v1/companies", "GET", None),
            ("/api/v1/companies/CHGG", "GET", None),
            ("/api/v1/financial/metrics", "GET", {"ticker": "CHGG"}),
            ("/api/v1/intelligence/competitive", "GET", {"sector": "edtech"}),
        ]

        for endpoint, method, params in endpoints:
            print(f"  Testing {method} {endpoint}...", end=" ")
            metric = await self.measure_api_endpoint(endpoint, method, params)

            if metric.success:
                status = "✓" if metric.response_time_ms < 100 else "⚠"
                print(f"{status} {metric.response_time_ms:.2f}ms")
            else:
                print(f"✗ FAILED: {metric.error}")

    async def benchmark_api_latency_distribution(self):
        """Measure latency distribution with repeated calls"""
        print("\n📊 Latency Distribution (100 requests to /health/ping)")
        print("-" * 70)

        latencies = []
        for i in range(100):
            metric = await self.measure_api_endpoint("/health/ping", "GET")
            if metric.success:
                latencies.append(metric.response_time_ms)

            if (i + 1) % 20 == 0:
                print(f"  Progress: {i + 1}/100 requests completed")

        if latencies:
            sorted_latencies = sorted(latencies)
            print(f"\n  Min: {min(latencies):.2f}ms")
            print(f"  Max: {max(latencies):.2f}ms")
            print(f"  Mean: {statistics.mean(latencies):.2f}ms")
            print(f"  Median: {statistics.median(latencies):.2f}ms")
            print(f"  P95: {sorted_latencies[int(len(sorted_latencies) * 0.95)]:.2f}ms")
            print(f"  P99: {sorted_latencies[int(len(sorted_latencies) * 0.99)]:.2f}ms")

    # ==================== Database Performance Tests ====================

    async def measure_db_query(self, query: str, query_name: str, params: List = None) -> DatabaseMetrics:
        """Measure database query performance"""
        start_time = time.time()

        try:
            async with self.pool.acquire() as conn:
                # Get execution plan
                explain_query = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}"
                if params:
                    plan_result = await conn.fetchval(explain_query, *params)
                else:
                    plan_result = await conn.fetchval(explain_query)

                plan = plan_result[0]
                execution_time = plan.get('Execution Time', 0)

                # Check index usage
                plan_str = json.dumps(plan).lower()
                index_used = any(x in plan_str for x in ['index scan', 'index only scan', 'bitmap index scan'])

                # Check cache hits
                cache_hit = plan.get('Shared Hit Blocks', 0) > plan.get('Shared Read Blocks', 0)

                metric = DatabaseMetrics(
                    timestamp=datetime.now().isoformat(),
                    query_name=query_name,
                    execution_time_ms=execution_time,
                    rows_returned=plan.get('Plan', {}).get('Actual Rows', 0),
                    index_used=index_used,
                    cache_hit=cache_hit
                )
                self.db_metrics.append(metric)
                return metric

        except Exception as e:
            print(f"    ✗ Query failed: {e}")
            return None

    async def benchmark_database_queries(self):
        """Benchmark critical database queries"""
        print("\n📊 Phase 2: Database Query Performance")
        print("-" * 70)

        queries = [
            ("SELECT * FROM companies WHERE ticker = $1", "ticker_lookup", ['CHGG']),
            ("SELECT * FROM companies WHERE category = $1", "category_filter", ['edtech']),
            ("SELECT * FROM companies WHERE name ILIKE $1 LIMIT 20", "name_search", ['%Chegg%']),
            ("""
                SELECT c.ticker, fm.*
                FROM companies c
                JOIN financial_metrics fm ON c.company_id = fm.company_id
                WHERE c.ticker = $1
                ORDER BY fm.report_date DESC
                LIMIT 10
            """, "financial_join", ['CHGG']),
            ("""
                SELECT c.ticker, s.*
                FROM companies c
                JOIN sec_filings s ON c.company_id = s.company_id
                WHERE s.filing_date >= CURRENT_DATE - INTERVAL '90 days'
                ORDER BY s.filing_date DESC
                LIMIT 20
            """, "sec_filings_recent", []),
        ]

        for query, name, params in queries:
            print(f"  Testing {name}...", end=" ")
            metric = await self.measure_db_query(query, name, params if params else None)

            if metric:
                index_status = "✓ INDEX" if metric.index_used else "✗ NO INDEX"
                cache_status = "CACHED" if metric.cache_hit else "DISK"
                print(f"{metric.execution_time_ms:.2f}ms ({index_status}, {cache_status})")

    async def measure_connection_pool(self):
        """Measure database connection pool performance"""
        print("\n📊 Connection Pool Metrics")
        print("-" * 70)

        pool_size = self.pool.get_size()
        free_size = self.pool.get_idle_size()

        print(f"  Pool Size: {pool_size}")
        print(f"  Idle Connections: {free_size}")
        print(f"  Active Connections: {pool_size - free_size}")

    # ==================== Resource Monitoring ====================

    def capture_resource_metrics(self) -> ResourceMetrics:
        """Capture system resource metrics"""
        cpu_percent = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()
        net_io = psutil.net_io_counters()

        metric = ResourceMetrics(
            timestamp=datetime.now().isoformat(),
            cpu_percent=cpu_percent,
            memory_percent=mem.percent,
            memory_mb=mem.used / (1024 * 1024),
            disk_io_read_mb=disk_io.read_bytes / (1024 * 1024),
            disk_io_write_mb=disk_io.write_bytes / (1024 * 1024),
            network_sent_mb=net_io.bytes_sent / (1024 * 1024),
            network_recv_mb=net_io.bytes_recv / (1024 * 1024)
        )
        self.resource_metrics.append(metric)
        return metric

    async def monitor_resources(self, duration_seconds: int = 10):
        """Monitor resource utilization over time"""
        print("\n📊 Phase 3: Resource Utilization")
        print(f"  Monitoring for {duration_seconds} seconds...")
        print("-" * 70)

        samples = []
        for i in range(duration_seconds):
            metric = self.capture_resource_metrics()
            samples.append(metric)
            await asyncio.sleep(1)

        # Calculate averages
        avg_cpu = statistics.mean([m.cpu_percent for m in samples])
        avg_mem = statistics.mean([m.memory_percent for m in samples])
        avg_mem_mb = statistics.mean([m.memory_mb for m in samples])

        print(f"\n  Average CPU: {avg_cpu:.2f}%")
        print(f"  Average Memory: {avg_mem:.2f}% ({avg_mem_mb:.2f} MB)")
        print(f"  Disk I/O Read: {samples[-1].disk_io_read_mb:.2f} MB")
        print(f"  Disk I/O Write: {samples[-1].disk_io_write_mb:.2f} MB")
        print(f"  Network Sent: {samples[-1].network_sent_mb:.2f} MB")
        print(f"  Network Recv: {samples[-1].network_recv_mb:.2f} MB")

    # ==================== Concurrent Load Testing ====================

    async def benchmark_concurrent_load(self, num_users: int = 10, requests_per_user: int = 50):
        """Test concurrent user load"""
        print(f"\n📊 Phase 4: Concurrent Load Test ({num_users} users, {requests_per_user} requests each)")
        print("-" * 70)

        async def user_workload(user_id: int):
            """Simulate user workload"""
            endpoints = [
                "/health/ping",
                "/api/v1/companies/CHGG",
                "/api/v1/financial/metrics?ticker=CHGG"
            ]

            for i in range(requests_per_user):
                endpoint = endpoints[i % len(endpoints)]
                await self.measure_api_endpoint(endpoint, "GET")

        start_time = time.time()
        tasks = [user_workload(i) for i in range(num_users)]
        await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        total_requests = num_users * requests_per_user
        throughput = total_requests / total_time

        print(f"\n  Total Requests: {total_requests}")
        print(f"  Total Duration: {total_time:.2f}s")
        print(f"  Throughput: {throughput:.2f} requests/sec")

        # Calculate success rate
        concurrent_metrics = self.api_metrics[-total_requests:]
        successful = sum(1 for m in concurrent_metrics if m.success)
        print(f"  Success Rate: {(successful/total_requests)*100:.2f}%")

    # ==================== Report Generation ====================

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive baseline report"""

        # API metrics analysis
        api_times = [m.response_time_ms for m in self.api_metrics if m.success]
        api_sorted = sorted(api_times)

        api_stats = {
            "total_requests": len(self.api_metrics),
            "successful_requests": len(api_times),
            "failed_requests": len(self.api_metrics) - len(api_times),
            "min_ms": min(api_times) if api_times else 0,
            "max_ms": max(api_times) if api_times else 0,
            "mean_ms": statistics.mean(api_times) if api_times else 0,
            "median_ms": statistics.median(api_times) if api_times else 0,
            "p50_ms": api_sorted[int(len(api_sorted) * 0.50)] if api_sorted else 0,
            "p95_ms": api_sorted[int(len(api_sorted) * 0.95)] if api_sorted else 0,
            "p99_ms": api_sorted[int(len(api_sorted) * 0.99)] if api_sorted else 0,
        }

        # Database metrics analysis
        db_times = [m.execution_time_ms for m in self.db_metrics if m]
        db_stats = {
            "total_queries": len(self.db_metrics),
            "mean_ms": statistics.mean(db_times) if db_times else 0,
            "median_ms": statistics.median(db_times) if db_times else 0,
            "index_usage_pct": (sum(1 for m in self.db_metrics if m and m.index_used) / len(self.db_metrics) * 100) if self.db_metrics else 0,
            "cache_hit_pct": (sum(1 for m in self.db_metrics if m and m.cache_hit) / len(self.db_metrics) * 100) if self.db_metrics else 0,
        }

        # Resource metrics analysis
        if self.resource_metrics:
            resource_stats = {
                "avg_cpu_percent": statistics.mean([m.cpu_percent for m in self.resource_metrics]),
                "avg_memory_percent": statistics.mean([m.memory_percent for m in self.resource_metrics]),
                "avg_memory_mb": statistics.mean([m.memory_mb for m in self.resource_metrics]),
            }
        else:
            resource_stats = {}

        return {
            "timestamp": datetime.now().isoformat(),
            "environment": "staging",
            "api_performance": api_stats,
            "database_performance": db_stats,
            "resource_utilization": resource_stats,
            "detailed_api_metrics": [asdict(m) for m in self.api_metrics],
            "detailed_db_metrics": [asdict(m) for m in self.db_metrics if m],
            "detailed_resource_metrics": [asdict(m) for m in self.resource_metrics],
        }

    async def run_full_baseline(self):
        """Execute complete baseline measurement suite"""
        print("\n" + "=" * 70)
        print("PERFORMANCE BASELINE MEASUREMENT - STAGING ENVIRONMENT")
        print("=" * 70)

        try:
            await self.initialize()

            # Phase 1: API Performance
            await self.benchmark_api_endpoints()
            await self.benchmark_api_latency_distribution()

            # Phase 2: Database Performance
            await self.benchmark_database_queries()
            await self.measure_connection_pool()

            # Phase 3: Resource Monitoring
            await self.monitor_resources(duration_seconds=10)

            # Phase 4: Concurrent Load
            await self.benchmark_concurrent_load(num_users=10, requests_per_user=50)

            # Generate report
            report = self.generate_report()

            # Print summary
            print("\n" + "=" * 70)
            print("BASELINE SUMMARY")
            print("=" * 70)

            api = report['api_performance']
            db = report['database_performance']
            res = report['resource_utilization']

            print(f"\n🌐 API Performance:")
            print(f"  Total Requests: {api['total_requests']}")
            print(f"  Success Rate: {(api['successful_requests']/api['total_requests']*100):.2f}%")
            print(f"  Mean Latency: {api['mean_ms']:.2f}ms")
            print(f"  P50 Latency: {api['p50_ms']:.2f}ms")
            print(f"  P95 Latency: {api['p95_ms']:.2f}ms")
            print(f"  P99 Latency: {api['p99_ms']:.2f}ms")

            # Check against target
            p99_target = 100  # <100ms p99 latency
            if api['p99_ms'] < p99_target:
                print(f"  ✓ P99 latency meets target (<{p99_target}ms)")
            else:
                print(f"  ✗ P99 latency exceeds target (>{p99_target}ms)")

            print(f"\n💾 Database Performance:")
            print(f"  Total Queries: {db['total_queries']}")
            print(f"  Mean Execution: {db['mean_ms']:.2f}ms")
            print(f"  Index Usage: {db['index_usage_pct']:.2f}%")
            print(f"  Cache Hit Rate: {db['cache_hit_pct']:.2f}%")

            print(f"\n🖥️  Resource Utilization:")
            if res:
                print(f"  Average CPU: {res['avg_cpu_percent']:.2f}%")
                print(f"  Average Memory: {res['avg_memory_percent']:.2f}%")
                print(f"  Memory Usage: {res['avg_memory_mb']:.2f} MB")

            # Save report
            report_file = f"docs/performance_baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)

            print(f"\n✓ Baseline report saved to: {report_file}")
            print("=" * 70)

            return report

        finally:
            await self.close()


async def main():
    """Main execution"""
    baseline = PerformanceBaseline(
        api_base_url="http://localhost:8004",
        db_config={
            'host': 'localhost',
            'port': 5435,
            'user': 'intel_staging_user',
            'password': 'lsZXGgU92KhK5VqR',
            'database': 'corporate_intel_staging'
        }
    )

    report = await baseline.run_full_baseline()

    # Store in memory for swarm coordination
    print("\n📝 Storing baseline in swarm memory...")
    return report


if __name__ == "__main__":
    try:
        report = asyncio.run(main())
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Baseline measurement failed: {e}")
        sys.exit(1)
