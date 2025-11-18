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
