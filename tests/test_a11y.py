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


def test_form_inputs_without_labels():
    """Test detection of form inputs without labels."""
    html = """
    <html>
        <body>
            <form>
                <input type="text" name="username">
                <label for="email">Email:</label>
                <input type="text" id="email" name="email">
                <input type="text" aria-label="Phone" name="phone">
            </form>
        </body>
    </html>
    """

    checker = A11yChecker(html)
    violations = checker.check_form_labels()

    # Should detect first input (no label or aria-label)
    assert len(violations) == 1
    assert violations[0].severity == "critical"
    assert violations[0].check == "input_without_label"
    assert violations[0].wcag_criterion == "1.3.1"


def test_empty_buttons_detection():
    """Test detection of buttons without text or labels."""
    html = """
    <html>
        <body>
            <button></button>
            <button>Click me</button>
            <button aria-label="Close"></button>
            <button><img src="icon.png" alt=""></button>
        </body>
    </html>
    """

    checker = A11yChecker(html)
    violations = checker.check_empty_buttons()

    # Should detect first and last button (no text or aria-label)
    assert len(violations) == 2
    assert violations[0].severity == "serious"
    assert violations[0].check == "empty_button"
