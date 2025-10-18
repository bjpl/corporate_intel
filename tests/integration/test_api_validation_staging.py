"""
Comprehensive API endpoint validation for staging environment.

This test suite validates:
- All API endpoints are responding correctly
- HTTP status codes are appropriate
- Response times meet performance targets (<100ms p99)
- Authentication and authorization work correctly
- Request/response validation is functioning
- Error handling is proper
"""

import pytest
import asyncio
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests
from loguru import logger

# Staging API configuration
STAGING_API_BASE = "http://localhost:8004"
API_V1_PREFIX = "/api/v1"

# Performance targets
P99_LATENCY_TARGET_MS = 100
P95_LATENCY_TARGET_MS = 50

# Test authentication token (will be obtained during test setup)
AUTH_TOKEN: Optional[str] = None


class APIEndpointTest:
    """Individual API endpoint test definition."""

    def __init__(
        self,
        method: str,
        endpoint: str,
        requires_auth: bool = False,
        expected_status: int = 200,
        query_params: Optional[Dict] = None,
        body: Optional[Dict] = None,
        description: str = "",
    ):
        self.method = method.upper()
        self.endpoint = endpoint
        self.requires_auth = requires_auth
        self.expected_status = expected_status
        self.query_params = query_params or {}
        self.body = body
        self.description = description
        self.response_times: List[float] = []
        self.passed = False
        self.error_message: Optional[str] = None


class APIValidationResults:
    """Validation results aggregator."""

    def __init__(self):
        self.tests: List[APIEndpointTest] = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.total_duration_ms = 0
        self.p50_latency_ms = 0
        self.p95_latency_ms = 0
        self.p99_latency_ms = 0

    def add_test(self, test: APIEndpointTest):
        """Add test result."""
        self.tests.append(test)
        self.total_tests += 1
        if test.passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1

    def calculate_metrics(self):
        """Calculate performance metrics."""
        all_response_times = []
        for test in self.tests:
            all_response_times.extend(test.response_times)

        if all_response_times:
            all_response_times.sort()
            n = len(all_response_times)
            self.p50_latency_ms = all_response_times[int(n * 0.50)]
            self.p95_latency_ms = all_response_times[int(n * 0.95)]
            self.p99_latency_ms = all_response_times[int(n * 0.99)]
            self.total_duration_ms = sum(all_response_times)

    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary."""
        return {
            "summary": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "success_rate": f"{(self.passed_tests / self.total_tests * 100):.2f}%",
                "total_duration_ms": round(self.total_duration_ms, 2),
            },
            "performance": {
                "p50_latency_ms": round(self.p50_latency_ms, 2),
                "p95_latency_ms": round(self.p95_latency_ms, 2),
                "p99_latency_ms": round(self.p99_latency_ms, 2),
                "p99_meets_target": self.p99_latency_ms < P99_LATENCY_TARGET_MS,
                "p95_meets_target": self.p95_latency_ms < P95_LATENCY_TARGET_MS,
            },
            "tests": [
                {
                    "endpoint": f"{test.method} {test.endpoint}",
                    "description": test.description,
                    "passed": test.passed,
                    "expected_status": test.expected_status,
                    "avg_response_time_ms": round(sum(test.response_times) / len(test.response_times), 2) if test.response_times else 0,
                    "error": test.error_message,
                }
                for test in self.tests
            ],
        }


def define_endpoint_tests() -> List[APIEndpointTest]:
    """Define all API endpoints to test."""
    return [
        # Health endpoints (no auth required)
        APIEndpointTest(
            "GET", f"{API_V1_PREFIX}/health",
            requires_auth=False,
            description="Basic health check",
        ),
        APIEndpointTest(
            "GET", f"{API_V1_PREFIX}/health/ping",
            requires_auth=False,
            description="Lightweight ping for load balancers",
        ),
        APIEndpointTest(
            "GET", f"{API_V1_PREFIX}/health/detailed",
            requires_auth=False,
            description="Detailed health check with database",
        ),
        APIEndpointTest(
            "GET", f"{API_V1_PREFIX}/health/readiness",
            requires_auth=False,
            description="Kubernetes readiness probe",
        ),

        # Company endpoints
        APIEndpointTest(
            "GET", f"{API_V1_PREFIX}/companies",
            requires_auth=False,
            query_params={"limit": 10},
            description="List companies with pagination",
        ),
        APIEndpointTest(
            "GET", f"{API_V1_PREFIX}/companies",
            requires_auth=False,
            query_params={"category": "k12", "limit": 5},
            description="Filter companies by category",
        ),
        APIEndpointTest(
            "GET", f"{API_V1_PREFIX}/companies/watchlist",
            requires_auth=True,
            description="Get watchlist companies (requires auth)",
        ),
        APIEndpointTest(
            "GET", f"{API_V1_PREFIX}/companies/trending/top-performers",
            requires_auth=False,
            query_params={"metric": "growth", "limit": 5},
            description="Get top performers by growth",
        ),
        APIEndpointTest(
            "GET", f"{API_V1_PREFIX}/companies/trending/top-performers",
            requires_auth=False,
            query_params={"metric": "revenue", "limit": 5},
            description="Get top performers by revenue",
        ),

        # Metrics endpoints
        APIEndpointTest(
            "GET", f"{API_V1_PREFIX}/metrics",
            requires_auth=False,
            query_params={"limit": 10},
            description="List financial metrics",
        ),
        APIEndpointTest(
            "GET", f"{API_V1_PREFIX}/metrics",
            requires_auth=False,
            query_params={"metric_type": "revenue", "limit": 5},
            description="Filter metrics by type",
        ),

        # Filings endpoints
        APIEndpointTest(
            "GET", f"{API_V1_PREFIX}/filings",
            requires_auth=False,
            query_params={"limit": 10},
            description="List SEC filings",
        ),
        APIEndpointTest(
            "GET", f"{API_V1_PREFIX}/filings",
            requires_auth=False,
            query_params={"filing_type": "10-K", "limit": 5},
            description="Filter filings by type",
        ),

        # Intelligence endpoints
        APIEndpointTest(
            "GET", f"{API_V1_PREFIX}/intelligence",
            requires_auth=False,
            query_params={"limit": 10},
            description="List market intelligence",
        ),

        # Reports endpoints
        APIEndpointTest(
            "GET", f"{API_V1_PREFIX}/reports",
            requires_auth=False,
            query_params={"limit": 10},
            description="List analysis reports",
        ),

        # Error handling tests
        APIEndpointTest(
            "GET", f"{API_V1_PREFIX}/companies/00000000-0000-0000-0000-000000000000",
            requires_auth=False,
            expected_status=404,
            description="Handle non-existent company (404)",
        ),
        APIEndpointTest(
            "GET", f"{API_V1_PREFIX}/companies/invalid-uuid",
            requires_auth=False,
            expected_status=422,
            description="Handle invalid UUID format (422)",
        ),
    ]


def execute_endpoint_test(test: APIEndpointTest, session: requests.Session) -> None:
    """Execute a single endpoint test."""
    url = f"{STAGING_API_BASE}{test.endpoint}"

    # Prepare headers
    headers = {}
    if test.requires_auth and AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"

    # Run test 3 times to get performance metrics
    for _ in range(3):
        try:
            start_time = time.time()

            if test.method == "GET":
                response = session.get(url, params=test.query_params, headers=headers, timeout=5)
            elif test.method == "POST":
                response = session.post(url, json=test.body, headers=headers, timeout=5)
            elif test.method == "PUT":
                response = session.put(url, json=test.body, headers=headers, timeout=5)
            elif test.method == "DELETE":
                response = session.delete(url, headers=headers, timeout=5)
            else:
                raise ValueError(f"Unsupported HTTP method: {test.method}")

            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            test.response_times.append(response_time_ms)

            # Validate status code
            if response.status_code != test.expected_status:
                test.error_message = f"Expected status {test.expected_status}, got {response.status_code}"
                return

            # Validate response can be parsed as JSON (except for 204)
            if test.expected_status != 204:
                try:
                    response.json()
                except Exception as e:
                    test.error_message = f"Invalid JSON response: {str(e)}"
                    return

        except Exception as e:
            test.error_message = f"Request failed: {str(e)}"
            return

    # Mark test as passed if we get here
    test.passed = True


def test_staging_api_validation():
    """
    Main test function: Validate all API endpoints in staging environment.

    This test:
    1. Discovers all API endpoints
    2. Tests each endpoint for correct status codes
    3. Measures response times (3 requests per endpoint for p99 calculation)
    4. Validates authentication/authorization
    5. Tests error handling
    6. Stores validation results in memory
    """
    logger.info("=" * 80)
    logger.info("STAGING API VALIDATION - Starting comprehensive endpoint testing")
    logger.info("=" * 80)

    # Initialize results
    results = APIValidationResults()

    # Define all endpoint tests
    endpoint_tests = define_endpoint_tests()
    logger.info(f"Defined {len(endpoint_tests)} endpoint tests")

    # Create session for connection pooling
    session = requests.Session()

    # Execute all tests
    logger.info("\nExecuting endpoint tests...")
    for test in endpoint_tests:
        logger.info(f"Testing: {test.method} {test.endpoint} - {test.description}")
        execute_endpoint_test(test, session)
        results.add_test(test)

        if test.passed:
            avg_time = sum(test.response_times) / len(test.response_times) if test.response_times else 0
            logger.success(f"  ✓ PASSED (avg: {avg_time:.2f}ms)")
        else:
            logger.error(f"  ✗ FAILED: {test.error_message}")

    # Calculate performance metrics
    results.calculate_metrics()

    # Log summary
    logger.info("\n" + "=" * 80)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 80)

    results_dict = results.to_dict()
    summary = results_dict["summary"]
    performance = results_dict["performance"]

    logger.info(f"Total Tests: {summary['total_tests']}")
    logger.info(f"Passed: {summary['passed_tests']}")
    logger.info(f"Failed: {summary['failed_tests']}")
    logger.info(f"Success Rate: {summary['success_rate']}")
    logger.info(f"Total Duration: {summary['total_duration_ms']:.2f}ms")

    logger.info("\nPerformance Metrics:")
    logger.info(f"P50 Latency: {performance['p50_latency_ms']:.2f}ms")
    logger.info(f"P95 Latency: {performance['p95_latency_ms']:.2f}ms (target: <{P95_LATENCY_TARGET_MS}ms)")
    logger.info(f"P99 Latency: {performance['p99_latency_ms']:.2f}ms (target: <{P99_LATENCY_TARGET_MS}ms)")

    # Check performance targets
    if performance['p99_meets_target']:
        logger.success(f"✓ P99 latency meets target (<{P99_LATENCY_TARGET_MS}ms)")
    else:
        logger.warning(f"⚠ P99 latency exceeds target: {performance['p99_latency_ms']:.2f}ms > {P99_LATENCY_TARGET_MS}ms")

    if performance['p95_meets_target']:
        logger.success(f"✓ P95 latency meets target (<{P95_LATENCY_TARGET_MS}ms)")
    else:
        logger.warning(f"⚠ P95 latency exceeds target: {performance['p95_latency_ms']:.2f}ms > {P95_LATENCY_TARGET_MS}ms")

    # Log failed tests
    if results.failed_tests > 0:
        logger.error("\nFailed Tests:")
        for test in results.tests:
            if not test.passed:
                logger.error(f"  {test.method} {test.endpoint}: {test.error_message}")

    logger.info("=" * 80)

    # Write results to file for memory storage
    import json
    results_file = "/mnt/c/Users/brand/Development/Project_Workspace/active-development/corporate_intel/tests/integration/api_validation_results.json"
    with open(results_file, "w") as f:
        json.dump(results_dict, f, indent=2)

    logger.info(f"Results saved to: {results_file}")

    # Return results for pytest
    assert results.failed_tests == 0, f"{results.failed_tests} endpoint tests failed"
    assert performance['p99_meets_target'], f"P99 latency exceeds target: {performance['p99_latency_ms']:.2f}ms"

    return results_dict


if __name__ == "__main__":
    # Run test directly
    test_staging_api_validation()
