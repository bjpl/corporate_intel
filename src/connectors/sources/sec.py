"""SEC EDGAR API connector for financial filings."""

from typing import Any, Dict, List

from loguru import logger
from sec_edgar_api import EdgarClient

from src.core.config import get_settings
from src.connectors.sources.base import RateLimiter


class SECEdgarConnector:
    """
    SEC EDGAR API connector for financial filings.
    Free API with 10 requests/second limit.
    """

    def __init__(self):
        self.settings = get_settings()
        self.client = EdgarClient(user_agent=self.settings.SEC_USER_AGENT)
        self.rate_limiter = RateLimiter(10)  # 10 requests/second

    async def get_company_filings(
        self,
        ticker: str,
        filing_types: List[str] = ["10-K", "10-Q", "8-K"],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Fetch recent filings for a company."""
        await self.rate_limiter.acquire()

        try:
            # Get company CIK
            submissions = self.client.get_submissions(ticker=ticker)

            if not submissions:
                logger.warning(f"No submissions found for {ticker}")
                return []

            filings = []
            recent_filings = submissions['filings']['recent']

            for i in range(min(limit, len(recent_filings['form']))):
                if recent_filings['form'][i] in filing_types:
                    filings.append({
                        'ticker': ticker,
                        'form': recent_filings['form'][i],
                        'filing_date': recent_filings['filingDate'][i],
                        'accession_number': recent_filings['accessionNumber'][i],
                        'primary_document': recent_filings['primaryDocument'][i],
                        'description': recent_filings['primaryDocDescription'][i],
                    })

            return filings

        except Exception as e:
            logger.error(f"Error fetching SEC filings for {ticker}: {e}")
            return []

    async def get_filing_content(self, accession_number: str, ticker: str) -> str:
        """Download actual filing content."""
        await self.rate_limiter.acquire()

        try:
            # Get filing details
            filing = self.client.get_filing(accession_number)
            return filing.get('content', '')

        except Exception as e:
            logger.error(f"Error downloading filing {accession_number}: {e}")
            return ""
