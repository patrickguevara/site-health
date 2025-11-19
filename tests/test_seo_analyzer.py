# tests/test_seo_analyzer.py
from site_health.seo_analyzer import SEOAnalyzer
from site_health.models import PageVitals
from datetime import datetime


def test_analyzer_missing_title():
    """Test detection of missing title tag."""
    html = """
    <html>
        <head></head>
        <body><h1>Hello</h1></body>
    </html>
    """

    analyzer = SEOAnalyzer("https://example.com", html, 200, None)
    result = analyzer.analyze()

    assert result.overall_score < 100
    critical_issues = [i for i in result.issues if i.severity == "CRITICAL"]
    assert any(i.check == "missing_title" for i in critical_issues)


def test_analyzer_perfect_page():
    """Test analysis of a perfect page."""
    html = """
    <!DOCTYPE html>
    <html>
        <head>
            <title>Test Page - 50 Characters Long Title Here</title>
            <meta name="description" content="This is a well-written meta description that is between 150 and 160 characters long and describes the page content accurately and completely.">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="canonical" href="https://example.com">
        </head>
        <body>
            <h1>Main Heading</h1>
            <h2>Subheading</h2>
            <p>This is a content paragraph with at least 300 words. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum. Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum. Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo. Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt. Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur, adipisci velit, sed quia non numquam eius modi tempora incidunt ut labore et dolore magnam aliquam quaerat voluptatem. Ut enim ad minima veniam, quis nostrum exercitationem ullam corporis suscipit laboriosam, nisi ut aliquid ex ea commodi consequatur. At vero eos et accusamus et iusto odio dignissimos ducimus qui blanditiis praesentium voluptatum deleniti atque corrupti quos dolores et quas molestias excepturi sint occaecati cupiditate non provident, similique sunt in culpa qui officia deserunt mollitia animi, id est laborum et dolorum fuga. Et harum quidem rerum facilis est et expedita distinctio.</p>
            <img src="test.jpg" alt="Test image with descriptive alt text">
        </body>
    </html>
    """

    analyzer = SEOAnalyzer("https://example.com", html, 200, None)
    result = analyzer.analyze()

    # Should have high scores
    assert result.technical_score >= 80
    assert result.content_score >= 80
    assert result.mobile_score >= 80

    # Should have no critical issues
    critical_issues = [i for i in result.issues if i.severity == "CRITICAL"]
    assert len(critical_issues) == 0


def test_analyzer_with_vitals():
    """Test analyzer incorporating Core Web Vitals data."""
    html = """
    <html>
        <head><title>Test</title></head>
        <body><h1>Test</h1></body>
    </html>
    """

    vitals = PageVitals(
        url="https://example.com",
        lcp=2.0,  # Good
        cls=0.05,  # Good
        inp=150,   # Good
        measured_at=datetime.now(),
        status="success"
    )

    analyzer = SEOAnalyzer("https://example.com", html, 200, vitals)
    result = analyzer.analyze()

    # Performance score should be high with good vitals
    assert result.performance_score >= 90


def test_analyzer_bad_heading_structure():
    """Test detection of bad heading hierarchy."""
    html = """
    <html>
        <head><title>Test</title></head>
        <body>
            <h2>Subheading without H1</h2>
            <h1>Main heading comes after</h1>
            <h4>Skipped H3</h4>
        </body>
    </html>
    """

    analyzer = SEOAnalyzer("https://example.com", html, 200, None)
    result = analyzer.analyze()

    heading_issues = [i for i in result.issues if "heading" in i.check.lower()]
    assert len(heading_issues) > 0


def test_analyzer_missing_alt_text():
    """Test detection of images without alt text."""
    html = """
    <html>
        <head><title>Test</title></head>
        <body>
            <h1>Test</h1>
            <img src="test.jpg">
            <img src="test2.jpg" alt="">
        </body>
    </html>
    """

    analyzer = SEOAnalyzer("https://example.com", html, 200, None)
    result = analyzer.analyze()

    alt_issues = [i for i in result.issues if "alt" in i.check.lower()]
    assert len(alt_issues) > 0
