# SEO Audit Feature Design

## Overview

Add comprehensive SEO auditing capabilities to the site-health crawler, providing both launch-blocking critical issues and ongoing optimization metrics through a severity-based scoring system.

## Goals

- **Quick wins**: Identify critical SEO issues that must be fixed before launch (missing titles, broken meta tags)
- **Comprehensive analysis**: Track and measure SEO health over time across multiple dimensions
- **Google-aligned scoring**: Weight factors based on known Google ranking priorities
- **Seamless integration**: Follow existing architectural patterns (opt-in flag like `--vitals`)

## Architecture

### Core Components

**1. SEOAnalyzer (`site_health/seo_analyzer.py`)**
- Performs all SEO checks on a page
- Input: HTML content, URL, response metadata
- Output: Structured SEOResult with scores and issues
- Synchronous implementation (HTML parsing doesn't need async)

**2. Data Models (`site_health/models.py`)**
```python
@dataclass
class SEOIssue:
    severity: str  # "CRITICAL", "WARNING", "INFO"
    category: str  # "technical", "content", "performance", "mobile", "structured_data"
    check: str     # e.g., "missing_title", "low_word_count"
    message: str   # Human-readable issue description

@dataclass
class SEOResult:
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

**3. Database Schema (`site_health/database.py`)**
```sql
CREATE TABLE seo_results (
    id INTEGER PRIMARY KEY,
    crawl_id INTEGER NOT NULL,
    url TEXT NOT NULL,
    overall_score REAL,
    technical_score REAL,
    content_score REAL,
    performance_score REAL,
    mobile_score REAL,
    structured_data_score REAL,
    issues TEXT,  -- JSON array of SEOIssue objects
    timestamp TEXT,
    FOREIGN KEY (crawl_id) REFERENCES crawls(id)
)
```

**4. Crawler Integration (`site_health/crawler.py`)**
- When `--seo` flag enabled, call SEOAnalyzer after fetching each page
- Reuse Core Web Vitals data when both `--vitals` and `--seo` are enabled
- Store results via database layer

## SEO Checks & Scoring

### Category Breakdown

**Technical SEO (Weight: 25%)**
- Title tag: existence, length (50-60 chars optimal), uniqueness
- Meta description: existence, length (150-160 chars optimal)
- Canonical URL: presence and validity
- Heading structure: single H1, proper hierarchy (no skipping levels)
- Robots meta tag: check for blocking directives
- URL structure: readability, parameter count
- Internal linking: reasonable link count per page

**Content Quality (Weight: 20%)**
- Word count: minimum threshold (300+ words for content pages)
- Image alt text: all images have descriptive alt attributes
- Content-to-HTML ratio: sufficient text vs markup

**Performance (Weight: 30%)**
- Reuse existing Core Web Vitals data when available (LCP, CLS, INP)
- If vitals not run: flag as "Run with --vitals for performance score"
- HTTPS usage verification
- Page size assessment

**Mobile & Accessibility (Weight: 15%)**
- Viewport meta tag: presence and configuration
- Font sizes: mobile readability
- Touch targets: adequate spacing
- Basic ARIA: landmarks and labels

**Structured Data (Weight: 10%)**
- Detect JSON-LD or microdata presence
- Identify schema types (Article, Product, Organization, etc.)
- Basic validation of required properties

### Severity Mapping

- **CRITICAL**: Missing title, missing H1, no HTTPS, blocking robots directives
- **WARNING**: Suboptimal meta descriptions, heading hierarchy issues, missing alt text
- **INFO**: Missing structured data, low word count on specific pages, optimization suggestions

### Site-Wide Score Calculation

Aggregate scores calculated as weighted averages across all crawled pages:
- Homepage weighted 2x to reflect its importance
- Prevents single bad page from tanking overall score
- Still reflects widespread issues across multiple pages

## User Interface

### CLI

**New Flag:**
```bash
site-health crawl https://example.com --seo
site-health crawl https://example.com --seo --vitals  # Both audits
```

**Terminal Output:**
- SEO section with overall score (colored green/yellow/red)
- Category scores displayed as horizontal bars
- Top 5-10 critical issues listed
- Summary: "Found X critical, Y warnings, Z info issues"

**HTML Report:**
- SEO section with score visualization (gauge/progress bars)
- Expandable issue list grouped by severity and category
- Per-page SEO scores in results table
- Extends existing report.html template

**JSON Export:**
- Full `seo_results` array with all scores and issues
- Top-level key maintains existing structure

### Web Interface

- "Include SEO Audit" checkbox on crawl form
- SEO scores in crawl results table
- Detailed SEO view for specific crawls

## Implementation Details

### Dependencies

**Existing:**
- BeautifulSoup4: HTML parsing (already used for link extraction)

**New:**
- extruct: Extract structured data (JSON-LD, microdata, RDFa)
- lxml (optional): Faster HTML parsing, fallback to html.parser

### SEOAnalyzer Flow

1. Parse HTML with BeautifulSoup
2. Run check groups in parallel (technical, content, mobile, structured_data)
3. Incorporate vitals data if available, else partial performance score
4. Calculate category scores with Google-aligned weights
5. Aggregate into overall score (0-100)
6. Return SEOResult with issues sorted by severity

### Error Handling

- HTML parsing failure: skip SEO for that page, log warning
- Specific check failure: mark as INFO-level "unable_to_analyze"
- Never fail entire crawl due to SEO analysis errors

### Performance

- Adds ~50-200ms per page (acceptable for opt-in feature)
- No extra network requests (HTML already fetched)
- Reuse BeautifulSoup parsing from link extraction where possible

## Testing Strategy

- Unit tests for each SEO check with HTML fixtures
- Integration tests for score calculations
- Database persistence verification
- Report generation tests

## Future Extensibility

### Supported Future Enhancements

1. **Custom weights**: Config file overrides for category weights
2. **Historical trending**: Query score changes over time from seo_results table
3. **Competitive analysis**: Compare SEO scores across multiple domains
4. **Issue prioritization**: Add impact scores to guide fix decisions
5. **Enhanced recommendations**: Upgrade from issue-only to include code examples

### Out of Scope (YAGNI)

- Custom check plugins/extensions
- AI-powered content quality analysis
- Backlink analysis (requires external data)
- Keyword rank tracking (requires search API)
- Multi-language SEO support

### Maintenance Considerations

- Review check weights periodically as SEO best practices evolve
- Adjust severity levels based on Google algorithm updates
- Update structured data checks as Schema.org evolves

## Implementation Order

1. Data models (SEOIssue, SEOResult)
2. Database schema and methods
3. SEOAnalyzer core implementation
4. Crawler integration with --seo flag
5. Report generation (terminal, HTML, JSON)
6. Web interface updates
7. Tests
8. Documentation

## Success Metrics

- Users can identify critical SEO issues before launch
- SEO scores improve over time as issues are fixed
- Performance impact remains under 200ms per page
- No false positives causing alarm fatigue
