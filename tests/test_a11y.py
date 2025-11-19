"""Tests for accessibility analyzer."""

from site_health.a11y import A11yChecker


def test_missing_alt_text_detection():
    """Test detection of images without alt attributes."""
    html = """
    <html>
        <body>
            <img src="logo.png">
            <img src="photo.jpg" alt="">
            <img src="icon.png" alt="Home icon">
        </body>
    </html>
    """

    checker = A11yChecker(html)
    violations = checker.check_images_alt_text()

    # Should detect one missing alt (first img)
    assert len(violations) == 1
    assert violations[0].severity == "critical"
    assert violations[0].check == "missing_alt_text"
    assert violations[0].wcag_criterion == "1.1.1"
    assert "logo.png" in violations[0].element


def test_suspicious_alt_text_detection():
    """Test detection of images with empty or suspicious alt text."""
    html = """
    <html>
        <body>
            <img src="photo.jpg" alt="">
            <img src="icon.png" alt="image">
            <img src="pic.jpg" alt="Good description">
        </body>
    </html>
    """

    checker = A11yChecker(html)
    violations = checker.check_suspicious_alt_text()

    # Should detect empty alt (potential non-decorative) and generic "image"
    assert len(violations) == 2
    assert violations[0].severity == "moderate"
    assert violations[0].check == "suspicious_alt_text"
