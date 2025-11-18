# Site Health Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Python tool to crawl websites, detect broken links, and generate triage reports via CLI and web interface.

**Architecture:** Crawler-first design with async SiteCrawler as core, SQLite for history, thin CLI/web wrappers using same crawler instance.

**Tech Stack:** Python 3.11+, httpx (async HTTP), BeautifulSoup4 (parsing), FastAPI (web), typer (CLI), aiosqlite (database), pytest

---

## Task 1: Project Setup and Package Structure

**Files:**
- Create: `pyproject.toml`
- Create: `site_health/__init__.py`
- Create: `site_health/__main__.py`
- Create: `config.example.yaml`
- Create: `.gitignore`
- Create: `requirements-dev.txt`

**Step 1: Create pyproject.toml with dependencies**

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "site-health"
version = "0.1.0"
description = "Crawl a site, find bad links, determine performance, output a triage report"
readme = "README.md"
requires-python = ">=3.11"
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
dependencies = [
    "httpx>=0.25.0",
    "beautifulsoup4>=4.12.0",
    "aiosqlite>=0.19.0",
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "typer>=0.9.0",
    "pyyaml>=6.0",
    "jinja2>=3.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
]

[project.scripts]
site-health = "site_health.cli:app"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"
```

**Step 2: Create package __init__.py**

```python
"""Site Health - Website crawler and link checker."""

__version__ = "0.1.0"
```

**Step 3: Create __main__.py entry point**

```python
"""Main entry point for site-health package."""

from site_health.cli import app

if __name__ == "__main__":
    app()
```

**Step 4: Create example config file**

```yaml
# Example configuration file for site-health
# Usage: site-health crawl --config config.yaml

url: https://example.com
depth: 2
max_concurrent: 10
timeout: 10.0
respect_robots: true
output_format: terminal
```

**Step 5: Create .gitignore**

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/

# Site Health specific
site_health.db
reports/*.html
*.yaml
!config.example.yaml
```

**Step 6: Create requirements-dev.txt**

```
-e .[dev]
```

**Step 7: Install package in editable mode**

Run: `python -m venv venv && source venv/bin/activate && pip install -e .[dev]`
Expected: Package installed successfully

**Step 8: Verify installation**

Run: `python -c "import site_health; print(site_health.__version__)"`
Expected: `0.1.0`

**Step 9: Commit**

```bash
git add pyproject.toml site_health/__init__.py site_health/__main__.py config.example.yaml .gitignore requirements-dev.txt
git commit -m "feat: initialize project structure and dependencies"
```

---

## Task 2: Data Models

**Files:**
- Create: `site_health/models.py`
- Create: `tests/test_models.py`

**Step 1: Write test for LinkResult model**

```python
# tests/test_models.py
from site_health.models import LinkResult

def test_link_result_creation():
    result = LinkResult(
        source_url="https://example.com/page1",
        target_url="https://example.com/page2",
        link_type="page",
        status_code=200,
        response_time=0.5,
        severity="success",
        error_message=None
    )

    assert result.source_url == "https://example.com/page1"
    assert result.target_url == "https://example.com/page2"
    assert result.link_type == "page"
    assert result.status_code == 200
    assert result.severity == "success"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_models.py::test_link_result_creation -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'site_health.models'"

**Step 3: Create models.py with dataclasses**

```python
# site_health/models.py
"""Data models for site health crawler."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class LinkResult:
    """Result of checking a single link."""

    source_url: str
    target_url: str
    link_type: str  # 'page', 'image', 'css', 'js', 'external'
    status_code: int | None
    response_time: float
    severity: str  # 'error', 'warning', 'success'
    error_message: str | None = None


@dataclass
class CrawlSummary:
    """Summary of a crawl session."""

    id: int
    start_url: str
    started_at: datetime
    completed_at: datetime | None
    max_depth: int
    total_pages: int
    total_links: int
    errors: int
    warnings: int
    status: str  # 'running', 'completed', 'failed'
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_models.py::test_link_result_creation -v`
Expected: PASS

**Step 5: Write test for CrawlSummary model**

```python
# tests/test_models.py (append)
from datetime import datetime
from site_health.models import CrawlSummary

def test_crawl_summary_creation():
    now = datetime.now()
    summary = CrawlSummary(
        id=1,
        start_url="https://example.com",
        started_at=now,
        completed_at=None,
        max_depth=2,
        total_pages=10,
        total_links=50,
        errors=2,
        warnings=5,
        status="running"
    )

    assert summary.id == 1
    assert summary.status == "running"
    assert summary.completed_at is None
```

**Step 6: Run test to verify it passes**

Run: `pytest tests/test_models.py::test_crawl_summary_creation -v`
Expected: PASS

**Step 7: Commit**

```bash
git add site_health/models.py tests/test_models.py
git commit -m "feat: add data models for LinkResult and CrawlSummary"
```

---

## Task 3: Database Layer

**Files:**
- Create: `site_health/database.py`
- Create: `tests/test_database.py`

**Step 1: Write test for database initialization**

```python
# tests/test_database.py
import pytest
import aiosqlite
from pathlib import Path
from site_health.database import Database

@pytest.mark.asyncio
async def test_database_initialization(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))

    await db.initialize()

    # Verify database file was created
    assert db_path.exists()

    # Verify tables exist
    async with aiosqlite.connect(str(db_path)) as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in await cursor.fetchall()]
        assert "crawls" in tables
        assert "link_results" in tables
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database.py::test_database_initialization -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'site_health.database'"

**Step 3: Create database.py with schema**

```python
# site_health/database.py
"""Database layer for storing crawl results."""

import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from site_health.models import LinkResult, CrawlSummary


class Database:
    """SQLite database for crawl history and results."""

    def __init__(self, db_path: str = "site_health.db"):
        self.db_path = db_path

    async def initialize(self):
        """Create database schema if it doesn't exist."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS crawls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_url TEXT NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    max_depth INTEGER,
                    total_pages INTEGER DEFAULT 0,
                    total_links_checked INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running'
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS link_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    crawl_id INTEGER NOT NULL,
                    source_url TEXT NOT NULL,
                    target_url TEXT NOT NULL,
                    link_type TEXT NOT NULL,
                    status_code INTEGER,
                    response_time REAL,
                    severity TEXT NOT NULL,
                    error_message TEXT,
                    checked_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (crawl_id) REFERENCES crawls(id)
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_crawl_id
                ON link_results(crawl_id)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_severity
                ON link_results(severity)
            """)

            await conn.commit()

    async def create_crawl(self, start_url: str, max_depth: int) -> int:
        """Create a new crawl session and return its ID."""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                """
                INSERT INTO crawls (start_url, started_at, max_depth, status)
                VALUES (?, ?, ?, 'running')
                """,
                (start_url, datetime.now(), max_depth)
            )
            await conn.commit()
            return cursor.lastrowid

    async def save_link_result(self, crawl_id: int, result: LinkResult):
        """Save a single link check result."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT INTO link_results
                (crawl_id, source_url, target_url, link_type, status_code,
                 response_time, severity, error_message, checked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    crawl_id,
                    result.source_url,
                    result.target_url,
                    result.link_type,
                    result.status_code,
                    result.response_time,
                    result.severity,
                    result.error_message,
                    datetime.now()
                )
            )
            await conn.commit()

    async def complete_crawl(
        self,
        crawl_id: int,
        total_pages: int,
        total_links: int,
        status: str = "completed"
    ):
        """Mark crawl as completed and update statistics."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                UPDATE crawls
                SET completed_at = ?, total_pages = ?,
                    total_links_checked = ?, status = ?
                WHERE id = ?
                """,
                (datetime.now(), total_pages, total_links, status, crawl_id)
            )
            await conn.commit()

    async def get_crawl_summary(self, crawl_id: int) -> Optional[CrawlSummary]:
        """Get summary information for a crawl."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                """
                SELECT
                    c.*,
                    SUM(CASE WHEN lr.severity = 'error' THEN 1 ELSE 0 END) as errors,
                    SUM(CASE WHEN lr.severity = 'warning' THEN 1 ELSE 0 END) as warnings
                FROM crawls c
                LEFT JOIN link_results lr ON c.id = lr.crawl_id
                WHERE c.id = ?
                GROUP BY c.id
                """,
                (crawl_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return None

            return CrawlSummary(
                id=row["id"],
                start_url=row["start_url"],
                started_at=datetime.fromisoformat(row["started_at"]),
                completed_at=datetime.fromisoformat(row["completed_at"])
                    if row["completed_at"] else None,
                max_depth=row["max_depth"],
                total_pages=row["total_pages"],
                total_links=row["total_links_checked"],
                errors=row["errors"] or 0,
                warnings=row["warnings"] or 0,
                status=row["status"]
            )

    async def get_link_results(
        self,
        crawl_id: int,
        severity: Optional[str] = None
    ) -> List[LinkResult]:
        """Get link results for a crawl, optionally filtered by severity."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row

            if severity:
                cursor = await conn.execute(
                    """
                    SELECT * FROM link_results
                    WHERE crawl_id = ? AND severity = ?
                    ORDER BY checked_at
                    """,
                    (crawl_id, severity)
                )
            else:
                cursor = await conn.execute(
                    """
                    SELECT * FROM link_results
                    WHERE crawl_id = ?
                    ORDER BY severity DESC, checked_at
                    """,
                    (crawl_id,)
                )

            rows = await cursor.fetchall()
            return [
                LinkResult(
                    source_url=row["source_url"],
                    target_url=row["target_url"],
                    link_type=row["link_type"],
                    status_code=row["status_code"],
                    response_time=row["response_time"],
                    severity=row["severity"],
                    error_message=row["error_message"]
                )
                for row in rows
            ]

    async def list_crawls(self, limit: int = 50) -> List[CrawlSummary]:
        """List recent crawls."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                """
                SELECT
                    c.*,
                    SUM(CASE WHEN lr.severity = 'error' THEN 1 ELSE 0 END) as errors,
                    SUM(CASE WHEN lr.severity = 'warning' THEN 1 ELSE 0 END) as warnings
                FROM crawls c
                LEFT JOIN link_results lr ON c.id = lr.crawl_id
                GROUP BY c.id
                ORDER BY c.started_at DESC
                LIMIT ?
                """,
                (limit,)
            )
            rows = await cursor.fetchall()

            return [
                CrawlSummary(
                    id=row["id"],
                    start_url=row["start_url"],
                    started_at=datetime.fromisoformat(row["started_at"]),
                    completed_at=datetime.fromisoformat(row["completed_at"])
                        if row["completed_at"] else None,
                    max_depth=row["max_depth"],
                    total_pages=row["total_pages"],
                    total_links=row["total_links_checked"],
                    errors=row["errors"] or 0,
                    warnings=row["warnings"] or 0,
                    status=row["status"]
                )
                for row in rows
            ]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_database.py::test_database_initialization -v`
Expected: PASS

**Step 5: Write test for create_crawl**

```python
# tests/test_database.py (append)
@pytest.mark.asyncio
async def test_create_crawl(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    crawl_id = await db.create_crawl("https://example.com", max_depth=2)

    assert crawl_id > 0

    # Verify crawl was created
    summary = await db.get_crawl_summary(crawl_id)
    assert summary is not None
    assert summary.start_url == "https://example.com"
    assert summary.status == "running"
```

**Step 6: Run test to verify it passes**

Run: `pytest tests/test_database.py::test_create_crawl -v`
Expected: PASS

**Step 7: Write test for save_link_result**

```python
# tests/test_database.py (append)
from site_health.models import LinkResult

@pytest.mark.asyncio
async def test_save_link_result(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    crawl_id = await db.create_crawl("https://example.com", max_depth=2)

    result = LinkResult(
        source_url="https://example.com",
        target_url="https://example.com/page",
        link_type="page",
        status_code=404,
        response_time=0.5,
        severity="error",
        error_message="Not found"
    )

    await db.save_link_result(crawl_id, result)

    # Verify result was saved
    results = await db.get_link_results(crawl_id)
    assert len(results) == 1
    assert results[0].target_url == "https://example.com/page"
    assert results[0].status_code == 404
```

**Step 8: Run test to verify it passes**

Run: `pytest tests/test_database.py::test_save_link_result -v`
Expected: PASS

**Step 9: Commit**

```bash
git add site_health/database.py tests/test_database.py
git commit -m "feat: add database layer with SQLite operations"
```

---

## Task 4: Core Crawler

**Files:**
- Create: `site_health/crawler.py`
- Create: `tests/test_crawler.py`

**Step 1: Write test for URL normalization**

```python
# tests/test_crawler.py
import pytest
from site_health.crawler import SiteCrawler

def test_normalize_url():
    crawler = SiteCrawler("https://example.com", max_depth=1)

    # Test various URL formats
    assert crawler._normalize_url("page.html") == "https://example.com/page.html"
    assert crawler._normalize_url("/about") == "https://example.com/about"
    assert crawler._normalize_url("https://example.com/test") == "https://example.com/test"
    assert crawler._normalize_url("https://example.com/test#anchor") == "https://example.com/test"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_crawler.py::test_normalize_url -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'site_health.crawler'"

**Step 3: Create crawler.py with basic structure**

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_crawler.py::test_normalize_url -v`
Expected: PASS

**Step 5: Write test for checking single link**

```python
# tests/test_crawler.py (append)
import httpx
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_check_link_success():
    crawler = SiteCrawler("https://example.com", max_depth=1)

    # Mock successful response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.elapsed.total_seconds.return_value = 0.5

    with patch.object(httpx.AsyncClient, 'head', return_value=mock_response):
        result = await crawler._check_link(
            "https://example.com",
            "https://example.com/page"
        )

    assert result.status_code == 200
    assert result.severity == "success"
    assert result.link_type == "page"

@pytest.mark.asyncio
async def test_check_link_404():
    crawler = SiteCrawler("https://example.com", max_depth=1)

    # Mock 404 response
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_response.elapsed.total_seconds.return_value = 0.3

    with patch.object(httpx.AsyncClient, 'head', return_value=mock_response):
        result = await crawler._check_link(
            "https://example.com",
            "https://example.com/missing"
        )

    assert result.status_code == 404
    assert result.severity == "error"
```

**Step 6: Run test to verify it fails**

Run: `pytest tests/test_crawler.py::test_check_link_success -v`
Expected: FAIL with "AttributeError: 'SiteCrawler' object has no attribute '_check_link'"

**Step 7: Implement _check_link method**

```python
# site_health/crawler.py (add to SiteCrawler class)
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
```

**Step 8: Run tests to verify they pass**

Run: `pytest tests/test_crawler.py -v`
Expected: All tests PASS

**Step 9: Commit**

```bash
git add site_health/crawler.py tests/test_crawler.py
git commit -m "feat: add URL normalization and link checking"
```

**Step 10: Write test for extracting links from HTML**

```python
# tests/test_crawler.py (append)
@pytest.mark.asyncio
async def test_extract_links():
    crawler = SiteCrawler("https://example.com", max_depth=1)

    html = """
    <html>
        <head>
            <link rel="stylesheet" href="/style.css">
            <script src="/script.js"></script>
        </head>
        <body>
            <a href="/page1">Page 1</a>
            <a href="https://external.com">External</a>
            <img src="/image.png">
        </body>
    </html>
    """

    links = crawler._extract_links(html, "https://example.com")

    assert "https://example.com/page1" in links
    assert "https://example.com/style.css" in links
    assert "https://example.com/script.js" in links
    assert "https://example.com/image.png" in links
    assert "https://external.com" in links
```

**Step 11: Run test to verify it fails**

Run: `pytest tests/test_crawler.py::test_extract_links -v`
Expected: FAIL with "AttributeError: 'SiteCrawler' object has no attribute '_extract_links'"

**Step 12: Implement _extract_links method**

```python
# site_health/crawler.py (add to SiteCrawler class)
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
```

**Step 13: Run test to verify it passes**

Run: `pytest tests/test_crawler.py::test_extract_links -v`
Expected: PASS

**Step 14: Implement main crawl method**

```python
# site_health/crawler.py (add to SiteCrawler class)
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
```

**Step 15: Write integration test for full crawl**

```python
# tests/test_crawler.py (append)
@pytest.mark.asyncio
async def test_full_crawl_simple(tmp_path):
    """Test crawling with mocked responses."""
    crawler = SiteCrawler("https://example.com", max_depth=1)

    # Mock responses
    async def mock_get(url, *args, **kwargs):
        response = AsyncMock()
        response.headers = {'content-type': 'text/html'}
        response.elapsed.total_seconds.return_value = 0.1

        if url == "https://example.com":
            response.status_code = 200
            response.text = '<a href="/page1">Page 1</a>'
        elif url == "https://example.com/page1":
            response.status_code = 200
            response.text = '<p>Content</p>'
        else:
            response.status_code = 404
            response.text = 'Not found'

        return response

    with patch.object(httpx.AsyncClient, 'get', side_effect=mock_get), \
         patch.object(httpx.AsyncClient, 'head', side_effect=mock_get):
        results = await crawler.crawl()

    assert len(results) > 0
    assert crawler.pages_crawled >= 1
```

**Step 16: Run integration test**

Run: `pytest tests/test_crawler.py::test_full_crawl_simple -v`
Expected: PASS

**Step 17: Commit**

```bash
git add site_health/crawler.py tests/test_crawler.py
git commit -m "feat: implement core crawling logic with link extraction"
```

---

## Task 5: Report Generation - Terminal Output

**Files:**
- Create: `site_health/report.py`
- Create: `tests/test_report.py`

**Step 1: Write test for terminal report generation**

```python
# tests/test_report.py
import pytest
from site_health.report import ReportGenerator
from site_health.database import Database
from site_health.models import LinkResult

@pytest.mark.asyncio
async def test_terminal_report_generation(tmp_path):
    # Setup database with test data
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    crawl_id = await db.create_crawl("https://example.com", max_depth=2)

    # Add some test results
    await db.save_link_result(crawl_id, LinkResult(
        source_url="https://example.com",
        target_url="https://example.com/missing",
        link_type="page",
        status_code=404,
        response_time=0.5,
        severity="error",
        error_message="Not found"
    ))

    await db.save_link_result(crawl_id, LinkResult(
        source_url="https://example.com",
        target_url="https://example.com/slow",
        link_type="page",
        status_code=200,
        response_time=6.0,
        severity="warning",
        error_message=None
    ))

    await db.complete_crawl(crawl_id, total_pages=10, total_links=25)

    # Generate report
    generator = ReportGenerator(crawl_id, db)
    report = await generator.generate('terminal')

    assert "Site Health Report" in report
    assert "404" in report
    assert "error" in report.lower()
    assert "warning" in report.lower()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_report.py::test_terminal_report_generation -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'site_health.report'"

**Step 3: Create report.py with terminal output**

```python
# site_health/report.py
"""Report generation for crawl results."""

from pathlib import Path
from typing import Optional
from site_health.database import Database
from site_health.models import CrawlSummary, LinkResult


class ReportGenerator:
    """Generate reports in various formats."""

    def __init__(self, crawl_id: int, db: Database):
        self.crawl_id = crawl_id
        self.db = db

    async def generate(self, format: str = 'terminal') -> str:
        """Generate report in specified format."""
        if format == 'terminal':
            return await self._generate_terminal()
        elif format == 'html':
            return await self._generate_html()
        elif format == 'json':
            return await self._generate_json()
        else:
            raise ValueError(f"Unknown format: {format}")

    async def _generate_terminal(self) -> str:
        """Generate colorized terminal output."""
        summary = await self.db.get_crawl_summary(self.crawl_id)
        if not summary:
            return "Crawl not found"

        # ANSI color codes
        RED = '\033[91m'
        YELLOW = '\033[93m'
        GREEN = '\033[92m'
        BOLD = '\033[1m'
        RESET = '\033[0m'

        lines = []
        lines.append(f"\n{BOLD}=== Site Health Report ==={RESET}\n")
        lines.append(f"URL: {summary.start_url}")
        lines.append(f"Status: {summary.status}")
        lines.append(f"Crawl Depth: {summary.max_depth}")
        lines.append(f"Pages Crawled: {summary.total_pages}")
        lines.append(f"Total Links Checked: {summary.total_links}")

        if summary.completed_at:
            duration = summary.completed_at - summary.started_at
            lines.append(f"Duration: {duration.total_seconds():.1f}s")

        lines.append("")

        # Summary statistics
        lines.append(f"{BOLD}Summary:{RESET}")
        lines.append(f"  {RED}Errors: {summary.errors}{RESET}")
        lines.append(f"  {YELLOW}Warnings: {summary.warnings}{RESET}")
        lines.append(f"  {GREEN}Success: {summary.total_links - summary.errors - summary.warnings}{RESET}")
        lines.append("")

        # Errors section
        if summary.errors > 0:
            lines.append(f"{BOLD}{RED}=== Errors ==={RESET}")
            errors = await self.db.get_link_results(self.crawl_id, severity='error')

            for result in errors[:20]:  # Limit to first 20
                lines.append(f"\n{RED}✗{RESET} {result.target_url}")
                lines.append(f"  Source: {result.source_url}")
                lines.append(f"  Type: {result.link_type}")
                if result.status_code:
                    lines.append(f"  Status: {result.status_code}")
                if result.error_message:
                    lines.append(f"  Error: {result.error_message}")

            if len(errors) > 20:
                lines.append(f"\n... and {len(errors) - 20} more errors")

            lines.append("")

        # Warnings section
        if summary.warnings > 0:
            lines.append(f"{BOLD}{YELLOW}=== Warnings ==={RESET}")
            warnings = await self.db.get_link_results(self.crawl_id, severity='warning')

            for result in warnings[:10]:  # Limit to first 10
                lines.append(f"\n{YELLOW}⚠{RESET} {result.target_url}")
                lines.append(f"  Source: {result.source_url}")
                if result.status_code:
                    lines.append(f"  Status: {result.status_code}")
                if result.response_time > 5.0:
                    lines.append(f"  Slow response: {result.response_time:.1f}s")

            if len(warnings) > 10:
                lines.append(f"\n... and {len(warnings) - 10} more warnings")

            lines.append("")

        # Statistics by type
        all_results = await self.db.get_link_results(self.crawl_id)
        by_type = {}
        for result in all_results:
            by_type[result.link_type] = by_type.get(result.link_type, 0) + 1

        if by_type:
            lines.append(f"{BOLD}Links by Type:{RESET}")
            for link_type, count in sorted(by_type.items()):
                lines.append(f"  {link_type}: {count}")

        return "\n".join(lines)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_report.py::test_terminal_report_generation -v`
Expected: PASS

**Step 5: Commit**

```bash
git add site_health/report.py tests/test_report.py
git commit -m "feat: add terminal report generation with colored output"
```

---

## Task 6: Report Generation - HTML and JSON

**Files:**
- Modify: `site_health/report.py`
- Create: `site_health/templates/report.html`
- Modify: `tests/test_report.py`

**Step 1: Write test for JSON report**

```python
# tests/test_report.py (append)
import json

@pytest.mark.asyncio
async def test_json_report_generation(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    crawl_id = await db.create_crawl("https://example.com", max_depth=2)

    await db.save_link_result(crawl_id, LinkResult(
        source_url="https://example.com",
        target_url="https://example.com/page",
        link_type="page",
        status_code=200,
        response_time=0.5,
        severity="success"
    ))

    await db.complete_crawl(crawl_id, total_pages=1, total_links=1)

    generator = ReportGenerator(crawl_id, db)
    report = await generator.generate('json')

    data = json.loads(report)
    assert data['crawl_id'] == crawl_id
    assert 'summary' in data
    assert 'results' in data
    assert len(data['results']) == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_report.py::test_json_report_generation -v`
Expected: FAIL (JSON generation not implemented)

**Step 3: Implement JSON report generation**

```python
# site_health/report.py (add to ReportGenerator class)
import json

    async def _generate_json(self) -> str:
        """Generate JSON output."""
        summary = await self.db.get_crawl_summary(self.crawl_id)
        if not summary:
            return json.dumps({"error": "Crawl not found"})

        results = await self.db.get_link_results(self.crawl_id)

        data = {
            "crawl_id": self.crawl_id,
            "summary": {
                "start_url": summary.start_url,
                "status": summary.status,
                "started_at": summary.started_at.isoformat(),
                "completed_at": summary.completed_at.isoformat() if summary.completed_at else None,
                "max_depth": summary.max_depth,
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
            ]
        }

        return json.dumps(data, indent=2)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_report.py::test_json_report_generation -v`
Expected: PASS

**Step 5: Create HTML template directory and file**

```bash
mkdir -p site_health/templates
```

```html
<!-- site_health/templates/report.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Site Health Report - {{ summary.start_url }}</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: system-ui, -apple-system, sans-serif; line-height: 1.6; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; margin-bottom: 10px; }
        h2 { color: #555; margin: 30px 0 15px; padding-bottom: 10px; border-bottom: 2px solid #eee; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat { background: #f8f9fa; padding: 15px; border-radius: 5px; }
        .stat-label { font-size: 12px; color: #666; text-transform: uppercase; }
        .stat-value { font-size: 24px; font-weight: bold; margin-top: 5px; }
        .error { color: #dc3545; }
        .warning { color: #ffc107; }
        .success { color: #28a745; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #ddd; }
        th { background: #f8f9fa; font-weight: 600; position: sticky; top: 0; }
        tr:hover { background: #f8f9fa; }
        .badge { display: inline-block; padding: 3px 8px; border-radius: 3px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
        .badge-error { background: #dc3545; color: white; }
        .badge-warning { background: #ffc107; color: black; }
        .badge-success { background: #28a745; color: white; }
        .url { word-break: break-all; font-family: monospace; font-size: 13px; }
        .filter { margin: 20px 0; }
        .filter button { padding: 8px 16px; margin-right: 10px; border: 1px solid #ddd; background: white; cursor: pointer; border-radius: 4px; }
        .filter button.active { background: #007bff; color: white; border-color: #007bff; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Site Health Report</h1>
        <p><strong>URL:</strong> <span class="url">{{ summary.start_url }}</span></p>
        <p><strong>Status:</strong> {{ summary.status }} | <strong>Completed:</strong> {{ summary.completed_at or 'In Progress' }}</p>

        <div class="summary">
            <div class="stat">
                <div class="stat-label">Pages Crawled</div>
                <div class="stat-value">{{ summary.total_pages }}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Links Checked</div>
                <div class="stat-value">{{ summary.total_links }}</div>
            </div>
            <div class="stat">
                <div class="stat-label error">Errors</div>
                <div class="stat-value error">{{ summary.errors }}</div>
            </div>
            <div class="stat">
                <div class="stat-label warning">Warnings</div>
                <div class="stat-value warning">{{ summary.warnings }}</div>
            </div>
        </div>

        <h2>Results</h2>

        <div class="filter">
            <button class="active" onclick="filterResults('all')">All</button>
            <button onclick="filterResults('error')">Errors Only</button>
            <button onclick="filterResults('warning')">Warnings Only</button>
            <button onclick="filterResults('success')">Success Only</button>
        </div>

        <table id="results-table">
            <thead>
                <tr>
                    <th>Status</th>
                    <th>Type</th>
                    <th>Target URL</th>
                    <th>Source URL</th>
                    <th>Code</th>
                    <th>Time (s)</th>
                </tr>
            </thead>
            <tbody>
                {% for result in results %}
                <tr class="result-row" data-severity="{{ result.severity }}">
                    <td>
                        <span class="badge badge-{{ result.severity }}">{{ result.severity }}</span>
                    </td>
                    <td>{{ result.link_type }}</td>
                    <td class="url">{{ result.target_url }}</td>
                    <td class="url">{{ result.source_url }}</td>
                    <td>{{ result.status_code or 'N/A' }}</td>
                    <td>{{ "%.2f"|format(result.response_time) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <script>
        function filterResults(severity) {
            const rows = document.querySelectorAll('.result-row');
            const buttons = document.querySelectorAll('.filter button');

            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');

            rows.forEach(row => {
                if (severity === 'all' || row.dataset.severity === severity) {
                    row.classList.remove('hidden');
                } else {
                    row.classList.add('hidden');
                }
            });
        }
    </script>
</body>
</html>
```

**Step 6: Implement HTML report generation**

```python
# site_health/report.py (add imports at top)
from jinja2 import Environment, PackageLoader, select_autoescape

# Add to ReportGenerator class
    async def _generate_html(self) -> str:
        """Generate HTML report and save to reports directory."""
        from pathlib import Path

        summary = await self.db.get_crawl_summary(self.crawl_id)
        if not summary:
            return "Crawl not found"

        results = await self.db.get_link_results(self.crawl_id)

        # Setup Jinja2
        env = Environment(
            loader=PackageLoader('site_health', 'templates'),
            autoescape=select_autoescape(['html'])
        )
        template = env.get_template('report.html')

        # Render template
        html = template.render(
            summary=summary,
            results=results
        )

        # Save to reports directory
        reports_dir = Path('reports')
        reports_dir.mkdir(exist_ok=True)

        timestamp = summary.started_at.strftime('%Y%m%d_%H%M%S')
        filename = f"crawl_{self.crawl_id}_{timestamp}.html"
        filepath = reports_dir / filename

        filepath.write_text(html)

        return str(filepath)
```

**Step 7: Write test for HTML generation**

```python
# tests/test_report.py (append)
from pathlib import Path

@pytest.mark.asyncio
async def test_html_report_generation(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    crawl_id = await db.create_crawl("https://example.com", max_depth=2)
    await db.complete_crawl(crawl_id, total_pages=1, total_links=1)

    # Change to temp directory for report generation
    import os
    original_dir = os.getcwd()
    os.chdir(tmp_path)

    try:
        generator = ReportGenerator(crawl_id, db)
        filepath = await generator.generate('html')

        assert Path(filepath).exists()
        assert filepath.endswith('.html')

        # Verify HTML content
        content = Path(filepath).read_text()
        assert '<!DOCTYPE html>' in content
        assert 'Site Health Report' in content
    finally:
        os.chdir(original_dir)
```

**Step 8: Run test to verify it passes**

Run: `pytest tests/test_report.py::test_html_report_generation -v`
Expected: PASS

**Step 9: Commit**

```bash
git add site_health/report.py site_health/templates/report.html tests/test_report.py
git commit -m "feat: add HTML and JSON report generation"
```

---

## Task 7: Configuration File Support

**Files:**
- Create: `site_health/config.py`
- Create: `tests/test_config.py`

**Step 1: Write test for loading YAML config**

```python
# tests/test_config.py
import pytest
from pathlib import Path
from site_health.config import Config

def test_load_config_from_yaml(tmp_path):
    config_file = tmp_path / "test.yaml"
    config_file.write_text("""
url: https://example.com
depth: 3
max_concurrent: 5
timeout: 15.0
respect_robots: false
output_format: json
""")

    config = Config.from_yaml(str(config_file))

    assert config.url == "https://example.com"
    assert config.depth == 3
    assert config.max_concurrent == 5
    assert config.timeout == 15.0
    assert config.respect_robots == False
    assert config.output_format == "json"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py::test_load_config_from_yaml -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'site_health.config'"

**Step 3: Create config.py**

```python
# site_health/config.py
"""Configuration management for site-health."""

import yaml
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Configuration for site health crawler."""

    url: Optional[str] = None
    depth: int = 2
    max_concurrent: int = 10
    timeout: float = 10.0
    respect_robots: bool = True
    output_format: str = "terminal"
    output_path: Optional[str] = None

    @classmethod
    def from_yaml(cls, filepath: str) -> 'Config':
        """Load configuration from YAML file."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")

        with open(filepath, 'r') as f:
            data = yaml.safe_load(f) or {}

        return cls(**data)

    def merge_with_args(self, **kwargs) -> 'Config':
        """Create new config by merging with command-line arguments.

        Command-line arguments override config file values.
        """
        # Start with current config values
        merged = {
            'url': self.url,
            'depth': self.depth,
            'max_concurrent': self.max_concurrent,
            'timeout': self.timeout,
            'respect_robots': self.respect_robots,
            'output_format': self.output_format,
            'output_path': self.output_path,
        }

        # Override with any non-None kwargs
        for key, value in kwargs.items():
            if value is not None:
                merged[key] = value

        return Config(**merged)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py::test_load_config_from_yaml -v`
Expected: PASS

**Step 5: Write test for merging CLI args with config**

```python
# tests/test_config.py (append)
def test_merge_config_with_cli_args(tmp_path):
    config_file = tmp_path / "test.yaml"
    config_file.write_text("""
url: https://example.com
depth: 2
output_format: html
""")

    config = Config.from_yaml(str(config_file))

    # CLI args should override config file
    merged = config.merge_with_args(depth=5, output_format="json")

    assert merged.url == "https://example.com"  # From config
    assert merged.depth == 5  # Overridden by CLI
    assert merged.output_format == "json"  # Overridden by CLI
```

**Step 6: Run test to verify it passes**

Run: `pytest tests/test_config.py::test_merge_config_with_cli_args -v`
Expected: PASS

**Step 7: Commit**

```bash
git add site_health/config.py tests/test_config.py
git commit -m "feat: add configuration file support with YAML"
```

---

## Task 8: CLI Interface

**Files:**
- Create: `site_health/cli.py`
- Create: `tests/test_cli.py`

**Step 1: Create CLI with crawl command**

```python
# site_health/cli.py
"""Command-line interface for site-health."""

import asyncio
import typer
from pathlib import Path
from typing import Optional
from site_health.config import Config
from site_health.crawler import SiteCrawler
from site_health.database import Database
from site_health.report import ReportGenerator

app = typer.Typer(help="Crawl websites and check for broken links")


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
        db_path=db_path,
    ))


async def _crawl_async(
    url: Optional[str],
    depth: Optional[int],
    format: Optional[str],
    output: Optional[str],
    config_file: Optional[str],
    max_concurrent: Optional[int],
    timeout: Optional[float],
    no_robots: bool,
    db_path: str,
):
    """Async implementation of crawl command."""
    # Load config file if provided
    if config_file:
        config = Config.from_yaml(config_file)
    else:
        config = Config()

    # Merge with CLI arguments (CLI takes precedence)
    config = config.merge_with_args(
        url=url,
        depth=depth,
        output_format=format,
        output_path=output,
        max_concurrent=max_concurrent,
        timeout=timeout,
        respect_robots=not no_robots,
    )

    # Validate required fields
    if not config.url:
        typer.echo("Error: URL is required (provide via argument or config file)", err=True)
        raise typer.Exit(1)

    typer.echo(f"Starting crawl of {config.url}...")
    typer.echo(f"Max depth: {config.depth}")

    # Initialize database
    db = Database(db_path)
    await db.initialize()

    # Create crawl session
    crawl_id = await db.create_crawl(config.url, config.depth)

    try:
        # Run crawler
        crawler = SiteCrawler(
            start_url=config.url,
            max_depth=config.depth,
            max_concurrent=config.max_concurrent,
            timeout=config.timeout,
            respect_robots=config.respect_robots,
        )

        results = await crawler.crawl()

        # Save results to database
        for result in results:
            await db.save_link_result(crawl_id, result)

        # Mark crawl as complete
        await db.complete_crawl(
            crawl_id,
            total_pages=crawler.pages_crawled,
            total_links=len(results),
        )

        typer.echo(f"\nCrawl complete! Pages crawled: {crawler.pages_crawled}, Links checked: {len(results)}")

        # Generate report
        generator = ReportGenerator(crawl_id, db)
        report = await generator.generate(config.output_format)

        if config.output_format == 'terminal':
            typer.echo(report)
        elif config.output_format == 'html':
            typer.echo(f"\nHTML report saved to: {report}")
        elif config.output_format == 'json':
            if config.output_path:
                Path(config.output_path).write_text(report)
                typer.echo(f"\nJSON report saved to: {config.output_path}")
            else:
                typer.echo(report)

    except Exception as e:
        # Mark crawl as failed
        await db.complete_crawl(crawl_id, total_pages=0, total_links=0, status="failed")
        typer.echo(f"Error during crawl: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def list(
    db_path: str = typer.Option("site_health.db", "--db", help="Database path"),
    limit: int = typer.Option(50, "--limit", "-n", help="Number of crawls to show"),
):
    """List previous crawls."""
    asyncio.run(_list_async(db_path, limit))


async def _list_async(db_path: str, limit: int):
    """Async implementation of list command."""
    db = Database(db_path)
    await db.initialize()

    crawls = await db.list_crawls(limit)

    if not crawls:
        typer.echo("No crawls found")
        return

    # Print table header
    typer.echo("\n{:<5} {:<40} {:<20} {:<10} {:<8} {:<8}".format(
        "ID", "URL", "Date", "Status", "Errors", "Warnings"
    ))
    typer.echo("-" * 100)

    # Print crawls
    for crawl in crawls:
        date_str = crawl.started_at.strftime("%Y-%m-%d %H:%M")
        url_short = crawl.start_url[:37] + "..." if len(crawl.start_url) > 40 else crawl.start_url

        typer.echo("{:<5} {:<40} {:<20} {:<10} {:<8} {:<8}".format(
            crawl.id,
            url_short,
            date_str,
            crawl.status,
            crawl.errors,
            crawl.warnings,
        ))


@app.command()
def report(
    crawl_id: int = typer.Argument(..., help="Crawl ID to generate report for"),
    format: str = typer.Option("terminal", "--format", "-f", help="Output format"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    db_path: str = typer.Option("site_health.db", "--db", help="Database path"),
):
    """Generate report for a previous crawl."""
    asyncio.run(_report_async(crawl_id, format, output, db_path))


async def _report_async(crawl_id: int, format: str, output: Optional[str], db_path: str):
    """Async implementation of report command."""
    db = Database(db_path)
    await db.initialize()

    generator = ReportGenerator(crawl_id, db)
    report_output = await generator.generate(format)

    if format == 'terminal':
        typer.echo(report_output)
    elif format == 'html':
        typer.echo(f"HTML report saved to: {report_output}")
    elif format == 'json':
        if output:
            Path(output).write_text(report_output)
            typer.echo(f"JSON report saved to: {output}")
        else:
            typer.echo(report_output)


@app.command()
def serve(
    port: int = typer.Option(8000, "--port", "-p", help="Port to run server on"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to"),
    db_path: str = typer.Option("site_health.db", "--db", help="Database path"),
):
    """Start web interface."""
    import uvicorn
    from site_health.web.app import create_app

    app = create_app(db_path)

    typer.echo(f"Starting web server on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    app()
```

**Step 2: Write basic CLI test**

```python
# tests/test_cli.py
from typer.testing import CliRunner
from site_health.cli import app

runner = CliRunner()

def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Crawl websites" in result.output

def test_crawl_missing_url():
    result = runner.invoke(app, ["crawl"])
    assert result.exit_code == 1
    assert "Error" in result.output
```

**Step 3: Run tests**

Run: `pytest tests/test_cli.py -v`
Expected: PASS

**Step 4: Test CLI installation**

Run: `site-health --help`
Expected: Help message displayed

**Step 5: Commit**

```bash
git add site_health/cli.py tests/test_cli.py
git commit -m "feat: add CLI interface with crawl, list, report, and serve commands"
```

---

## Task 9: Web Interface - FastAPI Backend

**Files:**
- Create: `site_health/web/__init__.py`
- Create: `site_health/web/app.py`
- Create: `tests/test_web.py`

**Step 1: Write test for API endpoints**

```python
# tests/test_web.py
import pytest
from httpx import AsyncClient
from site_health.web.app import create_app
from site_health.database import Database

@pytest.mark.asyncio
async def test_list_crawls_endpoint(tmp_path):
    db_path = tmp_path / "test.db"
    app = create_app(str(db_path))

    # Initialize database
    db = Database(str(db_path))
    await db.initialize()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/crawls")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web.py::test_list_crawls_endpoint -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'site_health.web.app'"

**Step 3: Create web/__init__.py**

```python
# site_health/web/__init__.py
"""Web interface for site-health."""
```

**Step 4: Create web/app.py**

```python
# site_health/web/app.py
"""FastAPI web application."""

import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, List
from site_health.database import Database
from site_health.crawler import SiteCrawler
from site_health.report import ReportGenerator


# Request/Response models
class CrawlRequest(BaseModel):
    url: str
    depth: int = 2
    max_concurrent: int = 10
    timeout: float = 10.0


class CrawlResponse(BaseModel):
    crawl_id: int
    message: str


def create_app(db_path: str = "site_health.db") -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(title="Site Health", version="0.1.0")

    # Initialize database
    db = Database(db_path)

    @app.on_event("startup")
    async def startup():
        await db.initialize()

    @app.get("/")
    async def home():
        """Serve home page."""
        # For now, return simple message
        # Will add proper HTML template in next task
        return {"message": "Site Health API", "version": "0.1.0"}

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
            db=db,
        )

        return CrawlResponse(
            crawl_id=crawl_id,
            message=f"Crawl started for {request.url}"
        )

    @app.get("/api/crawls")
    async def list_crawls(limit: int = 50):
        """List all crawls."""
        crawls = await db.list_crawls(limit)
        return [
            {
                "id": c.id,
                "start_url": c.start_url,
                "started_at": c.started_at.isoformat(),
                "completed_at": c.completed_at.isoformat() if c.completed_at else None,
                "status": c.status,
                "total_pages": c.total_pages,
                "total_links": c.total_links,
                "errors": c.errors,
                "warnings": c.warnings,
            }
            for c in crawls
        ]

    @app.get("/api/crawls/{crawl_id}")
    async def get_crawl(crawl_id: int):
        """Get details for a specific crawl."""
        summary = await db.get_crawl_summary(crawl_id)
        if not summary:
            raise HTTPException(status_code=404, detail="Crawl not found")

        results = await db.get_link_results(crawl_id)

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
            ]
        }

    @app.get("/api/crawls/{crawl_id}/report")
    async def get_crawl_report(crawl_id: int, format: str = "json"):
        """Get report for a crawl in specified format."""
        summary = await db.get_crawl_summary(crawl_id)
        if not summary:
            raise HTTPException(status_code=404, detail="Crawl not found")

        generator = ReportGenerator(crawl_id, db)

        if format == "html":
            filepath = await generator.generate('html')
            return FileResponse(filepath, media_type="text/html")
        elif format == "json":
            report = await generator.generate('json')
            return report
        else:
            raise HTTPException(status_code=400, detail="Invalid format")

    # Serve static reports
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    app.mount("/reports", StaticFiles(directory="reports"), name="reports")

    return app


async def run_crawl(
    crawl_id: int,
    url: str,
    depth: int,
    max_concurrent: int,
    timeout: float,
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

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_web.py::test_list_crawls_endpoint -v`
Expected: PASS

**Step 6: Write more API tests**

```python
# tests/test_web.py (append)
@pytest.mark.asyncio
async def test_start_crawl_endpoint(tmp_path):
    db_path = tmp_path / "test.db"
    app = create_app(str(db_path))

    db = Database(str(db_path))
    await db.initialize()

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/crawl",
            json={"url": "https://example.com", "depth": 1}
        )
        assert response.status_code == 200
        data = response.json()
        assert "crawl_id" in data
        assert data["crawl_id"] > 0
```

**Step 7: Run test**

Run: `pytest tests/test_web.py::test_start_crawl_endpoint -v`
Expected: PASS

**Step 8: Commit**

```bash
git add site_health/web/__init__.py site_health/web/app.py tests/test_web.py
git commit -m "feat: add FastAPI backend with crawl API endpoints"
```

---

## Task 10: Web Interface - Frontend

**Files:**
- Create: `site_health/web/templates/index.html`
- Create: `site_health/web/static/style.css`
- Modify: `site_health/web/app.py`

**Step 1: Create templates directory**

```bash
mkdir -p site_health/web/templates site_health/web/static
```

**Step 2: Create index.html**

```html
<!-- site_health/web/templates/index.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Site Health</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>Site Health</h1>
            <p>Crawl websites and check for broken links</p>
        </header>

        <section class="crawl-form">
            <h2>Start New Crawl</h2>
            <form id="crawlForm">
                <div class="form-group">
                    <label for="url">URL to Crawl</label>
                    <input type="url" id="url" name="url" required
                           placeholder="https://example.com">
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label for="depth">Max Depth</label>
                        <select id="depth" name="depth">
                            <option value="1">1</option>
                            <option value="2" selected>2</option>
                            <option value="3">3</option>
                            <option value="4">4</option>
                            <option value="5">5</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="maxConcurrent">Max Concurrent</label>
                        <input type="number" id="maxConcurrent" name="maxConcurrent"
                               value="10" min="1" max="50">
                    </div>

                    <div class="form-group">
                        <label for="timeout">Timeout (s)</label>
                        <input type="number" id="timeout" name="timeout"
                               value="10" min="5" max="60" step="0.5">
                    </div>
                </div>

                <button type="submit" class="btn-primary">Start Crawl</button>
            </form>

            <div id="message" class="message hidden"></div>
        </section>

        <section class="crawl-history">
            <div class="section-header">
                <h2>Crawl History</h2>
                <button onclick="loadCrawls()" class="btn-secondary">Refresh</button>
            </div>

            <table id="crawlsTable">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>URL</th>
                        <th>Date</th>
                        <th>Status</th>
                        <th>Pages</th>
                        <th>Errors</th>
                        <th>Warnings</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="crawlsBody">
                    <tr>
                        <td colspan="8" class="loading">Loading...</td>
                    </tr>
                </tbody>
            </table>
        </section>
    </div>

    <script>
        // Load crawls on page load
        loadCrawls();

        // Handle form submission
        document.getElementById('crawlForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = new FormData(e.target);
            const data = {
                url: formData.get('url'),
                depth: parseInt(formData.get('depth')),
                max_concurrent: parseInt(formData.get('maxConcurrent')),
                timeout: parseFloat(formData.get('timeout'))
            };

            try {
                const response = await fetch('/api/crawl', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (response.ok) {
                    showMessage(`Crawl started! ID: ${result.crawl_id}`, 'success');
                    setTimeout(() => loadCrawls(), 2000);
                } else {
                    showMessage('Error starting crawl: ' + result.detail, 'error');
                }
            } catch (error) {
                showMessage('Error: ' + error.message, 'error');
            }
        });

        async function loadCrawls() {
            try {
                const response = await fetch('/api/crawls');
                const crawls = await response.json();

                const tbody = document.getElementById('crawlsBody');

                if (crawls.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8">No crawls yet</td></tr>';
                    return;
                }

                tbody.innerHTML = crawls.map(crawl => `
                    <tr>
                        <td>${crawl.id}</td>
                        <td class="url">${truncateUrl(crawl.start_url, 50)}</td>
                        <td>${formatDate(crawl.started_at)}</td>
                        <td><span class="status status-${crawl.status}">${crawl.status}</span></td>
                        <td>${crawl.total_pages}</td>
                        <td class="error">${crawl.errors}</td>
                        <td class="warning">${crawl.warnings}</td>
                        <td>
                            <button onclick="viewReport(${crawl.id})" class="btn-small">View</button>
                            <a href="/api/crawls/${crawl.id}/report?format=json"
                               download="crawl-${crawl.id}.json" class="btn-small">JSON</a>
                        </td>
                    </tr>
                `).join('');
            } catch (error) {
                document.getElementById('crawlsBody').innerHTML =
                    `<tr><td colspan="8">Error loading crawls</td></tr>`;
            }
        }

        function viewReport(crawlId) {
            window.open(`/api/crawls/${crawlId}/report?format=html`, '_blank');
        }

        function showMessage(text, type) {
            const messageEl = document.getElementById('message');
            messageEl.textContent = text;
            messageEl.className = `message message-${type}`;
            setTimeout(() => messageEl.classList.add('hidden'), 5000);
        }

        function formatDate(dateStr) {
            const date = new Date(dateStr);
            return date.toLocaleString();
        }

        function truncateUrl(url, maxLen) {
            return url.length > maxLen ? url.substring(0, maxLen) + '...' : url;
        }
    </script>
</body>
</html>
```

**Step 3: Create style.css**

```css
/* site_health/web/static/style.css */
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
    line-height: 1.6;
    color: #333;
    background: #f5f5f5;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

header {
    background: white;
    padding: 30px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin-bottom: 30px;
}

header h1 {
    color: #2c3e50;
    margin-bottom: 5px;
}

header p {
    color: #7f8c8d;
}

section {
    background: white;
    padding: 30px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    margin-bottom: 30px;
}

h2 {
    margin-bottom: 20px;
    color: #2c3e50;
}

.form-group {
    margin-bottom: 20px;
}

.form-group label {
    display: block;
    margin-bottom: 5px;
    font-weight: 600;
    color: #555;
}

.form-group input,
.form-group select {
    width: 100%;
    padding: 10px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
}

.form-row {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 15px;
}

.btn-primary {
    background: #3498db;
    color: white;
    border: none;
    padding: 12px 30px;
    border-radius: 4px;
    font-size: 16px;
    cursor: pointer;
    font-weight: 600;
}

.btn-primary:hover {
    background: #2980b9;
}

.btn-secondary {
    background: #95a5a6;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
}

.btn-secondary:hover {
    background: #7f8c8d;
}

.btn-small {
    background: #ecf0f1;
    border: 1px solid #bdc3c7;
    padding: 4px 12px;
    border-radius: 3px;
    cursor: pointer;
    font-size: 12px;
    text-decoration: none;
    color: #2c3e50;
    display: inline-block;
    margin-right: 5px;
}

.btn-small:hover {
    background: #bdc3c7;
}

.message {
    margin-top: 20px;
    padding: 15px;
    border-radius: 4px;
}

.message-success {
    background: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
}

.message-error {
    background: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}

.message.hidden {
    display: none;
}

.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th, td {
    text-align: left;
    padding: 12px;
    border-bottom: 1px solid #ddd;
}

th {
    background: #f8f9fa;
    font-weight: 600;
    color: #2c3e50;
}

tr:hover {
    background: #f8f9fa;
}

.url {
    font-family: monospace;
    font-size: 13px;
}

.status {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 3px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
}

.status-running {
    background: #fff3cd;
    color: #856404;
}

.status-completed {
    background: #d4edda;
    color: #155724;
}

.status-failed {
    background: #f8d7da;
    color: #721c24;
}

.error {
    color: #dc3545;
    font-weight: 600;
}

.warning {
    color: #ffc107;
    font-weight: 600;
}

.loading {
    text-align: center;
    color: #7f8c8d;
    font-style: italic;
}
```

**Step 4: Update app.py to serve HTML**

```python
# site_health/web/app.py (modify create_app function)
# Add these imports at the top
from fastapi.templating import Jinja2Templates
from fastapi import Request

# In create_app function, add after app creation:
    # Setup templates and static files
    templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

    # Update home route
    @app.get("/")
    async def home(request: Request):
        """Serve home page."""
        return templates.TemplateResponse("index.html", {"request": request})
```

**Step 5: Test web interface manually**

Run: `site-health serve`
Open browser to: `http://127.0.0.1:8000`
Expected: Web interface loads, form is visible

**Step 6: Commit**

```bash
git add site_health/web/templates/ site_health/web/static/ site_health/web/app.py
git commit -m "feat: add web interface frontend with HTML and CSS"
```

---

## Task 11: Final Integration and Documentation

**Files:**
- Modify: `README.md`
- Create: `docs/usage.md`

**Step 1: Update README.md**

```markdown
# Site Health

Crawl a site, find bad links, determine performance, output a triage report.

## Features

- Async web crawler with configurable depth and rate limiting
- Detects broken links, missing assets, and categorizes by severity
- Multiple report formats: terminal, HTML, JSON
- SQLite database for crawl history
- CLI and web interface
- Config file support (YAML)

## Installation

### From Source

```bash
git clone <repository-url>
cd site-health
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .[dev]
```

### Verify Installation

```bash
site-health --help
```

## Quick Start

### CLI Usage

```bash
# Crawl a site (terminal output)
site-health crawl https://example.com

# Specify depth and format
site-health crawl https://example.com --depth 3 --format html

# Use config file
site-health crawl --config mysite.yaml

# List previous crawls
site-health list

# View previous crawl report
site-health report 123 --format terminal
```

### Web Interface

```bash
# Start web server
site-health serve

# Open browser to http://127.0.0.1:8000
```

## Configuration

Create a YAML config file:

```yaml
url: https://example.com
depth: 2
max_concurrent: 10
timeout: 10.0
respect_robots: true
output_format: terminal
```

CLI arguments override config file settings.

## Architecture

- **Crawler-first design**: Core `SiteCrawler` class handles async crawling
- **SQLite storage**: Crawl history and results stored locally
- **Thin interfaces**: CLI and web are wrappers around the same crawler

## Development

### Run Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=site_health --cov-report=html
```

### Code Quality

```bash
ruff check site_health/
```

## Project Structure

```
site-health/
├── site_health/
│   ├── crawler.py          # Core crawler logic
│   ├── database.py         # SQLite operations
│   ├── report.py           # Report generation
│   ├── cli.py             # CLI interface
│   └── web/               # Web interface
├── tests/                 # Test suite
├── docs/                  # Documentation
└── reports/              # Generated HTML reports
```

## License

MIT
```

**Step 2: Create usage documentation**

```markdown
<!-- docs/usage.md -->
# Usage Guide

## Command Line Interface

### Crawling a Website

Basic crawl:
```bash
site-health crawl https://example.com
```

With options:
```bash
site-health crawl https://example.com \
  --depth 3 \
  --format html \
  --max-concurrent 10 \
  --timeout 15
```

### Using Config Files

Create `mysite.yaml`:
```yaml
url: https://example.com
depth: 3
max_concurrent: 10
timeout: 10.0
respect_robots: true
output_format: html
```

Run with config:
```bash
site-health crawl --config mysite.yaml
```

Override config values:
```bash
site-health crawl --config mysite.yaml --depth 5
```

### Viewing Crawl History

List all crawls:
```bash
site-health list
```

View specific crawl:
```bash
site-health report 123 --format terminal
```

Export to JSON:
```bash
site-health report 123 --format json --output crawl-123.json
```

## Web Interface

Start server:
```bash
site-health serve --port 8000
```

Features:
- Form to start new crawls
- History table showing all crawls
- View reports in browser
- Download JSON reports

## Report Formats

### Terminal Output

Colorized output with:
- Summary statistics
- Errors (broken links)
- Warnings (redirects, slow responses)
- Statistics by link type

### HTML Report

Static HTML file with:
- Interactive table
- Filterable results
- Visual indicators
- No external dependencies

### JSON Output

Machine-readable format for:
- CI/CD pipelines
- Custom processing
- Integration with other tools

## Link Types and Severity

### Link Types

- **page**: Same-domain HTML pages
- **image**: Image assets (png, jpg, etc.)
- **css**: Stylesheets
- **js**: JavaScript files
- **external**: Links to other domains

### Severity Levels

- **error**: 404, 500, timeouts (broken links)
- **warning**: Redirects, slow responses (>5s)
- **success**: 2xx status codes

## Best Practices

1. **Start with low depth** (1-2) for large sites
2. **Use rate limiting** to be respectful (max_concurrent: 10)
3. **Set reasonable timeout** (10-15s)
4. **Respect robots.txt** (default: true)
5. **Save HTML reports** for sharing with team
6. **Use JSON output** for CI/CD integration

## CI/CD Integration

Example GitHub Actions workflow:

```yaml
- name: Check site health
  run: |
    site-health crawl ${{ secrets.SITE_URL }} \
      --depth 2 \
      --format json \
      --output report.json

    # Fail if errors found
    errors=$(jq '.summary.errors' report.json)
    if [ "$errors" -gt 0 ]; then
      echo "Found $errors broken links"
      exit 1
    fi
```
```

**Step 3: Commit documentation**

```bash
git add README.md docs/usage.md
git commit -m "docs: add comprehensive README and usage guide"
```

**Step 4: Run full test suite**

Run: `pytest tests/ -v --cov=site_health`
Expected: All tests pass with good coverage

**Step 5: Final commit**

```bash
git add .
git commit -m "chore: final integration and testing complete"
```

---

## Summary

This implementation plan provides:

✅ Complete package structure with dependencies
✅ Data models and database layer with SQLite
✅ Core async crawler with rate limiting
✅ Report generation (terminal, HTML, JSON)
✅ Configuration file support
✅ Full CLI interface with all commands
✅ FastAPI backend with REST API
✅ Web frontend with form and history
✅ Comprehensive test suite
✅ Documentation

All tasks follow TDD principles and include:
- Exact file paths
- Complete code examples
- Test-first approach
- Verification steps
- Frequent commits

**Next Steps:** Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan.
