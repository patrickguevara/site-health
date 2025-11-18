# site_health/crawler.py
"""Web crawler for checking site health."""

import asyncio
import httpx
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
from typing import Set, List, Dict, Optional
from site_health.models import LinkResult


class SiteCrawler:
    """Async web crawler for detecting broken links."""

    def __init__(
        self,
        start_url: str,
        max_depth: int = 2,
        max_concurrent: int = 10,
        timeout: float = 10.0,
        respect_robots: bool = True
    ):
        self.start_url = start_url
        self.max_depth = max_depth
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.respect_robots = respect_robots

        # Parse base domain
        parsed = urlparse(start_url)
        self.base_domain = f"{parsed.scheme}://{parsed.netloc}"
        self.domain = parsed.netloc

        # Tracking
        self.visited: Set[str] = set()
        self.results: List[LinkResult] = []
        self.pages_crawled = 0

        # Semaphore for rate limiting
        self.semaphore = asyncio.Semaphore(max_concurrent)

    def _normalize_url(self, url: str, base_url: str = None) -> str:
        """Normalize URL by removing fragments and resolving relative paths."""
        if base_url is None:
            base_url = self.base_domain

        # Resolve relative URLs
        full_url = urljoin(base_url, url)

        # Parse and remove fragment
        parsed = urlparse(full_url)
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            ""  # Remove fragment
        ))

        return normalized

    def _is_same_domain(self, url: str) -> bool:
        """Check if URL belongs to the same domain."""
        parsed = urlparse(url)
        return parsed.netloc == self.domain

    def _get_link_type(self, url: str) -> str:
        """Determine link type based on URL."""
        url_lower = url.lower()

        if url_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.ico')):
            return 'image'
        elif url_lower.endswith('.css'):
            return 'css'
        elif url_lower.endswith('.js'):
            return 'js'
        elif not self._is_same_domain(url):
            return 'external'
        else:
            return 'page'

    async def _check_link(self, source_url: str, target_url: str) -> LinkResult:
        """Check if a link is valid and return result."""
        link_type = self._get_link_type(target_url)

        async with self.semaphore:
            try:
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                    # Use HEAD for efficiency, fall back to GET if needed
                    try:
                        response = await client.head(target_url)
                    except httpx.HTTPStatusError:
                        # Some servers don't support HEAD, try GET
                        response = await client.get(target_url)

                    response_time = response.elapsed.total_seconds()

                    # Determine severity
                    if response.status_code >= 400:
                        severity = "error"
                    elif response.status_code >= 300 or response_time > 5.0:
                        severity = "warning"
                    else:
                        severity = "success"

                    return LinkResult(
                        source_url=source_url,
                        target_url=target_url,
                        link_type=link_type,
                        status_code=response.status_code,
                        response_time=response_time,
                        severity=severity,
                        error_message=None
                    )

            except httpx.TimeoutException:
                return LinkResult(
                    source_url=source_url,
                    target_url=target_url,
                    link_type=link_type,
                    status_code=None,
                    response_time=self.timeout,
                    severity="error",
                    error_message="Request timeout"
                )

            except Exception as e:
                return LinkResult(
                    source_url=source_url,
                    target_url=target_url,
                    link_type=link_type,
                    status_code=None,
                    response_time=0.0,
                    severity="error",
                    error_message=str(e)
                )
