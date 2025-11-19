# Accessibility Audit Feature Design

**Date:** 2025-11-19
**Status:** Approved

## Overview

Add accessibility (a11y) audit capability to site-health to identify WCAG compliance violations and help ensure websites are accessible to all users. The feature will follow the existing architectural patterns established by the SEO audit, providing both fast static HTML analysis and optional deep browser-based checks.

## Goals

- Flag WCAG violations with severity levels to help meet legal compliance requirements
- Provide configurable WCAG level targeting (A, AA, AAA)
- Integrate seamlessly with existing crawl, report, and storage systems
- Follow hybrid approach: fast static checks with optional deep browser checks

## Architecture & Integration

### Core Components

1. **`site_health/a11y.py`** - New module containing:
   - `A11yChecker` class with static HTML analysis methods
   - `A11yAuditor` class that orchestrates checks and scoring
   - WCAG criteria definitions organized by level (A, AA, AAA)
   - Severity classification (critical, serious, moderate, minor)

2. **Extended `LinkResult` model** - Add optional `a11y_result` field to store:
   - List of violations with type, severity, WCAG criterion, element details
   - Overall compliance score (0-100)
   - WCAG level achieved
   - Violation counts by severity

3. **CLI integration** - Add `--a11y` flag and `--a11y-level` option:
   ```bash
   site-health crawl https://example.com --a11y
   site-health crawl https://example.com --a11y --a11y-level AA
   site-health crawl https://example.com --a11y --a11y-use-browser
   ```

4. **Configuration support** - Extend `config.yaml`:
   ```yaml
   run_a11y_audit: true
   a11y_level: "AA"  # A, AA, or AAA
   a11y_use_browser: false  # Enable Playwright checks
   ```

## Static HTML Analysis Checks

The `A11yChecker` class implements fast, static HTML analysis using BeautifulSoup (already a dependency). These checks run on HTML already fetched during crawling, adding minimal overhead.

### Critical Violations (WCAG Level A)
- **Images without alt text** - `<img>` tags missing `alt` attribute
- **Form inputs without labels** - `<input>` elements without associated `<label>` or `aria-label`
- **Empty links** - `<a>` tags with no text content or aria-label
- **Missing page title** - No `<title>` element in `<head>`
- **Missing language attribute** - `<html>` without `lang` attribute
- **Duplicate IDs** - Multiple elements with the same `id` (breaks ARIA relationships)

### Serious Violations (WCAG Level AA)
- **Insufficient heading structure** - Skipped heading levels (h1 → h3)
- **Empty buttons** - `<button>` elements without text or aria-label
- **Missing form fieldsets** - Radio/checkbox groups without `<fieldset>` and `<legend>`
- **Tables without headers** - `<table>` elements missing `<th>` elements

### Moderate Issues
- **Suspicious link text** - Links with only "click here", "read more", etc.
- **Images with empty alt** - `alt=""` on non-decorative images (flagged for review)
- **Missing ARIA landmarks** - No `role="main"`, `role="navigation"`, etc.

## Playwright Integration

When `--a11y-use-browser` is enabled, the system uses Playwright to run axe-core for comprehensive automated testing. This follows the same pattern as the `--vitals` feature.

### Implementation Approach

1. **Dependency**: Add `axe-playwright-python` to `pyproject.toml` (integrates axe-core with Playwright)

2. **Integration point**: Extend the existing `vitals.py` module or create `a11y_browser.py` to:
   - Inject axe-core into pages already loaded for vitals measurement
   - Run axe with configurable WCAG level and rule sets
   - Convert axe results to our violation format

3. **Additional checks via browser**:
   - **Color contrast** - Text/background contrast ratios (4.5:1 for normal text, 3:1 for large)
   - **Focus indicators** - Elements that receive focus have visible indicators
   - **ARIA validity** - Proper ARIA attribute usage and relationships
   - **Dynamic content** - Issues in JavaScript-rendered content missed by static analysis
   - **Keyboard navigation** - Tab order and keyboard traps

4. **Performance consideration**: Browser checks only run when both `--a11y` and `--a11y-use-browser` are enabled, similar to how `--vitals` is optional.

## Scoring System

The a11y scoring system follows the SEO audit pattern with severity-based weighting and category breakdown.

### Severity Weights
- **Critical**: -10 points per violation (Level A failures - legal compliance risk)
- **Serious**: -5 points per violation (Level AA failures - significant barriers)
- **Moderate**: -2 points per violation (Level AAA or best practice issues)
- **Minor**: -1 point per violation (Warnings or potential issues)

### Score Calculation
- Start at 100 points
- Subtract points based on violations found
- Minimum score: 0
- Formula: `max(0, 100 - total_penalty)`

### Category Breakdown
1. **Images & Media** - Alt text, captions, decorative images
2. **Forms & Inputs** - Labels, fieldsets, error identification
3. **Navigation & Links** - Link text, keyboard access, skip links
4. **Structure & Semantics** - Headings, landmarks, HTML validity
5. **Color & Contrast** - Text contrast, color-only information (browser-only)
6. **ARIA & Dynamic Content** - ARIA usage, live regions (browser-only)

### WCAG Level Achievement
- Level A: No critical violations
- Level AA: No critical or serious violations
- Level AAA: Score >= 95

## Reporting Integration

The a11y results will be displayed in all three output formats (terminal, HTML, JSON) with a dedicated section similar to SEO.

### Terminal Output
```
=== Accessibility Audit ===
Overall Score: 78/100
WCAG Level: A (AA not achieved)

Compliance:
  ✓ Level A: Passed
  ✗ Level AA: 3 serious violations
  ✗ Level AAA: Not assessed

Violations by Severity:
  Critical: 0
  Serious: 3
  Moderate: 8
  Minor: 5

Top Issues:
  • 2 form inputs without labels (serious)
  • 1 skipped heading level (serious)
  • 5 images with suspicious alt text (moderate)
  • 3 links with generic text (moderate)
```

### HTML Report
- Dedicated "Accessibility" section with:
  - Score gauge visualization (similar to SEO)
  - WCAG level badges (A, AA, AAA with pass/fail colors)
  - Category breakdown table with violation counts
  - Expandable violation details per page showing:
    - Element selector/location
    - WCAG criterion violated
    - Suggested fix

### JSON Export
```json
{
  "a11y_summary": {
    "overall_score": 78,
    "wcag_level_achieved": "A",
    "total_violations": 16,
    "violations_by_severity": {
      "critical": 0,
      "serious": 3,
      "moderate": 8,
      "minor": 5
    },
    "category_scores": {...}
  },
  "pages": [
    {
      "url": "https://example.com",
      "a11y_result": {
        "score": 85,
        "violations": [...]
      }
    }
  ]
}
```

## Database Storage

Extend the existing SQLite schema to store a11y results for historical tracking.

### Schema Changes

1. **`crawl_results` table** - Add columns:
   - `a11y_score INTEGER`
   - `a11y_level_achieved TEXT` (A, AA, AAA, or NULL)
   - `a11y_violations_json TEXT` (JSON blob of violation details)

2. **`crawl_metadata` table** - Add columns:
   - `a11y_enabled BOOLEAN`
   - `a11y_level TEXT` (configured level: A, AA, AAA)
   - `a11y_browser_enabled BOOLEAN`

This allows historical tracking and comparison of accessibility over time.

## Testing Strategy

### Unit Tests (`tests/test_a11y.py`)
- Test each static check with HTML fixtures (missing alt, empty links, etc.)
- Test scoring calculation with various violation combinations
- Test WCAG level determination logic

### Integration Tests
- Mock HTML pages with known a11y issues
- Verify violations are correctly identified and scored
- Test CLI flags (`--a11y`, `--a11y-level`, `--a11y-use-browser`)
- Test config file parsing

### Browser Tests (if `--a11y-use-browser`)
- Test axe-core integration with sample pages
- Verify contrast checking on test fixtures
- Mock axe results to avoid Playwright dependency in unit tests

### Report Tests
- Verify a11y section appears in terminal/HTML/JSON output
- Test formatting of violation details

## Implementation Considerations

### YAGNI Principle
- Start with static checks only in MVP
- Add browser integration in follow-up phase if needed
- Focus on most common violations first
- Avoid over-engineering the scoring algorithm

### Consistency with Existing Patterns
- Follow SEO audit architecture (checker + auditor classes)
- Use same CLI flag pattern (`--a11y` like `--seo`, `--vitals`)
- Reuse existing report generation infrastructure
- Maintain database schema naming conventions

### Performance
- Static checks add minimal overhead (parse HTML already fetched)
- Browser checks are opt-in via `--a11y-use-browser`
- Consider caching axe-core results if page content unchanged

## Success Criteria

1. Users can run `site-health crawl URL --a11y` and get accessibility violations
2. Violations are categorized by severity and WCAG level
3. Overall accessibility score is calculated and displayed
4. Results appear in terminal, HTML, and JSON reports
5. Historical a11y data is stored in database
6. All tests pass with good coverage
7. Documentation updated (README, usage.md)
