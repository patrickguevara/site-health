"""Integration tests for a11y feature."""

import pytest
from site_health.a11y import A11yAuditor


@pytest.mark.asyncio
async def test_a11y_full_integration():
    """Test complete a11y workflow from HTML to result."""

    # Realistic HTML with multiple a11y issues
    html = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Test Page</title>
        </head>
        <body>
            <h1>Welcome</h1>

            <img src="logo.png">
            <img src="photo.jpg" alt="">
            <img src="icon.png" alt="icon">

            <form>
                <input type="text" name="username">
                <label for="email">Email</label>
                <input type="email" id="email">
            </form>

            <a href="/page1"></a>
            <a href="/page2">click here</a>
            <a href="/page3">Learn more about Python</a>

            <button></button>
            <button>Submit</button>
        </body>
    </html>
    """

    auditor = A11yAuditor("https://example.com/test", html)
    result = auditor.analyze()

    # Verify result structure
    assert result.url == "https://example.com/test"
    assert 0 <= result.overall_score <= 100
    assert result.wcag_level_achieved in ["None", "A", "AA", "AAA"]

    # Verify we found the expected violations
    violation_checks = {v.check for v in result.violations}

    # Should find these issues:
    assert "missing_alt_text" in violation_checks  # First img
    assert "input_without_label" in violation_checks  # First input
    assert "empty_link" in violation_checks  # First link
    assert "generic_link_text" in violation_checks  # "click here"
    assert "empty_button" in violation_checks  # First button

    # Should have critical violations (missing alt, no label, empty link, empty button)
    critical = [v for v in result.violations if v.severity == "critical"]
    assert len(critical) >= 3

    # With critical violations, can't achieve Level A
    assert result.wcag_level_achieved == "None"

    # Verify category scores
    assert result.images_media_score < 100  # Has issues
    assert result.forms_inputs_score < 100  # Has issues
    assert result.navigation_links_score < 100  # Has issues


@pytest.mark.asyncio
async def test_a11y_perfect_page():
    """Test analysis of page with no a11y issues."""

    html = """
    <!DOCTYPE html>
    <html lang="en">
        <head>
            <title>Accessible Page</title>
        </head>
        <body>
            <h1>Welcome</h1>
            <h2>Section</h2>

            <img src="logo.png" alt="Company logo">

            <form>
                <label for="username">Username</label>
                <input type="text" id="username" name="username">
            </form>

            <a href="/about">Learn about our company</a>

            <button>Submit form</button>
        </body>
    </html>
    """

    auditor = A11yAuditor("https://example.com/perfect", html)
    result = auditor.analyze()

    assert result.overall_score == 100.0
    assert result.wcag_level_achieved == "AAA"
    assert len(result.violations) == 0
    assert result.images_media_score == 100.0
    assert result.forms_inputs_score == 100.0
