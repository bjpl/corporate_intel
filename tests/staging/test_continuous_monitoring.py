"""
Continuous Monitoring Tests - 2-Hour Stability Validation
Tests system stability, memory leaks, CPU utilization, and performance over time.
"""

import asyncio
import psutil
import pytest
import time
from datetime import datetime, timedelta
from typing import List, Dict
import httpx
from sqlalchemy import create_engine, text
from contextlib import asynccontextmanager


class SystemMetrics:
    """Track system metrics over time."""

    def __init__(self):
        self.metrics: List[Dict] = []
        self.start_time = datetime.now()

    def record(self):
        """Record current system metrics."""
        process = psutil.Process()

        metric = {
            'timestamp': datetime.now(),
            'elapsed_seconds': (datetime.now() - self.start_time).total_seconds(),
            'memory_mb': process.memory_info().rss / 1024 / 1024,
            'cpu_percent': process.cpu_percent(interval=1),
            'num_threads': process.num_threads(),
            'num_fds': process.num_fds() if hasattr(process, 'num_fds') else 0,
            'system_memory_percent': psutil.virtual_memory().percent,
            'system_cpu_percent': psutil.cpu_percent(interval=1)
        }

        self.metrics.append(metric)
        return metric

    def get_summary(self) -> Dict:
        """Get summary statistics."""
        if not self.metrics:
            return {}

        memory_values = [m['memory_mb'] for m in self.metrics]
        cpu_values = [m['cpu_percent'] for m in self.metrics]

        return {
            'duration_seconds': (datetime.now() - self.start_time).total_seconds(),
            'total_samples': len(self.metrics),
            'memory': {
                'min_mb': min(memory_values),
                'max_mb': max(memory_values),
                'avg_mb': sum(memory_values) / len(memory_values),
                'growth_mb': memory_values[-1] - memory_values[0],
                'growth_rate_mb_per_hour': ((memory_values[-1] - memory_values[0]) /
                                            (self.metrics[-1]['elapsed_seconds'] / 3600))
            },
            'cpu': {
                'min_percent': min(cpu_values),
                'max_percent': max(cpu_values),
                'avg_percent': sum(cpu_values) / len(cpu_values)
            },
            'threads': {
                'current': self.metrics[-1]['num_threads'],
                'max': max(m['num_threads'] for m in self.metrics)
            }
        }

    def check_memory_leak(self, threshold_mb_per_hour: float = 50) -> tuple[bool, str]:
        """Check for potential memory leaks."""
        summary = self.get_summary()
        growth_rate = summary['memory']['growth_rate_mb_per_hour']

        if growth_rate > threshold_mb_per_hour:
            return False, f"Potential memory leak detected: {growth_rate:.2f} MB/hour growth"

        return True, f"Memory stable: {growth_rate:.2f} MB/hour growth"


@pytest.fixture
def system_metrics():
    """System metrics tracker fixture."""
    return SystemMetrics()


@pytest.fixture
def staging_api_url():
    """Staging API URL."""
    return "http://localhost:8000"


@pytest.fixture
def database_url():
    """Database connection URL."""
    return "postgresql://corpintel_user:your_password@localhost:5432/corporate_intel"


@pytest.mark.asyncio
@pytest.mark.slow
async def test_two_hour_stability(system_metrics: SystemMetrics, staging_api_url: str):
    """
    Test system stability over 2 hours with continuous load.

    This test:
    - Makes API requests every 10 seconds
    - Records system metrics every minute
    - Checks for memory leaks
    - Validates response times remain stable
    """
    duration_hours = 2
    request_interval = 10  # seconds
    metric_interval = 60   # seconds

    print(f"\n🔬 Starting {duration_hours}-hour stability test...")
    print(f"📊 Recording metrics every {metric_interval}s")
    print(f"🌐 Making requests every {request_interval}s")

    start_time = time.time()
    end_time = start_time + (duration_hours * 3600)

    last_metric_time = start_time
    request_count = 0
    error_count = 0
    response_times = []

    async with httpx.AsyncClient(base_url=staging_api_url, timeout=30.0) as client:
        while time.time() < end_time:
            current_time = time.time()

            # Record system metrics
            if current_time - last_metric_time >= metric_interval:
                metric = system_metrics.record()
                print(f"📊 [{int(current_time - start_time)}s] "
                      f"Memory: {metric['memory_mb']:.1f}MB, "
                      f"CPU: {metric['cpu_percent']:.1f}%, "
                      f"Requests: {request_count}, "
                      f"Errors: {error_count}")
                last_metric_time = current_time

            # Make API request
            try:
                req_start = time.time()
                response = await client.get("/api/v1/health")
                req_duration = time.time() - req_start

                response_times.append(req_duration)
                request_count += 1

                if response.status_code != 200:
                    error_count += 1
                    print(f"⚠️ Non-200 response: {response.status_code}")

            except Exception as e:
                error_count += 1
                print(f"❌ Request error: {e}")

            # Wait before next request
            await asyncio.sleep(request_interval)

    # Analyze results
    summary = system_metrics.get_summary()

    print(f"\n" + "="*80)
    print(f"📊 STABILITY TEST SUMMARY ({duration_hours} hours)")
    print("="*80)

    print(f"\n🌐 API Metrics:")
    print(f"  Total Requests: {request_count}")
    print(f"  Errors: {error_count}")
    print(f"  Error Rate: {(error_count/request_count*100):.2f}%")
    print(f"  Avg Response Time: {sum(response_times)/len(response_times)*1000:.2f}ms")
    print(f"  P95 Response Time: {sorted(response_times)[int(len(response_times)*0.95)]*1000:.2f}ms")
    print(f"  P99 Response Time: {sorted(response_times)[int(len(response_times)*0.99)]*1000:.2f}ms")

    print(f"\n💾 Memory Metrics:")
    print(f"  Initial: {summary['memory']['min_mb']:.1f}MB")
    print(f"  Final: {summary['memory']['max_mb']:.1f}MB")
    print(f"  Average: {summary['memory']['avg_mb']:.1f}MB")
    print(f"  Growth: {summary['memory']['growth_mb']:.1f}MB")
    print(f"  Growth Rate: {summary['memory']['growth_rate_mb_per_hour']:.2f}MB/hour")

    print(f"\n⚡ CPU Metrics:")
    print(f"  Average: {summary['cpu']['avg_percent']:.1f}%")
    print(f"  Peak: {summary['cpu']['max_percent']:.1f}%")

    print(f"\n🧵 Thread Metrics:")
    print(f"  Current: {summary['threads']['current']}")
    print(f"  Peak: {summary['threads']['max']}")

    # Assertions
    leak_ok, leak_msg = system_metrics.check_memory_leak()
    print(f"\n{leak_msg}")
    assert leak_ok, "Memory leak detected!"

    assert error_count / request_count < 0.01, f"Error rate too high: {error_count/request_count*100:.2f}%"

    avg_response = sum(response_times) / len(response_times)
    assert avg_response < 1.0, f"Average response time too high: {avg_response*1000:.2f}ms"

    print("\n✅ Stability test passed!")


@pytest.mark.asyncio
async def test_database_connection_pool_monitoring(database_url: str):
    """
    Monitor database connection pool over time.

    Tests for:
    - Connection pool leaks
    - Connection timeout issues
    - Query performance degradation
    """
    duration_minutes = 30
    query_interval = 5  # seconds

    print(f"\n🗄️ Starting {duration_minutes}-minute database pool test...")

    engine = create_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True
    )

    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)

    query_count = 0
    error_count = 0
    query_times = []

    while time.time() < end_time:
        try:
            query_start = time.time()

            with engine.connect() as conn:
                # Test query
                result = conn.execute(text("SELECT COUNT(*) FROM companies"))
                result.fetchone()

                # Check pool stats
                pool = engine.pool
                pool_size = pool.size()
                checked_out = pool.checkedout()

                query_duration = time.time() - query_start
                query_times.append(query_duration)
                query_count += 1

                if query_count % 60 == 0:  # Log every minute
                    print(f"📊 [{int(time.time() - start_time)}s] "
                          f"Queries: {query_count}, "
                          f"Pool: {checked_out}/{pool_size}, "
                          f"Avg Time: {sum(query_times)/len(query_times)*1000:.2f}ms")

        except Exception as e:
            error_count += 1
            print(f"❌ Query error: {e}")

        await asyncio.sleep(query_interval)

    # Summary
    print(f"\n" + "="*80)
    print(f"📊 DATABASE POOL TEST SUMMARY")
    print("="*80)
    print(f"Total Queries: {query_count}")
    print(f"Errors: {error_count}")
    print(f"Error Rate: {(error_count/query_count*100):.2f}%")
    print(f"Avg Query Time: {sum(query_times)/len(query_times)*1000:.2f}ms")
    print(f"P95 Query Time: {sorted(query_times)[int(len(query_times)*0.95)]*1000:.2f}ms")

    # Assertions
    assert error_count / query_count < 0.01, f"Error rate too high: {error_count/query_count*100:.2f}%"

    avg_time = sum(query_times) / len(query_times)
    assert avg_time < 0.1, f"Average query time too high: {avg_time*1000:.2f}ms"

    print("\n✅ Database pool test passed!")

    engine.dispose()


@pytest.mark.asyncio
async def test_api_latency_tracking(staging_api_url: str, system_metrics: SystemMetrics):
    """
    Track API endpoint latency over 1 hour.

    Tests for:
    - Latency degradation
    - Slow endpoints
    - Performance consistency
    """
    duration_minutes = 60

    endpoints = [
        "/api/v1/health",
        "/api/v1/companies",
        "/api/v1/metrics/AAPL",
        "/api/v1/intelligence/sector-analysis?sector=Technology"
    ]

    print(f"\n⚡ Starting {duration_minutes}-minute latency tracking test...")

    endpoint_metrics = {ep: {'times': [], 'errors': 0} for ep in endpoints}

    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)

    async with httpx.AsyncClient(base_url=staging_api_url, timeout=30.0) as client:
        iteration = 0
        while time.time() < end_time:
            iteration += 1

            # Test all endpoints
            for endpoint in endpoints:
                try:
                    req_start = time.time()
                    response = await client.get(endpoint)
                    req_duration = time.time() - req_start

                    endpoint_metrics[endpoint]['times'].append(req_duration)

                    if response.status_code >= 400:
                        endpoint_metrics[endpoint]['errors'] += 1

                except Exception as e:
                    endpoint_metrics[endpoint]['errors'] += 1
                    print(f"❌ Error on {endpoint}: {e}")

            # Log progress every 10 minutes
            if iteration % 60 == 0:
                elapsed = int(time.time() - start_time)
                print(f"📊 [{elapsed}s] Completed {iteration} iterations")
                system_metrics.record()

            await asyncio.sleep(10)

    # Analyze and report
    print(f"\n" + "="*80)
    print(f"📊 API LATENCY TRACKING SUMMARY")
    print("="*80)

    for endpoint, metrics in endpoint_metrics.items():
        times = metrics['times']
        if not times:
            continue

        print(f"\n📍 {endpoint}:")
        print(f"  Requests: {len(times)}")
        print(f"  Errors: {metrics['errors']}")
        print(f"  Avg: {sum(times)/len(times)*1000:.2f}ms")
        print(f"  P50: {sorted(times)[len(times)//2]*1000:.2f}ms")
        print(f"  P95: {sorted(times)[int(len(times)*0.95)]*1000:.2f}ms")
        print(f"  P99: {sorted(times)[int(len(times)*0.99)]*1000:.2f}ms")
        print(f"  Max: {max(times)*1000:.2f}ms")

        # Assertions
        avg_time = sum(times) / len(times)
        assert avg_time < 2.0, f"{endpoint}: Average response time too high: {avg_time*1000:.2f}ms"

        error_rate = metrics['errors'] / len(times)
        assert error_rate < 0.05, f"{endpoint}: Error rate too high: {error_rate*100:.2f}%"

    print("\n✅ Latency tracking test passed!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
