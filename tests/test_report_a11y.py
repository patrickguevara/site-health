"""Tests for a11y reporting."""

import pytest
from datetime import datetime
from site_health.database import Database
from site_health.report import ReportGenerator
from site_health.models import A11yResult, A11yViolation


@pytest.mark.asyncio
async def test_a11y_terminal_report(tmp_path):
    """Test a11y section in terminal report."""
    db_path = tmp_path / "test.db"
    db = Database(str(db_path))
    await db.initialize()

    crawl_id = await db.create_crawl("https://example.com", 2)

    # Create a11y result with violations
    violations = [
        A11yViolation("critical", "images_media", "1.1.1", "missing_alt_text", "Image missing alt"),
        A11yViolation("serious", "forms_inputs", "1.3.1", "input_without_label", "Input missing label"),
        A11yViolation("moderate", "navigation_links", "2.4.4", "generic_link_text", "Generic link"),
    ]

    result = A11yResult(
        url="https://example.com",
        overall_score=73.0,
        wcag_level_achieved="A",
        images_media_score=90.0,
        forms_inputs_score=95.0,
        navigation_links_score=98.0,
        structure_semantics_score=100.0,
        color_contrast_score=100.0,
        aria_dynamic_score=100.0,
        violations=violations,
        timestamp=datetime.now()
    )

    await db.save_a11y_result(crawl_id, result)
    await db.complete_crawl(crawl_id, 1, 5)

    # Generate report
    generator = ReportGenerator(crawl_id, db)
    report = await generator.generate("terminal")

    # Verify a11y section exists
    assert "Accessibility Audit" in report
    assert "Overall Score: 73" in report
    # With critical violation, should be "None"
    assert "WCAG Level: None" in report
    assert "Critical: 1" in report
    assert "Serious: 1" in report
    assert "Moderate: 1" in report
