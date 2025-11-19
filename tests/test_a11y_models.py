"""Tests for accessibility data models."""

from site_health.models import A11yViolation, A11yResult
from datetime import datetime


def test_a11y_violation_creation():
    """Test creating an A11yViolation instance."""
    violation = A11yViolation(
        severity="critical",
        category="images_media",
        wcag_criterion="1.1.1",
        check="missing_alt_text",
        message="Image missing alt attribute",
        element="<img src='test.jpg'>",
        suggested_fix="Add alt attribute describing the image"
    )

    assert violation.severity == "critical"
    assert violation.category == "images_media"
    assert violation.wcag_criterion == "1.1.1"
    assert violation.check == "missing_alt_text"
    assert "missing alt attribute" in violation.message
    assert violation.element == "<img src='test.jpg'>"
    assert "Add alt attribute" in violation.suggested_fix


def test_a11y_result_creation():
    """Test creating an A11yResult instance."""
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
        overall_score=85.0,
        wcag_level_achieved="A",
        images_media_score=70.0,
        forms_inputs_score=100.0,
        navigation_links_score=90.0,
        structure_semantics_score=95.0,
        color_contrast_score=100.0,
        aria_dynamic_score=100.0,
        violations=violations,
        timestamp=datetime.now()
    )

    assert result.url == "https://example.com"
    assert result.overall_score == 85.0
    assert result.wcag_level_achieved == "A"
    assert len(result.violations) == 1
    assert result.violations[0].severity == "critical"
