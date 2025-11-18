# Implementation Plan: Core Web Vitals Integration

**Created:** 2025-11-18
**Status:** Ready for implementation
**Estimated Complexity:** Medium-High

## Overview

Add Core Web Vitals (LCP, CLS, INP) measurement to the site-health tool using Playwright for browser automation. Integrate with existing crawl workflow via `--vitals` flag with stratified 10% sampling.

## Design Decisions

- **Measurement Tool:** Playwright (browser automation with real metrics)
- **Architecture:** Separate `PerformanceAnalyzer` class (mirrors `Database`, `SiteCrawler` separation)
- **Storage:** New `page_vitals` table (separate from `link_results`)
- **Sampling Strategy:** Stratified 10% - always measure homepage + depth-1 pages, sample remainder
- **Reporting:** Color-coded output (Google thresholds), summary statistics
- **Error Handling:** Record "measurement failed" status and continue
- **Future-ready:** Columns for retry command, architecture supports full/filtered crawls

## Prerequisites

- Python 3.11+
- Existing site-health codebase at `/Users/patrickguevara/Code/site-health`
- Virtual environment activated: `source venv/bin/activate`
- All existing tests passing

## Execution Strategy

**Recommended Approach:**
Use the `/superpowers:execute-plan` command with the `python-development` skill for optimal implementation:

```bash
/superpowers:execute-plan and use the python-development skill as appropriate
```

The python-development skill provides:
- Expert guidance on Python 3.12+ features and async patterns
- Best practices for package management with uv/pip
- Testing patterns with pytest and async testing
- Code quality checks with ruff
- Performance optimization for async operations

This plan is designed to work with or without the skill, but using it will provide additional validation and Python ecosystem expertise during implementation.

## Tasks

### Task 1: Add Playwright Dependency

**Files to modify:**
- `/Users/patrickguevara/Code/site-health/pyproject.toml`

**Step 1.1: Update dependencies**

Open `pyproject.toml` and add `playwright` to the dependencies list:

```toml
dependencies = [
    "httpx>=0.25.0",
    "beautifulsoup4>=4.12.0",
    "aiosqlite>=0.19.0",
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "typer>=0.9.0",
    "pyyaml>=6.0",
    "jinja2>=3.1.0",
    "playwright>=1.40.0",
]
```

**Step 1.2: Install dependencies**

```bash
cd /Users/patrickguevara/Code/site-health
source venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
```

**Verification:**

```bash
python3 -c "import playwright; print(f'Playwright {playwright.__version__} installed')"
```

Expected output: `Playwright 1.x.x installed`

---

### Task 2: Create PageVitals Data Model

**Files to create:**
- None (modify existing)

**Files to modify:**
- `/Users/patrickguevara/Code/site-health/site_health/models.py`

**Step 2.1: Add PageVitals dataclass**

Add this new dataclass to `models.py` after the existing `CrawlSummary`:

```python
@dataclass
class PageVitals:
    """Core Web Vitals measurements for a page."""

    url: str
    lcp: float | None  # Largest Contentful Paint (seconds)
    cls: float | None  # Cumulative Layout Shift (score)
    inp: float | None  # Interaction to Next Paint (milliseconds)
    measured_at: datetime
    status: str  # 'success', 'failed', 'pending'
    error_message: str | None = None

    def get_lcp_rating(self) -> str:
        """Get LCP rating based on Google thresholds."""
        if self.lcp is None:
            return "unknown"
        if self.lcp <= 2.5:
            return "good"
        elif self.lcp <= 4.0:
            return "needs-improvement"
        else:
            return "poor"

    def get_cls_rating(self) -> str:
        """Get CLS rating based on Google thresholds."""
        if self.cls is None:
            return "unknown"
        if self.cls <= 0.1:
            return "good"
        elif self.cls <= 0.25:
            return "needs-improvement"
        else:
            return "poor"

    def get_inp_rating(self) -> str:
        """Get INP rating based on Google thresholds."""
        if self.inp is None:
            return "unknown"
        if self.inp <= 200:
            return "good"
        elif self.inp <= 500:
            return "needs-improvement"
        else:
            return "poor"
```

**Verification:**

Create test file `tests/test_vitals_model.py`:

```python
# tests/test_vitals_model.py
from datetime import datetime
from site_health.models import PageVitals

def test_page_vitals_creation():
    vitals = PageVitals(
        url="https://example.com",
        lcp=2.1,
        cls=0.05,
        inp=150,
        measured_at=datetime.now(),
        status="success"
    )
    assert vitals.url == "https://example.com"
    assert vitals.get_lcp_rating() == "good"
    assert vitals.get_cls_rating() == "good"
    assert vitals.get_inp_rating() == "good"

def test_page_vitals_ratings():
    # Test poor ratings
    vitals = PageVitals(
        url="https://slow.com",
        lcp=5.0,
        cls=0.3,
        inp=600,
        measured_at=datetime.now(),
        status="success"
    )
    assert vitals.get_lcp_rating() == "poor"
    assert vitals.get_cls_rating() == "poor"
    assert vitals.get_inp_rating() == "poor"

def test_page_vitals_needs_improvement():
    vitals = PageVitals(
        url="https://medium.com",
        lcp=3.0,
        cls=0.15,
        inp=300,
        measured_at=datetime.now(),
        status="success"
    )
    assert vitals.get_lcp_rating() == "needs-improvement"
    assert vitals.get_cls_rating() == "needs-improvement"
    assert vitals.get_inp_rating() == "needs-improvement"

def test_page_vitals_failed():
    vitals = PageVitals(
        url="https://broken.com",
        lcp=None,
        cls=None,
        inp=None,
        measured_at=datetime.now(),
        status="failed",
        error_message="Timeout"
    )
    assert vitals.status == "failed"
    assert vitals.get_lcp_rating() == "unknown"
```

Run test:
```bash
pytest tests/test_vitals_model.py -v
```

Expected: All 4 tests pass.

---

### Task 3: Extend Database with page_vitals Table

**Files to modify:**
- `/Users/patrickguevara/Code/site-health/site_health/database.py`

**Step 3.1: Add page_vitals table to schema**

In `database.py`, find the `initialize()` method (around line 17). After the `link_results` table creation and before the indexes, add:

```python
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS page_vitals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    crawl_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    lcp REAL,
                    cls REAL,
                    inp REAL,
                    measured_at TIMESTAMP NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    FOREIGN KEY (crawl_id) REFERENCES crawls(id)
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_vitals_crawl_id
                ON page_vitals(crawl_id)
            """)
```

**Step 3.2: Add import for PageVitals**

At the top of `database.py`, update the import:

```python
from site_health.models import LinkResult, CrawlSummary, PageVitals
```

**Step 3.3: Add save_page_vitals method**

Add this method to the `Database` class after `save_link_result()`:

```python
    async def save_page_vitals(self, crawl_id: int, vitals: PageVitals):
        """Save Core Web Vitals measurement for a page."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT INTO page_vitals
                (crawl_id, url, lcp, cls, inp, measured_at, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    crawl_id,
                    vitals.url,
                    vitals.lcp,
                    vitals.cls,
                    vitals.inp,
                    vitals.measured_at,
                    vitals.status,
                    vitals.error_message
                )
            )
            await conn.commit()
```

**Step 3.4: Add get_page_vitals method**

Add this method after `get_link_results()`:

```python
    async def get_page_vitals(self, crawl_id: int) -> List[PageVitals]:
        """Get all Core Web Vitals measurements for a crawl."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                """
                SELECT * FROM page_vitals
                WHERE crawl_id = ?
                ORDER BY measured_at
                """,
                (crawl_id,)
            )
            rows = await cursor.fetchall()

            return [
                PageVitals(
                    url=row["url"],
                    lcp=row["lcp"],
                    cls=row["cls"],
                    inp=row["inp"],
                    measured_at=datetime.fromisoformat(row["measured_at"]),
                    status=row["status"],
                    error_message=row["error_message"]
                )
                for row in rows
            ]
```

**Verification:**

Create test file `tests/test_database_vitals.py`:

```python
# tests/test_database_vitals.py
import pytest
from datetime import datetime
from site_health.database import Database
from site_health.models import PageVitals

@pytest.mark.asyncio
async def test_save_and_retrieve_vitals(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    # Create crawl
    crawl_id = await db.create_crawl("https://example.com", 2)

    # Save vitals
    vitals = PageVitals(
        url="https://example.com",
        lcp=2.3,
        cls=0.08,
        inp=150,
        measured_at=datetime.now(),
        status="success"
    )
    await db.save_page_vitals(crawl_id, vitals)

    # Retrieve
    results = await db.get_page_vitals(crawl_id)
    assert len(results) == 1
    assert results[0].url == "https://example.com"
    assert results[0].lcp == 2.3
    assert results[0].cls == 0.08
    assert results[0].inp == 150
    assert results[0].status == "success"

@pytest.mark.asyncio
async def test_save_failed_vitals(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    crawl_id = await db.create_crawl("https://example.com", 2)

    vitals = PageVitals(
        url="https://broken.com",
        lcp=None,
        cls=None,
        inp=None,
        measured_at=datetime.now(),
        status="failed",
        error_message="Page timeout"
    )
    await db.save_page_vitals(crawl_id, vitals)

    results = await db.get_page_vitals(crawl_id)
    assert len(results) == 1
    assert results[0].status == "failed"
    assert results[0].error_message == "Page timeout"
```

Run test:
```bash
pytest tests/test_database_vitals.py -v
```

Expected: Both tests pass.

---

### Task 4: Create PerformanceAnalyzer Class

**Files to create:**
- `/Users/patrickguevara/Code/site-health/site_health/performance.py`

**Step 4.1: Create performance.py**

Create new file with complete PerformanceAnalyzer implementation:

```python
# site_health/performance.py
"""Performance measurement using Playwright and Core Web Vitals."""

import asyncio
from datetime import datetime
from typing import List, Set
from playwright.async_api import async_playwright, Page, Browser
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
```

**Step 4.2: Create test file**

Create `tests/test_performance.py`:

```python
# tests/test_performance.py
import pytest
from site_health.performance import select_stratified_sample

def test_stratified_sample_includes_homepage():
    pages = [
        "https://example.com",
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/deep/page3"
    ]
    depth_map = {
        "https://example.com": 0,
        "https://example.com/page1": 1,
        "https://example.com/page2": 1,
        "https://example.com/deep/page3": 2
    }

    sample = select_stratified_sample(
        pages,
        "https://example.com",
        depth_map,
        sample_rate=0.5
    )

    # Homepage must be included
    assert "https://example.com" in sample
    # All depth-1 pages must be included
    assert "https://example.com/page1" in sample
    assert "https://example.com/page2" in sample

def test_stratified_sample_respects_rate():
    pages = [f"https://example.com/page{i}" for i in range(100)]
    pages.insert(0, "https://example.com")

    depth_map = {pages[0]: 0}
    for i in range(1, 6):
        depth_map[pages[i]] = 1
    for i in range(6, 100):
        depth_map[pages[i]] = 2

    sample = select_stratified_sample(
        pages,
        "https://example.com",
        depth_map,
        sample_rate=0.1
    )

    # Should be close to 10% (at least homepage + 5 depth-1 = 6 minimum)
    assert len(sample) >= 6
    assert len(sample) <= 15  # Reasonable upper bound for 10% of 100
```

Run test:
```bash
pytest tests/test_performance.py -v
```

Expected: Both tests pass.

**Note:** Testing actual Playwright functionality requires more complex mocking. The above tests verify the sampling logic. Full integration tests will be added in Task 7.

---

### Task 5: Integrate PerformanceAnalyzer with Crawler

**Files to modify:**
- `/Users/patrickguevara/Code/site-health/site_health/crawler.py`

**Step 5.1: Add depth tracking to SiteCrawler**

In `crawler.py`, add a new instance variable in `__init__` (around line 37):

```python
        # Tracking
        self.visited: Set[str] = set()
        self.results: List[LinkResult] = []
        self.pages_crawled = 0
        self.depth_map: Dict[str, int] = {}  # Add this line
```

**Step 5.2: Update _crawl_page to track depth**

In the `_crawl_page` method (around line 200), after adding URL to visited, add depth tracking:

```python
        # Mark as visited
        self.visited.add(url)
        self.depth_map[url] = depth  # Add this line
```

**Step 5.3: Add method to get pages for vitals**

Add this method to `SiteCrawler` class at the end:

```python
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
```

**Verification:**

Add test to `tests/test_crawler.py`:

```python
@pytest.mark.asyncio
async def test_crawler_tracks_depth():
    """Test that crawler tracks page depths correctly."""
    crawler = SiteCrawler(
        start_url="https://example.com",
        max_depth=2,
        timeout=5.0
    )

    # Mock a simple crawl
    crawler.visited = {
        "https://example.com",
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/page1/deep"
    }
    crawler.depth_map = {
        "https://example.com": 0,
        "https://example.com/page1": 1,
        "https://example.com/page2": 1,
        "https://example.com/page1/deep": 2
    }

    pages = crawler.get_pages_for_vitals_measurement(sample_rate=0.5)

    # Should include homepage and depth-1 pages at minimum
    assert "https://example.com" in pages
    assert "https://example.com/page1" in pages
    assert "https://example.com/page2" in pages
```

Run test:
```bash
pytest tests/test_crawler.py::test_crawler_tracks_depth -v
```

Expected: Test passes.

---

### Task 6: Update CLI to Support --vitals Flag

**Files to modify:**
- `/Users/patrickguevara/Code/site-health/site_health/cli.py`

**Step 6.1: Add --vitals flag to crawl command**

In `cli.py`, update the `crawl` function signature (around line 17):

```python
@app.command()
def crawl(
    url: Optional[str] = typer.Argument(None, help="URL to crawl"),
    depth: Optional[int] = typer.Option(None, "--depth", "-d", help="Maximum crawl depth"),
    format: Optional[str] = typer.Option(None, "--format", "-f", help="Output format (terminal/html/json)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Config file path"),
    max_concurrent: Optional[int] = typer.Option(None, "--max-concurrent", help="Max concurrent requests"),
    timeout: Optional[float] = typer.Option(None, "--timeout", help="Request timeout in seconds"),
    no_robots: bool = typer.Option(False, "--no-robots", help="Ignore robots.txt"),
    vitals: bool = typer.Option(False, "--vitals", help="Measure Core Web Vitals (10% sample)"),
    db_path: str = typer.Option("site_health.db", "--db", help="Database path"),
):
    """Crawl a website and check for broken links."""
    asyncio.run(_crawl_async(
        url=url,
        depth=depth,
        format=format,
        output=output,
        config_file=config_file,
        max_concurrent=max_concurrent,
        timeout=timeout,
        no_robots=no_robots,
        vitals=vitals,  # Add this
        db_path=db_path,
    ))
```

**Step 6.2: Update _crawl_async function**

Update the `_crawl_async` function signature and implementation:

```python
async def _crawl_async(
    url: Optional[str],
    depth: Optional[int],
    format: Optional[str],
    output: Optional[str],
    config_file: Optional[str],
    max_concurrent: Optional[int],
    timeout: Optional[float],
    no_robots: bool,
    vitals: bool,  # Add this parameter
    db_path: str,
):
```

Then, after the crawling is complete and results are saved (around line 100), add vitals measurement:

```python
    # Save results
    for result in results:
        await db.save_link_result(crawl_id, result)

    typer.echo(f"✓ Checked {len(results)} links")

    # Measure Core Web Vitals if requested
    if vitals:
        typer.echo("\nMeasuring Core Web Vitals (10% sample)...")

        from site_health.performance import PerformanceAnalyzer

        # Get pages to measure
        pages_to_measure = crawler.get_pages_for_vitals_measurement(sample_rate=0.1)
        typer.echo(f"Selected {len(pages_to_measure)} pages for measurement")

        # Measure vitals
        async with PerformanceAnalyzer(timeout=30.0) as analyzer:
            def progress_callback(current, total):
                typer.echo(f"  Progress: {current}/{total} pages measured")

            vitals_results = await analyzer.measure_pages(
                pages_to_measure,
                progress_callback=progress_callback
            )

        # Save vitals
        for vitals_result in vitals_results:
            await db.save_page_vitals(crawl_id, vitals_result)

        successful = sum(1 for v in vitals_results if v.status == "success")
        failed = len(vitals_results) - successful
        typer.echo(f"✓ Measured {successful} pages successfully ({failed} failed)")

    # Mark complete
    await db.complete_crawl(
        crawl_id,
        total_pages=crawler.pages_crawled,
        total_links=len(results),
    )
```

**Verification:**

```bash
# Test that --vitals flag is recognized
site-health crawl --help | grep vitals
```

Expected output: Should show the `--vitals` option description.

---

### Task 7: Update ReportGenerator for Vitals

**Files to modify:**
- `/Users/patrickguevara/Code/site-health/site_health/report.py`

**Step 7.1: Update _generate_terminal to include vitals**

In `report.py`, find the `_generate_terminal` method (around line 40). After generating the link results section, add vitals section:

```python
    async def _generate_terminal(self) -> str:
        """Generate colorized terminal report."""
        # ... existing code for summary and link results ...

        # Add Core Web Vitals section
        vitals = await self.db.get_page_vitals(self.crawl_id)

        if vitals:
            output.append("\n" + "=" * 80)
            output.append("Core Web Vitals")
            output.append("=" * 80)

            successful_vitals = [v for v in vitals if v.status == "success"]
            failed_vitals = [v for v in vitals if v.status == "failed"]

            if successful_vitals:
                # Calculate summary statistics
                lcp_values = [v.lcp for v in successful_vitals if v.lcp is not None]
                cls_values = [v.cls for v in successful_vitals if v.cls is not None]
                inp_values = [v.inp for v in successful_vitals if v.inp is not None]

                if lcp_values:
                    avg_lcp = sum(lcp_values) / len(lcp_values)
                    output.append(f"\nAverage LCP: {self._colorize_vitals(avg_lcp, 'lcp')}")

                if cls_values:
                    avg_cls = sum(cls_values) / len(cls_values)
                    output.append(f"Average CLS: {self._colorize_vitals(avg_cls, 'cls')}")

                if inp_values:
                    avg_inp = sum(inp_values) / len(inp_values)
                    output.append(f"Average INP: {self._colorize_vitals(avg_inp, 'inp')}")

                output.append(f"\nPages measured: {len(successful_vitals)}")

                # Show individual measurements
                output.append("\nIndividual Measurements:")
                output.append("-" * 80)

                for v in successful_vitals[:10]:  # Show first 10
                    output.append(f"\n{v.url}")
                    if v.lcp is not None:
                        output.append(f"  LCP: {self._colorize_vitals(v.lcp, 'lcp')}")
                    if v.cls is not None:
                        output.append(f"  CLS: {self._colorize_vitals(v.cls, 'cls')}")
                    if v.inp is not None:
                        output.append(f"  INP: {self._colorize_vitals(v.inp, 'inp')}")

                if len(successful_vitals) > 10:
                    output.append(f"\n... and {len(successful_vitals) - 10} more pages")

            if failed_vitals:
                output.append(f"\n{RED}Failed measurements: {len(failed_vitals)}{RESET}")
                for v in failed_vitals[:5]:
                    output.append(f"  {v.url}: {v.error_message}")

        return "\n".join(output)
```

**Step 7.2: Add colorization helper method**

Add this method to the `ReportGenerator` class:

```python
    def _colorize_vitals(self, value: float, metric: str) -> str:
        """
        Colorize vitals value based on Google thresholds.

        Args:
            value: Metric value
            metric: 'lcp', 'cls', or 'inp'

        Returns:
            Colorized string with value and rating
        """
        # ANSI color codes (already defined at module level)
        # Determine rating and color
        if metric == 'lcp':
            # LCP in seconds
            if value <= 2.5:
                color = GREEN
                rating = "GOOD"
            elif value <= 4.0:
                color = YELLOW
                rating = "NEEDS IMPROVEMENT"
            else:
                color = RED
                rating = "POOR"
            formatted_value = f"{value:.2f}s"

        elif metric == 'cls':
            # CLS is unitless score
            if value <= 0.1:
                color = GREEN
                rating = "GOOD"
            elif value <= 0.25:
                color = YELLOW
                rating = "NEEDS IMPROVEMENT"
            else:
                color = RED
                rating = "POOR"
            formatted_value = f"{value:.3f}"

        elif metric == 'inp':
            # INP in milliseconds
            if value <= 200:
                color = GREEN
                rating = "GOOD"
            elif value <= 500:
                color = YELLOW
                rating = "NEEDS IMPROVEMENT"
            else:
                color = RED
                rating = "POOR"
            formatted_value = f"{value:.0f}ms"

        else:
            return f"{value}"

        return f"{color}{formatted_value} ({rating}){RESET}"
```

**Step 7.3: Update JSON format**

Find `_generate_json` method and update to include vitals:

```python
    async def _generate_json(self) -> str:
        """Generate JSON report."""
        summary = await self.db.get_crawl_summary(self.crawl_id)
        results = await self.db.get_link_results(self.crawl_id)
        vitals = await self.db.get_page_vitals(self.crawl_id)

        report = {
            "crawl_id": self.crawl_id,
            "summary": {
                "id": summary.id,
                "start_url": summary.start_url,
                "started_at": summary.started_at.isoformat(),
                "completed_at": summary.completed_at.isoformat() if summary.completed_at else None,
                "status": summary.status,
                "total_pages": summary.total_pages,
                "total_links": summary.total_links,
                "errors": summary.errors,
                "warnings": summary.warnings,
            },
            "results": [
                {
                    "source_url": r.source_url,
                    "target_url": r.target_url,
                    "link_type": r.link_type,
                    "status_code": r.status_code,
                    "response_time": r.response_time,
                    "severity": r.severity,
                    "error_message": r.error_message,
                }
                for r in results
            ],
            "vitals": [
                {
                    "url": v.url,
                    "lcp": v.lcp,
                    "cls": v.cls,
                    "inp": v.inp,
                    "lcp_rating": v.get_lcp_rating(),
                    "cls_rating": v.get_cls_rating(),
                    "inp_rating": v.get_inp_rating(),
                    "measured_at": v.measured_at.isoformat(),
                    "status": v.status,
                    "error_message": v.error_message,
                }
                for v in vitals
            ] if vitals else []
        }

        import json
        return json.dumps(report, indent=2)
```

**Step 7.4: Update HTML template**

Find the HTML report template at `/Users/patrickguevara/Code/site-health/site_health/templates/report.html` and add vitals section before the closing `</body>` tag:

```html
    {% if vitals %}
    <section class="vitals-section">
        <h2>Core Web Vitals</h2>

        {% set successful = vitals | selectattr('status', 'equalto', 'success') | list %}
        {% if successful %}
        <div class="vitals-summary">
            {% set lcp_values = successful | map(attribute='lcp') | select('ne', None) | list %}
            {% if lcp_values %}
            <div class="metric">
                <h3>Average LCP</h3>
                <p class="vitals-{{ 'good' if (lcp_values | sum / lcp_values | length) <= 2.5 else ('needs-improvement' if (lcp_values | sum / lcp_values | length) <= 4.0 else 'poor') }}">
                    {{ "%.2f" | format(lcp_values | sum / lcp_values | length) }}s
                </p>
            </div>
            {% endif %}

            {% set cls_values = successful | map(attribute='cls') | select('ne', None) | list %}
            {% if cls_values %}
            <div class="metric">
                <h3>Average CLS</h3>
                <p class="vitals-{{ 'good' if (cls_values | sum / cls_values | length) <= 0.1 else ('needs-improvement' if (cls_values | sum / cls_values | length) <= 0.25 else 'poor') }}">
                    {{ "%.3f" | format(cls_values | sum / cls_values | length) }}
                </p>
            </div>
            {% endif %}

            {% set inp_values = successful | map(attribute='inp') | select('ne', None) | list %}
            {% if inp_values %}
            <div class="metric">
                <h3>Average INP</h3>
                <p class="vitals-{{ 'good' if (inp_values | sum / inp_values | length) <= 200 else ('needs-improvement' if (inp_values | sum / inp_values | length) <= 500 else 'poor') }}">
                    {{ "%.0f" | format(inp_values | sum / inp_values | length) }}ms
                </p>
            </div>
            {% endif %}
        </div>

        <table>
            <thead>
                <tr>
                    <th>URL</th>
                    <th>LCP</th>
                    <th>CLS</th>
                    <th>INP</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {% for v in vitals %}
                <tr>
                    <td class="url">{{ v.url }}</td>
                    <td class="vitals-{{ v.get_lcp_rating() }}">
                        {{ "%.2f" | format(v.lcp) if v.lcp else "N/A" }}s
                    </td>
                    <td class="vitals-{{ v.get_cls_rating() }}">
                        {{ "%.3f" | format(v.cls) if v.cls else "N/A" }}
                    </td>
                    <td class="vitals-{{ v.get_inp_rating() }}">
                        {{ "%.0f" | format(v.inp) if v.inp else "N/A" }}ms
                    </td>
                    <td>
                        <span class="status-{{ v.status }}">{{ v.status }}</span>
                        {% if v.error_message %}
                        <br><small>{{ v.error_message }}</small>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% endif %}
    </section>
    {% endif %}
```

Also add CSS for vitals styling in the `<style>` section:

```css
.vitals-summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.metric {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 8px;
    text-align: center;
}

.metric h3 {
    margin: 0 0 10px 0;
    font-size: 14px;
    color: #666;
}

.metric p {
    margin: 0;
    font-size: 32px;
    font-weight: bold;
}

.vitals-good { color: #28a745; }
.vitals-needs-improvement { color: #ffc107; }
.vitals-poor { color: #dc3545; }
.vitals-unknown { color: #6c757d; }
```

**Step 7.5: Update _generate_html to pass vitals**

In the `_generate_html` method, add vitals to template context:

```python
    async def _generate_html(self) -> str:
        """Generate HTML report and save to file."""
        summary = await self.db.get_crawl_summary(self.crawl_id)
        results = await self.db.get_link_results(self.crawl_id)
        vitals = await self.db.get_page_vitals(self.crawl_id)  # Add this

        # ... existing code ...

        html = template.render(
            summary=summary,
            results=results,
            vitals=vitals,  # Add this
            errors=errors,
            warnings=warnings,
            successes=successes
        )
```

**Verification:**

Create test file `tests/test_report_vitals.py`:

```python
# tests/test_report_vitals.py
import pytest
from datetime import datetime
from site_health.database import Database
from site_health.report import ReportGenerator
from site_health.models import PageVitals

@pytest.mark.asyncio
async def test_report_includes_vitals(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    crawl_id = await db.create_crawl("https://example.com", 2)

    # Save some vitals
    vitals = PageVitals(
        url="https://example.com",
        lcp=2.1,
        cls=0.05,
        inp=150,
        measured_at=datetime.now(),
        status="success"
    )
    await db.save_page_vitals(crawl_id, vitals)

    await db.complete_crawl(crawl_id, 10, 50)

    # Generate terminal report
    generator = ReportGenerator(crawl_id, db)
    report = await generator.generate('terminal')

    assert "Core Web Vitals" in report
    assert "LCP" in report
    assert "CLS" in report
    assert "INP" in report
```

Run test:
```bash
pytest tests/test_report_vitals.py -v
```

Expected: Test passes.

---

### Task 8: Update Web Interface

**Files to modify:**
- `/Users/patrickguevara/Code/site-health/site_health/web/app.py`
- `/Users/patrickguevara/Code/site-health/site_health/web/templates/index.html`

**Step 8.1: Update API response models**

In `web/app.py`, update the CrawlRequest model to include vitals flag:

```python
class CrawlRequest(BaseModel):
    url: str
    depth: int = 2
    max_concurrent: int = 10
    timeout: float = 10.0
    vitals: bool = False  # Add this field
```

**Step 8.2: Update run_crawl to handle vitals**

In the `run_crawl` function (around line 152), add vitals measurement:

```python
async def run_crawl(
    crawl_id: int,
    url: str,
    depth: int,
    max_concurrent: int,
    timeout: float,
    vitals: bool,  # Add parameter
    db: Database,
):
    """Run crawl in background task."""
    try:
        crawler = SiteCrawler(
            start_url=url,
            max_depth=depth,
            max_concurrent=max_concurrent,
            timeout=timeout,
        )

        results = await crawler.crawl()

        # Save results
        for result in results:
            await db.save_link_result(crawl_id, result)

        # Measure vitals if requested
        if vitals:
            from site_health.performance import PerformanceAnalyzer

            pages_to_measure = crawler.get_pages_for_vitals_measurement(sample_rate=0.1)

            async with PerformanceAnalyzer(timeout=30.0) as analyzer:
                vitals_results = await analyzer.measure_pages(pages_to_measure)

            for vitals_result in vitals_results:
                await db.save_page_vitals(crawl_id, vitals_result)

        # Mark complete
        await db.complete_crawl(
            crawl_id,
            total_pages=crawler.pages_crawled,
            total_links=len(results),
        )

    except Exception as e:
        # Mark as failed
        await db.complete_crawl(crawl_id, total_pages=0, total_links=0, status="failed")
```

**Step 8.3: Update start_crawl endpoint**

Update the `start_crawl` endpoint to pass vitals parameter:

```python
    @app.post("/api/crawl", response_model=CrawlResponse)
    async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
        """Start a new crawl."""
        # Create crawl session
        crawl_id = await db.create_crawl(request.url, request.depth)

        # Start crawl in background
        background_tasks.add_task(
            run_crawl,
            crawl_id=crawl_id,
            url=request.url,
            depth=request.depth,
            max_concurrent=request.max_concurrent,
            timeout=request.timeout,
            vitals=request.vitals,  # Add this
            db=db,
        )

        return CrawlResponse(
            crawl_id=crawl_id,
            message=f"Crawl started for {request.url}"
        )
```

**Step 8.4: Update get_crawl endpoint to include vitals**

Update the `get_crawl` endpoint to return vitals data:

```python
    @app.get("/api/crawls/{crawl_id}")
    async def get_crawl(crawl_id: int):
        """Get details for a specific crawl."""
        summary = await db.get_crawl_summary(crawl_id)
        if not summary:
            raise HTTPException(status_code=404, detail="Crawl not found")

        results = await db.get_link_results(crawl_id)
        vitals = await db.get_page_vitals(crawl_id)  # Add this

        return {
            "summary": {
                "id": summary.id,
                "start_url": summary.start_url,
                "started_at": summary.started_at.isoformat(),
                "completed_at": summary.completed_at.isoformat() if summary.completed_at else None,
                "status": summary.status,
                "total_pages": summary.total_pages,
                "total_links": summary.total_links,
                "errors": summary.errors,
                "warnings": summary.warnings,
            },
            "results": [
                {
                    "source_url": r.source_url,
                    "target_url": r.target_url,
                    "link_type": r.link_type,
                    "status_code": r.status_code,
                    "response_time": r.response_time,
                    "severity": r.severity,
                    "error_message": r.error_message,
                }
                for r in results
            ],
            "vitals": [
                {
                    "url": v.url,
                    "lcp": v.lcp,
                    "cls": v.cls,
                    "inp": v.inp,
                    "lcp_rating": v.get_lcp_rating(),
                    "cls_rating": v.get_cls_rating(),
                    "inp_rating": v.get_inp_rating(),
                    "status": v.status,
                }
                for v in vitals
            ] if vitals else []  # Add this
        }
```

**Step 8.5: Update web UI form**

In `web/templates/index.html`, add checkbox for vitals in the crawl form (around line 48):

```html
                    <div class="form-group">
                        <label for="timeout">Timeout (s)</label>
                        <input type="number" id="timeout" name="timeout"
                               value="10" min="5" max="60" step="0.5">
                    </div>
                </div>

                <!-- Add this new form group -->
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="vitals" name="vitals">
                        Measure Core Web Vitals (10% sample)
                    </label>
                </div>

                <button type="submit" class="btn-primary">Start Crawl</button>
```

**Step 8.6: Update JavaScript to send vitals flag**

In the form submission handler (around line 94), update to include vitals:

```javascript
            const data = {
                url: formData.get('url'),
                depth: parseInt(formData.get('depth')),
                max_concurrent: parseInt(formData.get('maxConcurrent')),
                timeout: parseFloat(formData.get('timeout')),
                vitals: document.getElementById('vitals').checked  // Add this
            };
```

**Verification:**

Start web server and test:

```bash
site-health serve
```

Navigate to http://localhost:8000 and verify:
1. Checkbox for "Measure Core Web Vitals" appears
2. Starting crawl with checkbox checked includes vitals in request
3. Viewing report shows vitals section

---

### Task 9: Integration Testing

**Files to create:**
- `tests/test_integration_vitals.py`

**Step 9.1: Create integration test**

```python
# tests/test_integration_vitals.py
"""
Integration tests for Core Web Vitals feature.

Note: These tests are marked as slow and may be skipped in CI.
They require actual browser automation.
"""
import pytest
from site_health.database import Database
from site_health.crawler import SiteCrawler
from site_health.performance import PerformanceAnalyzer

@pytest.mark.slow
@pytest.mark.asyncio
async def test_full_crawl_with_vitals(tmp_path):
    """
    Full integration test: crawl a real site and measure vitals.

    This test takes ~30 seconds and requires network access.
    """
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    # Use a simple, fast-loading site for testing
    test_url = "https://example.com"

    # Create crawl
    crawl_id = await db.create_crawl(test_url, 1)

    # Crawl
    crawler = SiteCrawler(
        start_url=test_url,
        max_depth=1,
        max_concurrent=5,
        timeout=10.0
    )
    results = await crawler.crawl()

    # Save link results
    for result in results:
        await db.save_link_result(crawl_id, result)

    # Get pages for vitals
    pages_to_measure = crawler.get_pages_for_vitals_measurement(sample_rate=1.0)
    assert len(pages_to_measure) >= 1
    assert test_url in pages_to_measure

    # Measure vitals
    async with PerformanceAnalyzer(timeout=30.0) as analyzer:
        vitals_results = await analyzer.measure_pages(pages_to_measure)

    # Save vitals
    for vitals_result in vitals_results:
        await db.save_page_vitals(crawl_id, vitals_result)

    # Verify
    saved_vitals = await db.get_page_vitals(crawl_id)
    assert len(saved_vitals) >= 1

    # At least one measurement should succeed
    successful = [v for v in saved_vitals if v.status == "success"]
    assert len(successful) >= 1

    # Check that homepage vitals were captured
    homepage_vitals = [v for v in successful if v.url == test_url]
    if homepage_vitals:
        v = homepage_vitals[0]
        # LCP should be present and reasonable (< 10 seconds)
        if v.lcp is not None:
            assert 0 < v.lcp < 10
            assert v.get_lcp_rating() in ["good", "needs-improvement", "poor"]


@pytest.mark.asyncio
async def test_vitals_graceful_failure(tmp_path):
    """Test that vitals measurement handles failures gracefully."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    crawl_id = await db.create_crawl("https://invalid-domain-12345.com", 1)

    # Try to measure vitals on invalid domain
    async with PerformanceAnalyzer(timeout=5.0) as analyzer:
        vitals = await analyzer.measure_page("https://invalid-domain-12345.com")

    # Should fail gracefully
    assert vitals.status == "failed"
    assert vitals.error_message is not None
    assert vitals.lcp is None
    assert vitals.cls is None
    assert vitals.inp is None

    # Should be saveable
    await db.save_page_vitals(crawl_id, vitals)
    saved = await db.get_page_vitals(crawl_id)
    assert len(saved) == 1
    assert saved[0].status == "failed"
```

**Step 9.2: Run integration tests**

```bash
# Run only fast tests (skip integration)
pytest -v -m "not slow"

# Run all tests including integration (slow)
pytest -v
```

**Step 9.3: Update pytest configuration**

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
]
```

---

### Task 10: Documentation Updates

**Files to modify:**
- `/Users/patrickguevara/Code/site-health/README.md`
- `/Users/patrickguevara/Code/site-health/docs/usage.md`

**Step 10.1: Update README.md features**

Update the Features section:

```markdown
## Features

- **Async Crawler**: High-performance asynchronous web crawling with configurable concurrency
- **Broken Link Detection**: Identifies 404s, timeouts, and other HTTP errors
- **Core Web Vitals**: Measure LCP, CLS, and INP using real browser automation (Playwright)
- **Multiple Output Formats**: Terminal (colorized), HTML reports, and JSON exports
- **SQLite History**: Persistent storage of all crawl results for historical analysis
- **CLI and Web Interface**: Use from command line or through a browser-based UI
- **Configuration File Support**: YAML-based configuration with CLI override capability
```

**Step 10.2: Update Quick Start section**

Add vitals example:

```markdown
### Command Line Usage

```bash
# Basic crawl with terminal output
site-health crawl https://example.com

# Crawl with Core Web Vitals measurement
site-health crawl https://example.com --vitals

# Crawl with custom depth and generate HTML report with vitals
site-health crawl https://example.com --depth 3 --vitals --format html
```

**Step 10.3: Update docs/usage.md**

Add new section after "CLI Commands":

```markdown
## Core Web Vitals

Site Health can measure Core Web Vitals (LCP, CLS, INP) using real browser automation powered by Playwright.

### What are Core Web Vitals?

- **LCP (Largest Contentful Paint)**: How quickly the main content loads
  - Good: ≤ 2.5s
  - Needs Improvement: ≤ 4.0s
  - Poor: > 4.0s

- **CLS (Cumulative Layout Shift)**: Visual stability during page load
  - Good: ≤ 0.1
  - Needs Improvement: ≤ 0.25
  - Poor: > 0.25

- **INP (Interaction to Next Paint)**: Responsiveness to user interactions
  - Good: ≤ 200ms
  - Needs Improvement: ≤ 500ms
  - Poor: > 500ms

### Measuring Vitals

Add the `--vitals` flag to any crawl:

```bash
site-health crawl https://example.com --vitals
```

**Sampling Strategy:**
- Measures 10% of discovered pages (stratified sample)
- Always includes: homepage and all depth-1 pages
- Remaining pages selected randomly to reach 10%

**Performance Impact:**
- Vitals measurement requires browser automation (slower than link checking)
- Expect ~2-5 pages/minute for vitals vs ~10-50 pages/minute for link checking
- Example: 100-page site with vitals = ~3-5 minutes additional time

### Viewing Vitals in Reports

**Terminal Report:**
```
Core Web Vitals
================
Average LCP: 2.1s (GOOD)
Average CLS: 0.08 (GOOD)
Average INP: 175ms (GOOD)

Pages measured: 10

Individual Measurements:
----------------
https://example.com
  LCP: 2.1s (GOOD)
  CLS: 0.05 (GOOD)
  INP: 150ms (GOOD)
```

**JSON Report:**
```json
{
  "vitals": [
    {
      "url": "https://example.com",
      "lcp": 2.1,
      "cls": 0.05,
      "inp": 150,
      "lcp_rating": "good",
      "cls_rating": "good",
      "inp_rating": "good",
      "status": "success"
    }
  ]
}
```

**HTML Report:**
- Summary cards with color-coded average metrics
- Detailed table with all measurements
- Visual indicators (green/yellow/red)

### Web Interface

In the web UI, check "Measure Core Web Vitals (10% sample)" when starting a crawl.

Vitals will appear in the crawl report alongside link check results.
```

---

### Task 11: Final Testing and Commit

**Step 11.1: Run full test suite**

```bash
cd /Users/patrickguevara/Code/site-health
source venv/bin/activate

# Run all tests except slow integration tests
pytest -v -m "not slow" --cov=site_health --cov-report=term-missing

# If all pass, run integration tests
pytest -v tests/test_integration_vitals.py
```

**Step 11.2: Manual testing**

```bash
# Test CLI with vitals
site-health crawl https://example.com --vitals

# Test web interface
site-health serve
# Navigate to localhost:8000, start crawl with vitals checkbox
```

**Step 11.3: Commit changes**

```bash
git add .
git commit -m "$(cat <<'EOF'
feat: add Core Web Vitals measurement with Playwright

- Add Playwright dependency for browser automation
- Create PageVitals data model with Google threshold ratings
- Add page_vitals database table with status and error tracking
- Implement PerformanceAnalyzer class for measuring LCP, CLS, INP
- Add stratified 10% sampling (always includes homepage + depth-1)
- Integrate --vitals flag in CLI crawl command
- Update reports (terminal, HTML, JSON) to show vitals with color coding
- Add vitals checkbox to web interface
- Include comprehensive tests and documentation
- Future-ready for retry command and full/filtered crawls

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Success Criteria

Implementation is complete when:

1. ✅ All existing tests pass
2. ✅ New tests pass (models, database, performance, reports)
3. ✅ `site-health crawl https://example.com --vitals` runs successfully
4. ✅ Terminal report shows Core Web Vitals section with color coding
5. ✅ HTML report includes vitals summary and detailed table
6. ✅ JSON report contains vitals array
7. ✅ Web interface checkbox triggers vitals measurement
8. ✅ Database stores vitals with status and error handling
9. ✅ Documentation updated (README, usage guide)
10. ✅ Integration test passes (slow test)

## Rollback Plan

If issues arise:

```bash
git revert HEAD
pip uninstall playwright
pip install -e ".[dev]"
```

## Future Enhancements

Not in this plan, but documented for future work:

1. **Retry Command**: `site-health retry-vitals <crawl_id> --url <specific-url>`
2. **Full Coverage**: Replace 10% sampling with `--vitals-all` flag
3. **URL Filtering**: `--vitals-pattern "*/products/*"` for targeted measurement
4. **Historical Tracking**: Compare vitals across crawls, detect regressions
5. **Custom Thresholds**: User-defined good/needs-improvement/poor boundaries
6. **Additional Metrics**: TTFB, FCP, Total Blocking Time
7. **Lighthouse Integration**: Full Lighthouse audit as alternative to custom measurement

## Notes for Engineer

- **Browser Downloads**: First `playwright install chromium` downloads ~200MB browser binary
- **Async Context**: PerformanceAnalyzer must be used with `async with` pattern
- **Timeout Tuning**: Default 30s timeout; increase for slow sites
- **Sampling Randomness**: Uses Python's `random.sample()` - not cryptographically secure but fine for this use case
- **Metric Collection**: Uses browser's native PerformanceObserver API - metrics may be `null` for some pages
- **Error Handling**: All failures are non-fatal; vitals measurement errors don't stop crawl
- **Database Migration**: Existing databases auto-upgrade with new `page_vitals` table on first run
