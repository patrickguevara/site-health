# tests/test_models.py
from datetime import datetime
from site_health.models import LinkResult, CrawlSummary

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
