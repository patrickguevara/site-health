# tests/test_report_vitals.py
import pytest
from datetime import datetime
from site_health.database import Database
from site_health.report import ReportGenerator
from site_health.models import PageVitals

@pytest.mark.asyncio
async def test_report_includes_vitals(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    crawl_id = await db.create_crawl("https://example.com", 2)

    # Save some vitals
    vitals = PageVitals(
        url="https://example.com",
        lcp=2.1,
        cls=0.05,
        inp=150,
        measured_at=datetime.now(),
        status="success"
    )
    await db.save_page_vitals(crawl_id, vitals)

    await db.complete_crawl(crawl_id, 10, 50)

    # Generate terminal report
    generator = ReportGenerator(crawl_id, db)
    report = await generator.generate('terminal')

    assert "Core Web Vitals" in report
    assert "LCP" in report
    assert "CLS" in report
    assert "INP" in report

@pytest.mark.asyncio
async def test_json_report_includes_vitals(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    crawl_id = await db.create_crawl("https://example.com", 2)

    vitals = PageVitals(
        url="https://example.com",
        lcp=2.3,
        cls=0.08,
        inp=180,
        measured_at=datetime.now(),
        status="success"
    )
    await db.save_page_vitals(crawl_id, vitals)

    await db.complete_crawl(crawl_id, 10, 50)

    # Generate JSON report
    generator = ReportGenerator(crawl_id, db)
    json_report = await generator.generate('json')

    import json
    data = json.loads(json_report)

    assert "vitals" in data
    assert len(data["vitals"]) == 1
    assert data["vitals"][0]["url"] == "https://example.com"
    assert data["vitals"][0]["lcp"] == 2.3
    assert data["vitals"][0]["lcp_rating"] == "good"
