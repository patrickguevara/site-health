# Site Health Usage Guide

This guide provides detailed information on using Site Health to crawl websites, detect broken links, and generate reports.

## Table of Contents

- [CLI Commands](#cli-commands)
- [Web Interface](#web-interface)
- [Report Formats](#report-formats)
- [Link Types](#link-types)
- [Severity Levels](#severity-levels)
- [Best Practices](#best-practices)
- [CI/CD Integration](#cicd-integration)

## CLI Commands

### `crawl` - Start a New Crawl

The primary command to crawl a website and check for broken links.

**Basic Usage:**
```bash
site-health crawl https://example.com
```

**All Options:**
```bash
site-health crawl [OPTIONS] URL

Options:
  --depth INTEGER          Maximum depth to crawl (default: 2)
  --max-concurrent INTEGER Maximum concurrent requests (default: 10)
  --timeout FLOAT          Request timeout in seconds (default: 10.0)
  --format TEXT            Output format: terminal, html, json (default: terminal)
  --config PATH            Path to YAML configuration file
  --help                   Show this message and exit
```

**Examples:**

```bash
# Crawl with depth 3
site-health crawl https://example.com --depth 3

# Generate HTML report
site-health crawl https://example.com --format html

# Use custom timeout and concurrency
site-health crawl https://example.com --timeout 30 --max-concurrent 20

# Load settings from config file
site-health crawl --config mysite.yaml
```

### `list` - View Previous Crawls

List all crawls stored in the database.

**Basic Usage:**
```bash
site-health list
```

**Options:**
```bash
site-health list [OPTIONS]

Options:
  --limit INTEGER  Maximum number of crawls to show (default: 50)
  --help          Show this message and exit
```

**Example:**
```bash
# Show last 10 crawls
site-health list --limit 10
```

### `report` - Generate Report for Previous Crawl

Generate a new report from a previously completed crawl.

**Basic Usage:**
```bash
site-health report CRAWL_ID
```

**Options:**
```bash
site-health report [OPTIONS] CRAWL_ID

Options:
  --format TEXT  Output format: terminal, html, json (default: terminal)
  --help        Show this message and exit
```

**Examples:**
```bash
# View terminal report for crawl #5
site-health report 5

# Generate HTML report for crawl #3
site-health report 3 --format html

# Export crawl #7 to JSON
site-health report 7 --format json
```

### `serve` - Start Web Interface

Launch the web server with the browser-based UI.

**Basic Usage:**
```bash
site-health serve
```

**Options:**
```bash
site-health serve [OPTIONS]

Options:
  --host TEXT     Host to bind to (default: 127.0.0.1)
  --port INTEGER  Port to bind to (default: 8000)
  --help         Show this message and exit
```

**Examples:**
```bash
# Start on default port (8000)
site-health serve

# Bind to all interfaces on port 9000
site-health serve --host 0.0.0.0 --port 9000

# Local development
site-health serve --host localhost --port 5000
```

## Web Interface

The web interface provides a user-friendly way to manage crawls and view results.

### Starting a Crawl

1. Navigate to http://localhost:8000
2. Enter the URL to crawl
3. Configure options:
   - **Max Depth**: How deep to crawl (1-5 levels)
   - **Max Concurrent**: Number of parallel requests (1-50)
   - **Timeout**: Request timeout in seconds (5-60)
4. Click "Start Crawl"

### Viewing Crawl History

The crawl history table shows:
- Crawl ID
- Starting URL
- Date and time started
- Status (running, completed, failed)
- Number of pages crawled
- Error count
- Warning count

### Viewing Reports

Click "View" to see the HTML report in a new tab, or "JSON" to download the raw data.

## Report Formats

### Terminal Report

Colorized text output suitable for console display.

**Features:**
- Summary statistics
- First 20 errors with details
- First 10 warnings
- Breakdown by link type

**Colors:**
- Red: Errors (404, 500, timeouts)
- Yellow: Warnings (redirects, slow responses)
- Green: Success summary

**Example:**
```
Site Health Report
==================
URL: https://example.com
Crawled: 45 pages, 324 links
Errors: 3 | Warnings: 8

Errors:
  [404] https://example.com/missing.html
    Source: https://example.com/about.html

  [Timeout] https://slow.example.com/api
    Source: https://example.com/contact.html
```

### HTML Report

Standalone HTML file with interactive table and filtering.

**Features:**
- Sortable columns
- Filterable by severity, link type, status code
- Search functionality
- Responsive design
- Saved to `reports/` directory

**File Location:**
```
reports/crawl_<crawl_id>_<timestamp>.html
```

### JSON Report

Machine-readable JSON export for integration with other tools.

**Structure:**
```json
{
  "crawl_id": 1,
  "summary": {
    "id": 1,
    "start_url": "https://example.com",
    "started_at": "2025-01-18T10:30:00",
    "completed_at": "2025-01-18T10:35:22",
    "status": "completed",
    "total_pages": 45,
    "total_links": 324,
    "errors": 3,
    "warnings": 8
  },
  "results": [
    {
      "source_url": "https://example.com/index.html",
      "target_url": "https://example.com/about.html",
      "link_type": "page",
      "status_code": 200,
      "response_time": 0.234,
      "severity": "success",
      "error_message": null
    }
  ]
}
```

## Link Types

Site Health categorizes links into different types:

### `page`
Standard HTML pages on the same domain.

**Examples:**
- `/about.html`
- `/products/item.html`
- Same-domain relative links

### `image`
Image resources (jpg, png, gif, svg, webp).

**Examples:**
- `/images/logo.png`
- `/assets/photo.jpg`

### `css`
Stylesheet files.

**Examples:**
- `/static/style.css`
- `/css/main.css`

### `js`
JavaScript files.

**Examples:**
- `/static/app.js`
- `/scripts/analytics.js`

### `external`
Links to different domains.

**Examples:**
- `https://cdn.example.com/library.js`
- `https://other-site.com/page.html`

**Note:** External links are checked but not crawled further.

## Severity Levels

### `error`
Critical issues that need immediate attention.

**Causes:**
- HTTP 404 (Not Found)
- HTTP 500+ (Server Errors)
- Connection timeouts
- DNS resolution failures
- SSL/TLS errors

**Impact:** Broken user experience, SEO penalties.

### `warning`
Issues that should be reviewed but may not break functionality.

**Causes:**
- HTTP 301/302 (Redirects)
- Slow responses (>5 seconds)
- HTTP 403 (Forbidden)
- HTTP 401 (Unauthorized)

**Impact:** Degraded performance, potential issues.

### `success`
Links that work correctly.

**Criteria:**
- HTTP 200 (OK)
- HTTP 304 (Not Modified)
- Reasonable response time (<5 seconds)

## Best Practices

### Choosing Crawl Depth

- **Depth 1**: Homepage links only. Fast, good for quick checks.
- **Depth 2**: Homepage and one level deep. Recommended for most sites.
- **Depth 3**: Three levels deep. Good for comprehensive checks.
- **Depth 4-5**: Very thorough but slow. Use for critical sites or before major launches.

### Configuring Concurrency

**Low Concurrency (1-5):**
- Respectful to small sites
- Lower server load
- Slower crawls

**Medium Concurrency (10-20):**
- Good balance for most sites
- Reasonable speed and politeness
- Default recommendation

**High Concurrency (30-50):**
- Fast crawls
- Only for robust sites or local testing
- May trigger rate limiting

### Timeout Settings

- **5-10 seconds**: Standard websites
- **15-30 seconds**: Slow APIs or international sites
- **30+ seconds**: Very slow endpoints or complex applications

### Respecting robots.txt

The `respect_robots: true` configuration option will:
- Parse robots.txt before crawling
- Skip disallowed paths
- Respect crawl-delay directives

Disable only if:
- You own the site
- You have explicit permission
- Testing in development environment

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Check Site Health

on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight
  workflow_dispatch:

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install site-health
        run: |
          pip install -e .

      - name: Run crawler
        run: |
          site-health crawl https://your-site.com --format json > report.json

      - name: Check for errors
        run: |
          errors=$(jq '.summary.errors' report.json)
          if [ "$errors" -gt 0 ]; then
            echo "Found $errors broken links!"
            exit 1
          fi

      - name: Upload report
        uses: actions/upload-artifact@v3
        with:
          name: site-health-report
          path: report.json
```

### GitLab CI Example

```yaml
site-health-check:
  image: python:3.11
  script:
    - pip install -e .
    - site-health crawl https://your-site.com --format json > report.json
    - |
      errors=$(jq '.summary.errors' report.json)
      if [ "$errors" -gt 0 ]; then
        echo "Found $errors broken links!"
        exit 1
      fi
  artifacts:
    paths:
      - report.json
  only:
    - schedules
```

### Pre-deployment Check

```bash
#!/bin/bash
# pre-deploy-check.sh

set -e

echo "Checking staging site health..."
site-health crawl https://staging.your-site.com --depth 3 --format json > health.json

errors=$(jq '.summary.errors' health.json)
warnings=$(jq '.summary.warnings' health.json)

echo "Errors: $errors"
echo "Warnings: $warnings"

if [ "$errors" -gt 0 ]; then
    echo "❌ Deployment blocked: $errors broken links found"
    site-health report $(jq '.crawl_id' health.json) --format terminal
    exit 1
fi

if [ "$warnings" -gt 10 ]; then
    echo "⚠️  Warning: $warnings issues found"
fi

echo "✅ Site health check passed"
```

### Monitoring Script

```bash
#!/bin/bash
# monitor.sh - Run periodic site health checks

SITE="https://your-site.com"
ALERT_EMAIL="ops@your-site.com"

site-health crawl "$SITE" --format json > /tmp/health.json

errors=$(jq '.summary.errors' /tmp/health.json)

if [ "$errors" -gt 0 ]; then
    mail -s "Site Health Alert: $errors broken links" "$ALERT_EMAIL" < /tmp/health.json
fi
```

## Advanced Usage

### Using Configuration Files

Create `production.yaml`:

```yaml
url: https://production.example.com
depth: 3
max_concurrent: 15
timeout: 20.0
respect_robots: true
output_format: html
```

Run with:
```bash
site-health crawl --config production.yaml
```

Override specific values:
```bash
site-health crawl --config production.yaml --depth 2
```

### Database Location

By default, Site Health stores data in `site_health.db` in the current directory.

To use a custom location:
```bash
# Set via environment variable (if implemented)
export SITE_HEALTH_DB=/path/to/custom.db
site-health crawl https://example.com
```

### Batch Processing

```bash
#!/bin/bash
# Crawl multiple sites

sites=(
    "https://site1.com"
    "https://site2.com"
    "https://site3.com"
)

for site in "${sites[@]}"; do
    echo "Crawling $site..."
    site-health crawl "$site" --format html
done
```

## Troubleshooting

### "Connection timeout" errors

Increase timeout:
```bash
site-health crawl https://slow-site.com --timeout 30
```

### Too many redirects

Check for redirect loops on the site. The crawler follows up to 10 redirects by default.

### High memory usage

Reduce concurrency:
```bash
site-health crawl https://large-site.com --max-concurrent 5
```

### SSL certificate errors

This indicates the target site has SSL/TLS issues. The crawler validates certificates by default.

## Getting Help

- Run `site-health --help` for command overview
- Run `site-health <command> --help` for command-specific help
- Check logs in the terminal for detailed error messages
- Review the HTML report for visual analysis of issues
