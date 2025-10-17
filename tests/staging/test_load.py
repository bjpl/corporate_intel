"""Load testing for staging environment using Locust.

Simulates 10x expected traffic to validate performance:
- Concurrent user scenarios
- Database performance under load
- API response time validation
- System stability under stress
"""

from locust import HttpUser, task, between, events
from typing import Dict, Any
import random
import json
import os


class CorporateIntelUser(HttpUser):
    """Simulated user for load testing."""

    # Wait between 1-5 seconds between tasks
    wait_time = between(1, 5)

    def on_start(self) -> None:
        """Initialize user session."""
        # Get auth token from environment or login
        self.token = os.getenv("STAGING_AUTH_TOKEN", "")

        if not self.token:
            # Try to login
            self.login()

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        # Cache company IDs for detail requests
        self.company_ids = []
        self._load_company_ids()

    def login(self) -> None:
        """Login to get auth token."""
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "test123"
            },
            name="/api/v1/auth/login",
            catch_response=True
        )

        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token", "")
            response.success()
        else:
            response.failure(f"Login failed: {response.status_code}")

    def _load_company_ids(self) -> None:
        """Load company IDs for testing."""
        try:
            response = self.client.get(
                "/api/v1/companies",
                headers=self.headers,
                name="/api/v1/companies"
            )
            if response.status_code == 200:
                companies = response.json()
                self.company_ids = [c["id"] for c in companies if "id" in c]
        except Exception:
            # If fails, use empty list
            self.company_ids = []

    @task(5)
    def health_check(self) -> None:
        """Frequent health check requests (50% of traffic)."""
        self.client.get(
            "/api/v1/health/ping",
            name="/api/v1/health/ping"
        )

    @task(3)
    def list_companies(self) -> None:
        """List companies (30% of traffic)."""
        self.client.get(
            "/api/v1/companies",
            headers=self.headers,
            name="/api/v1/companies"
        )

    @task(2)
    def company_detail(self) -> None:
        """Get company details (20% of traffic)."""
        if not self.company_ids:
            self._load_company_ids()

        if self.company_ids:
            company_id = random.choice(self.company_ids)
            self.client.get(
                f"/api/v1/companies/{company_id}",
                headers=self.headers,
                name="/api/v1/companies/[id]"
            )

    @task(2)
    def financial_metrics(self) -> None:
        """Get financial metrics (20% of traffic)."""
        params = {
            "limit": 50,
            "offset": 0
        }
        self.client.get(
            "/api/v1/metrics",
            params=params,
            headers=self.headers,
            name="/api/v1/metrics"
        )

    @task(1)
    def intelligence_summary(self) -> None:
        """Get intelligence summary (10% of traffic)."""
        self.client.get(
            "/api/v1/intelligence/summary",
            headers=self.headers,
            name="/api/v1/intelligence/summary"
        )

    @task(1)
    def search_companies(self) -> None:
        """Search companies (10% of traffic)."""
        search_terms = ["tech", "edu", "learning", "platform", "software"]
        term = random.choice(search_terms)

        self.client.get(
            f"/api/v1/companies/search?q={term}",
            headers=self.headers,
            name="/api/v1/companies/search"
        )


class DashboardUser(HttpUser):
    """Simulated dashboard user for load testing."""

    # Wait between 2-10 seconds (dashboards typically viewed longer)
    wait_time = between(2, 10)

    @task(5)
    def view_dashboard(self) -> None:
        """View main dashboard page."""
        self.client.get(
            "/",
            name="Dashboard Homepage"
        )

    @task(2)
    def dashboard_assets(self) -> None:
        """Load dashboard assets."""
        # Dash typically has these endpoints
        endpoints = [
            "/_dash-layout",
            "/_dash-dependencies",
        ]

        for endpoint in endpoints:
            self.client.get(
                endpoint,
                name=f"Dashboard {endpoint}"
            )

    @task(1)
    def dashboard_update(self) -> None:
        """Simulate dashboard update (callback)."""
        # Dash callbacks are POST requests
        self.client.post(
            "/_dash-update-component",
            json={
                "output": "graph.figure",
                "inputs": [{"id": "dropdown", "property": "value", "value": "all"}]
            },
            name="Dashboard Update Component"
        )


class AdminUser(HttpUser):
    """Simulated admin user for load testing."""

    # Admin users typically perform slower operations
    wait_time = between(5, 15)

    def on_start(self) -> None:
        """Initialize admin session."""
        self.token = os.getenv("STAGING_ADMIN_TOKEN", "")
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    @task(3)
    def view_system_health(self) -> None:
        """Check system health."""
        self.client.get(
            "/api/v1/health/ready",
            headers=self.headers,
            name="/api/v1/health/ready"
        )

    @task(2)
    def view_users(self) -> None:
        """View user list."""
        self.client.get(
            "/api/v1/admin/users",
            headers=self.headers,
            name="/api/v1/admin/users"
        )

    @task(1)
    def view_audit_logs(self) -> None:
        """View audit logs."""
        self.client.get(
            "/api/v1/admin/audit-logs",
            headers=self.headers,
            name="/api/v1/admin/audit-logs"
        )

    @task(1)
    def generate_report(self) -> None:
        """Generate system report."""
        self.client.post(
            "/api/v1/reports/generate",
            json={"report_type": "system_health", "format": "json"},
            headers=self.headers,
            name="/api/v1/reports/generate"
        )


# Locust event handlers for custom metrics
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track request metrics."""
    if exception:
        print(f"Request failed: {name} - {exception}")


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """Generate summary report on test completion."""
    stats = environment.stats

    print("\n" + "="*80)
    print("LOAD TEST SUMMARY")
    print("="*80)

    if stats.total.num_requests > 0:
        print(f"\nTotal Requests: {stats.total.num_requests}")
        print(f"Total Failures: {stats.total.num_failures}")
        print(f"Failure Rate: {stats.total.fail_ratio:.2%}")
        print(f"Average Response Time: {stats.total.avg_response_time:.2f}ms")
        print(f"Median Response Time: {stats.total.median_response_time:.2f}ms")
        print(f"95th Percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
        print(f"99th Percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")
        print(f"Max Response Time: {stats.total.max_response_time:.2f}ms")
        print(f"Requests/sec: {stats.total.total_rps:.2f}")

        # Check performance thresholds
        print("\n" + "-"*80)
        print("PERFORMANCE VALIDATION")
        print("-"*80)

        success = True

        # P95 should be < 500ms
        p95 = stats.total.get_response_time_percentile(0.95)
        if p95 > 500:
            print(f"❌ P95 Response Time: {p95:.2f}ms (threshold: 500ms)")
            success = False
        else:
            print(f"✅ P95 Response Time: {p95:.2f}ms (threshold: 500ms)")

        # Failure rate should be < 1%
        if stats.total.fail_ratio > 0.01:
            print(f"❌ Failure Rate: {stats.total.fail_ratio:.2%} (threshold: 1%)")
            success = False
        else:
            print(f"✅ Failure Rate: {stats.total.fail_ratio:.2%} (threshold: 1%)")

        # Average response time should be < 200ms
        if stats.total.avg_response_time > 200:
            print(f"❌ Average Response Time: {stats.total.avg_response_time:.2f}ms (threshold: 200ms)")
            success = False
        else:
            print(f"✅ Average Response Time: {stats.total.avg_response_time:.2f}ms (threshold: 200ms)")

        if success:
            print("\n✅ All performance thresholds met!")
        else:
            print("\n❌ Some performance thresholds not met")

    print("\n" + "="*80 + "\n")


# Configuration for different load scenarios
"""
Run load tests with different scenarios:

1. Basic load test (10 users):
   locust -f test_load.py --host=http://staging:8000 --users=10 --spawn-rate=2 --run-time=5m

2. Peak load test (100 users - 10x expected):
   locust -f test_load.py --host=http://staging:8000 --users=100 --spawn-rate=10 --run-time=10m

3. Stress test (200 users):
   locust -f test_load.py --host=http://staging:8000 --users=200 --spawn-rate=20 --run-time=15m

4. Spike test (rapid ramp-up):
   locust -f test_load.py --host=http://staging:8000 --users=100 --spawn-rate=50 --run-time=5m

5. Endurance test (sustained load):
   locust -f test_load.py --host=http://staging:8000 --users=50 --spawn-rate=5 --run-time=60m

6. With dashboard testing:
   locust -f test_load.py --host=http://staging:8000 --users=100 --spawn-rate=10 --run-time=10m \\
          --class-picker CorporateIntelUser:70,DashboardUser:25,AdminUser:5

Environment variables needed:
- STAGING_AUTH_TOKEN: Authentication token for API access
- STAGING_ADMIN_TOKEN: Admin authentication token
"""
