#!/usr/bin/env python3
"""
Test Report Generator - HTML Dashboard and Visualizations
Generates comprehensive test reports with coverage, trends, and failure analysis.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import xml.etree.ElementTree as ET


class TestReportGenerator:
    """Generate comprehensive HTML test reports with visualizations."""

    def __init__(self, results_dir: Path, output_dir: Optional[Path] = None):
        self.results_dir = results_dir
        self.output_dir = output_dir or results_dir / "reports"
        self.output_dir.mkdir(exist_ok=True, parents=True)

    def load_execution_summary(self) -> Dict:
        """Load test execution summary from JSON."""
        summary_file = self.results_dir / "test-execution-summary.json"
        if not summary_file.exists():
            raise FileNotFoundError(f"Test summary not found: {summary_file}")

        with open(summary_file) as f:
            return json.load(f)

    def load_coverage_data(self) -> Optional[Dict]:
        """Load coverage data from coverage.json."""
        coverage_file = self.results_dir / "coverage.json"
        if not coverage_file.exists():
            return None

        with open(coverage_file) as f:
            return json.load(f)

    def generate_html_report(self) -> Path:
        """Generate comprehensive HTML test report."""
        summary = self.load_execution_summary()
        coverage = self.load_coverage_data()

        html = self._build_html_report(summary, coverage)

        report_file = self.output_dir / f"test-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
        with open(report_file, "w") as f:
            f.write(html)

        # Also create a "latest" symlink
        latest_link = self.output_dir / "test-report-latest.html"
        if latest_link.exists():
            latest_link.unlink()
        latest_link.symlink_to(report_file.name)

        return report_file

    def _build_html_report(self, summary: Dict, coverage: Optional[Dict]) -> str:
        """Build HTML report content."""
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Report - {summary['start_time']}</title>
    <style>
        {self._get_css_styles()}
    </style>
    <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
</head>
<body>
    <div class="container">
        <header>
            <h1>🧪 Test Execution Report</h1>
            <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>

        {self._build_summary_section(summary)}
        {self._build_suite_breakdown(summary)}
        {self._build_failure_analysis(summary)}
        {self._build_coverage_section(coverage) if coverage else ''}
        {self._build_performance_section(summary)}
        {self._build_retry_section(summary)}
    </div>

    <script>
        {self._get_javascript()}
    </script>
</body>
</html>
"""
        return html

    def _get_css_styles(self) -> str:
        """Get CSS styles for the report."""
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }

        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }

        header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }

        .timestamp {
            opacity: 0.9;
            font-size: 0.9rem;
        }

        .section {
            padding: 40px;
            border-bottom: 1px solid #e0e0e0;
        }

        .section:last-child {
            border-bottom: none;
        }

        .section h2 {
            color: #667eea;
            margin-bottom: 20px;
            font-size: 1.8rem;
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }

        .metric-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            transition: transform 0.2s;
        }

        .metric-card:hover {
            transform: translateY(-5px);
        }

        .metric-card.success {
            background: linear-gradient(135deg, #56ab2f 0%, #a8e063 100%);
            color: white;
        }

        .metric-card.failure {
            background: linear-gradient(135deg, #ee0979 0%, #ff6a00 100%);
            color: white;
        }

        .metric-card.warning {
            background: linear-gradient(135deg, #f2994a 0%, #f2c94c 100%);
            color: white;
        }

        .metric-value {
            font-size: 3rem;
            font-weight: bold;
            margin: 10px 0;
        }

        .metric-label {
            font-size: 0.9rem;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .suite-list {
            margin-top: 20px;
        }

        .suite-item {
            background: #f8f9fa;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }

        .suite-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .suite-name {
            font-size: 1.2rem;
            font-weight: bold;
            color: #333;
        }

        .suite-status {
            font-size: 1.5rem;
        }

        .progress-bar {
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            position: relative;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #56ab2f 0%, #a8e063 100%);
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 0.9rem;
        }

        .failure-list {
            background: #fff5f5;
            border-left: 4px solid #e53e3e;
            padding: 20px;
            margin-top: 20px;
            border-radius: 8px;
        }

        .failure-item {
            margin-bottom: 15px;
            padding-bottom: 15px;
            border-bottom: 1px solid #fed7d7;
        }

        .failure-item:last-child {
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }

        .failure-test {
            font-weight: bold;
            color: #c53030;
            margin-bottom: 5px;
        }

        .failure-message {
            color: #742a2a;
            font-family: monospace;
            font-size: 0.9rem;
            background: white;
            padding: 10px;
            border-radius: 4px;
            margin-top: 5px;
        }

        .chart-container {
            margin: 30px 0;
            min-height: 400px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }

        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }

        th {
            background: #f8f9fa;
            font-weight: bold;
            color: #667eea;
        }

        tr:hover {
            background: #f8f9fa;
        }

        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: bold;
        }

        .badge-success {
            background: #c6f6d5;
            color: #22543d;
        }

        .badge-failure {
            background: #fed7d7;
            color: #742a2a;
        }

        .badge-warning {
            background: #feebc8;
            color: #7c2d12;
        }
        """

    def _build_summary_section(self, summary: Dict) -> str:
        """Build summary metrics section."""
        success_rate = summary['overall_success_rate']
        card_class = 'success' if success_rate >= 95 else 'failure' if success_rate < 80 else 'warning'

        return f"""
        <section class="section">
            <h2>📊 Overall Summary</h2>
            <div class="summary-grid">
                <div class="metric-card {card_class}">
                    <div class="metric-label">Success Rate</div>
                    <div class="metric-value">{success_rate:.1f}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Total Tests</div>
                    <div class="metric-value">{summary['total_tests']}</div>
                </div>
                <div class="metric-card success">
                    <div class="metric-label">Passed</div>
                    <div class="metric-value">{summary['total_passed']}</div>
                </div>
                <div class="metric-card failure">
                    <div class="metric-label">Failed</div>
                    <div class="metric-value">{summary['total_failed']}</div>
                </div>
                <div class="metric-card warning">
                    <div class="metric-label">Skipped</div>
                    <div class="metric-value">{summary['total_skipped']}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Duration</div>
                    <div class="metric-value">{summary['total_duration']:.1f}s</div>
                </div>
            </div>
        </section>
        """

    def _build_suite_breakdown(self, summary: Dict) -> str:
        """Build suite breakdown section."""
        suites_html = ""

        for result in sorted(summary['results'], key=lambda r: r['success_rate']):
            status = "✅" if result['failed'] == 0 else "❌"
            progress_pct = result['success_rate']

            suites_html += f"""
            <div class="suite-item">
                <div class="suite-header">
                    <div class="suite-name">{status} {result['suite']}</div>
                    <div class="suite-status">{result['passed']}/{result['passed'] + result['failed'] + result['skipped']}</div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {progress_pct}%">
                        {progress_pct:.1f}%
                    </div>
                </div>
                <div style="margin-top: 10px; font-size: 0.9rem; color: #666;">
                    Duration: {result['duration']:.2f}s |
                    Failed: {result['failed']} |
                    Errors: {result['errors']} |
                    Skipped: {result['skipped']}
                </div>
            </div>
            """

        return f"""
        <section class="section">
            <h2>📋 Suite Breakdown</h2>
            <div class="suite-list">
                {suites_html}
            </div>
        </section>
        """

    def _build_failure_analysis(self, summary: Dict) -> str:
        """Build failure analysis section."""
        failures = []
        for result in summary['results']:
            for failure in result.get('failures', []):
                failures.append({
                    'suite': result['suite'],
                    **failure
                })

        if not failures:
            return """
            <section class="section">
                <h2>✅ No Failures</h2>
                <p style="color: #22543d; font-size: 1.1rem; margin-top: 20px;">
                    All tests passed successfully! 🎉
                </p>
            </section>
            """

        failures_html = ""
        for failure in failures[:10]:  # Show first 10
            failures_html += f"""
            <div class="failure-item">
                <div class="failure-test">
                    {failure.get('suite', '')} :: {failure.get('test', 'Unknown')}
                </div>
                <div style="color: #666; font-size: 0.9rem; margin: 5px 0;">
                    {failure.get('classname', '')}
                </div>
                <div class="failure-message">
                    {failure.get('message', 'No message')[:500]}
                </div>
            </div>
            """

        return f"""
        <section class="section">
            <h2>❌ Failure Analysis</h2>
            <div class="failure-list">
                {failures_html}
            </div>
        </section>
        """

    def _build_coverage_section(self, coverage: Dict) -> str:
        """Build coverage visualization section."""
        totals = coverage.get('totals', {})
        percent_covered = totals.get('percent_covered', 0)

        coverage_class = 'success' if percent_covered >= 80 else 'warning' if percent_covered >= 60 else 'failure'

        return f"""
        <section class="section">
            <h2>📈 Code Coverage</h2>
            <div class="summary-grid">
                <div class="metric-card {coverage_class}">
                    <div class="metric-label">Coverage</div>
                    <div class="metric-value">{percent_covered:.1f}%</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Statements</div>
                    <div class="metric-value">{totals.get('num_statements', 0)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Missing</div>
                    <div class="metric-value">{totals.get('missing_lines', 0)}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Branches</div>
                    <div class="metric-value">{totals.get('num_branches', 0)}</div>
                </div>
            </div>
            <div class="chart-container" id="coverage-chart"></div>
        </section>
        """

    def _build_performance_section(self, summary: Dict) -> str:
        """Build performance metrics section."""
        return f"""
        <section class="section">
            <h2>⚡ Performance Metrics</h2>
            <div class="chart-container" id="performance-chart"></div>
            <table>
                <thead>
                    <tr>
                        <th>Suite</th>
                        <th>Duration</th>
                        <th>Tests</th>
                        <th>Avg Time/Test</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(f"""
                    <tr>
                        <td>{r['suite']}</td>
                        <td>{r['duration']:.2f}s</td>
                        <td>{r['passed'] + r['failed'] + r['skipped']}</td>
                        <td>{r['duration'] / max(r['passed'] + r['failed'], 1):.3f}s</td>
                    </tr>
                    """ for r in sorted(summary['results'], key=lambda x: x['duration'], reverse=True))}
                </tbody>
            </table>
        </section>
        """

    def _build_retry_section(self, summary: Dict) -> str:
        """Build retry analysis section."""
        if not summary.get('retried_tests'):
            return ""

        return f"""
        <section class="section">
            <h2>🔄 Retried Tests</h2>
            <p style="margin-bottom: 15px; color: #666;">
                The following tests were retried due to initial failures:
            </p>
            <ul style="list-style: none; padding: 0;">
                {''.join(f'<li style="padding: 8px; background: #fef3c7; margin: 5px 0; border-radius: 4px;">⚠️ {test}</li>' for test in summary['retried_tests'])}
            </ul>
        </section>
        """

    def _get_javascript(self) -> str:
        """Get JavaScript for interactive charts."""
        return """
        // Add any interactive chart code here using Plotly
        console.log('Test report generated successfully');
        """


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) > 1:
        results_dir = Path(sys.argv[1])
    else:
        results_dir = Path("test-results")

    generator = TestReportGenerator(results_dir)
    report_file = generator.generate_html_report()

    print(f"✅ Test report generated: {report_file}")
    print(f"📊 View report: file://{report_file.absolute()}")


if __name__ == "__main__":
    main()
