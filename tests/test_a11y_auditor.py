"""Tests for A11y auditor scoring."""

from site_health.a11y import A11yAuditor
from site_health.models import A11yViolation


def test_score_calculation_no_violations():
    """Test score is 100 with no violations."""
    auditor = A11yAuditor("https://example.com", "<html></html>")

    violations = []
    score = auditor.calculate_score(violations)

    assert score == 100.0


def test_score_calculation_with_violations():
    """Test score calculation with various severity violations."""
    auditor = A11yAuditor("https://example.com", "<html></html>")

    violations = [
        A11yViolation("critical", "images_media", "1.1.1", "test", "msg"),  # -10
        A11yViolation("critical", "images_media", "1.1.1", "test", "msg"),  # -10
        A11yViolation("serious", "forms_inputs", "1.3.1", "test", "msg"),   # -5
        A11yViolation("moderate", "navigation_links", "2.4.4", "test", "msg"),  # -2
        A11yViolation("minor", "structure_semantics", "1.3.1", "test", "msg"),  # -1
    ]

    score = auditor.calculate_score(violations)

    # 100 - 10 - 10 - 5 - 2 - 1 = 72
    assert score == 72.0


def test_score_minimum_is_zero():
    """Test score cannot go below 0."""
    auditor = A11yAuditor("https://example.com", "<html></html>")

    # Create 20 critical violations (20 * -10 = -200)
    violations = [
        A11yViolation("critical", "images_media", "1.1.1", "test", "msg")
        for _ in range(20)
    ]

    score = auditor.calculate_score(violations)

    assert score == 0.0


def test_wcag_level_determination():
    """Test WCAG level achievement based on violations."""
    auditor = A11yAuditor("https://example.com", "<html></html>")

    # No violations = AAA if score >= 95
    assert auditor.determine_wcag_level([], 100.0) == "AAA"
    assert auditor.determine_wcag_level([], 95.0) == "AAA"
    assert auditor.determine_wcag_level([], 94.0) == "AA"

    # Any critical = can't achieve Level A
    violations_critical = [
        A11yViolation("critical", "images_media", "1.1.1", "test", "msg")
    ]
    assert auditor.determine_wcag_level(violations_critical, 90.0) == "None"

    # Any serious (but no critical) = Level A achieved, not AA
    violations_serious = [
        A11yViolation("serious", "forms_inputs", "1.3.1", "test", "msg")
    ]
    assert auditor.determine_wcag_level(violations_serious, 95.0) == "A"

    # Only moderate/minor = AA (or AAA if score >= 95)
    violations_moderate = [
        A11yViolation("moderate", "navigation_links", "2.4.4", "test", "msg"),
        A11yViolation("minor", "structure_semantics", "1.3.1", "test", "msg")
    ]
    assert auditor.determine_wcag_level(violations_moderate, 96.0) == "AAA"
    assert auditor.determine_wcag_level(violations_moderate, 94.0) == "AA"
