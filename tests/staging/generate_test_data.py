#!/usr/bin/env python3
"""
Test Data Generator - Create Realistic Test Data
Generates test data for UAT, load testing, and edge case validation.
"""

import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
import uuid


@dataclass
class Company:
    """Company test data."""
    ticker: str
    name: str
    sector: str
    industry: str
    description: str
    website: str
    employees: int
    founded: int
    headquarters: str
    market_cap: float


@dataclass
class FinancialMetric:
    """Financial metrics test data."""
    company_id: str
    ticker: str
    date: str
    revenue: float
    revenue_growth: float
    gross_profit: float
    gross_margin: float
    operating_income: float
    net_income: float
    ebitda: float
    eps: float
    cash_flow: float


@dataclass
class SECFiling:
    """SEC filing test data."""
    company_id: str
    ticker: str
    filing_type: str
    filing_date: str
    period_end: str
    accession_number: str
    url: str


class TestDataGenerator:
    """Generate realistic test data for various scenarios."""

    SECTORS = [
        "Technology", "Healthcare", "Finance", "Consumer", "Energy",
        "Industrial", "Materials", "Utilities", "Real Estate", "Communication"
    ]

    TECH_COMPANIES = [
        ("AAPL", "Apple Inc.", "Consumer Electronics"),
        ("MSFT", "Microsoft Corporation", "Software"),
        ("GOOGL", "Alphabet Inc.", "Internet Services"),
        ("AMZN", "Amazon.com Inc.", "E-commerce"),
        ("META", "Meta Platforms Inc.", "Social Media"),
        ("NVDA", "NVIDIA Corporation", "Semiconductors"),
        ("TSLA", "Tesla Inc.", "Electric Vehicles"),
        ("NFLX", "Netflix Inc.", "Streaming"),
    ]

    FILING_TYPES = ["10-K", "10-Q", "8-K", "S-1", "DEF 14A"]

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("test-data")
        self.output_dir.mkdir(exist_ok=True, parents=True)

    def generate_companies(self, count: int = 50) -> List[Company]:
        """Generate realistic company data."""
        companies = []

        # Add real tech companies first
        for ticker, name, industry in self.TECH_COMPANIES[:min(count, len(self.TECH_COMPANIES))]:
            company = Company(
                ticker=ticker,
                name=name,
                sector="Technology",
                industry=industry,
                description=f"{name} is a leading company in {industry}.",
                website=f"https://www.{ticker.lower()}.com",
                employees=random.randint(10000, 150000),
                founded=random.randint(1975, 2010),
                headquarters=random.choice([
                    "Cupertino, CA", "Redmond, WA", "Mountain View, CA",
                    "Seattle, WA", "Menlo Park, CA", "Santa Clara, CA"
                ]),
                market_cap=random.uniform(100e9, 3e12)
            )
            companies.append(company)

        # Generate additional synthetic companies
        for i in range(count - len(companies)):
            sector = random.choice(self.SECTORS)
            ticker = self._generate_ticker()

            company = Company(
                ticker=ticker,
                name=f"{ticker} Corporation",
                sector=sector,
                industry=self._generate_industry(sector),
                description=f"A {sector.lower()} company.",
                website=f"https://www.{ticker.lower()}.com",
                employees=random.randint(100, 50000),
                founded=random.randint(1980, 2020),
                headquarters=self._generate_headquarters(),
                market_cap=random.uniform(1e9, 500e9)
            )
            companies.append(company)

        return companies

    def generate_financial_metrics(
        self,
        companies: List[Company],
        years: int = 3,
        quarters: int = 4
    ) -> List[FinancialMetric]:
        """Generate financial metrics for companies."""
        metrics = []

        for company in companies:
            base_revenue = company.market_cap * 0.1
            revenue_growth = random.uniform(-0.1, 0.5)

            for year in range(years):
                for quarter in range(quarters):
                    date = datetime.now() - timedelta(days=365 * year + 90 * quarter)

                    # Calculate metrics with realistic relationships
                    revenue = base_revenue * (1 + revenue_growth) ** year * (0.8 + random.uniform(0, 0.4))
                    gross_margin = random.uniform(0.3, 0.7)
                    gross_profit = revenue * gross_margin
                    operating_margin = gross_margin * random.uniform(0.6, 0.9)
                    operating_income = revenue * operating_margin
                    net_margin = operating_margin * random.uniform(0.7, 0.95)
                    net_income = revenue * net_margin

                    metric = FinancialMetric(
                        company_id=str(uuid.uuid4()),
                        ticker=company.ticker,
                        date=date.isoformat(),
                        revenue=revenue,
                        revenue_growth=revenue_growth + random.uniform(-0.05, 0.05),
                        gross_profit=gross_profit,
                        gross_margin=gross_margin,
                        operating_income=operating_income,
                        net_income=net_income,
                        ebitda=operating_income * 1.2,
                        eps=net_income / 1000000,  # Simplified
                        cash_flow=net_income * random.uniform(0.8, 1.2)
                    )
                    metrics.append(metric)

        return metrics

    def generate_sec_filings(
        self,
        companies: List[Company],
        filings_per_company: int = 10
    ) -> List[SECFiling]:
        """Generate SEC filing data."""
        filings = []

        for company in companies:
            for i in range(filings_per_company):
                filing_date = datetime.now() - timedelta(days=random.randint(1, 730))
                period_end = filing_date - timedelta(days=random.randint(1, 90))

                filing = SECFiling(
                    company_id=str(uuid.uuid4()),
                    ticker=company.ticker,
                    filing_type=random.choice(self.FILING_TYPES),
                    filing_date=filing_date.isoformat(),
                    period_end=period_end.isoformat(),
                    accession_number=self._generate_accession_number(),
                    url=f"https://www.sec.gov/Archives/edgar/data/{random.randint(1000, 999999)}"
                )
                filings.append(filing)

        return filings

    def generate_edge_cases(self) -> Dict:
        """Generate edge case test data."""
        return {
            "empty_ticker": {
                "ticker": "",
                "name": "Empty Ticker Co"
            },
            "very_long_ticker": {
                "ticker": "A" * 20,
                "name": "Long Ticker Company"
            },
            "special_chars_ticker": {
                "ticker": "TEST-123.A",
                "name": "Special Characters Co"
            },
            "negative_revenue": {
                "ticker": "NEG",
                "revenue": -1000000,
                "net_income": -500000
            },
            "zero_values": {
                "ticker": "ZERO",
                "revenue": 0,
                "employees": 0,
                "market_cap": 0
            },
            "extreme_values": {
                "ticker": "HUGE",
                "revenue": 1e15,
                "market_cap": 1e16,
                "employees": 10000000
            },
            "missing_fields": {
                "ticker": "MISS"
                # Intentionally missing required fields
            },
            "invalid_dates": {
                "ticker": "DATE",
                "filing_date": "not-a-date",
                "period_end": "2999-99-99"
            }
        }

    def generate_load_test_data(self, num_requests: int = 1000) -> List[Dict]:
        """Generate data for load testing."""
        companies = self.generate_companies(100)

        test_cases = []
        for i in range(num_requests):
            company = random.choice(companies)

            test_case = {
                "id": i,
                "endpoint": random.choice([
                    f"/api/v1/companies/{company.ticker}",
                    f"/api/v1/metrics/{company.ticker}",
                    "/api/v1/companies",
                    f"/api/v1/intelligence/sector-analysis?sector={company.sector}"
                ]),
                "method": "GET",
                "expected_status": 200
            }
            test_cases.append(test_case)

        return test_cases

    def save_all(self):
        """Generate and save all test data."""
        print("🔧 Generating test data...")

        # Generate companies
        print("  📊 Generating companies...")
        companies = self.generate_companies(50)
        self._save_json("companies.json", [asdict(c) for c in companies])
        print(f"  ✅ Generated {len(companies)} companies")

        # Generate financial metrics
        print("  💰 Generating financial metrics...")
        metrics = self.generate_financial_metrics(companies, years=3, quarters=4)
        self._save_json("financial_metrics.json", [asdict(m) for m in metrics])
        print(f"  ✅ Generated {len(metrics)} financial metrics")

        # Generate SEC filings
        print("  📄 Generating SEC filings...")
        filings = self.generate_sec_filings(companies, filings_per_company=10)
        self._save_json("sec_filings.json", [asdict(f) for f in filings])
        print(f"  ✅ Generated {len(filings)} SEC filings")

        # Generate edge cases
        print("  ⚠️  Generating edge cases...")
        edge_cases = self.generate_edge_cases()
        self._save_json("edge_cases.json", edge_cases)
        print(f"  ✅ Generated {len(edge_cases)} edge cases")

        # Generate load test data
        print("  🔥 Generating load test data...")
        load_data = self.generate_load_test_data(1000)
        self._save_json("load_test_requests.json", load_data)
        print(f"  ✅ Generated {len(load_data)} load test cases")

        print(f"\n✅ All test data saved to {self.output_dir}")

    def _save_json(self, filename: str, data):
        """Save data to JSON file."""
        filepath = self.output_dir / filename
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def _generate_ticker(self) -> str:
        """Generate a random ticker symbol."""
        length = random.choice([3, 4])
        return ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=length))

    def _generate_industry(self, sector: str) -> str:
        """Generate industry based on sector."""
        industries = {
            "Technology": ["Software", "Hardware", "Semiconductors", "Internet Services"],
            "Healthcare": ["Pharmaceuticals", "Biotechnology", "Medical Devices", "Healthcare Services"],
            "Finance": ["Banking", "Insurance", "Asset Management", "FinTech"],
            "Consumer": ["Retail", "E-commerce", "Consumer Goods", "Restaurants"],
            "Energy": ["Oil & Gas", "Renewable Energy", "Utilities", "Energy Services"]
        }
        return random.choice(industries.get(sector, ["General"]))

    def _generate_headquarters(self) -> str:
        """Generate random headquarters location."""
        cities = [
            "New York, NY", "San Francisco, CA", "Boston, MA", "Chicago, IL",
            "Seattle, WA", "Austin, TX", "Atlanta, GA", "Denver, CO",
            "Miami, FL", "Los Angeles, CA"
        ]
        return random.choice(cities)

    def _generate_accession_number(self) -> str:
        """Generate SEC accession number."""
        return f"{random.randint(1, 9999):04d}-{random.randint(1, 99):02d}-{random.randint(1, 999999):06d}"


def main():
    """Main entry point."""
    generator = TestDataGenerator()
    generator.save_all()


if __name__ == "__main__":
    main()
