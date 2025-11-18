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
