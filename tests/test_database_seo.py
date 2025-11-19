# tests/test_database_seo.py
import pytest
from datetime import datetime
from site_health.database import Database
from site_health.models import SEOResult, SEOIssue


@pytest.mark.asyncio
async def test_save_seo_result(tmp_path):
    """Test saving SEO result to database."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    crawl_id = await db.create_crawl("https://example.com", 2)

    result = SEOResult(
        url="https://example.com",
        overall_score=85.5,
        technical_score=90.0,
        content_score=80.0,
        performance_score=95.0,
        mobile_score=75.0,
        structured_data_score=70.0,
        issues=[
            SEOIssue(
                severity="WARNING",
                category="content",
                check="low_word_count",
                message="Page has only 150 words"
            )
        ],
        timestamp=datetime.now()
    )

    await db.save_seo_result(crawl_id, result)

    # Verify saved
    results = await db.get_seo_results(crawl_id)
    assert len(results) == 1
    assert results[0].url == "https://example.com"
    assert results[0].overall_score == 85.5
    assert len(results[0].issues) == 1


@pytest.mark.asyncio
async def test_get_seo_results_empty(tmp_path):
    """Test getting SEO results when none exist."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    crawl_id = await db.create_crawl("https://example.com", 2)

    results = await db.get_seo_results(crawl_id)
    assert len(results) == 0


@pytest.mark.asyncio
async def test_save_multiple_seo_results(tmp_path):
    """Test saving multiple SEO results."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    crawl_id = await db.create_crawl("https://example.com", 2)

    result1 = SEOResult(
        url="https://example.com/page1",
        overall_score=90.0,
        technical_score=90.0,
        content_score=90.0,
        performance_score=90.0,
        mobile_score=90.0,
        structured_data_score=90.0,
        issues=[],
        timestamp=datetime.now()
    )

    result2 = SEOResult(
        url="https://example.com/page2",
        overall_score=70.0,
        technical_score=70.0,
        content_score=70.0,
        performance_score=70.0,
        mobile_score=70.0,
        structured_data_score=70.0,
        issues=[
            SEOIssue("CRITICAL", "technical", "missing_title", "No title tag")
        ],
        timestamp=datetime.now()
    )

    await db.save_seo_result(crawl_id, result1)
    await db.save_seo_result(crawl_id, result2)

    results = await db.get_seo_results(crawl_id)
    assert len(results) == 2
