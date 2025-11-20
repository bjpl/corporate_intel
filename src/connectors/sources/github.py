"""GitHub connector for open source activity metrics."""

import aiohttp
from typing import Any, Dict

from loguru import logger

from src.connectors.sources.base import RateLimiter


class GitHubConnector:
    """
    GitHub connector for open source activity metrics.
    Useful for EdTech companies with open source tools.
    """

    def __init__(self):
        self.base_url = "https://api.github.com"
        self.rate_limiter = RateLimiter(60/3600)  # 60 requests per hour

    async def get_repo_metrics(self, org: str, repo: str) -> Dict[str, Any]:
        """Get repository metrics for EdTech open source projects."""
        await self.rate_limiter.acquire()

        try:
            async with aiohttp.ClientSession() as session:
                # Get repo info
                async with session.get(f"{self.base_url}/repos/{org}/{repo}") as response:
                    repo_data = await response.json()

                # Get recent commits
                async with session.get(
                    f"{self.base_url}/repos/{org}/{repo}/commits",
                    params={'per_page': 100}
                ) as response:
                    commits = await response.json()

                # Get contributors
                async with session.get(
                    f"{self.base_url}/repos/{org}/{repo}/contributors",
                    params={'per_page': 100}
                ) as response:
                    contributors = await response.json()

                return {
                    'stars': repo_data.get('stargazers_count', 0),
                    'forks': repo_data.get('forks_count', 0),
                    'watchers': repo_data.get('watchers_count', 0),
                    'open_issues': repo_data.get('open_issues_count', 0),
                    'recent_commits': len(commits) if isinstance(commits, list) else 0,
                    'contributors': len(contributors) if isinstance(contributors, list) else 0,
                    'created_at': repo_data.get('created_at'),
                    'updated_at': repo_data.get('updated_at'),
                    'language': repo_data.get('language'),
                    'license': repo_data.get('license', {}).get('name'),
                }

        except Exception as e:
            logger.error(f"Error fetching GitHub data for {org}/{repo}: {e}")
            return {}
