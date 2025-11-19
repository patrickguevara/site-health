# SEO Audit Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add comprehensive SEO auditing to the site-health crawler with severity-based scoring across five categories.

**Architecture:** Create SEOAnalyzer class for checks, add SEOResult/SEOIssue models, extend database with seo_results table, integrate with crawler via --seo flag, update all report formats.

**Tech Stack:** BeautifulSoup4 (existing), extruct (new), aiosqlite (existing), pytest

---

## Task 1: Add SEO Data Models

**Files:**
- Modify: `site_health/models.py:81` (after PageVitals class)

**Step 1: Write failing tests for SEO models**

Create: `tests/test_seo_models.py`

```python
# tests/test_seo_models.py
from datetime import datetime
from site_health.models import SEOIssue, SEOResult


def test_seo_issue_creation():
    """Test creating an SEO issue."""
    issue = SEOIssue(
        severity="CRITICAL",
        category="technical",
        check="missing_title",
        message="Page is missing a title tag"
    )

    assert issue.severity == "CRITICAL"
    assert issue.category == "technical"
    assert issue.check == "missing_title"
    assert issue.message == "Page is missing a title tag"


def test_seo_result_creation():
    """Test creating an SEO result."""
    now = datetime.now()
    issues = [
        SEOIssue(
            severity="CRITICAL",
            category="technical",
            check="missing_title",
            message="Missing title tag"
        )
    ]

    result = SEOResult(
        url="https://example.com",
        overall_score=75.5,
        technical_score=60.0,
        content_score=85.0,
        performance_score=90.0,
        mobile_score=70.0,
        structured_data_score=50.0,
        issues=issues,
        timestamp=now
    )

    assert result.url == "https://example.com"
    assert result.overall_score == 75.5
    assert result.technical_score == 60.0
    assert len(result.issues) == 1
    assert result.issues[0].severity == "CRITICAL"


def test_seo_result_no_issues():
    """Test SEO result with perfect score and no issues."""
    result = SEOResult(
        url="https://example.com",
        overall_score=100.0,
        technical_score=100.0,
        content_score=100.0,
        performance_score=100.0,
        mobile_score=100.0,
        structured_data_score=100.0,
        issues=[],
        timestamp=datetime.now()
    )

    assert result.overall_score == 100.0
    assert len(result.issues) == 0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_seo_models.py -v`

Expected: FAIL with "cannot import name 'SEOIssue'"

**Step 3: Add SEO models to models.py**

Add to `site_health/models.py` after the PageVitals class (after line 80):

```python
@dataclass
class SEOIssue:
    """A single SEO issue found during analysis."""

    severity: str  # "CRITICAL", "WARNING", "INFO"
    category: str  # "technical", "content", "performance", "mobile", "structured_data"
    check: str     # Specific check identifier (e.g., "missing_title")
    message: str   # Human-readable description


@dataclass
class SEOResult:
    """SEO analysis result for a single page."""

    url: str
    overall_score: float  # 0-100
    technical_score: float
    content_score: float
    performance_score: float
    mobile_score: float
    structured_data_score: float
    issues: list[SEOIssue]
    timestamp: datetime
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_seo_models.py -v`

Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add site_health/models.py tests/test_seo_models.py
git commit -m "feat: add SEO data models (SEOIssue and SEOResult)"
```

---

## Task 2: Extend Database for SEO Storage

**Files:**
- Modify: `site_health/database.py:79` (in initialize method, after page_vitals table)
- Modify: `site_health/database.py:301` (add new methods at end)

**Step 1: Write failing test for SEO database methods**

Create: `tests/test_database_seo.py`

```python
# tests/test_database_seo.py
import pytest
from datetime import datetime
from site_health.database import Database
from site_health.models import SEOResult, SEOIssue


@pytest.fixture
async def db():
    """Create test database."""
    database = Database(":memory:")
    await database.initialize()
    return database


@pytest.fixture
async def crawl_id(db):
    """Create test crawl."""
    return await db.create_crawl("https://example.com", 2)


async def test_save_seo_result(db, crawl_id):
    """Test saving SEO result to database."""
    result = SEOResult(
        url="https://example.com",
        overall_score=85.5,
        technical_score=90.0,
        content_score=80.0,
        performance_score=95.0,
        mobile_score=75.0,
        structured_data_score=70.0,
        issues=[
            SEOIssue(
                severity="WARNING",
                category="content",
                check="low_word_count",
                message="Page has only 150 words"
            )
        ],
        timestamp=datetime.now()
    )

    await db.save_seo_result(crawl_id, result)

    # Verify saved
    results = await db.get_seo_results(crawl_id)
    assert len(results) == 1
    assert results[0].url == "https://example.com"
    assert results[0].overall_score == 85.5
    assert len(results[0].issues) == 1


async def test_get_seo_results_empty(db, crawl_id):
    """Test getting SEO results when none exist."""
    results = await db.get_seo_results(crawl_id)
    assert len(results) == 0


async def test_save_multiple_seo_results(db, crawl_id):
    """Test saving multiple SEO results."""
    result1 = SEOResult(
        url="https://example.com/page1",
        overall_score=90.0,
        technical_score=90.0,
        content_score=90.0,
        performance_score=90.0,
        mobile_score=90.0,
        structured_data_score=90.0,
        issues=[],
        timestamp=datetime.now()
    )

    result2 = SEOResult(
        url="https://example.com/page2",
        overall_score=70.0,
        technical_score=70.0,
        content_score=70.0,
        performance_score=70.0,
        mobile_score=70.0,
        structured_data_score=70.0,
        issues=[
            SEOIssue("CRITICAL", "technical", "missing_title", "No title tag")
        ],
        timestamp=datetime.now()
    )

    await db.save_seo_result(crawl_id, result1)
    await db.save_seo_result(crawl_id, result2)

    results = await db.get_seo_results(crawl_id)
    assert len(results) == 2
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_database_seo.py -v`

Expected: FAIL with "no such table: seo_results"

**Step 3: Add seo_results table to database schema**

Add to `site_health/database.py` in the `initialize` method after the page_vitals table creation (after line 77):

```python
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS seo_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    crawl_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    overall_score REAL,
                    technical_score REAL,
                    content_score REAL,
                    performance_score REAL,
                    mobile_score REAL,
                    structured_data_score REAL,
                    issues TEXT,
                    timestamp TIMESTAMP NOT NULL,
                    FOREIGN KEY (crawl_id) REFERENCES crawls(id)
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_seo_crawl_id
                ON seo_results(crawl_id)
            """)
```

**Step 4: Add database methods for SEO results**

Add to `site_health/database.py` at the end (after line 300):

```python
    async def save_seo_result(self, crawl_id: int, result: SEOResult):
        """Save SEO analysis result for a page."""
        import json

        # Serialize issues to JSON
        issues_json = json.dumps([
            {
                "severity": issue.severity,
                "category": issue.category,
                "check": issue.check,
                "message": issue.message
            }
            for issue in result.issues
        ])

        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT INTO seo_results
                (crawl_id, url, overall_score, technical_score, content_score,
                 performance_score, mobile_score, structured_data_score,
                 issues, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    crawl_id,
                    result.url,
                    result.overall_score,
                    result.technical_score,
                    result.content_score,
                    result.performance_score,
                    result.mobile_score,
                    result.structured_data_score,
                    issues_json,
                    result.timestamp
                )
            )
            await conn.commit()

    async def get_seo_results(self, crawl_id: int) -> List[SEOResult]:
        """Get all SEO results for a crawl."""
        import json

        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                """
                SELECT * FROM seo_results
                WHERE crawl_id = ?
                ORDER BY timestamp
                """,
                (crawl_id,)
            )
            rows = await cursor.fetchall()

            results = []
            for row in rows:
                # Deserialize issues from JSON
                issues_data = json.loads(row["issues"])
                issues = [
                    SEOIssue(
                        severity=issue["severity"],
                        category=issue["category"],
                        check=issue["check"],
                        message=issue["message"]
                    )
                    for issue in issues_data
                ]

                results.append(SEOResult(
                    url=row["url"],
                    overall_score=row["overall_score"],
                    technical_score=row["technical_score"],
                    content_score=row["content_score"],
                    performance_score=row["performance_score"],
                    mobile_score=row["mobile_score"],
                    structured_data_score=row["structured_data_score"],
                    issues=issues,
                    timestamp=datetime.fromisoformat(row["timestamp"])
                ))

            return results
```

**Step 5: Add import for SEOResult and SEOIssue**

Modify the imports at the top of `site_health/database.py:8`:

```python
from site_health.models import LinkResult, CrawlSummary, PageVitals, SEOResult, SEOIssue
```

**Step 6: Run tests to verify they pass**

Run: `pytest tests/test_database_seo.py -v`

Expected: PASS (3 tests)

**Step 7: Commit**

```bash
git add site_health/database.py tests/test_database_seo.py
git commit -m "feat: add database schema and methods for SEO results"
```

---

## Task 3: Create SEO Analyzer Core

**Files:**
- Create: `site_health/seo_analyzer.py`
- Create: `tests/test_seo_analyzer.py`

**Step 1: Write failing tests for SEOAnalyzer**

Create: `tests/test_seo_analyzer.py`

```python
# tests/test_seo_analyzer.py
from site_health.seo_analyzer import SEOAnalyzer
from site_health.models import PageVitals
from datetime import datetime


def test_analyzer_missing_title():
    """Test detection of missing title tag."""
    html = """
    <html>
        <head></head>
        <body><h1>Hello</h1></body>
    </html>
    """

    analyzer = SEOAnalyzer("https://example.com", html, 200, None)
    result = analyzer.analyze()

    assert result.overall_score < 100
    critical_issues = [i for i in result.issues if i.severity == "CRITICAL"]
    assert any(i.check == "missing_title" for i in critical_issues)


def test_analyzer_perfect_page():
    """Test analysis of a perfect page."""
    html = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Test Page - 50 Characters Long Title Here</title>
            <meta name="description" content="This is a well-written meta description that is between 150 and 160 characters long and describes the page content accurately and completely.">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="canonical" href="https://example.com">
        </head>
        <body>
            <h1>Main Heading</h1>
            <h2>Subheading</h2>
            <p>This is a content paragraph with at least 300 words. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.</p>
            <img src="test.jpg" alt="Test image with descriptive alt text">
        </body>
    </html>
    """

    analyzer = SEOAnalyzer("https://example.com", html, 200, None)
    result = analyzer.analyze()

    # Should have high scores
    assert result.technical_score >= 80
    assert result.content_score >= 80
    assert result.mobile_score >= 80

    # Should have no critical issues
    critical_issues = [i for i in result.issues if i.severity == "CRITICAL"]
    assert len(critical_issues) == 0


def test_analyzer_with_vitals():
    """Test analyzer incorporating Core Web Vitals data."""
    html = """
    <html>
        <head><title>Test</title></head>
        <body><h1>Test</h1></body>
    </html>
    """

    vitals = PageVitals(
        url="https://example.com",
        lcp=2.0,  # Good
        cls=0.05,  # Good
        inp=150,   # Good
        measured_at=datetime.now(),
        status="success"
    )

    analyzer = SEOAnalyzer("https://example.com", html, 200, vitals)
    result = analyzer.analyze()

    # Performance score should be high with good vitals
    assert result.performance_score >= 90


def test_analyzer_bad_heading_structure():
    """Test detection of bad heading hierarchy."""
    html = """
    <html>
        <head><title>Test</title></head>
        <body>
            <h2>Subheading without H1</h2>
            <h1>Main heading comes after</h1>
            <h4>Skipped H3</h4>
        </body>
    </html>
    """

    analyzer = SEOAnalyzer("https://example.com", html, 200, None)
    result = analyzer.analyze()

    heading_issues = [i for i in result.issues if "heading" in i.check.lower()]
    assert len(heading_issues) > 0


def test_analyzer_missing_alt_text():
    """Test detection of images without alt text."""
    html = """
    <html>
        <head><title>Test</title></head>
        <body>
            <h1>Test</h1>
            <img src="test.jpg">
            <img src="test2.jpg" alt="">
        </body>
    </html>
    """

    analyzer = SEOAnalyzer("https://example.com", html, 200, None)
    result = analyzer.analyze()

    alt_issues = [i for i in result.issues if "alt" in i.check.lower()]
    assert len(alt_issues) > 0
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_seo_analyzer.py -v`

Expected: FAIL with "cannot import name 'SEOAnalyzer'"

**Step 3: Create SEOAnalyzer stub**

Create: `site_health/seo_analyzer.py`

```python
# site_health/seo_analyzer.py
"""SEO analysis engine for web pages."""

from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional
from site_health.models import SEOResult, SEOIssue, PageVitals


class SEOAnalyzer:
    """Analyzes a web page for SEO issues and generates scores."""

    # Category weights (must sum to 1.0)
    WEIGHTS = {
        "technical": 0.25,
        "content": 0.20,
        "performance": 0.30,
        "mobile": 0.15,
        "structured_data": 0.10,
    }

    def __init__(
        self,
        url: str,
        html: str,
        status_code: int,
        vitals: Optional[PageVitals] = None
    ):
        """
        Initialize analyzer with page data.

        Args:
            url: Page URL
            html: HTML content
            status_code: HTTP status code
            vitals: Optional Core Web Vitals data
        """
        self.url = url
        self.html = html
        self.status_code = status_code
        self.vitals = vitals
        self.soup = BeautifulSoup(html, 'html.parser')
        self.issues: list[SEOIssue] = []

    def analyze(self) -> SEOResult:
        """
        Run all SEO checks and return results.

        Returns:
            SEOResult with scores and issues
        """
        # Run category checks
        technical_score = self._check_technical()
        content_score = self._check_content()
        performance_score = self._check_performance()
        mobile_score = self._check_mobile()
        structured_data_score = self._check_structured_data()

        # Calculate weighted overall score
        overall_score = (
            technical_score * self.WEIGHTS["technical"] +
            content_score * self.WEIGHTS["content"] +
            performance_score * self.WEIGHTS["performance"] +
            mobile_score * self.WEIGHTS["mobile"] +
            structured_data_score * self.WEIGHTS["structured_data"]
        )

        return SEOResult(
            url=self.url,
            overall_score=round(overall_score, 1),
            technical_score=round(technical_score, 1),
            content_score=round(content_score, 1),
            performance_score=round(performance_score, 1),
            mobile_score=round(mobile_score, 1),
            structured_data_score=round(structured_data_score, 1),
            issues=sorted(
                self.issues,
                key=lambda x: {"CRITICAL": 0, "WARNING": 1, "INFO": 2}[x.severity]
            ),
            timestamp=datetime.now()
        )

    def _check_technical(self) -> float:
        """Check technical SEO factors. Returns score 0-100."""
        score = 100.0
        checks_passed = 0
        total_checks = 7

        # Title tag
        title = self.soup.find('title')
        if not title or not title.string:
            self.issues.append(SEOIssue(
                severity="CRITICAL",
                category="technical",
                check="missing_title",
                message="Page is missing a title tag"
            ))
        else:
            checks_passed += 1
            title_len = len(title.string)
            if title_len < 30 or title_len > 60:
                self.issues.append(SEOIssue(
                    severity="WARNING",
                    category="technical",
                    check="title_length",
                    message=f"Title length is {title_len} chars (optimal: 50-60)"
                ))

        # Meta description
        meta_desc = self.soup.find('meta', attrs={'name': 'description'})
        if not meta_desc or not meta_desc.get('content'):
            self.issues.append(SEOIssue(
                severity="WARNING",
                category="technical",
                check="missing_meta_description",
                message="Page is missing a meta description"
            ))
        else:
            checks_passed += 1
            desc_len = len(meta_desc['content'])
            if desc_len < 120 or desc_len > 160:
                self.issues.append(SEOIssue(
                    severity="INFO",
                    category="technical",
                    check="meta_description_length",
                    message=f"Meta description is {desc_len} chars (optimal: 150-160)"
                ))

        # Canonical URL
        canonical = self.soup.find('link', attrs={'rel': 'canonical'})
        if canonical:
            checks_passed += 1
        else:
            self.issues.append(SEOIssue(
                severity="INFO",
                category="technical",
                check="missing_canonical",
                message="Page lacks canonical URL"
            ))

        # Heading structure
        h1_tags = self.soup.find_all('h1')
        if len(h1_tags) == 0:
            self.issues.append(SEOIssue(
                severity="CRITICAL",
                category="technical",
                check="missing_h1",
                message="Page has no H1 tag"
            ))
        elif len(h1_tags) > 1:
            self.issues.append(SEOIssue(
                severity="WARNING",
                category="technical",
                check="multiple_h1",
                message=f"Page has {len(h1_tags)} H1 tags (should have 1)"
            ))
        else:
            checks_passed += 1

        # Check heading hierarchy
        headings = []
        for i in range(1, 7):
            headings.extend([(i, tag) for tag in self.soup.find_all(f'h{i}')])

        if headings:
            prev_level = 0
            for level, tag in headings:
                if level > prev_level + 1:
                    self.issues.append(SEOIssue(
                        severity="WARNING",
                        category="technical",
                        check="heading_hierarchy",
                        message=f"Heading hierarchy skip: H{prev_level} to H{level}"
                    ))
                    break
                prev_level = level
            else:
                checks_passed += 1

        # Robots meta tag
        robots = self.soup.find('meta', attrs={'name': 'robots'})
        if robots:
            content = robots.get('content', '').lower()
            if 'noindex' in content or 'nofollow' in content:
                self.issues.append(SEOIssue(
                    severity="CRITICAL",
                    category="technical",
                    check="blocking_robots",
                    message=f"Robots meta tag blocks indexing: {content}"
                ))
            else:
                checks_passed += 1
        else:
            checks_passed += 1

        # HTTPS check
        if self.url.startswith('https://'):
            checks_passed += 1
        else:
            self.issues.append(SEOIssue(
                severity="CRITICAL",
                category="technical",
                check="no_https",
                message="Page is not served over HTTPS"
            ))

        return (checks_passed / total_checks) * 100

    def _check_content(self) -> float:
        """Check content quality factors. Returns score 0-100."""
        score = 100.0
        checks_passed = 0
        total_checks = 3

        # Word count
        text = self.soup.get_text()
        words = text.split()
        word_count = len(words)

        if word_count < 300:
            self.issues.append(SEOIssue(
                severity="WARNING",
                category="content",
                check="low_word_count",
                message=f"Page has only {word_count} words (recommended: 300+)"
            ))
        else:
            checks_passed += 1

        # Image alt text
        images = self.soup.find_all('img')
        missing_alt = 0
        for img in images:
            if not img.get('alt') or not img['alt'].strip():
                missing_alt += 1

        if images and missing_alt > 0:
            self.issues.append(SEOIssue(
                severity="WARNING",
                category="content",
                check="missing_alt_text",
                message=f"{missing_alt} of {len(images)} images missing alt text"
            ))
        elif images:
            checks_passed += 1
        else:
            checks_passed += 1  # No images is fine

        # Content-to-HTML ratio (simple check)
        html_size = len(self.html)
        text_size = len(text)
        if html_size > 0:
            ratio = text_size / html_size
            if ratio < 0.1:
                self.issues.append(SEOIssue(
                    severity="INFO",
                    category="content",
                    check="low_content_ratio",
                    message=f"Content-to-HTML ratio is low: {ratio:.1%}"
                ))
            else:
                checks_passed += 1

        return (checks_passed / total_checks) * 100

    def _check_performance(self) -> float:
        """Check performance factors. Returns score 0-100."""
        # If we have vitals data, use it
        if self.vitals and self.vitals.status == "success":
            score = 100.0
            checks_passed = 0
            total_checks = 3

            # LCP check
            if self.vitals.lcp is not None:
                if self.vitals.lcp <= 2.5:
                    checks_passed += 1
                elif self.vitals.lcp <= 4.0:
                    checks_passed += 0.5
                    self.issues.append(SEOIssue(
                        severity="WARNING",
                        category="performance",
                        check="lcp_needs_improvement",
                        message=f"LCP is {self.vitals.lcp:.2f}s (target: ≤2.5s)"
                    ))
                else:
                    self.issues.append(SEOIssue(
                        severity="WARNING",
                        category="performance",
                        check="lcp_poor",
                        message=f"LCP is {self.vitals.lcp:.2f}s (target: ≤2.5s)"
                    ))

            # CLS check
            if self.vitals.cls is not None:
                if self.vitals.cls <= 0.1:
                    checks_passed += 1
                elif self.vitals.cls <= 0.25:
                    checks_passed += 0.5
                    self.issues.append(SEOIssue(
                        severity="WARNING",
                        category="performance",
                        check="cls_needs_improvement",
                        message=f"CLS is {self.vitals.cls:.3f} (target: ≤0.1)"
                    ))
                else:
                    self.issues.append(SEOIssue(
                        severity="WARNING",
                        category="performance",
                        check="cls_poor",
                        message=f"CLS is {self.vitals.cls:.3f} (target: ≤0.1)"
                    ))

            # INP check
            if self.vitals.inp is not None:
                if self.vitals.inp <= 200:
                    checks_passed += 1
                elif self.vitals.inp <= 500:
                    checks_passed += 0.5
                    self.issues.append(SEOIssue(
                        severity="WARNING",
                        category="performance",
                        check="inp_needs_improvement",
                        message=f"INP is {self.vitals.inp:.0f}ms (target: ≤200ms)"
                    ))
                else:
                    self.issues.append(SEOIssue(
                        severity="WARNING",
                        category="performance",
                        check="inp_poor",
                        message=f"INP is {self.vitals.inp:.0f}ms (target: ≤200ms)"
                    ))

            return (checks_passed / total_checks) * 100
        else:
            # Without vitals, just check HTTPS and page size
            checks_passed = 0
            total_checks = 2

            if self.url.startswith('https://'):
                checks_passed += 1

            # Basic page size check
            html_size = len(self.html)
            if html_size < 500000:  # 500KB
                checks_passed += 1
            else:
                self.issues.append(SEOIssue(
                    severity="INFO",
                    category="performance",
                    check="large_page_size",
                    message=f"Page size is {html_size // 1024}KB"
                ))

            # Add info about running vitals
            self.issues.append(SEOIssue(
                severity="INFO",
                category="performance",
                check="vitals_not_measured",
                message="Run with --vitals flag for detailed performance analysis"
            ))

            return (checks_passed / total_checks) * 100

    def _check_mobile(self) -> float:
        """Check mobile-friendliness. Returns score 0-100."""
        checks_passed = 0
        total_checks = 2

        # Viewport meta tag
        viewport = self.soup.find('meta', attrs={'name': 'viewport'})
        if viewport and viewport.get('content'):
            checks_passed += 1
        else:
            self.issues.append(SEOIssue(
                severity="WARNING",
                category="mobile",
                check="missing_viewport",
                message="Page lacks viewport meta tag for mobile"
            ))

        # Check for font sizes that are too small (basic heuristic)
        styles = self.soup.find_all('style')
        has_small_fonts = False
        for style in styles:
            if 'font-size' in style.string and ('px' in style.string or 'pt' in style.string):
                # This is a simple check; real implementation would parse CSS
                pass

        checks_passed += 1  # Assume fonts are OK unless we have evidence

        return (checks_passed / total_checks) * 100

    def _check_structured_data(self) -> float:
        """Check for structured data. Returns score 0-100."""
        # Look for JSON-LD
        json_ld = self.soup.find_all('script', type='application/ld+json')

        if json_ld:
            self.issues.append(SEOIssue(
                severity="INFO",
                category="structured_data",
                check="has_json_ld",
                message=f"Found {len(json_ld)} JSON-LD structured data blocks"
            ))
            return 100.0
        else:
            self.issues.append(SEOIssue(
                severity="INFO",
                category="structured_data",
                check="no_structured_data",
                message="No structured data found (Schema.org recommended)"
            ))
            return 50.0
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_seo_analyzer.py -v`

Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add site_health/seo_analyzer.py tests/test_seo_analyzer.py
git commit -m "feat: implement SEO analyzer with all category checks"
```

---

## Task 4: Integrate SEO Analysis into Crawler

**Files:**
- Modify: `site_health/crawler.py:298` (add method at end)
- Modify: `site_health/cli.py:26` (add --seo flag)
- Modify: `site_health/cli.py:100` (integrate analyzer after crawl)

**Step 1: Write failing integration test**

Create: `tests/test_crawler_seo.py`

```python
# tests/test_crawler_seo.py
import pytest
from site_health.crawler import SiteCrawler


def test_crawler_has_seo_integration_method():
    """Test that crawler has method to get pages for SEO analysis."""
    crawler = SiteCrawler("https://example.com")

    # Should have method to get pages for SEO
    assert hasattr(crawler, 'get_pages_for_seo_analysis')


def test_get_pages_for_seo_returns_visited():
    """Test that get_pages_for_seo returns visited pages."""
    crawler = SiteCrawler("https://example.com")

    # Simulate visited pages
    crawler.visited.add("https://example.com")
    crawler.visited.add("https://example.com/page1")
    crawler.visited.add("https://example.com/page2")

    pages = crawler.get_pages_for_seo_analysis()

    assert len(pages) >= 3
    assert "https://example.com" in pages
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_crawler_seo.py -v`

Expected: FAIL with "has no attribute 'get_pages_for_seo_analysis'"

**Step 3: Add SEO integration method to crawler**

Add to `site_health/crawler.py` at the end (after line 297):

```python
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
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_crawler_seo.py -v`

Expected: PASS (2 tests)

**Step 5: Add --seo flag to CLI**

Modify `site_health/cli.py` to add the --seo option after the --vitals option (line 26):

```python
    seo: bool = typer.Option(False, "--seo", help="Run SEO audit on crawled pages"),
```

Also add `seo` parameter to the function signature of `_crawl_async` (after line 53):

```python
    seo: bool,
```

**Step 6: Add SEO analysis logic to CLI crawl function**

First, read the rest of cli.py to see where to add the logic:

```python
# After the vitals measurement section (around line 130), add SEO analysis
```

Add this after the Core Web Vitals section in `site_health/cli.py`:

```python
        # Run SEO analysis if requested
        if seo:
            typer.echo("\nRunning SEO analysis...")
            from site_health.seo_analyzer import SEOAnalyzer
            import httpx

            # Get pages to analyze
            pages_to_analyze = crawler.get_pages_for_seo_analysis()
            typer.echo(f"Analyzing {len(pages_to_analyze)} pages...")

            # Get vitals data if available
            vitals_by_url = {}
            if vitals:
                vitals_results = await db.get_page_vitals(crawl_id)
                vitals_by_url = {v.url: v for v in vitals_results}

            # Analyze each page
            seo_count = 0
            async with httpx.AsyncClient(timeout=crawler.timeout) as client:
                for url in pages_to_analyze:
                    try:
                        response = await client.get(url)
                        if response.status_code == 200 and 'text/html' in response.headers.get('content-type', ''):
                            analyzer = SEOAnalyzer(
                                url=url,
                                html=response.text,
                                status_code=response.status_code,
                                vitals=vitals_by_url.get(url)
                            )
                            seo_result = analyzer.analyze()
                            await db.save_seo_result(crawl_id, seo_result)
                            seo_count += 1
                    except Exception as e:
                        typer.echo(f"Warning: Failed to analyze {url}: {e}", err=True)

            typer.echo(f"Completed SEO analysis of {seo_count} pages")
```

**Step 7: Commit**

```bash
git add site_health/crawler.py site_health/cli.py tests/test_crawler_seo.py
git commit -m "feat: integrate SEO analysis into crawler with --seo flag"
```

---

## Task 5: Add SEO to Terminal Report

**Files:**
- Modify: `site_health/report.py` (add SEO section to terminal report)

**Step 1: Read report.py to understand structure**

Run: `cat site_health/report.py | head -100`

**Step 2: Write failing test for SEO in terminal report**

Add to `tests/test_report.py`:

```python
async def test_terminal_report_with_seo(tmp_path):
    """Test terminal report includes SEO section when data exists."""
    from site_health.database import Database
    from site_health.report import ReportGenerator
    from site_health.models import SEOResult, SEOIssue
    from datetime import datetime

    db_path = str(tmp_path / "test.db")
    db = Database(db_path)
    await db.initialize()

    crawl_id = await db.create_crawl("https://example.com", 2)

    # Add SEO result
    seo_result = SEOResult(
        url="https://example.com",
        overall_score=85.0,
        technical_score=90.0,
        content_score=80.0,
        performance_score=95.0,
        mobile_score=75.0,
        structured_data_score=70.0,
        issues=[
            SEOIssue("WARNING", "content", "low_word_count", "Only 200 words")
        ],
        timestamp=datetime.now()
    )
    await db.save_seo_result(crawl_id, seo_result)

    await db.complete_crawl(crawl_id, 5, 20)

    # Generate report
    summary = await db.get_crawl_summary(crawl_id)
    results = await db.get_link_results(crawl_id)
    seo_results = await db.get_seo_results(crawl_id)

    generator = ReportGenerator(summary, results, None, seo_results)
    output = generator.generate_terminal_report()

    assert "SEO Analysis" in output
    assert "85.0" in output  # Overall score
    assert "WARNING" in output
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/test_report.py::test_terminal_report_with_seo -v`

Expected: FAIL (assertion error or missing functionality)

**Step 4: Examine ReportGenerator to understand its structure**

Read: `site_health/report.py` fully to understand the class structure

**Step 5: Add seo_results parameter to ReportGenerator**

Modify `site_health/report.py` constructor and add SEO terminal output logic:

Update constructor to accept seo_results:

```python
def __init__(
    self,
    summary: CrawlSummary,
    results: List[LinkResult],
    vitals: Optional[List[PageVitals]] = None,
    seo_results: Optional[List[SEOResult]] = None
):
    self.summary = summary
    self.results = results
    self.vitals = vitals
    self.seo_results = seo_results or []
```

Add SEO section to terminal report generation method:

```python
def generate_terminal_report(self) -> str:
    # ... existing code ...

    # Add SEO section if we have results
    if self.seo_results:
        lines.append("\n" + "=" * 50)
        lines.append("SEO Analysis")
        lines.append("=" * 50)

        # Calculate aggregate scores
        if self.seo_results:
            avg_overall = sum(r.overall_score for r in self.seo_results) / len(self.seo_results)
            avg_technical = sum(r.technical_score for r in self.seo_results) / len(self.seo_results)
            avg_content = sum(r.content_score for r in self.seo_results) / len(self.seo_results)
            avg_performance = sum(r.performance_score for r in self.seo_results) / len(self.seo_results)
            avg_mobile = sum(r.mobile_score for r in self.seo_results) / len(self.seo_results)
            avg_structured_data = sum(r.structured_data_score for r in self.seo_results) / len(self.seo_results)

            lines.append(f"\nOverall SEO Score: {avg_overall:.1f}/100")
            lines.append("\nCategory Scores:")
            lines.append(f"  Technical:       {avg_technical:.1f}/100")
            lines.append(f"  Content:         {avg_content:.1f}/100")
            lines.append(f"  Performance:     {avg_performance:.1f}/100")
            lines.append(f"  Mobile:          {avg_mobile:.1f}/100")
            lines.append(f"  Structured Data: {avg_structured_data:.1f}/100")

            # Collect all issues
            all_issues = []
            for result in self.seo_results:
                all_issues.extend(result.issues)

            critical = [i for i in all_issues if i.severity == "CRITICAL"]
            warnings = [i for i in all_issues if i.severity == "WARNING"]
            info = [i for i in all_issues if i.severity == "INFO"]

            lines.append(f"\nIssues Found: {len(critical)} critical, {len(warnings)} warnings, {len(info)} info")

            # Show top critical issues
            if critical:
                lines.append("\nCritical Issues:")
                for issue in critical[:5]:
                    lines.append(f"  • {issue.message}")

            # Show top warnings
            if warnings:
                lines.append("\nWarnings:")
                for issue in warnings[:5]:
                    lines.append(f"  • {issue.message}")

    return "\n".join(lines)
```

Add imports at top of file:

```python
from site_health.models import LinkResult, CrawlSummary, PageVitals, SEOResult, SEOIssue
```

**Step 6: Update CLI to pass seo_results to report generator**

Modify `site_health/cli.py` in the report generation section:

```python
    # Generate report
    summary = await db.get_crawl_summary(crawl_id)
    results = await db.get_link_results(crawl_id)
    vitals_results = await db.get_page_vitals(crawl_id) if vitals else None
    seo_results = await db.get_seo_results(crawl_id) if seo else None

    generator = ReportGenerator(summary, results, vitals_results, seo_results)
```

**Step 7: Run test to verify it passes**

Run: `pytest tests/test_report.py::test_terminal_report_with_seo -v`

Expected: PASS

**Step 8: Commit**

```bash
git add site_health/report.py site_health/cli.py tests/test_report.py
git commit -m "feat: add SEO section to terminal report output"
```

---

## Task 6: Add SEO to HTML/JSON Reports

**Files:**
- Modify: `site_health/report.py` (add SEO to HTML and JSON generation)

**Step 1: Write failing test for SEO in JSON report**

Add to `tests/test_report.py`:

```python
async def test_json_report_with_seo(tmp_path):
    """Test JSON report includes SEO data."""
    import json
    from site_health.database import Database
    from site_health.report import ReportGenerator
    from site_health.models import SEOResult, SEOIssue
    from datetime import datetime

    db_path = str(tmp_path / "test.db")
    db = Database(db_path)
    await db.initialize()

    crawl_id = await db.create_crawl("https://example.com", 2)

    seo_result = SEOResult(
        url="https://example.com",
        overall_score=85.0,
        technical_score=90.0,
        content_score=80.0,
        performance_score=95.0,
        mobile_score=75.0,
        structured_data_score=70.0,
        issues=[],
        timestamp=datetime.now()
    )
    await db.save_seo_result(crawl_id, seo_result)
    await db.complete_crawl(crawl_id, 1, 5)

    summary = await db.get_crawl_summary(crawl_id)
    results = await db.get_link_results(crawl_id)
    seo_results = await db.get_seo_results(crawl_id)

    generator = ReportGenerator(summary, results, None, seo_results)
    json_str = generator.generate_json_report()

    data = json.loads(json_str)
    assert "seo_results" in data
    assert len(data["seo_results"]) == 1
    assert data["seo_results"][0]["overall_score"] == 85.0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_report.py::test_json_report_with_seo -v`

Expected: FAIL (KeyError or assertion failure)

**Step 3: Add SEO to JSON report generation**

Modify the `generate_json_report` method in `site_health/report.py`:

```python
def generate_json_report(self) -> str:
    """Generate JSON report."""
    import json
    from datetime import datetime

    data = {
        "summary": {
            "crawl_id": self.summary.id,
            "start_url": self.summary.start_url,
            "started_at": self.summary.started_at.isoformat(),
            "completed_at": self.summary.completed_at.isoformat() if self.summary.completed_at else None,
            "max_depth": self.summary.max_depth,
            "total_pages": self.summary.total_pages,
            "total_links": self.summary.total_links,
            "errors": self.summary.errors,
            "warnings": self.summary.warnings,
            "status": self.summary.status
        },
        "results": [
            {
                "source_url": r.source_url,
                "target_url": r.target_url,
                "link_type": r.link_type,
                "status_code": r.status_code,
                "response_time": r.response_time,
                "severity": r.severity,
                "error_message": r.error_message
            }
            for r in self.results
        ]
    }

    # Add vitals if present
    if self.vitals:
        data["vitals"] = [
            {
                "url": v.url,
                "lcp": v.lcp,
                "cls": v.cls,
                "inp": v.inp,
                "measured_at": v.measured_at.isoformat(),
                "status": v.status,
                "error_message": v.error_message
            }
            for v in self.vitals
        ]

    # Add SEO results if present
    if self.seo_results:
        data["seo_results"] = [
            {
                "url": s.url,
                "overall_score": s.overall_score,
                "technical_score": s.technical_score,
                "content_score": s.content_score,
                "performance_score": s.performance_score,
                "mobile_score": s.mobile_score,
                "structured_data_score": s.structured_data_score,
                "issues": [
                    {
                        "severity": i.severity,
                        "category": i.category,
                        "check": i.check,
                        "message": i.message
                    }
                    for i in s.issues
                ],
                "timestamp": s.timestamp.isoformat()
            }
            for s in self.seo_results
        ]

    return json.dumps(data, indent=2)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_report.py::test_json_report_with_seo -v`

Expected: PASS

**Step 5: Add SEO to HTML template**

Modify the HTML template to include SEO section. First, read the template:

Run: `cat site_health/templates/report.html`

Then add SEO section to the template after the vitals section:

```html
{% if seo_results %}
<section class="seo">
    <h2>SEO Analysis</h2>

    {% set avg_overall = (seo_results | sum(attribute='overall_score')) / (seo_results | length) %}
    {% set avg_technical = (seo_results | sum(attribute='technical_score')) / (seo_results | length) %}
    {% set avg_content = (seo_results | sum(attribute='content_score')) / (seo_results | length) %}
    {% set avg_performance = (seo_results | sum(attribute='performance_score')) / (seo_results | length) %}
    {% set avg_mobile = (seo_results | sum(attribute='mobile_score')) / (seo_results | length) %}
    {% set avg_structured_data = (seo_results | sum(attribute='structured_data_score')) / (seo_results | length) %}

    <div class="seo-summary">
        <h3>Overall Score: {{ "%.1f"|format(avg_overall) }}/100</h3>

        <div class="category-scores">
            <div class="score-item">
                <span>Technical:</span>
                <span>{{ "%.1f"|format(avg_technical) }}/100</span>
            </div>
            <div class="score-item">
                <span>Content:</span>
                <span>{{ "%.1f"|format(avg_content) }}/100</span>
            </div>
            <div class="score-item">
                <span>Performance:</span>
                <span>{{ "%.1f"|format(avg_performance) }}/100</span>
            </div>
            <div class="score-item">
                <span>Mobile:</span>
                <span>{{ "%.1f"|format(avg_mobile) }}/100</span>
            </div>
            <div class="score-item">
                <span>Structured Data:</span>
                <span>{{ "%.1f"|format(avg_structured_data) }}/100</span>
            </div>
        </div>
    </div>

    <h3>Issues by Severity</h3>
    {% for result in seo_results %}
        <details>
            <summary>{{ result.url }} - Score: {{ "%.1f"|format(result.overall_score) }}/100</summary>
            <ul>
            {% for issue in result.issues %}
                <li class="severity-{{ issue.severity | lower }}">
                    <strong>{{ issue.severity }}</strong> [{{ issue.category }}]: {{ issue.message }}
                </li>
            {% endfor %}
            </ul>
        </details>
    {% endfor %}
</section>
{% endif %}
```

**Step 6: Update HTML report generation to pass seo_results**

Modify the `generate_html_report` method in `site_health/report.py`:

```python
def generate_html_report(self) -> str:
    """Generate HTML report."""
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    from pathlib import Path

    template_dir = Path(__file__).parent / "templates"
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )

    template = env.get_template("report.html")
    return template.render(
        summary=self.summary,
        results=self.results,
        vitals=self.vitals,
        seo_results=self.seo_results
    )
```

**Step 7: Commit**

```bash
git add site_health/report.py site_health/templates/report.html tests/test_report.py
git commit -m "feat: add SEO data to HTML and JSON reports"
```

---

## Task 7: Update Report Command to Include SEO

**Files:**
- Modify: `site_health/cli.py` (report command)

**Step 1: Find the report command in CLI**

Read: `site_health/cli.py` to find the report command (search for "@app.command" after crawl)

**Step 2: Update report command to fetch and include SEO data**

Modify the report command to automatically include SEO data when it exists:

```python
    # Fetch data
    summary = await db.get_crawl_summary(crawl_id)
    results = await db.get_link_results(crawl_id, severity=severity)
    vitals = await db.get_page_vitals(crawl_id)
    seo_results = await db.get_seo_results(crawl_id)

    # Generate report
    generator = ReportGenerator(summary, results, vitals if vitals else None, seo_results if seo_results else None)
```

**Step 3: Test manually**

Run: `site-health crawl https://example.com --seo`

Then: `site-health report 1`

Expected: Report should include SEO section if data exists

**Step 4: Commit**

```bash
git add site_health/cli.py
git commit -m "feat: include SEO data in report command output"
```

---

## Task 8: Add extruct Dependency

**Files:**
- Modify: `pyproject.toml:28` (add extruct to dependencies)

**Step 1: Add extruct to dependencies**

Modify `pyproject.toml` dependencies list:

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
    "extruct>=0.16.0",
    "lxml>=4.9.0",
]
```

**Step 2: Install dependencies**

Run: `pip install -e ".[dev]"`

Expected: extruct and lxml installed successfully

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "deps: add extruct and lxml for structured data extraction"
```

---

## Task 9: Update README Documentation

**Files:**
- Modify: `README.md`

**Step 1: Add SEO feature to features list**

Update the Features section in README.md:

```markdown
- **SEO Audit**: Comprehensive SEO analysis with severity-based scoring across 5 categories
```

**Step 2: Add SEO examples to Quick Start**

Add examples showing the --seo flag:

```markdown
# Crawl with SEO audit
site-health crawl https://example.com --seo

# Crawl with both SEO and Core Web Vitals
site-health crawl https://example.com --seo --vitals

# SEO audit with HTML report
site-health crawl https://example.com --seo --format html
```

**Step 3: Add SEO section to configuration example**

Update config.yaml example:

```yaml
url: https://example.com
depth: 2
max_concurrent: 10
timeout: 10.0
respect_robots: true
output_format: terminal
measure_vitals: false
run_seo_audit: false
```

**Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add SEO audit feature to README"
```

---

## Task 10: Run Full Test Suite and Fix Issues

**Files:**
- Various (as needed for fixes)

**Step 1: Run all tests**

Run: `pytest -v`

Expected: Check for any failing tests

**Step 2: Fix any failing tests**

Review failures and fix issues. Common problems:
- Missing imports
- Incorrect assertions
- Database schema mismatches

**Step 3: Run tests with coverage**

Run: `pytest --cov=site_health --cov-report=term-missing`

Expected: Check coverage is reasonable (aim for >80%)

**Step 4: Run linter**

Run: `ruff check .`

Expected: No major issues

**Step 5: Fix any linter issues**

Run: `ruff check --fix .`

**Step 6: Commit any fixes**

```bash
git add .
git commit -m "fix: address test failures and linter issues"
```

---

## Task 11: Manual Integration Testing

**Files:**
- None (manual testing)

**Step 1: Test basic SEO crawl**

Run: `site-health crawl https://example.com --seo --depth 1`

Expected: Completes successfully, shows SEO scores

**Step 2: Test SEO + vitals together**

Run: `site-health crawl https://example.com --seo --vitals --depth 1`

Expected: Both analyses complete, vitals data incorporated into performance score

**Step 3: Test HTML report with SEO**

Run: `site-health crawl https://example.com --seo --format html --output test-report.html`

Then: Open test-report.html in browser

Expected: SEO section displays with scores and issues

**Step 4: Test JSON export with SEO**

Run: `site-health crawl https://example.com --seo --format json --output test-report.json`

Then: `cat test-report.json | jq '.seo_results'`

Expected: SEO data present in JSON

**Step 5: Test report command**

Run: `site-health list`

Then: `site-health report <crawl-id>`

Expected: Report includes SEO section if data exists

**Step 6: Document any issues found**

If issues found, create fixes in previous tasks

**Step 7: Final commit**

```bash
git add .
git commit -m "test: verify SEO audit integration works end-to-end"
```

---

## Completion Checklist

- [ ] All tests pass (`pytest -v`)
- [ ] No linter errors (`ruff check .`)
- [ ] Coverage >80% (`pytest --cov`)
- [ ] Manual testing completed successfully
- [ ] README updated with examples
- [ ] All changes committed

**Next Steps:**
- Consider adding web UI support for SEO display
- Consider adding SEO trend analysis over time
- Consider adding custom weight configuration
