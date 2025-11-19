# site_health/performance.py
"""Performance measurement using Playwright and Core Web Vitals."""

from datetime import datetime
from typing import List, Set
from playwright.async_api import async_playwright, Browser
from site_health.models import PageVitals


class PerformanceAnalyzer:
    """Measure Core Web Vitals using real browser automation."""

    def __init__(self, timeout: float = 30.0):
        """
        Initialize performance analyzer.

        Args:
            timeout: Maximum time to wait for page load (seconds)
        """
        self.timeout = timeout * 1000  # Convert to milliseconds for Playwright
        self.browser: Browser | None = None

    async def __aenter__(self):
        """Async context manager entry - start browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close browser."""
        if self.browser:
            await self.browser.close()
        await self.playwright.stop()

    async def measure_page(self, url: str) -> PageVitals:
        """
        Measure Core Web Vitals for a single page.

        Args:
            url: Page URL to measure

        Returns:
            PageVitals object with measurements or error status
        """
        if not self.browser:
            raise RuntimeError("Browser not initialized. Use async context manager.")

        try:
            page = await self.browser.new_page()

            # Navigate to page with timeout
            try:
                await page.goto(url, wait_until="networkidle", timeout=self.timeout)
            except Exception as e:
                await page.close()
                return PageVitals(
                    url=url,
                    lcp=None,
                    cls=None,
                    inp=None,
                    measured_at=datetime.now(),
                    status="failed",
                    error_message=f"Navigation failed: {str(e)}"
                )

            # Inject Web Vitals measurement script
            vitals_script = """
                () => {
                    return new Promise((resolve) => {
                        // Simple implementation - measure what's available
                        const vitals = {
                            lcp: null,
                            cls: null,
                            inp: null
                        };

                        // LCP - Largest Contentful Paint
                        const lcpObserver = new PerformanceObserver((list) => {
                            const entries = list.getEntries();
                            if (entries.length > 0) {
                                const lastEntry = entries[entries.length - 1];
                                vitals.lcp = lastEntry.renderTime || lastEntry.loadTime;
                            }
                        });
                        lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true });

                        // CLS - Cumulative Layout Shift
                        let clsScore = 0;
                        const clsObserver = new PerformanceObserver((list) => {
                            for (const entry of list.getEntries()) {
                                if (!entry.hadRecentInput) {
                                    clsScore += entry.value;
                                }
                            }
                            vitals.cls = clsScore;
                        });
                        clsObserver.observe({ type: 'layout-shift', buffered: true });

                        // INP - Interaction to Next Paint (approximation using FID for now)
                        const inpObserver = new PerformanceObserver((list) => {
                            const entries = list.getEntries();
                            if (entries.length > 0) {
                                vitals.inp = entries[0].processingStart - entries[0].startTime;
                            }
                        });
                        inpObserver.observe({ type: 'first-input', buffered: true });

                        // Wait a bit for metrics to settle, then resolve
                        setTimeout(() => {
                            resolve(vitals);
                        }, 2000);
                    });
                }
            """

            # Execute script and get vitals
            try:
                vitals_data = await page.evaluate(vitals_script)
            except Exception as e:
                await page.close()
                return PageVitals(
                    url=url,
                    lcp=None,
                    cls=None,
                    inp=None,
                    measured_at=datetime.now(),
                    status="failed",
                    error_message=f"Metrics collection failed: {str(e)}"
                )

            await page.close()

            # Convert units: LCP from ms to seconds, keep CLS as-is, keep INP in ms
            lcp_seconds = vitals_data.get('lcp') / 1000 if vitals_data.get('lcp') else None
            cls_score = vitals_data.get('cls')
            inp_ms = vitals_data.get('inp')

            return PageVitals(
                url=url,
                lcp=lcp_seconds,
                cls=cls_score,
                inp=inp_ms,
                measured_at=datetime.now(),
                status="success" if lcp_seconds is not None else "failed",
                error_message=None if lcp_seconds is not None else "No metrics captured"
            )

        except Exception as e:
            return PageVitals(
                url=url,
                lcp=None,
                cls=None,
                inp=None,
                measured_at=datetime.now(),
                status="failed",
                error_message=f"Unexpected error: {str(e)}"
            )

    async def measure_pages(
        self,
        urls: List[str],
        progress_callback=None
    ) -> List[PageVitals]:
        """
        Measure Core Web Vitals for multiple pages.

        Args:
            urls: List of URLs to measure
            progress_callback: Optional callback(current, total) for progress updates

        Returns:
            List of PageVitals measurements
        """
        results = []
        total = len(urls)

        for i, url in enumerate(urls, 1):
            vitals = await self.measure_page(url)
            results.append(vitals)

            if progress_callback:
                progress_callback(i, total)

        return results


def select_stratified_sample(
    all_pages: List[str],
    homepage: str,
    depth_map: dict[str, int],
    sample_rate: float = 0.1
) -> List[str]:
    """
    Select stratified sample of pages for vitals measurement.

    Always includes:
    - Homepage
    - All depth-1 pages (directly linked from homepage)

    Then samples remainder to reach target percentage.

    Args:
        all_pages: All discovered page URLs
        homepage: The starting URL
        depth_map: Dict mapping URL -> depth level
        sample_rate: Target sampling rate (0.0 to 1.0)

    Returns:
        List of URLs to measure
    """
    selected: Set[str] = set()

    # Always include homepage
    if homepage in all_pages:
        selected.add(homepage)

    # Always include depth-1 pages
    for url in all_pages:
        if depth_map.get(url, 999) == 1:
            selected.add(url)

    # Calculate how many more we need
    target_count = max(len(selected), int(len(all_pages) * sample_rate))
    remaining_needed = target_count - len(selected)

    if remaining_needed > 0:
        # Get remaining pages (not already selected)
        remaining_pages = [url for url in all_pages if url not in selected]

        # Sample from remaining
        import random
        if len(remaining_pages) <= remaining_needed:
            selected.update(remaining_pages)
        else:
            sampled = random.sample(remaining_pages, remaining_needed)
            selected.update(sampled)

    return list(selected)
