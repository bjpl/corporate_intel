"""
User Acceptance Testing (UAT) Framework
Validates user stories, dashboard interactions, and business requirements.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
import httpx
from sqlalchemy import create_engine, text


class UserStory:
    """Represents a user story for UAT."""

    def __init__(
        self,
        story_id: str,
        title: str,
        description: str,
        acceptance_criteria: List[str]
    ):
        self.story_id = story_id
        self.title = title
        self.description = description
        self.acceptance_criteria = acceptance_criteria
        self.results: List[tuple[str, bool, str]] = []

    def add_result(self, criterion: str, passed: bool, details: str = ""):
        """Add test result for an acceptance criterion."""
        self.results.append((criterion, passed, details))

    def passed(self) -> bool:
        """Check if all acceptance criteria passed."""
        return all(passed for _, passed, _ in self.results)

    def summary(self) -> str:
        """Get summary of test results."""
        passed_count = sum(1 for _, passed, _ in self.results if passed)
        total = len(self.results)
        return f"{self.story_id}: {passed_count}/{total} criteria passed"


@pytest.fixture
def staging_client():
    """HTTP client for staging API."""
    return httpx.AsyncClient(
        base_url="http://localhost:8000",
        timeout=30.0
    )


@pytest.fixture
def database():
    """Database connection."""
    engine = create_engine(
        "postgresql://corpintel_user:your_password@localhost:5432/corporate_intel"
    )
    return engine


@pytest.mark.asyncio
async def test_user_story_view_company_list(staging_client: httpx.AsyncClient):
    """
    USER STORY: As an analyst, I want to view a list of companies
    so that I can select one for detailed analysis.

    Acceptance Criteria:
    1. Companies are displayed in a paginated list
    2. Each company shows ticker, name, and sector
    3. List can be filtered by sector
    4. List can be sorted by various fields
    5. Response time is under 500ms
    """
    story = UserStory(
        story_id="US-001",
        title="View Company List",
        description="Analyst views paginated company list with filtering",
        acceptance_criteria=[
            "Companies displayed in paginated list",
            "Shows ticker, name, sector",
            "Can filter by sector",
            "Can sort by fields",
            "Response under 500ms"
        ]
    )

    # Test 1: Basic company list
    start = asyncio.get_event_loop().time()
    response = await staging_client.get("/api/v1/companies?limit=10&offset=0")
    duration = asyncio.get_event_loop().time() - start

    if response.status_code == 200:
        data = response.json()
        has_companies = len(data.get("companies", [])) > 0
        has_pagination = "total" in data and "limit" in data
        story.add_result(
            "Companies displayed in paginated list",
            has_companies and has_pagination,
            f"Found {len(data.get('companies', []))} companies"
        )
    else:
        story.add_result("Companies displayed in paginated list", False, f"Status: {response.status_code}")

    # Test 2: Company data structure
    if response.status_code == 200:
        data = response.json()
        companies = data.get("companies", [])
        if companies:
            company = companies[0]
            has_required_fields = all(
                field in company for field in ["ticker", "name", "sector"]
            )
            story.add_result(
                "Shows ticker, name, sector",
                has_required_fields,
                f"Fields: {list(company.keys())}"
            )
        else:
            story.add_result("Shows ticker, name, sector", False, "No companies found")

    # Test 3: Sector filtering
    sector_response = await staging_client.get("/api/v1/companies?sector=Technology")
    if sector_response.status_code == 200:
        sector_data = sector_response.json()
        companies = sector_data.get("companies", [])
        all_tech = all(c.get("sector") == "Technology" for c in companies if "sector" in c)
        story.add_result(
            "Can filter by sector",
            all_tech or len(companies) == 0,
            f"Found {len(companies)} tech companies"
        )
    else:
        story.add_result("Can filter by sector", False, f"Status: {sector_response.status_code}")

    # Test 4: Sorting
    sort_response = await staging_client.get("/api/v1/companies?sort_by=name&limit=5")
    if sort_response.status_code == 200:
        sort_data = sort_response.json()
        companies = sort_data.get("companies", [])
        names = [c.get("name", "") for c in companies]
        is_sorted = names == sorted(names)
        story.add_result(
            "Can sort by fields",
            is_sorted or len(companies) < 2,
            f"Names: {names[:3]}"
        )
    else:
        story.add_result("Can sort by fields", False, f"Status: {sort_response.status_code}")

    # Test 5: Response time
    story.add_result(
        "Response under 500ms",
        duration < 0.5,
        f"Response time: {duration*1000:.2f}ms"
    )

    # Report
    print(f"\n{story.summary()}")
    for criterion, passed, details in story.results:
        status = "✅" if passed else "❌"
        print(f"  {status} {criterion}: {details}")

    assert story.passed(), f"User story failed: {story.summary()}"


@pytest.mark.asyncio
async def test_user_story_view_financial_metrics(staging_client: httpx.AsyncClient):
    """
    USER STORY: As an analyst, I want to view financial metrics for a company
    so that I can assess its financial health.

    Acceptance Criteria:
    1. Metrics include revenue, profit, margins
    2. Historical data is available
    3. Metrics are formatted correctly
    4. Charts can be generated
    5. Data is accurate (matches source)
    """
    story = UserStory(
        story_id="US-002",
        title="View Financial Metrics",
        description="Analyst views financial metrics for company analysis",
        acceptance_criteria=[
            "Shows revenue, profit, margins",
            "Historical data available",
            "Correct formatting",
            "Charts available",
            "Data accuracy verified"
        ]
    )

    # Test with a known company (AAPL)
    ticker = "AAPL"

    # Test 1: Metrics availability
    response = await staging_client.get(f"/api/v1/metrics/{ticker}")
    if response.status_code == 200:
        data = response.json()
        metrics = data.get("metrics", {})
        has_required = all(
            field in metrics
            for field in ["revenue", "net_income", "gross_margin"]
        )
        story.add_result(
            "Shows revenue, profit, margins",
            has_required,
            f"Fields: {list(metrics.keys())[:5]}"
        )
    else:
        story.add_result("Shows revenue, profit, margins", False, f"Status: {response.status_code}")

    # Test 2: Historical data
    hist_response = await staging_client.get(
        f"/api/v1/metrics/{ticker}/history?period=1y"
    )
    if hist_response.status_code == 200:
        hist_data = hist_response.json()
        history = hist_data.get("history", [])
        has_history = len(history) > 0
        story.add_result(
            "Historical data available",
            has_history,
            f"Found {len(history)} historical records"
        )
    else:
        story.add_result("Historical data available", False, f"Status: {hist_response.status_code}")

    # Test 3: Formatting
    if response.status_code == 200:
        data = response.json()
        metrics = data.get("metrics", {})
        # Check that numeric values are properly formatted
        revenue = metrics.get("revenue")
        is_numeric = isinstance(revenue, (int, float)) if revenue is not None else False
        story.add_result(
            "Correct formatting",
            is_numeric,
            f"Revenue type: {type(revenue).__name__}"
        )

    # Test 4: Chart data
    chart_response = await staging_client.get(f"/api/v1/metrics/{ticker}/chart")
    chart_available = chart_response.status_code == 200
    story.add_result(
        "Charts available",
        chart_available,
        f"Chart endpoint status: {chart_response.status_code}"
    )

    # Test 5: Data accuracy (basic check)
    if response.status_code == 200:
        data = response.json()
        metrics = data.get("metrics", {})
        # Basic sanity checks
        revenue = metrics.get("revenue", 0)
        net_income = metrics.get("net_income", 0)
        is_reasonable = revenue > 0 and abs(net_income) < revenue
        story.add_result(
            "Data accuracy verified",
            is_reasonable,
            f"Revenue: ${revenue:,.0f}, Net Income: ${net_income:,.0f}"
        )

    # Report
    print(f"\n{story.summary()}")
    for criterion, passed, details in story.results:
        status = "✅" if passed else "❌"
        print(f"  {status} {criterion}: {details}")

    assert story.passed(), f"User story failed: {story.summary()}"


@pytest.mark.asyncio
async def test_user_story_generate_report(staging_client: httpx.AsyncClient):
    """
    USER STORY: As an analyst, I want to generate a competitive analysis report
    so that I can share insights with stakeholders.

    Acceptance Criteria:
    1. Report can be generated for a sector
    2. Report includes key metrics and insights
    3. Report generation completes in reasonable time
    4. Report is downloadable in multiple formats
    5. Report contains accurate data
    """
    story = UserStory(
        story_id="US-003",
        title="Generate Report",
        description="Analyst generates and downloads competitive analysis report",
        acceptance_criteria=[
            "Report generated for sector",
            "Includes metrics and insights",
            "Completes in reasonable time",
            "Multiple formats available",
            "Data is accurate"
        ]
    )

    sector = "Technology"

    # Test 1: Report generation
    start = asyncio.get_event_loop().time()
    response = await staging_client.post(
        "/api/v1/reports/generate",
        json={"sector": sector, "report_type": "competitive_analysis"}
    )
    duration = asyncio.get_event_loop().time() - start

    if response.status_code in [200, 201, 202]:
        data = response.json()
        has_report_id = "report_id" in data or "id" in data
        story.add_result(
            "Report generated for sector",
            has_report_id,
            f"Status: {response.status_code}"
        )
        report_id = data.get("report_id") or data.get("id")
    else:
        story.add_result("Report generated for sector", False, f"Status: {response.status_code}")
        report_id = None

    # Test 2: Report contents
    if report_id:
        report_response = await staging_client.get(f"/api/v1/reports/{report_id}")
        if report_response.status_code == 200:
            report_data = report_response.json()
            has_content = "content" in report_data or "data" in report_data
            story.add_result(
                "Includes metrics and insights",
                has_content,
                f"Keys: {list(report_data.keys())}"
            )
        else:
            story.add_result("Includes metrics and insights", False, f"Status: {report_response.status_code}")

    # Test 3: Generation time
    story.add_result(
        "Completes in reasonable time",
        duration < 10.0,
        f"Generation time: {duration:.2f}s"
    )

    # Test 4: Multiple formats
    if report_id:
        formats_tested = []
        for fmt in ["json", "pdf", "html"]:
            fmt_response = await staging_client.get(
                f"/api/v1/reports/{report_id}?format={fmt}"
            )
            if fmt_response.status_code == 200:
                formats_tested.append(fmt)

        story.add_result(
            "Multiple formats available",
            len(formats_tested) > 0,
            f"Available formats: {formats_tested}"
        )

    # Test 5: Data accuracy
    if report_id:
        report_response = await staging_client.get(f"/api/v1/reports/{report_id}")
        if report_response.status_code == 200:
            report_data = report_response.json()
            # Basic validation
            has_sector = report_data.get("sector") == sector
            story.add_result(
                "Data is accurate",
                has_sector,
                f"Sector matches: {has_sector}"
            )
        else:
            story.add_result("Data is accurate", False, "Could not verify")

    # Report
    print(f"\n{story.summary()}")
    for criterion, passed, details in story.results:
        status = "✅" if passed else "❌"
        print(f"  {status} {criterion}: {details}")

    assert story.passed(), f"User story failed: {story.summary()}"


@pytest.mark.asyncio
async def test_dashboard_interaction_workflow():
    """
    Test complete dashboard interaction workflow.

    Simulates a user:
    1. Landing on dashboard
    2. Viewing company list
    3. Selecting a company
    4. Viewing metrics
    5. Generating a report
    """
    print("\n🎭 Testing Dashboard Interaction Workflow")

    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        # Step 1: Load dashboard
        print("📊 Step 1: Loading dashboard...")
        dashboard_response = await client.get("/")
        assert dashboard_response.status_code == 200, "Dashboard not accessible"
        print("✅ Dashboard loaded")

        # Step 2: Get company list
        print("📋 Step 2: Fetching company list...")
        companies_response = await client.get("/api/v1/companies?limit=10")
        assert companies_response.status_code == 200, "Companies endpoint failed"
        companies = companies_response.json().get("companies", [])
        assert len(companies) > 0, "No companies found"
        print(f"✅ Found {len(companies)} companies")

        # Step 3: Select company
        ticker = companies[0]["ticker"]
        print(f"🏢 Step 3: Selecting company {ticker}...")
        company_response = await client.get(f"/api/v1/companies/{ticker}")
        assert company_response.status_code == 200, f"Company {ticker} not found"
        print(f"✅ Company {ticker} details loaded")

        # Step 4: View metrics
        print(f"📈 Step 4: Loading metrics for {ticker}...")
        metrics_response = await client.get(f"/api/v1/metrics/{ticker}")
        assert metrics_response.status_code == 200, f"Metrics for {ticker} not found"
        metrics = metrics_response.json().get("metrics", {})
        assert len(metrics) > 0, "No metrics found"
        print(f"✅ Loaded {len(metrics)} metrics")

        # Step 5: Generate report
        print("📄 Step 5: Generating report...")
        report_response = await client.post(
            "/api/v1/reports/generate",
            json={"ticker": ticker, "report_type": "company_analysis"}
        )
        assert report_response.status_code in [200, 201, 202], "Report generation failed"
        print("✅ Report generated")

    print("\n✅ Dashboard workflow completed successfully!")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
