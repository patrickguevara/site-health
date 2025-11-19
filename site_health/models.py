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
