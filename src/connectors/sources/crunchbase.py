"""Crunchbase connector for funding and company data."""

import aiohttp
from typing import Any, Dict

from loguru import logger

from src.core.config import get_settings
from src.connectors.sources.base import RateLimiter


class CrunchbaseConnector:
    """
    Crunchbase connector for funding and company data.
    Requires paid API key.
    """

    def __init__(self):
        self.settings = get_settings()
        self.api_key = self.settings.CRUNCHBASE_API_KEY if hasattr(self.settings, 'CRUNCHBASE_API_KEY') else None
        self.base_url = "https://api.crunchbase.com/v4"
        self.rate_limiter = RateLimiter(1)  # Conservative rate limit

        if not self.api_key:
            logger.warning("Crunchbase API key not configured")

    async def get_company_funding(self, company_name: str) -> Dict[str, Any]:
        """Get funding history for a company."""
        if not self.api_key:
            logger.warning("Crunchbase API key not configured, skipping funding fetch")
            return {}

        await self.rate_limiter.acquire()

        headers = {
            'X-cb-user-key': self.api_key,
        }

        params = {
            'field_ids': 'name,funding_total,num_funding_rounds,last_funding_at',
            'q': company_name,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/searches/organizations",
                    headers=headers,
                    params=params
                ) as response:
                    data = await response.json()

                    if data.get('entities'):
                        company = data['entities'][0]['properties']
                        return {
                            'name': company.get('name'),
                            'funding_total': company.get('funding_total', {}).get('value', 0),
                            'num_funding_rounds': company.get('num_funding_rounds', 0),
                            'last_funding_date': company.get('last_funding_at'),
                        }

                    return {}

        except Exception as e:
            logger.error(f"Error fetching Crunchbase data for {company_name}: {e}")
            return {}
