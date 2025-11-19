"""Tests for a11y database operations."""

import pytest
from datetime import datetime
from site_health.database import Database
from site_health.models import A11yResult, A11yViolation


@pytest.mark.asyncio
async def test_save_and_retrieve_a11y_result(tmp_path):
    """Test saving and retrieving a11y results."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    # Create crawl
    crawl_id = await db.create_crawl("https://example.com", 2)

    # Create a11y result
    violations = [
        A11yViolation(
            severity="critical",
            category="images_media",
            wcag_criterion="1.1.1",
            check="missing_alt_text",
            message="Image missing alt",
            element="<img>",
            suggested_fix="Add alt"
        )
    ]

    result = A11yResult(
        url="https://example.com",
        overall_score=90.0,
        wcag_level_achieved="A",
        images_media_score=80.0,
        forms_inputs_score=100.0,
        navigation_links_score=100.0,
        structure_semantics_score=100.0,
        color_contrast_score=100.0,
        aria_dynamic_score=100.0,
        violations=violations,
        timestamp=datetime.now()
    )

    # Save result
    await db.save_a11y_result(crawl_id, result)

    # Retrieve results
    results = await db.get_a11y_results(crawl_id)

    assert len(results) == 1
    assert results[0].url == "https://example.com"
    assert results[0].overall_score == 90.0
    assert results[0].wcag_level_achieved == "A"
    assert len(results[0].violations) == 1
    assert results[0].violations[0].severity == "critical"
