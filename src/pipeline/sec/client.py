"""SEC EDGAR API client with rate limiting."""

import asyncio
import time
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx
from loguru import logger

from src.core.config import get_settings
from src.core.circuit_breaker import sec_breaker, sec_fallback


class RateLimiter:
    """Simple rate limiter for API calls."""

    def __init__(self, calls_per_second: int):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call = 0.0

    async def acquire(self):
        """Wait if necessary to respect rate limit."""
        current = time.time()
        time_since_last = current - self.last_call

        if time_since_last < self.min_interval:
            await asyncio.sleep(self.min_interval - time_since_last)

        self.last_call = time.time()


class SECAPIClient:
    """Client for SEC EDGAR API with rate limiting."""

    BASE_URL = "https://data.sec.gov"
    ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"
    TICKER_CIK_MAPPING_URL = "https://www.sec.gov/files/company_tickers.json"

    def __init__(self):
        self.settings = get_settings()
        self.headers = {
            "User-Agent": self.settings.SEC_USER_AGENT,
            "Accept": "application/json",
        }
        self.rate_limiter = RateLimiter(self.settings.SEC_RATE_LIMIT)
        self._ticker_cik_cache: Optional[Dict[str, str]] = None

    async def get_ticker_to_cik_mapping(self) -> Dict[str, str]:
        """Fetch the official SEC ticker-to-CIK mapping.

        Returns a dictionary mapping ticker symbols to CIK numbers.
        Caches the result to avoid repeated API calls.
        Protected by circuit breaker to prevent cascading failures.
        """
        if self._ticker_cik_cache is not None:
            return self._ticker_cik_cache

        await self.rate_limiter.acquire()

        try:
            async with httpx.AsyncClient() as client:
                # Wrap API call with circuit breaker
                response = sec_breaker.call(
                    client.get,
                    self.TICKER_CIK_MAPPING_URL,
                    headers=self.headers
                )
                # Await if coroutine
                if asyncio.iscoroutine(response):
                    response = await response

                if response.status_code != 200:
                    logger.error(f"Failed to fetch ticker mapping: {response.status_code}")
                    return {}

                data = response.json()

                # Convert to ticker -> CIK mapping (data is indexed by integers)
                mapping = {}
                for entry in data.values():
                    if isinstance(entry, dict) and "ticker" in entry and "cik_str" in entry:
                        ticker = entry["ticker"].upper()
                        cik = str(entry["cik_str"]).zfill(10)  # Zero-pad to 10 digits
                        mapping[ticker] = cik

                self._ticker_cik_cache = mapping
                logger.info(f"Loaded {len(mapping)} ticker-to-CIK mappings from SEC")
                return mapping

        except Exception as e:
            logger.error(f"Error fetching ticker-to-CIK mapping: {e}")
            return await sec_fallback()

    async def get_company_info(self, ticker: str) -> Dict[str, Any]:
        """Fetch company information from SEC.

        First looks up the CIK from the ticker, then fetches company submissions.
        Protected by circuit breaker to prevent cascading failures.
        """
        # Get CIK from ticker using official mapping
        ticker_mapping = await self.get_ticker_to_cik_mapping()
        cik = ticker_mapping.get(ticker.upper())

        if not cik:
            logger.error(f"Ticker {ticker} not found in SEC ticker-to-CIK mapping")
            return {}

        logger.info(f"Found CIK {cik} for ticker {ticker}")

        await self.rate_limiter.acquire()

        try:
            async with httpx.AsyncClient() as client:
                # Fetch company submissions using CIK
                submissions_url = f"{self.BASE_URL}/submissions/CIK{cik}.json"
                # Wrap API call with circuit breaker
                response = sec_breaker.call(client.get, submissions_url, headers=self.headers)
                # Await if coroutine
                if asyncio.iscoroutine(response):
                    response = await response

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to fetch company info for CIK {cik} (ticker {ticker}): {response.status_code}")
                    return {}

        except Exception as e:
            logger.error(f"Error fetching company info for {ticker}: {e}")
            return await sec_fallback(ticker)

    async def get_filings(
        self,
        cik: str,
        filing_types: List[str],
        start_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Fetch SEC filings for a company.

        Protected by circuit breaker to prevent cascading failures.
        """
        await self.rate_limiter.acquire()

        try:
            async with httpx.AsyncClient() as client:
                # Pad CIK to 10 digits
                padded_cik = cik.zfill(10)
                url = f"{self.BASE_URL}/submissions/CIK{padded_cik}.json"

                # Wrap API call with circuit breaker
                response = sec_breaker.call(client.get, url, headers=self.headers)
                # Await if coroutine
                if asyncio.iscoroutine(response):
                    response = await response

                if response.status_code != 200:
                    logger.error(f"Failed to fetch filings for CIK {cik}: {response.status_code}")
                    return []

                data = response.json()
                filings = []

                # Process recent filings
                recent = data.get("filings", {}).get("recent", {})

                for i in range(len(recent.get("form", []))):
                    form_type = recent["form"][i]

                    if form_type in filing_types:
                        filing_date = datetime.strptime(recent["filingDate"][i], "%Y-%m-%d")

                        if start_date and filing_date < start_date:
                            continue

                        filings.append({
                            "form": form_type,
                            "filingDate": recent["filingDate"][i],
                            "accessionNumber": recent["accessionNumber"][i],
                            "primaryDocument": recent["primaryDocument"][i],
                            "cik": cik,
                        })

                return filings

        except Exception as e:
            logger.error(f"Error fetching filings for CIK {cik}: {e}")
            return []

    async def download_filing_content(self, filing: Dict[str, Any]) -> str:
        """Download the actual filing content.

        Protected by circuit breaker to prevent cascading failures.
        """
        await self.rate_limiter.acquire()

        cik = filing["cik"].zfill(10)
        accession = filing["accessionNumber"].replace("-", "")
        document = filing["primaryDocument"]

        url = f"{self.ARCHIVES_URL}/{cik}/{accession}/{document}"

        try:
            async with httpx.AsyncClient() as client:
                # Wrap API call with circuit breaker
                response = sec_breaker.call(
                    client.get,
                    url,
                    headers=self.headers,
                    follow_redirects=True
                )
                # Await if coroutine
                if asyncio.iscoroutine(response):
                    response = await response

                if response.status_code == 200:
                    return response.text
                else:
                    logger.error(f"Failed to download filing: {url}")
                    return ""

        except Exception as e:
            logger.error(f"Error downloading filing content: {e}")
            return ""
