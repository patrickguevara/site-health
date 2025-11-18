# Site Health

A comprehensive web crawler and link checker that helps you find broken links, analyze site health, and generate detailed reports.

## Features

- **Async Crawler**: High-performance asynchronous web crawling with configurable concurrency
- **Broken Link Detection**: Identifies 404s, timeouts, and other HTTP errors
- **Core Web Vitals**: Measure LCP, CLS, and INP using real browser automation (Playwright)
- **Multiple Output Formats**: Terminal (colorized), HTML reports, and JSON exports
- **SQLite History**: Persistent storage of all crawl results for historical analysis
- **CLI and Web Interface**: Use from command line or through a browser-based UI
- **Configuration File Support**: YAML-based configuration with CLI override capability

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/site-health.git
cd site-health

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install with dependencies
pip install -e ".[dev]"
```

### Verify Installation

```bash
site-health --help
```

## Quick Start

### Command Line Usage

```bash
# Basic crawl with terminal output
site-health crawl https://example.com

# Crawl with Core Web Vitals measurement
site-health crawl https://example.com --vitals

# Crawl with custom depth and generate HTML report with vitals
site-health crawl https://example.com --depth 3 --vitals --format html

# Use configuration file
site-health crawl --config config.yaml

# List previous crawls
site-health list

# Generate report for a previous crawl
site-health report 1 --format json
```

### Web Interface

```bash
# Start the web server
site-health serve

# Or specify custom host/port
site-health serve --host 0.0.0.0 --port 8080
```

Then open http://localhost:8000 in your browser to access the web UI.

## Configuration

Create a `config.yaml` file:

```yaml
url: https://example.com
depth: 2
max_concurrent: 10
timeout: 10.0
respect_robots: true
output_format: terminal
```

CLI arguments override config file values.

## Architecture

### Crawler-First Design

The core `SiteCrawler` is independent and reusable. It:
- Uses `httpx` for async HTTP requests
- Implements rate limiting via semaphore
- Normalizes URLs and tracks visited pages
- Returns structured `LinkResult` objects

### SQLite Storage

The `Database` class provides async persistence:
- Stores crawl metadata and results
- Supports multiple concurrent crawls
- Enables historical analysis

### Thin Interfaces

Both CLI (`typer`) and web (`FastAPI`) interfaces are thin wrappers around the core crawler and database.

## Development

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=site_health --cov-report=term-missing

# Run specific test file
pytest tests/test_crawler.py
```

### Code Quality

```bash
# Run ruff linter
ruff check .

# Auto-fix issues
ruff check --fix .
```

## Project Structure

```
site-health/
├── site_health/
│   ├── __init__.py           # Package initialization
│   ├── __main__.py           # CLI entry point
│   ├── models.py             # Data models (LinkResult, CrawlSummary)
│   ├── database.py           # SQLite database layer
│   ├── crawler.py            # Core async crawler
│   ├── report.py             # Report generation (terminal, HTML, JSON)
│   ├── config.py             # Configuration management
│   ├── cli.py                # Typer CLI interface
│   ├── templates/            # Jinja2 templates for reports
│   │   └── report.html
│   └── web/                  # FastAPI web interface
│       ├── __init__.py
│       ├── app.py            # FastAPI application
│       ├── templates/        # Web UI templates
│       │   └── index.html
│       └── static/           # CSS and JavaScript
│           └── style.css
├── tests/                    # Test suite
│   ├── test_models.py
│   ├── test_database.py
│   ├── test_crawler.py
│   ├── test_report.py
│   ├── test_config.py
│   ├── test_cli.py
│   └── test_web.py
├── docs/                     # Documentation
│   ├── design.md             # Design document
│   └── plans/                # Implementation plans
├── pyproject.toml            # Package configuration
├── config.example.yaml       # Example configuration
└── README.md                 # This file
```

## License

MIT License - see LICENSE file for details.
