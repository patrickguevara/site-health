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


def test_empty_links_detection():
    """Test detection of links without text or labels."""
    html = """
    <html>
        <body>
            <a href="/page1"></a>
            <a href="/page2">Valid link</a>
            <a href="/page3" aria-label="Home"></a>
            <a href="/page4"><img src="icon.png" alt=""></a>
        </body>
    </html>
    """

    checker = A11yChecker(html)
    violations = checker.check_empty_links()

    # Should detect first and last link
    assert len(violations) == 2
    assert violations[0].severity == "critical"
    assert violations[0].check == "empty_link"
    assert violations[0].wcag_criterion == "2.4.4"


def test_generic_link_text_detection():
    """Test detection of links with generic text."""
    html = """
    <html>
        <body>
            <a href="/page1">click here</a>
            <a href="/page2">Read more about accessibility</a>
            <a href="/page3">More</a>
            <a href="/page4">Learn about Python</a>
        </body>
    </html>
    """

    checker = A11yChecker(html)
    violations = checker.check_generic_link_text()

    # Should detect "click here" and "More"
    assert len(violations) == 2
    assert violations[0].severity == "moderate"
    assert violations[0].check == "generic_link_text"


def test_missing_page_title():
    """Test detection of missing page title."""
    html_no_title = "<html><head></head><body>Content</body></html>"
    html_empty_title = "<html><head><title></title></head><body>Content</body></html>"
    html_valid = "<html><head><title>My Page</title></head><body>Content</body></html>"

    checker1 = A11yChecker(html_no_title)
    violations1 = checker1.check_page_structure()
    assert any(v.check == "missing_title" for v in violations1)

    checker2 = A11yChecker(html_empty_title)
    violations2 = checker2.check_page_structure()
    assert any(v.check == "missing_title" for v in violations2)

    checker3 = A11yChecker(html_valid)
    violations3 = checker3.check_page_structure()
    assert not any(v.check == "missing_title" for v in violations3)


def test_heading_structure():
    """Test detection of skipped heading levels."""
    html_bad = """
    <html>
        <body>
            <h1>Main Title</h1>
            <h3>Skipped h2</h3>
            <h2>Back to h2</h2>
        </body>
    </html>
    """

    html_good = """
    <html>
        <body>
            <h1>Main Title</h1>
            <h2>Subtitle</h2>
            <h3>Section</h3>
        </body>
    </html>
    """

    checker_bad = A11yChecker(html_bad)
    violations_bad = checker_bad.check_heading_structure()
    assert len(violations_bad) == 1
    assert violations_bad[0].check == "skipped_heading_level"

    checker_good = A11yChecker(html_good)
    violations_good = checker_good.check_heading_structure()
    assert len(violations_good) == 0
