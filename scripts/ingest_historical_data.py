"""Historical data ingestion script for EdTech companies.

This script ingests one year of historical data from multiple sources:
- SEC EDGAR filings (10-K, 10-Q, 8-K)
- Yahoo Finance stock data
- Alpha Vantage fundamentals
- NewsAPI sentiment data
- Crunchbase company information
- GitHub repository metrics
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import argparse
from tqdm import tqdm
import json

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.connectors.data_sources import (
    SECConnector, YahooFinanceConnector, AlphaVantageConnector,
    NewsAPIConnector, CrunchbaseConnector, GitHubConnector,
    DataAggregator
)
from src.db.base import get_db, init_db
from src.db.models import Company, SECFiling, FinancialMetric, Document
from src.pipeline.sec_ingestion import SECIngestionPipeline
from src.processing.embeddings import EmbeddingService
from src.cache.redis_cache import cache_manager
from sqlalchemy.orm import Session
from prefect import flow, task
import ray

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# EdTech companies to track
EDTECH_COMPANIES = [
    {
        "ticker": "DUOL",
        "name": "Duolingo, Inc.",
        "cik": "0001562088",
        "sector": "EdTech",
        "subsector": "Language Learning",
        "github_org": "duolingo"
    },
    {
        "ticker": "CHGG",
        "name": "Chegg, Inc.",
        "cik": "0001364954",
        "sector": "EdTech",
        "subsector": "Study Tools",
        "github_org": "chegg"
    },
    {
        "ticker": "COUR",
        "name": "Coursera, Inc.",
        "cik": "0001651562",
        "sector": "EdTech",
        "subsector": "Online Courses",
        "github_org": "coursera"
    },
    {
        "ticker": "UDMY",
        "name": "Udemy, Inc.",
        "cik": "0001607939",
        "sector": "EdTech",
        "subsector": "Skills Training",
        "github_org": "udemy"
    },
    {
        "ticker": "TWOU",
        "name": "2U, Inc.",
        "cik": "0001459417",
        "sector": "EdTech",
        "subsector": "Online Programs",
        "github_org": "2uinc"
    },
    {
        "ticker": "INST",
        "name": "Instructure Holdings, Inc.",
        "cik": "0001355754",
        "sector": "EdTech",
        "subsector": "Learning Management",
        "github_org": "instructure"
    },
    {
        "ticker": "POWW",
        "name": "PowerSchool Holdings, Inc.",
        "cik": "0001829457",
        "sector": "EdTech",
        "subsector": "K-12 Software",
        "github_org": "powerschool"
    },
    {
        "ticker": "ST",
        "name": "Stride, Inc.",
        "cik": "0001157408",
        "sector": "EdTech",
        "subsector": "K-12 Online",
        "github_org": None
    },
    {
        "ticker": "ATGE",
        "name": "Adtalem Global Education Inc.",
        "cik": "0000730464",
        "sector": "EdTech",
        "subsector": "Higher Education",
        "github_org": None
    },
    {
        "ticker": "APEI",
        "name": "American Public Education, Inc.",
        "cik": "0001201792",
        "sector": "EdTech",
        "subsector": "Online University",
        "github_org": None
    }
]


class HistoricalDataIngester:
    """Orchestrates historical data ingestion from multiple sources."""
    
    def __init__(self, db: Session):
        self.db = db
        self.sec_connector = SECConnector()
        self.yahoo_connector = YahooFinanceConnector()
        self.alpha_connector = AlphaVantageConnector()
        self.news_connector = NewsAPIConnector()
        self.crunchbase_connector = CrunchbaseConnector()
        self.github_connector = GitHubConnector()
        self.aggregator = DataAggregator()
        self.embedding_service = EmbeddingService()
        
        # Initialize Ray for parallel processing
        if not ray.is_initialized():
            ray.init(num_cpus=4)
    
    async def ingest_company(self, company_info: Dict, start_date: datetime, end_date: datetime):
        """Ingest all data for a single company."""
        logger.info(f"Ingesting data for {company_info['name']} ({company_info['ticker']})")
        
        try:
            # 1. Create or update company record
            company = await self.create_or_update_company(company_info)
            
            # 2. Ingest SEC filings
            filings = await self.ingest_sec_filings(company, company_info['cik'], start_date, end_date)
            logger.info(f"  - Ingested {len(filings)} SEC filings")
            
            # 3. Ingest financial metrics
            metrics = await self.ingest_financial_metrics(company, start_date, end_date)
            logger.info(f"  - Ingested {len(metrics)} financial metrics")
            
            # 4. Ingest news and sentiment
            news = await self.ingest_news_sentiment(company, start_date, end_date)
            logger.info(f"  - Analyzed {len(news)} news articles")
            
            # 5. Ingest GitHub metrics (if available)
            if company_info.get('github_org'):
                github_metrics = await self.ingest_github_metrics(company, company_info['github_org'])
                logger.info(f"  - Collected GitHub metrics: {github_metrics}")
            
            # 6. Generate embeddings for documents
            await self.generate_document_embeddings(company)
            
            return {
                "company": company.ticker,
                "filings": len(filings),
                "metrics": len(metrics),
                "news": len(news),
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error ingesting {company_info['ticker']}: {str(e)}")
            return {
                "company": company_info['ticker'],
                "status": "error",
                "error": str(e)
            }
    
    async def create_or_update_company(self, company_info: Dict) -> Company:
        """Create or update company record."""
        company = self.db.query(Company).filter(
            Company.ticker == company_info['ticker']
        ).first()
        
        if not company:
            company = Company(
                ticker=company_info['ticker'],
                name=company_info['name'],
                sector=company_info['sector'],
                industry=company_info.get('subsector', 'Education Technology'),
                description=f"{company_info['subsector']} company in the EdTech space"
            )
            self.db.add(company)
        else:
            # Update existing
            company.sector = company_info['sector']
            company.industry = company_info.get('subsector', company.industry)
        
        self.db.commit()
        return company
    
    async def ingest_sec_filings(self, company: Company, cik: str, start_date: datetime, end_date: datetime) -> List[SECFiling]:
        """Ingest SEC filings for a company."""
        filings = []
        filing_types = ['10-K', '10-Q', '8-K']
        
        for filing_type in filing_types:
            try:
                raw_filings = self.sec_connector.get_filings(
                    cik=cik,
                    filing_type=filing_type,
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d')
                )
                
                for raw_filing in raw_filings[:10]:  # Limit to 10 most recent
                    # Check if filing already exists
                    existing = self.db.query(SECFiling).filter(
                        SECFiling.company_id == company.id,
                        SECFiling.accession_number == raw_filing.get('accessionNumber')
                    ).first()
                    
                    if not existing:
                        filing = SECFiling(
                            company_id=company.id,
                            filing_type=filing_type,
                            filing_date=datetime.strptime(raw_filing['filingDate'], '%Y-%m-%d'),
                            period_end=datetime.strptime(raw_filing.get('periodOfReport', raw_filing['filingDate']), '%Y-%m-%d'),
                            accession_number=raw_filing['accessionNumber'],
                            file_number=raw_filing.get('fileNumber', ''),
                            form_type=raw_filing['form'],
                            filing_url=raw_filing['primaryDocument'],
                            content=raw_filing.get('documents', [{}])[0].get('description', ''),
                            processed=False
                        )
                        self.db.add(filing)
                        filings.append(filing)
                
                # Rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"Error fetching {filing_type} filings for {company.ticker}: {e}")
        
        self.db.commit()
        return filings
    
    async def ingest_financial_metrics(self, company: Company, start_date: datetime, end_date: datetime) -> List[FinancialMetric]:
        """Ingest financial metrics from Yahoo Finance and Alpha Vantage."""
        metrics = []
        
        try:
            # Get stock data from Yahoo Finance
            stock_data = self.yahoo_connector.get_stock_data(
                ticker=company.ticker,
                start_date=start_date,
                end_date=end_date
            )
            
            # Get fundamentals from Alpha Vantage
            fundamentals = self.alpha_connector.get_company_overview(company.ticker)
            quarterly_earnings = self.alpha_connector.get_earnings(company.ticker)
            
            # Create quarterly metrics
            for quarter in quarterly_earnings.get('quarterlyEarnings', [])[:8]:  # Last 8 quarters
                try:
                    metric_date = datetime.strptime(quarter['fiscalDateEnding'], '%Y-%m-%d')
                    
                    if start_date <= metric_date <= end_date:
                        # Check if metric exists
                        existing = self.db.query(FinancialMetric).filter(
                            FinancialMetric.company_id == company.id,
                            FinancialMetric.date == metric_date
                        ).first()
                        
                        if not existing:
                            metric = FinancialMetric(
                                company_id=company.id,
                                date=metric_date,
                                revenue=float(quarter.get('reportedRevenue', 0)),
                                revenue_growth=float(quarter.get('revenueGrowthYOY', 0)) / 100 if quarter.get('revenueGrowthYOY') else None,
                                earnings_per_share=float(quarter.get('reportedEPS', 0)),
                                
                                # From overview
                                market_cap=float(fundamentals.get('MarketCapitalization', 0)),
                                pe_ratio=float(fundamentals.get('PERatio', 0)) if fundamentals.get('PERatio') != 'None' else None,
                                price_to_sales=float(fundamentals.get('PriceToSalesRatioTTM', 0)) if fundamentals.get('PriceToSalesRatioTTM') != 'None' else None,
                                profit_margin=float(fundamentals.get('ProfitMargin', 0)) if fundamentals.get('ProfitMargin') != 'None' else None,
                                operating_margin=float(fundamentals.get('OperatingMarginTTM', 0)) if fundamentals.get('OperatingMarginTTM') != 'None' else None,
                                
                                # EdTech specific metrics (would need specialized data source)
                                monthly_active_users=None,  # Would need company API
                                average_revenue_per_user=None,
                                customer_acquisition_cost=None,
                                net_revenue_retention=None,
                                gross_merchandise_value=None
                            )
                            self.db.add(metric)
                            metrics.append(metric)
                
                except Exception as e:
                    logger.warning(f"Error processing metric for {company.ticker}: {e}")
            
            # Rate limiting for Alpha Vantage (5 calls/minute for free tier)
            await asyncio.sleep(12)
            
        except Exception as e:
            logger.error(f"Error fetching financial metrics for {company.ticker}: {e}")
        
        self.db.commit()
        return metrics
    
    async def ingest_news_sentiment(self, company: Company, start_date: datetime, end_date: datetime) -> List[Document]:
        """Ingest news articles and perform sentiment analysis."""
        documents = []
        
        try:
            # Search for company news
            news_articles = self.news_connector.get_company_news(
                company_name=company.name,
                start_date=start_date,
                end_date=end_date
            )
            
            for article in news_articles[:20]:  # Limit to 20 articles
                # Create document record
                doc = Document(
                    company_id=company.id,
                    title=article['title'],
                    content=article.get('description', ''),
                    document_type='news',
                    source=article.get('source', {}).get('name', 'Unknown'),
                    url=article.get('url'),
                    published_date=datetime.strptime(article['publishedAt'], '%Y-%m-%dT%H:%M:%SZ'),
                    
                    # Simple sentiment (would use NLP model in production)
                    sentiment_score=self._calculate_simple_sentiment(article['title'] + ' ' + article.get('description', ''))
                )
                self.db.add(doc)
                documents.append(doc)
            
        except Exception as e:
            logger.warning(f"Error fetching news for {company.name}: {e}")
        
        self.db.commit()
        return documents
    
    async def ingest_github_metrics(self, company: Company, github_org: str) -> Dict:
        """Ingest GitHub repository metrics for engineering assessment."""
        try:
            repos = self.github_connector.get_organization_repos(github_org)
            
            metrics = {
                "total_repos": len(repos),
                "total_stars": sum(r.get('stargazers_count', 0) for r in repos),
                "total_forks": sum(r.get('forks_count', 0) for r in repos),
                "open_source_activity": len([r for r in repos if not r.get('private', True)]),
                "languages": list(set(r.get('language') for r in repos if r.get('language')))
            }
            
            # Store as a document for analysis
            doc = Document(
                company_id=company.id,
                title=f"GitHub Metrics - {github_org}",
                content=json.dumps(metrics, indent=2),
                document_type='engineering_metrics',
                source='GitHub',
                published_date=datetime.utcnow()
            )
            self.db.add(doc)
            self.db.commit()
            
            return metrics
            
        except Exception as e:
            logger.warning(f"Error fetching GitHub metrics for {github_org}: {e}")
            return {}
    
    async def generate_document_embeddings(self, company: Company):
        """Generate embeddings for company documents."""
        try:
            # Get unprocessed documents
            documents = self.db.query(Document).filter(
                Document.company_id == company.id,
                Document.embedding == None
            ).limit(50).all()
            
            if documents:
                # Generate embeddings in batch
                texts = [f"{doc.title} {doc.content[:1000]}" for doc in documents]
                embeddings = self.embedding_service.generate_embeddings(texts)
                
                # Update documents with embeddings
                for doc, embedding in zip(documents, embeddings):
                    doc.embedding = embedding.tolist()
                
                self.db.commit()
                logger.info(f"  - Generated embeddings for {len(documents)} documents")
                
        except Exception as e:
            logger.warning(f"Error generating embeddings for {company.ticker}: {e}")
    
    def _calculate_simple_sentiment(self, text: str) -> float:
        """Simple sentiment calculation (placeholder for real NLP)."""
        positive_words = ['growth', 'increase', 'profit', 'success', 'expand', 'improve', 'gain', 'up']
        negative_words = ['loss', 'decline', 'decrease', 'fall', 'drop', 'concern', 'risk', 'down']
        
        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        if positive_count + negative_count == 0:
            return 0.5  # Neutral
        
        return positive_count / (positive_count + negative_count)


@flow(name="Historical Data Ingestion")
async def ingest_all_companies(months_back: int = 12):
    """Main flow to ingest historical data for all EdTech companies."""
    
    # Initialize database
    init_db()
    db = next(get_db())
    
    ingester = HistoricalDataIngester(db)
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30 * months_back)
    
    logger.info(f"Ingesting data from {start_date.date()} to {end_date.date()}")
    logger.info(f"Processing {len(EDTECH_COMPANIES)} EdTech companies")
    
    results = []
    
    # Process companies with progress bar
    for company_info in tqdm(EDTECH_COMPANIES, desc="Ingesting companies"):
        result = await ingester.ingest_company(company_info, start_date, end_date)
        results.append(result)
        
        # Be respectful of API rate limits
        await asyncio.sleep(2)
    
    # Summary
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] == 'error']
    
    logger.info("\n" + "="*50)
    logger.info("INGESTION SUMMARY")
    logger.info("="*50)
    logger.info(f"Successful: {len(successful)} companies")
    logger.info(f"Failed: {len(failed)} companies")
    
    if successful:
        total_filings = sum(r['filings'] for r in successful)
        total_metrics = sum(r['metrics'] for r in successful)
        total_news = sum(r['news'] for r in successful)
        
        logger.info(f"Total SEC filings: {total_filings}")
        logger.info(f"Total financial metrics: {total_metrics}")
        logger.info(f"Total news articles: {total_news}")
    
    if failed:
        logger.error("Failed companies:")
        for f in failed:
            logger.error(f"  - {f['company']}: {f.get('error', 'Unknown error')}")
    
    return results


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Ingest historical EdTech data')
    parser.add_argument('--months', type=int, default=12, help='Months of historical data to ingest')
    parser.add_argument('--companies', nargs='+', help='Specific company tickers to ingest')
    args = parser.parse_args()
    
    # Filter companies if specified
    if args.companies:
        global EDTECH_COMPANIES
        EDTECH_COMPANIES = [c for c in EDTECH_COMPANIES if c['ticker'] in args.companies]
    
    # Run the ingestion
    asyncio.run(ingest_all_companies(months_back=args.months))


if __name__ == "__main__":
    main()