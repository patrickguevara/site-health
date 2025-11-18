# Site Health - Design Document

**Date**: 2025-11-18
**Status**: Approved

## Overview

Site Health is a Python tool for crawling websites to detect broken links and generate triage reports. It provides both CLI and web interfaces for personal site maintenance and client audits.

## Goals

- Crawl websites with configurable depth
- Detect broken links and categorize by severity
- Generate reports in multiple formats (terminal, HTML, JSON)
- Provide both CLI and local web interface
- Store crawl history for reference

## Non-Goals (MVP)

- Performance metrics (Core Web Vitals, Lighthouse scores)
- SEO analysis
- Real-time WebSocket progress updates
- Scheduled/recurring crawls
- Email notifications

## Architecture

### Core Approach: Crawler-First Architecture

The crawler is the heart of the system. CLI and web interface are thin wrappers that invoke the crawler and format results.

**Key Components**:
- `SiteCrawler`: Async crawler with rate limiting
- `ReportGenerator`: Multi-format report generation
- `Database`: SQLite storage for crawl history
- CLI and FastAPI: Both use the same crawler instance

**Benefits**: Clean separation, easy to test, interfaces stay in sync

## Project Structure

```
site-health/
├── pyproject.toml              # Modern Python packaging
├── README.md
├── config.example.yaml         # Example configuration
├── site_health/
│   ├── __init__.py
│   ├── __main__.py            # Entry point for CLI
│   ├── crawler.py             # SiteCrawler class
│   ├── database.py            # SQLite operations
│   ├── report.py              # ReportGenerator class
│   ├── models.py              # Data models (crawl results, link info)
│   ├── config.py              # Config file loading
│   ├── cli.py                 # Typer CLI interface
│   └── web/
│       ├── __init__.py
│       ├── app.py             # FastAPI application
│       ├── static/            # CSS/JS for web UI
│       └── templates/         # Jinja2 templates
├── reports/                   # Generated HTML reports
└── tests/
    ├── test_crawler.py
    ├── test_database.py
    ├── test_report.py
    ├── test_cli.py
    ├── test_web.py
    └── fixtures/
```

## Dependencies

- **httpx**: Async HTTP client for crawling
- **beautifulsoup4**: HTML parsing
- **aiosqlite**: Async SQLite operations
- **FastAPI + uvicorn**: Web interface
- **typer**: CLI framework
- **pyyaml**: Config file support
- **jinja2**: HTML report templating
- **pytest + pytest-asyncio**: Testing

## Core Crawler Design

### SiteCrawler Class

```python
class SiteCrawler:
    def __init__(self,
                 start_url: str,
                 max_depth: int = 2,
                 max_concurrent: int = 10,
                 timeout: float = 10.0):
        self.start_url = start_url
        self.max_depth = max_depth
        self.max_concurrent = max_concurrent  # Rate limiting
        self.timeout = timeout
        self.visited = set()
        self.results = []
```

### Crawl Flow

1. Normalize and enqueue starting URL at depth 0
2. Process queue with async semaphore (max 10 concurrent requests)
3. For each page:
   - Fetch with httpx (follow redirects, record final status)
   - Parse HTML with BeautifulSoup
   - Extract links (`<a href>`) and assets (`<img>`, `<link>`, `<script>`)
   - Check each link/asset for existence (HEAD request when possible)
   - Enqueue new same-domain pages if depth < max_depth
4. Categorize results by severity and link type

### Link Handling Strategy

- **Same-domain pages**: Crawl recursively up to max_depth
- **External links**: Check but don't crawl
- **Assets**: Check all referenced assets regardless of domain
- **Categorization**:
  - Broken page links (404, 500, timeout on HTML pages)
  - Missing assets (404 on images/CSS/JS)
  - Warnings (redirects, slow responses >5s)
  - Success (2xx responses)

### Rate Limiting & Politeness

- Semaphore limits concurrent requests (default 10)
- Respect robots.txt by default (configurable)
- Proper User-Agent: `site-health/1.0`
- Handle 429 (rate limit) with exponential backoff

## Database Schema

### SQLite Tables

```sql
-- Crawl sessions (one per run)
CREATE TABLE crawls (
    id INTEGER PRIMARY KEY,
    start_url TEXT NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    max_depth INTEGER,
    total_pages INTEGER,
    total_links_checked INTEGER,
    status TEXT  -- 'running', 'completed', 'failed'
);

-- Individual link check results
CREATE TABLE link_results (
    id INTEGER PRIMARY KEY,
    crawl_id INTEGER,
    source_url TEXT,      -- Page where link was found
    target_url TEXT,      -- The link being checked
    link_type TEXT,       -- 'page', 'image', 'css', 'js', 'external'
    status_code INTEGER,
    response_time FLOAT,
    severity TEXT,        -- 'error', 'warning', 'success'
    error_message TEXT,
    checked_at TIMESTAMP,
    FOREIGN KEY (crawl_id) REFERENCES crawls(id)
);

CREATE INDEX idx_crawl_id ON link_results(crawl_id);
CREATE INDEX idx_severity ON link_results(severity);
```

### Data Models

```python
@dataclass
class LinkResult:
    source_url: str
    target_url: str
    link_type: str  # 'page', 'image', 'css', 'js', 'external'
    status_code: int | None
    response_time: float
    severity: str  # 'error', 'warning', 'success'
    error_message: str | None = None

@dataclass
class CrawlSummary:
    id: int
    start_url: str
    started_at: datetime
    completed_at: datetime | None
    total_pages: int
    total_links: int
    errors: int
    warnings: int
```

## Report Generation

### ReportGenerator Class

Handles multiple output formats from the same data:

```python
class ReportGenerator:
    def __init__(self, crawl_id: int, db: Database):
        self.crawl_id = crawl_id
        self.db = db

    async def generate(self, format: str) -> str:
        """Returns report content or file path"""
```

### Output Formats

**Terminal Output**:
- Colorized summary with sections
- Errors (red): Broken page links with source → target
- Warnings (yellow): Redirects, slow responses, missing assets
- Statistics: Breakdown by link type

**HTML Report**:
- Static HTML file saved to `reports/crawl_{id}_{timestamp}.html`
- Collapsible sections for errors/warnings/success
- Sortable/filterable table of results
- Visual indicators (red/yellow/green)
- No external dependencies (inline CSS/JS)

**JSON Output**:
- Machine-readable format for scripting/CI/CD
- Contains full crawl metadata and all link results

## CLI Interface

### Command Structure

```bash
# Main crawl command
site-health crawl https://example.com --depth 3 --format html

# With config file
site-health crawl --config mysite.yaml

# List previous crawls
site-health list

# View a previous crawl report
site-health report 123 --format terminal

# Start web server
site-health serve --port 8000
```

### CLI Arguments

**`crawl` command**:
- `url` (required): Starting URL
- `--depth` (default: 2): Max crawl depth
- `--format` (default: terminal): Output format (terminal/html/json)
- `--output` (optional): Output file path
- `--config` (optional): Load from YAML config
- `--max-concurrent` (default: 10): Rate limiting
- `--timeout` (default: 10): Request timeout in seconds
- `--no-robots` (flag): Ignore robots.txt

**`list` command**:
- Shows table of previous crawls with ID, URL, date, status

**`report` command**:
- `crawl_id` (required): Which crawl to view
- `--format` (default: terminal): Output format

**`serve` command**:
- `--port` (default: 8000): Web server port
- `--host` (default: 127.0.0.1): Bind address

### Config File Format (YAML)

```yaml
url: https://example.com
depth: 3
max_concurrent: 10
timeout: 10
respect_robots: true
output_format: html
```

CLI arguments override config file settings.

## Web Interface

### FastAPI Routes

```python
# Main page
GET  /                    # Home page with form and history list

# API endpoints
POST /api/crawl           # Start new crawl (async, returns crawl_id)
GET  /api/crawls          # List all crawls (for history table)
GET  /api/crawls/{id}     # Get crawl details + results
GET  /api/crawls/{id}/report?format=html  # Download report

# Static reports
GET  /reports/{filename}  # Serve generated HTML reports
```

### Home Page Layout

1. **Crawl Form** (top):
   - URL input field
   - Depth selector (dropdown: 1-5)
   - Advanced options (collapsible): max concurrent, timeout
   - "Start Crawl" button

2. **Crawl History** (below form):
   - Table: ID, URL, Date, Status, Pages, Errors, Actions
   - Actions: "View Report", "View JSON", "Delete"
   - Sorted by date (newest first)
   - Shows last 50 crawls

### Crawl Execution Flow

1. User submits form → POST to `/api/crawl`
2. Backend starts async crawl task, returns `crawl_id` immediately
3. Frontend shows "Crawl started" message
4. User refreshes to check when crawl completes
5. Click "View Report" to see HTML report

**Note**: Using polling/refresh for MVP. Real-time WebSocket updates can be added later if needed.

### Styling

- Minimal, functional CSS (no framework)
- Responsive for desktop/tablet
- Clear visual hierarchy

## Error Handling

### Network Errors

- Timeouts → Record as error with "timeout" message
- Connection refused → Record as error
- DNS failures → Record as error
- SSL certificate errors → Record as warning

### HTTP Errors

- 404, 410 → Error severity
- 500, 502, 503 → Error severity
- 301, 302, 307, 308 → Warning severity (might be intentional)
- 429 (Rate limit) → Back off, retry with exponential delay

### Content Issues

- Invalid HTML → Parse best-effort with BeautifulSoup
- Relative URLs → Resolve using urllib.parse
- Empty pages → Log zero links found
- Circular links → Prevent with visited set

### Graceful Degradation

- Database locked → Retry with backoff
- Keyboard interrupt (Ctrl+C) → Save partial results, mark crawl as 'failed'
- File system errors → Log and show user-friendly error

## Testing Strategy

### Test Structure

```
tests/
├── test_crawler.py       # Crawler logic tests
├── test_database.py      # Database operations
├── test_report.py        # Report generation
├── test_cli.py          # CLI interface
├── test_web.py          # FastAPI endpoints
└── fixtures/
    └── sample_pages/    # Sample HTML for testing
```

### Key Test Scenarios

- Single and multi-level crawls
- 404s, timeouts, redirects handled correctly
- Link type categorization
- Rate limiting enforcement
- Circular link detection
- Report generation (all formats)
- CLI argument parsing
- Web API endpoints

### Testing Tools

- **pytest**: Test framework
- **pytest-asyncio**: Async tests
- **httpx MockTransport**: Mock HTTP requests (no real crawling)
- **FastAPI TestClient**: Web endpoint testing

## Implementation Order

1. Project setup: pyproject.toml, package structure, dependencies
2. Database layer: Schema, models, basic CRUD operations
3. Core crawler: SiteCrawler class with async crawling logic
4. Report generator: Terminal output first, then HTML, then JSON
5. CLI interface: Basic crawl command, then list/report commands
6. Web interface: API endpoints, then frontend
7. Config file support: YAML parsing and CLI override logic
8. Tests: Write tests alongside implementation
9. Polish: Error handling, documentation, example configs

## Future Enhancements

These are explicitly out of scope for MVP but documented for future consideration:

- Real-time progress via WebSockets
- Performance metrics (Core Web Vitals, page load time)
- SEO analysis (meta tags, headings, etc.)
- Scheduled/recurring crawls
- Email notifications
- Export to CSV/PDF
- Authentication for web interface (if deploying remotely)
