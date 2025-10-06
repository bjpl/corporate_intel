"""Example usage of DashboardService for querying dashboard data.

This module demonstrates how to use the DashboardService to fetch data
for the dashboard visualizations. These examples show the typical patterns
for integrating the service with Dash callbacks.
"""

import asyncio
from typing import Dict, List

from src.db.session import get_db
from src.services.dashboard_service import DashboardService


async def example_get_company_performance():
    """Example: Fetch company performance data for dashboard table."""
    async with get_db() as session:
        service = DashboardService(session, cache_ttl=300)

        # Get all companies
        all_companies = await service.get_company_performance()
        print(f"Total companies: {len(all_companies)}")

        # Get K-12 segment companies
        k12_companies = await service.get_company_performance(category="k12")
        print(f"K-12 companies: {len(k12_companies)}")

        # Get top 10 companies by revenue
        top_companies = await service.get_company_performance(limit=10)
        print("\nTop 10 Companies:")
        for company in top_companies:
            print(f"  {company['ticker']}: ${company['latest_revenue'] / 1e6:.1f}M")

        # Filter by minimum revenue
        large_companies = await service.get_company_performance(min_revenue=500e6)
        print(f"\nCompanies with >$500M revenue: {len(large_companies)}")

        return all_companies


async def example_get_competitive_landscape():
    """Example: Fetch competitive landscape data for market analysis."""
    async with get_db() as session:
        service = DashboardService(session)

        # Get all segments
        landscape = await service.get_competitive_landscape()
        print("\nCompetitive Landscape:")
        print(f"Total market revenue: ${landscape['market_summary']['total_market_revenue'] / 1e9:.1f}B")
        print(f"Total companies: {landscape['market_summary']['total_companies']}")

        print("\nSegment Breakdown:")
        for segment in landscape['segments']:
            print(f"  {segment['edtech_category']}:")
            print(f"    Revenue: ${segment['total_segment_revenue'] / 1e9:.1f}B")
            print(f"    Companies: {segment['companies_in_segment']}")
            print(f"    Avg Growth: {segment['avg_revenue_growth']:.1f}%")
            print(f"    HHI Index: {segment['hhi_index']}")

        return landscape


async def example_get_company_details():
    """Example: Fetch detailed company information."""
    async with get_db() as session:
        service = DashboardService(session)

        # Get details for specific company
        ticker = "DUOL"
        company = await service.get_company_details(ticker)

        if company:
            print(f"\n{company['name']} ({ticker}):")
            print(f"  Category: {company['category']}")
            print(f"  Headquarters: {company['headquarters']}")
            print(f"  Founded: {company['founded_year']}")
            print(f"  Delivery Model: {company['delivery_model']}")

            if company['latest_metrics']:
                metrics = company['latest_metrics']
                print(f"\n  Latest Metrics:")
                print(f"    Revenue: ${metrics.get('latest_revenue', 0) / 1e6:.1f}M")
                print(f"    YoY Growth: {metrics.get('revenue_yoy_growth', 0):.1f}%")
                print(f"    NRR: {metrics.get('latest_nrr', 0):.0f}%")
                print(f"    MAU: {metrics.get('latest_mau', 0) / 1e6:.1f}M")

        return company


async def example_get_quarterly_metrics():
    """Example: Fetch time-series metrics for trend analysis."""
    async with get_db() as session:
        service = DashboardService(session)

        # Get revenue trend for Duolingo
        ticker = "DUOL"
        revenue_df = await service.get_quarterly_metrics(ticker, "revenue", quarters=8)

        print(f"\n{ticker} Quarterly Revenue Trend:")
        if not revenue_df.empty:
            for _, row in revenue_df.iterrows():
                print(f"  {row['metric_date'].strftime('%Y Q%q')}: "
                      f"${row['value'] / 1e6:.1f}M "
                      f"(YoY: {row['yoy_growth']:.1f}%)")
        else:
            print("  No data available")

        # Get MAU trend
        mau_df = await service.get_quarterly_metrics(ticker, "monthly_active_users")
        print(f"\n{ticker} MAU Trend:")
        if not mau_df.empty:
            for _, row in mau_df.iterrows():
                print(f"  {row['metric_date'].strftime('%Y Q%q')}: "
                      f"{row['value'] / 1e6:.1f}M users "
                      f"(QoQ: {row['qoq_growth']:.1f}%)")

        return revenue_df


async def example_get_market_summary():
    """Example: Fetch market KPIs for dashboard cards."""
    async with get_db() as session:
        service = DashboardService(session)

        summary = await service.get_market_summary()

        print("\nMarket Summary (KPIs):")
        print(f"  Total Revenue: ${summary['total_market_revenue'] / 1e9:.1f}B")
        print(f"  Avg YoY Growth: {summary['avg_yoy_growth']:.1f}%")
        print(f"  Avg NRR: {summary['avg_nrr']:.0f}%")
        print(f"  Total Users: {summary['total_active_users'] / 1e6:.1f}M")
        print(f"  Companies: {summary['num_companies']}")
        print(f"  Data Updated: {summary['data_freshness']}")

        return summary


async def example_get_segment_comparison():
    """Example: Fetch normalized segment metrics for radar chart."""
    async with get_db() as session:
        service = DashboardService(session)

        comparison = await service.get_segment_comparison()

        print("\nSegment Comparison (Normalized Metrics):")
        print(f"Metrics: {comparison['metrics']}")
        print(f"Segments: {comparison['segments']}")
        print("\nValues (0-100 scale):")
        for i, segment in enumerate(comparison['segments']):
            print(f"  {segment}: {comparison['values'][i]}")

        return comparison


async def example_get_data_freshness():
    """Example: Check data freshness and availability."""
    async with get_db() as session:
        service = DashboardService(session)

        freshness = await service.get_data_freshness()

        print("\nData Freshness:")
        print(f"  Last Updated: {freshness['last_updated']}")
        print(f"  Companies: {freshness['companies_count']}")
        print(f"  Metric Records: {freshness['metrics_count']}")

        print("\n  Coverage by Category:")
        for category, count in freshness['coverage_by_category'].items():
            print(f"    {category}: {count} companies")

        return freshness


async def example_dash_callback_pattern():
    """Example: How to use DashboardService in a Dash callback.

    This demonstrates the recommended pattern for integrating
    the service layer into Dash callback functions.
    """
    # In your dash_app.py, you would do something like:
    #
    # @app.callback(
    #     Output("filtered-data", "data"),
    #     [Input("category-filter", "value")]
    # )
    # async def update_data(category):
    #     async with get_db() as session:
    #         service = DashboardService(session)
    #         companies = await service.get_company_performance(category=category)
    #         return companies
    #
    # Note: Dash callbacks need to be async-aware. You may need to use
    # dash.dcc.Loading or create a wrapper that handles the async execution.

    # For demonstration, here's how you'd fetch the data:
    async with get_db() as session:
        service = DashboardService(session)

        # This would be inside your callback
        category = "k12"
        companies = await service.get_company_performance(category=category)

        # Convert to format expected by Dash DataTable
        table_data = [
            {
                "ticker": c["ticker"],
                "company_name": c["company_name"],
                "revenue": f"${c['latest_revenue'] / 1e6:.1f}M" if c['latest_revenue'] else "-",
                "growth": f"{c['revenue_yoy_growth']:.1f}%" if c['revenue_yoy_growth'] else "-",
                "nrr": f"{c['latest_nrr']:.0f}%" if c['latest_nrr'] else "-",
            }
            for c in companies
        ]

        print(f"\nDash callback returned {len(table_data)} companies")
        return table_data


async def run_all_examples():
    """Run all examples sequentially."""
    print("=" * 80)
    print("DashboardService Usage Examples")
    print("=" * 80)

    await example_get_company_performance()
    await example_get_competitive_landscape()
    await example_get_company_details()
    await example_get_quarterly_metrics()
    await example_get_market_summary()
    await example_get_segment_comparison()
    await example_get_data_freshness()
    await example_dash_callback_pattern()

    print("\n" + "=" * 80)
    print("All examples completed!")
    print("=" * 80)


if __name__ == "__main__":
    """Run examples when script is executed directly."""
    asyncio.run(run_all_examples())
