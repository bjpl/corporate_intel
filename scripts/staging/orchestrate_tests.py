#!/usr/bin/env python3
"""
Test Orchestrator - Parallel Test Execution and Reporting
Manages test execution, aggregation, and failure reporting for staging validation.
"""

import asyncio
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import xml.etree.ElementTree as ET


@dataclass
class TestResult:
    """Container for test execution results."""
    suite: str
    passed: int
    failed: int
    skipped: int
    errors: int
    duration: float
    timestamp: datetime
    failures: List[Dict[str, str]]

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped + self.errors

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100


@dataclass
class TestExecution:
    """Container for overall test execution."""
    results: List[TestResult]
    total_duration: float
    start_time: datetime
    end_time: datetime
    retried_tests: List[str]

    @property
    def total_passed(self) -> int:
        return sum(r.passed for r in self.results)

    @property
    def total_failed(self) -> int:
        return sum(r.failed for r in self.results)

    @property
    def total_skipped(self) -> int:
        return sum(r.skipped for r in self.results)

    @property
    def total_tests(self) -> int:
        return sum(r.total for r in self.results)

    @property
    def overall_success_rate(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.total_passed / self.total_tests) * 100


class TestOrchestrator:
    """Orchestrate parallel test execution with retry logic and reporting."""

    def __init__(
        self,
        max_workers: int = 4,
        max_retries: int = 2,
        output_dir: Optional[Path] = None
    ):
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.output_dir = output_dir or Path("test-results")
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Test suites to execute
        self.test_suites = {
            "unit": "tests/unit",
            "integration": "tests/integration",
            "api": "tests/api",
            "staging": "tests/staging",
            "services": "tests/services"
        }

    def run_test_suite(
        self,
        suite_name: str,
        suite_path: str,
        attempt: int = 1
    ) -> Tuple[str, TestResult]:
        """Execute a single test suite with pytest."""
        print(f"🔬 Running {suite_name} tests (attempt {attempt})...")

        junit_file = self.output_dir / f"junit-{suite_name}.xml"
        coverage_file = self.output_dir / f".coverage.{suite_name}"

        cmd = [
            "pytest",
            suite_path,
            "-v",
            "--tb=short",
            f"--junitxml={junit_file}",
            f"--cov=src",
            f"--cov-report=term-missing",
            f"--cov-report=html:{self.output_dir}/coverage-{suite_name}",
            "--cov-report=json",
            "-n", "auto",  # Parallel execution within suite
            "--maxfail=5",  # Stop after 5 failures
        ]

        start = datetime.now()

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                env={**subprocess.os.environ, "COVERAGE_FILE": str(coverage_file)}
            )

            duration = (datetime.now() - start).total_seconds()

            # Parse JUnit XML results
            test_result = self._parse_junit_xml(junit_file, suite_name, duration, start)

            return suite_name, test_result

        except subprocess.TimeoutExpired:
            print(f"❌ {suite_name} tests timed out")
            return suite_name, TestResult(
                suite=suite_name,
                passed=0,
                failed=1,
                skipped=0,
                errors=1,
                duration=600,
                timestamp=start,
                failures=[{"error": "Test suite timeout"}]
            )
        except Exception as e:
            print(f"❌ {suite_name} tests failed: {e}")
            return suite_name, TestResult(
                suite=suite_name,
                passed=0,
                failed=1,
                skipped=0,
                errors=1,
                duration=(datetime.now() - start).total_seconds(),
                timestamp=start,
                failures=[{"error": str(e)}]
            )

    def _parse_junit_xml(
        self,
        junit_file: Path,
        suite_name: str,
        duration: float,
        timestamp: datetime
    ) -> TestResult:
        """Parse JUnit XML output to extract test results."""
        if not junit_file.exists():
            return TestResult(
                suite=suite_name,
                passed=0,
                failed=1,
                skipped=0,
                errors=1,
                duration=duration,
                timestamp=timestamp,
                failures=[{"error": "JUnit XML not generated"}]
            )

        try:
            tree = ET.parse(junit_file)
            root = tree.getroot()

            testsuite = root.find(".//testsuite") or root

            passed = int(testsuite.get("tests", 0)) - int(testsuite.get("failures", 0)) - int(testsuite.get("errors", 0)) - int(testsuite.get("skipped", 0))
            failed = int(testsuite.get("failures", 0))
            errors = int(testsuite.get("errors", 0))
            skipped = int(testsuite.get("skipped", 0))

            # Extract failure details
            failures = []
            for testcase in root.findall(".//testcase"):
                failure = testcase.find("failure")
                error = testcase.find("error")

                if failure is not None:
                    failures.append({
                        "test": testcase.get("name", "unknown"),
                        "classname": testcase.get("classname", ""),
                        "message": failure.get("message", ""),
                        "type": "failure"
                    })
                elif error is not None:
                    failures.append({
                        "test": testcase.get("name", "unknown"),
                        "classname": testcase.get("classname", ""),
                        "message": error.get("message", ""),
                        "type": "error"
                    })

            return TestResult(
                suite=suite_name,
                passed=passed,
                failed=failed,
                skipped=skipped,
                errors=errors,
                duration=duration,
                timestamp=timestamp,
                failures=failures
            )

        except Exception as e:
            print(f"⚠️  Failed to parse JUnit XML for {suite_name}: {e}")
            return TestResult(
                suite=suite_name,
                passed=0,
                failed=1,
                skipped=0,
                errors=1,
                duration=duration,
                timestamp=timestamp,
                failures=[{"error": f"XML parsing error: {e}"}]
            )

    def should_retry(self, result: TestResult) -> bool:
        """Determine if a test suite should be retried."""
        # Retry if there are failures but not too many
        if result.failed > 0 and result.failed <= 3:
            return True
        return False

    def execute_with_retry(
        self,
        suite_name: str,
        suite_path: str
    ) -> Tuple[str, TestResult, int]:
        """Execute test suite with retry logic."""
        retries = 0
        result = None

        for attempt in range(1, self.max_retries + 1):
            suite_name_result, result = self.run_test_suite(
                suite_name,
                suite_path,
                attempt
            )

            if not self.should_retry(result) or attempt == self.max_retries:
                break

            print(f"🔄 Retrying {suite_name} tests (attempt {attempt + 1}/{self.max_retries})...")
            retries = attempt

        return suite_name, result, retries

    def run_all_tests(self) -> TestExecution:
        """Execute all test suites in parallel."""
        print("🚀 Starting parallel test execution...")
        start_time = datetime.now()

        results = []
        retried_tests = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all test suites
            future_to_suite = {
                executor.submit(self.execute_with_retry, name, path): name
                for name, path in self.test_suites.items()
            }

            # Collect results as they complete
            for future in as_completed(future_to_suite):
                suite_name = future_to_suite[future]
                try:
                    name, result, retries = future.result()
                    results.append(result)

                    if retries > 0:
                        retried_tests.append(f"{name} (retried {retries} times)")

                    # Print summary
                    status = "✅" if result.failed == 0 else "❌"
                    print(f"{status} {name}: {result.passed}/{result.total} passed ({result.success_rate:.1f}%)")

                except Exception as e:
                    print(f"❌ Failed to execute {suite_name}: {e}")

        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()

        execution = TestExecution(
            results=results,
            total_duration=total_duration,
            start_time=start_time,
            end_time=end_time,
            retried_tests=retried_tests
        )

        self._save_execution_summary(execution)

        return execution

    def _save_execution_summary(self, execution: TestExecution):
        """Save test execution summary to JSON."""
        summary_file = self.output_dir / "test-execution-summary.json"

        summary = {
            "start_time": execution.start_time.isoformat(),
            "end_time": execution.end_time.isoformat(),
            "total_duration": execution.total_duration,
            "total_tests": execution.total_tests,
            "total_passed": execution.total_passed,
            "total_failed": execution.total_failed,
            "total_skipped": execution.total_skipped,
            "overall_success_rate": execution.overall_success_rate,
            "retried_tests": execution.retried_tests,
            "results": [
                {
                    "suite": r.suite,
                    "passed": r.passed,
                    "failed": r.failed,
                    "skipped": r.skipped,
                    "errors": r.errors,
                    "duration": r.duration,
                    "success_rate": r.success_rate,
                    "failures": r.failures[:5]  # First 5 failures
                }
                for r in execution.results
            ]
        }

        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"\n📊 Test summary saved to {summary_file}")

    def print_summary(self, execution: TestExecution):
        """Print human-readable test execution summary."""
        print("\n" + "="*80)
        print("📊 TEST EXECUTION SUMMARY")
        print("="*80)
        print(f"Duration: {execution.total_duration:.2f}s")
        print(f"Total Tests: {execution.total_tests}")
        print(f"✅ Passed: {execution.total_passed}")
        print(f"❌ Failed: {execution.total_failed}")
        print(f"⏭️  Skipped: {execution.total_skipped}")
        print(f"Success Rate: {execution.overall_success_rate:.1f}%")

        if execution.retried_tests:
            print(f"\n🔄 Retried Tests:")
            for test in execution.retried_tests:
                print(f"  - {test}")

        print("\n📋 Suite Breakdown:")
        for result in sorted(execution.results, key=lambda r: r.success_rate):
            status = "✅" if result.failed == 0 else "❌"
            print(f"  {status} {result.suite:20s} {result.passed:3d}/{result.total:3d} ({result.success_rate:5.1f}%)")

        if execution.total_failed > 0:
            print("\n❌ FAILURES:")
            for result in execution.results:
                if result.failures:
                    print(f"\n  {result.suite}:")
                    for failure in result.failures[:3]:  # Show first 3
                        print(f"    - {failure.get('test', 'unknown')}: {failure.get('message', 'no message')[:100]}")

        print("="*80 + "\n")


def main():
    """Main entry point."""
    orchestrator = TestOrchestrator(
        max_workers=4,
        max_retries=2,
        output_dir=Path("test-results")
    )

    execution = orchestrator.run_all_tests()
    orchestrator.print_summary(execution)

    # Exit with appropriate code
    if execution.total_failed > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
