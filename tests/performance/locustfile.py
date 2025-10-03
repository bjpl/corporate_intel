"""
Locust Performance Testing Suite for Corporate Intel API
Run: locust -f locustfile.py --host=https://api.corporate-intel.com
"""

from locust import HttpUser, task, between, events
from locust.contrib.fasthttp import FastHttpUser
import json
import random
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CorporateIntelUser(FastHttpUser):
    """Simulates a user interacting with the Corporate Intel API"""

    wait_time = between(1, 3)  # Wait 1-3 seconds between requests
    auth_token = None
    user_id = None

    def on_start(self):
        """Setup: Login and get auth token"""
        self.login()

    def login(self):
        """Authenticate user and store token"""
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": f"loadtest_{random.randint(1, 1000)}@test.com",
                "password": "LoadTest123!"
            },
            name="auth/login"
        )
        if response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            self.user_id = data.get("user_id")
            logger.info(f"User logged in: {self.user_id}")
        else:
            logger.error(f"Login failed: {response.status_code}")

    @property
    def headers(self):
        """Return headers with auth token"""
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }

    @task(10)
    def get_dashboard(self):
        """Fetch user dashboard - most common operation"""
        self.client.get(
            "/api/v1/dashboard",
            headers=self.headers,
            name="dashboard/view"
        )

    @task(8)
    def list_organizations(self):
        """List user's organizations"""
        self.client.get(
            "/api/v1/organizations",
            headers=self.headers,
            params={"limit": 20, "offset": 0},
            name="organizations/list"
        )

    @task(6)
    def search_data(self):
        """Perform search operation"""
        search_terms = ["revenue", "growth", "market", "trends", "analysis"]
        term = random.choice(search_terms)

        self.client.get(
            "/api/v1/search",
            headers=self.headers,
            params={
                "q": term,
                "limit": 10,
                "filters": json.dumps({"category": "financial"})
            },
            name="search/query"
        )

    @task(5)
    def get_analytics(self):
        """Fetch analytics data"""
        start_date = (datetime.now() - timedelta(days=30)).isoformat()
        end_date = datetime.now().isoformat()

        self.client.post(
            "/api/v1/analytics/query",
            headers=self.headers,
            json={
                "start_date": start_date,
                "end_date": end_date,
                "metrics": ["revenue", "user_growth"],
                "dimensions": ["region", "category"]
            },
            name="analytics/query"
        )

    @task(4)
    def create_report(self):
        """Create a new report"""
        self.client.post(
            "/api/v1/reports",
            headers=self.headers,
            json={
                "title": f"Load Test Report {random.randint(1, 10000)}",
                "type": "financial",
                "parameters": {
                    "metrics": ["revenue", "profit_margin"],
                    "period": "monthly"
                }
            },
            name="reports/create"
        )

    @task(3)
    def list_reports(self):
        """List user's reports"""
        self.client.get(
            "/api/v1/reports",
            headers=self.headers,
            params={"limit": 20, "status": "completed"},
            name="reports/list"
        )

    @task(2)
    def export_data(self):
        """Export data - resource intensive"""
        self.client.post(
            "/api/v1/export",
            headers=self.headers,
            json={
                "format": "csv",
                "data_type": "analytics",
                "filters": {
                    "date_range": "last_month"
                }
            },
            name="export/csv"
        )

    @task(2)
    def get_user_profile(self):
        """Get user profile"""
        self.client.get(
            f"/api/v1/users/{self.user_id}",
            headers=self.headers,
            name="users/profile"
        )

    @task(1)
    def update_preferences(self):
        """Update user preferences"""
        self.client.patch(
            f"/api/v1/users/{self.user_id}/preferences",
            headers=self.headers,
            json={
                "theme": random.choice(["light", "dark"]),
                "language": "en",
                "notifications": True
            },
            name="users/preferences/update"
        )

    @task(1)
    def health_check(self):
        """Health check endpoint"""
        self.client.get(
            "/health",
            name="health/check"
        )


class AdminUser(FastHttpUser):
    """Simulates admin users with heavier operations"""

    wait_time = between(2, 5)
    auth_token = None

    def on_start(self):
        """Admin login"""
        response = self.client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin@test.com",
                "password": "AdminTest123!"
            }
        )
        if response.status_code == 200:
            self.auth_token = response.json().get("access_token")

    @property
    def headers(self):
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }

    @task(5)
    def get_system_metrics(self):
        """Fetch system metrics"""
        self.client.get(
            "/api/v1/admin/metrics",
            headers=self.headers,
            name="admin/metrics"
        )

    @task(3)
    def manage_users(self):
        """User management operations"""
        self.client.get(
            "/api/v1/admin/users",
            headers=self.headers,
            params={"limit": 50, "offset": 0},
            name="admin/users/list"
        )

    @task(2)
    def bulk_data_import(self):
        """Simulate bulk data import"""
        self.client.post(
            "/api/v1/admin/import",
            headers=self.headers,
            json={
                "source": "s3",
                "bucket": "data-imports",
                "file": f"import_{random.randint(1, 100)}.csv"
            },
            name="admin/import/bulk"
        )


class APIStressTest(FastHttpUser):
    """Stress testing with extreme load"""

    wait_time = between(0.1, 0.5)  # Very aggressive

    @task
    def rapid_requests(self):
        """Rapid fire requests"""
        endpoints = [
            "/health",
            "/api/v1/dashboard",
            "/api/v1/organizations",
        ]
        endpoint = random.choice(endpoints)
        self.client.get(endpoint, name="stress/rapid")


# Event handlers for custom metrics
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Log slow requests"""
    if response_time > 1000:  # > 1 second
        logger.warning(
            f"Slow request: {name} took {response_time}ms"
        )


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """Generate final report"""
    stats = environment.stats
    logger.info("=" * 80)
    logger.info("LOAD TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Total requests: {stats.total.num_requests}")
    logger.info(f"Total failures: {stats.total.num_failures}")
    logger.info(f"Average response time: {stats.total.avg_response_time}ms")
    logger.info(f"Min response time: {stats.total.min_response_time}ms")
    logger.info(f"Max response time: {stats.total.max_response_time}ms")
    logger.info(f"Requests per second: {stats.total.current_rps}")
    logger.info("=" * 80)


# Custom test scenarios
class SpikeTest(FastHttpUser):
    """Simulates sudden traffic spike"""
    wait_time = between(0.1, 0.3)

    @task
    def spike_load(self):
        self.client.get("/api/v1/dashboard", name="spike/dashboard")


class SoakTest(FastHttpUser):
    """Long-running endurance test"""
    wait_time = between(5, 10)

    @task
    def sustained_load(self):
        self.client.get("/api/v1/analytics/query", name="soak/analytics")
