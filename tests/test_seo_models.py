# tests/test_seo_models.py
from datetime import datetime
from site_health.models import SEOIssue, SEOResult


def test_seo_issue_creation():
    """Test creating an SEO issue."""
    issue = SEOIssue(
        severity="CRITICAL",
        category="technical",
        check="missing_title",
        message="Page is missing a title tag"
    )

    assert issue.severity == "CRITICAL"
    assert issue.category == "technical"
    assert issue.check == "missing_title"
    assert issue.message == "Page is missing a title tag"


def test_seo_result_creation():
    """Test creating an SEO result."""
    now = datetime.now()
    issues = [
        SEOIssue(
            severity="CRITICAL",
            category="technical",
            check="missing_title",
            message="Missing title tag"
        )
    ]

    result = SEOResult(
        url="https://example.com",
        overall_score=75.5,
        technical_score=60.0,
        content_score=85.0,
        performance_score=90.0,
        mobile_score=70.0,
        structured_data_score=50.0,
        issues=issues,
        timestamp=now
    )

    assert result.url == "https://example.com"
    assert result.overall_score == 75.5
    assert result.technical_score == 60.0
    assert len(result.issues) == 1
    assert result.issues[0].severity == "CRITICAL"


def test_seo_result_no_issues():
    """Test SEO result with perfect score and no issues."""
    result = SEOResult(
        url="https://example.com",
        overall_score=100.0,
        technical_score=100.0,
        content_score=100.0,
        performance_score=100.0,
        mobile_score=100.0,
        structured_data_score=100.0,
        issues=[],
        timestamp=datetime.now()
    )

    assert result.overall_score == 100.0
    assert len(result.issues) == 0
