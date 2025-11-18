# tests/test_database_vitals.py
import pytest
from datetime import datetime
from site_health.database import Database
from site_health.models import PageVitals

@pytest.mark.asyncio
async def test_save_and_retrieve_vitals(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    # Create crawl
    crawl_id = await db.create_crawl("https://example.com", 2)

    # Save vitals
    vitals = PageVitals(
        url="https://example.com",
        lcp=2.3,
        cls=0.08,
        inp=150,
        measured_at=datetime.now(),
        status="success"
    )
    await db.save_page_vitals(crawl_id, vitals)

    # Retrieve
    results = await db.get_page_vitals(crawl_id)
    assert len(results) == 1
    assert results[0].url == "https://example.com"
    assert results[0].lcp == 2.3
    assert results[0].cls == 0.08
    assert results[0].inp == 150
    assert results[0].status == "success"

@pytest.mark.asyncio
async def test_save_failed_vitals(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    crawl_id = await db.create_crawl("https://example.com", 2)

    vitals = PageVitals(
        url="https://broken.com",
        lcp=None,
        cls=None,
        inp=None,
        measured_at=datetime.now(),
        status="failed",
        error_message="Page timeout"
    )
    await db.save_page_vitals(crawl_id, vitals)

    results = await db.get_page_vitals(crawl_id)
    assert len(results) == 1
    assert results[0].status == "failed"
    assert results[0].error_message == "Page timeout"
