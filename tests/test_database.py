# tests/test_database.py
import pytest
import aiosqlite
from pathlib import Path
from site_health.database import Database
from site_health.models import LinkResult

@pytest.mark.asyncio
async def test_database_initialization(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))

    await db.initialize()

    # Verify database file was created
    assert db_path.exists()

    # Verify tables exist
    async with aiosqlite.connect(str(db_path)) as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = [row[0] for row in await cursor.fetchall()]
        assert "crawls" in tables
        assert "link_results" in tables

@pytest.mark.asyncio
async def test_create_crawl(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    crawl_id = await db.create_crawl("https://example.com", max_depth=2)

    assert crawl_id > 0

    # Verify crawl was created
    summary = await db.get_crawl_summary(crawl_id)
    assert summary is not None
    assert summary.start_url == "https://example.com"
    assert summary.status == "running"

@pytest.mark.asyncio
async def test_save_link_result(tmp_path):
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    crawl_id = await db.create_crawl("https://example.com", max_depth=2)

    result = LinkResult(
        source_url="https://example.com",
        target_url="https://example.com/page",
        link_type="page",
        status_code=404,
        response_time=0.5,
        severity="error",
        error_message="Not found"
    )

    await db.save_link_result(crawl_id, result)

    # Verify result was saved
    results = await db.get_link_results(crawl_id)
    assert len(results) == 1
    assert results[0].target_url == "https://example.com/page"
    assert results[0].status_code == 404
