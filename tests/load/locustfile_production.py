"""Production load testing scenarios using Locust.

Run scenarios:
1. Baseline: locust -f locustfile_production.py --host=https://api.prod --users=10 --spawn-rate=1 --run-time=5m
2. Peak Load: locust -f locustfile_production.py --host=https://api.prod --users=100 --spawn-rate=10 --run-time=10m
3. Stress Test: locust -f locustfile_production.py --host=https://api.prod --users=200 --spawn-rate=20 --run-time=15m
4. Endurance: locust -f locustfile_production.py --host=https://api.prod --users=50 --spawn-rate=5 --run-time=60m
"""

from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser
import random
import json
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaselineUser(FastHttpUser):
    """Baseline normal user behavior - realistic traffic patterns."""

    wait_time = between(2, 5)
    weight = 7  # 70% of traffic

    def on_start(self):
        """Setup: Get auth token."""
        self.token = os.getenv("PRODUCTION_AUTH_TOKEN", "")
        if not self.token:
            self.login()

    def login(self):
        """Login to get auth token."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": f"loadtest_{random.randint(1, 1000)}@test.com",
                "password": "LoadTest123!"
            },
            name="auth/login"
        )
        if response.status_code == 200:
            self.token = response.json().get("access_token", "")

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    @task(10)
    def health_check(self):
        """Most frequent - health checks."""
        self.client.get("/api/v1/health/ping", name="health/ping")

    @task(8)
    def list_companies(self):
        """List companies - common operation."""
        self.client.get(
            "/api/v1/companies",
            headers=self.headers,
            params={"limit": 20},
            name="companies/list"
        )

    @task(5)
    def view_company_details(self):
        """View company details."""
        # Simulate viewing random company
        company_id = random.randint(1, 100)
        self.client.get(
            f"/api/v1/companies/{company_id}",
            headers=self.headers,
            name="companies/detail",
            catch_response=True
        )

    @task(5)
    def get_metrics(self):
        """Get financial metrics."""
        self.client.get(
            "/api/v1/metrics",
            headers=self.headers,
            params={"limit": 50},
            name="metrics/list"
        )

    @task(3)
    def search_companies(self):
        """Search for companies."""
        terms = ["tech", "finance", "healthcare", "education", "retail"]
        term = random.choice(terms)
        self.client.get(
            f"/api/v1/companies/search",
            params={"q": term},
            headers=self.headers,
            name="companies/search"
        )

    @task(2)
    def get_intelligence_summary(self):
        """Get intelligence summary - heavier operation."""
        self.client.get(
            "/api/v1/intelligence/summary",
            headers=self.headers,
            name="intelligence/summary"
        )


class PeakUser(FastHttpUser):
    """Peak traffic user - more aggressive patterns."""

    wait_time = between(1, 3)
    weight = 2  # 20% of traffic during peak

    def on_start(self):
        self.token = os.getenv("PRODUCTION_AUTH_TOKEN", "")

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    @task(5)
    def rapid_company_browsing(self):
        """Rapid browsing of companies."""
        self.client.get(
            "/api/v1/companies",
            headers=self.headers,
            params={"limit": 50, "offset": random.randint(0, 200)},
            name="peak/companies"
        )

    @task(3)
    def concurrent_metrics_requests(self):
        """Multiple metrics requests."""
        self.client.get(
            "/api/v1/metrics",
            headers=self.headers,
            params={"limit": 100},
            name="peak/metrics"
        )

    @task(2)
    def dashboard_refresh(self):
        """Dashboard data refresh."""
        self.client.get(
            "/api/v1/intelligence/summary",
            headers=self.headers,
            name="peak/dashboard"
        )


class AdminUser(FastHttpUser):
    """Admin operations - resource intensive."""

    wait_time = between(5, 15)
    weight = 1  # 10% of traffic

    def on_start(self):
        self.token = os.getenv("PRODUCTION_ADMIN_TOKEN", os.getenv("PRODUCTION_AUTH_TOKEN", ""))

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    @task(5)
    def system_health_check(self):
        """Check system health."""
        self.client.get(
            "/api/v1/health/ready",
            headers=self.headers,
            name="admin/health"
        )

    @task(3)
    def bulk_data_query(self):
        """Bulk data queries."""
        self.client.get(
            "/api/v1/metrics",
            headers=self.headers,
            params={"limit": 500},
            name="admin/bulk_query"
        )

    @task(2)
    def generate_report(self):
        """Generate reports - expensive operation."""
        self.client.post(
            "/api/v1/reports/generate",
            headers=self.headers,
            json={
                "report_type": "financial_summary",
                "format": "json",
                "date_range": "last_month"
            },
            name="admin/report",
            catch_response=True
        )


class StressTestUser(FastHttpUser):
    """Stress test - extreme load patterns."""

    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.token = os.getenv("PRODUCTION_AUTH_TOKEN", "")

    @property
    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}

    @task
    def rapid_fire_requests(self):
        """Rapid fire requests to find breaking point."""
        endpoints = [
            "/api/v1/health/ping",
            "/api/v1/companies",
            "/api/v1/metrics",
        ]
        endpoint = random.choice(endpoints)
        self.client.get(endpoint, headers=self.headers, name="stress/rapid")


# Performance tracking
performance_metrics = {
    "slow_requests": [],
    "failed_requests": [],
    "response_times": [],
}


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Track performance metrics."""
    global performance_metrics

    # Track response time
    performance_metrics["response_times"].append({
        "name": name,
        "response_time": response_time,
        "timestamp": datetime.now().isoformat()
    })

    # Track slow requests (>1s)
    if response_time > 1000:
        logger.warning(f"SLOW REQUEST: {name} took {response_time}ms")
        performance_metrics["slow_requests"].append({
            "name": name,
            "response_time": response_time,
            "timestamp": datetime.now().isoformat()
        })

    # Track failures
    if exception:
        logger.error(f"FAILED REQUEST: {name} - {exception}")
        performance_metrics["failed_requests"].append({
            "name": name,
            "exception": str(exception),
            "timestamp": datetime.now().isoformat()
        })


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test."""
    logger.info("="*80)
    logger.info("LOAD TEST STARTING")
    logger.info(f"Host: {environment.host}")
    logger.info(f"Users: {environment.parsed_options.num_users if environment.parsed_options else 'N/A'}")
    logger.info("="*80)


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """Generate comprehensive performance report."""
    stats = environment.stats

    logger.info("\n" + "="*80)
    logger.info("LOAD TEST PERFORMANCE REPORT")
    logger.info("="*80)

    if stats.total.num_requests > 0:
        # Basic statistics
        logger.info(f"\n{'BASIC STATISTICS':^80}")
        logger.info("-"*80)
        logger.info(f"Total Requests:        {stats.total.num_requests:,}")
        logger.info(f"Total Failures:        {stats.total.num_failures:,}")
        logger.info(f"Failure Rate:          {stats.total.fail_ratio:.2%}")
        logger.info(f"Requests/sec:          {stats.total.total_rps:.2f}")

        # Response time statistics
        logger.info(f"\n{'RESPONSE TIME STATISTICS':^80}")
        logger.info("-"*80)
        logger.info(f"Average:               {stats.total.avg_response_time:.2f}ms")
        logger.info(f"Median:                {stats.total.median_response_time:.2f}ms")
        logger.info(f"Min:                   {stats.total.min_response_time:.2f}ms")
        logger.info(f"Max:                   {stats.total.max_response_time:.2f}ms")
        logger.info(f"50th Percentile (P50): {stats.total.get_response_time_percentile(0.50):.2f}ms")
        logger.info(f"75th Percentile (P75): {stats.total.get_response_time_percentile(0.75):.2f}ms")
        logger.info(f"90th Percentile (P90): {stats.total.get_response_time_percentile(0.90):.2f}ms")
        logger.info(f"95th Percentile (P95): {stats.total.get_response_time_percentile(0.95):.2f}ms")
        logger.info(f"99th Percentile (P99): {stats.total.get_response_time_percentile(0.99):.2f}ms")

        # Performance validation
        logger.info(f"\n{'PERFORMANCE VALIDATION':^80}")
        logger.info("-"*80)

        thresholds = {
            "P95 Response Time": (stats.total.get_response_time_percentile(0.95), 500, "ms"),
            "P99 Response Time": (stats.total.get_response_time_percentile(0.99), 1000, "ms"),
            "Average Response Time": (stats.total.avg_response_time, 200, "ms"),
            "Failure Rate": (stats.total.fail_ratio * 100, 1, "%"),
        }

        all_passed = True
        for metric, (value, threshold, unit) in thresholds.items():
            if metric == "Failure Rate":
                passed = value <= threshold
                symbol = "✅" if passed else "❌"
                logger.info(f"{symbol} {metric:25s} {value:.2f}{unit} (threshold: <{threshold}{unit})")
            else:
                passed = value <= threshold
                symbol = "✅" if passed else "❌"
                logger.info(f"{symbol} {metric:25s} {value:.2f}{unit} (threshold: <{threshold}{unit})")

            if not passed:
                all_passed = False

        # Overall result
        logger.info("\n" + "-"*80)
        if all_passed:
            logger.info("✅ ALL PERFORMANCE THRESHOLDS MET - SYSTEM PERFORMING WELL")
        else:
            logger.info("❌ SOME PERFORMANCE THRESHOLDS NOT MET - REVIEW REQUIRED")

        # Slow requests summary
        if performance_metrics["slow_requests"]:
            logger.info(f"\n{'SLOW REQUESTS (>1s)':^80}")
            logger.info("-"*80)
            logger.info(f"Total Slow Requests: {len(performance_metrics['slow_requests'])}")
            # Show top 10 slowest
            sorted_slow = sorted(performance_metrics["slow_requests"],
                               key=lambda x: x["response_time"], reverse=True)[:10]
            for req in sorted_slow:
                logger.info(f"  {req['name']:40s} {req['response_time']:>8.2f}ms")

        # Failed requests summary
        if performance_metrics["failed_requests"]:
            logger.info(f"\n{'FAILED REQUESTS':^80}")
            logger.info("-"*80)
            logger.info(f"Total Failed: {len(performance_metrics['failed_requests'])}")
            # Show unique failures
            unique_failures = {}
            for req in performance_metrics["failed_requests"]:
                key = f"{req['name']}:{req['exception']}"
                unique_failures[key] = unique_failures.get(key, 0) + 1

            for failure, count in sorted(unique_failures.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  {count:>4d}x {failure}")

        # Endpoint statistics
        logger.info(f"\n{'ENDPOINT STATISTICS':^80}")
        logger.info("-"*80)
        logger.info(f"{'Endpoint':<40s} {'Requests':>10s} {'Failures':>10s} {'Avg (ms)':>10s} {'P95 (ms)':>10s}")
        logger.info("-"*80)

        for stat in sorted(stats.entries.values(), key=lambda x: x.num_requests, reverse=True):
            if stat.num_requests > 0:
                logger.info(
                    f"{stat.name:<40s} "
                    f"{stat.num_requests:>10,d} "
                    f"{stat.num_failures:>10,d} "
                    f"{stat.avg_response_time:>10.2f} "
                    f"{stat.get_response_time_percentile(0.95):>10.2f}"
                )

    logger.info("\n" + "="*80 + "\n")

    # Save detailed report to file
    report_file = f"load_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_data = {
        "summary": {
            "total_requests": stats.total.num_requests,
            "total_failures": stats.total.num_failures,
            "failure_rate": stats.total.fail_ratio,
            "rps": stats.total.total_rps,
            "avg_response_time": stats.total.avg_response_time,
            "median_response_time": stats.total.median_response_time,
            "p95_response_time": stats.total.get_response_time_percentile(0.95),
            "p99_response_time": stats.total.get_response_time_percentile(0.99),
        },
        "slow_requests": performance_metrics["slow_requests"][:100],  # Top 100
        "failed_requests": performance_metrics["failed_requests"][:100],  # Top 100
    }

    try:
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        logger.info(f"Detailed report saved to: {report_file}")
    except Exception as e:
        logger.error(f"Failed to save report: {e}")
