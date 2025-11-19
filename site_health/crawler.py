# site_health/crawler.py
"""Web crawler for checking site health."""

import asyncio
import httpx
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
from typing import Set, List, Dict
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
        self.depth_map: Dict[str, int] = {}  # Track depth of each page

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

    def _extract_links(self, html: str, page_url: str) -> Set[str]:
        """Extract all links and assets from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        links = set()

        # Extract <a> tags
        for tag in soup.find_all('a', href=True):
            url = self._normalize_url(tag['href'], page_url)
            if url:
                links.add(url)

        # Extract <img> tags
        for tag in soup.find_all('img', src=True):
            url = self._normalize_url(tag['src'], page_url)
            if url:
                links.add(url)

        # Extract <link> tags (CSS)
        for tag in soup.find_all('link', href=True):
            url = self._normalize_url(tag['href'], page_url)
            if url:
                links.add(url)

        # Extract <script> tags
        for tag in soup.find_all('script', src=True):
            url = self._normalize_url(tag['src'], page_url)
            if url:
                links.add(url)

        return links

    async def crawl(self) -> List[LinkResult]:
        """Start crawling from the start URL."""
        self.visited.clear()
        self.results.clear()
        self.pages_crawled = 0

        # Queue of (url, depth) tuples
        queue = [(self.start_url, 0)]

        while queue:
            # Process batch of URLs at same depth
            current_batch = []
            current_depth = queue[0][1] if queue else 0

            while queue and queue[0][1] == current_depth:
                url, depth = queue.pop(0)
                if url not in self.visited:
                    current_batch.append((url, depth))
                    self.visited.add(url)
                    self.depth_map[url] = depth

            # Process batch concurrently
            tasks = [
                self._crawl_page(url, depth, queue)
                for url, depth in current_batch
            ]

            await asyncio.gather(*tasks, return_exceptions=True)

        return self.results

    async def _crawl_page(
        self,
        url: str,
        depth: int,
        queue: List[tuple]
    ):
        """Crawl a single page and extract links."""
        # Only fetch and parse pages from same domain
        if not self._is_same_domain(url):
            # Just check external links
            result = await self._check_link(url, url)
            self.results.append(result)
            return

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True
            ) as client:
                response = await client.get(url)

                if response.status_code >= 400:
                    self.results.append(LinkResult(
                        source_url=url,
                        target_url=url,
                        link_type="page",
                        status_code=response.status_code,
                        response_time=response.elapsed.total_seconds(),
                        severity="error",
                        error_message=f"HTTP {response.status_code}"
                    ))
                    return

                self.pages_crawled += 1

                # Extract links from HTML
                if 'text/html' in response.headers.get('content-type', ''):
                    links = self._extract_links(response.text, url)

                    # Check all links
                    check_tasks = [
                        self._check_link(url, link)
                        for link in links
                    ]

                    link_results = await asyncio.gather(*check_tasks, return_exceptions=True)

                    for result in link_results:
                        if isinstance(result, LinkResult):
                            self.results.append(result)

                            # Queue same-domain pages for crawling if within depth
                            if (depth < self.max_depth and
                                result.link_type == "page" and
                                result.severity != "error" and
                                result.target_url not in self.visited):
                                queue.append((result.target_url, depth + 1))

        except Exception as e:
            self.results.append(LinkResult(
                source_url=url,
                target_url=url,
                link_type="page",
                status_code=None,
                response_time=0.0,
                severity="error",
                error_message=str(e)
            ))

    def get_pages_for_vitals_measurement(self, sample_rate: float = 0.1) -> List[str]:
        """
        Get list of page URLs to measure vitals for.

        Uses stratified sampling - always includes homepage and depth-1 pages,
        then samples remainder to reach target rate.

        Args:
            sample_rate: Target percentage of pages to measure (0.0 to 1.0)

        Returns:
            List of URLs selected for vitals measurement
        """
        from site_health.performance import select_stratified_sample

        # Filter to only 'page' type links (exclude images, css, js)
        page_urls = [
            url for url in self.visited
            if self._get_link_type(url) == 'page' and self._is_same_domain(url)
        ]

        return select_stratified_sample(
            page_urls,
            self.start_url,
            self.depth_map,
            sample_rate
        )

    def get_pages_for_seo_analysis(self) -> list[str]:
        """
        Get list of page URLs to analyze for SEO.

        Returns all crawled same-domain pages that returned 200 OK.

        Returns:
            List of URLs to analyze
        """
        # Return all visited same-domain pages
        return [
            url for url in self.visited
            if self._get_link_type(url) == 'page' and self._is_same_domain(url)
        ]
