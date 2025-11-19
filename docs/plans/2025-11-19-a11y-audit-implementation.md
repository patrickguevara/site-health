# Accessibility Audit Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add WCAG compliance checking to site-health with configurable levels, severity-based scoring, and static HTML analysis

**Architecture:** Follow SEO analyzer pattern with A11yChecker (static HTML checks), A11yAuditor (orchestration/scoring), and integration into existing crawler/report/database infrastructure

**Tech Stack:** BeautifulSoup (HTML parsing), aiosqlite (storage), existing typer CLI, Jinja2 templates

---

## Task 1: Data Models for A11y Results

**Files:**
- Modify: `site_health/models.py:106` (after SEOResult class)
- Test: `tests/test_a11y_models.py` (new file)

### Step 1: Write the failing test for A11yViolation model

Create: `tests/test_a11y_models.py`

```python
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
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_a11y_models.py::test_a11y_violation_creation -v`

Expected: FAIL with "cannot import name 'A11yViolation'"

### Step 3: Write minimal A11yViolation model

Modify `site_health/models.py` - add after SEOResult class (around line 106):

```python
@dataclass
class A11yViolation:
    """A single accessibility violation found during analysis."""

    severity: str  # "critical", "serious", "moderate", "minor"
    category: str  # "images_media", "forms_inputs", "navigation_links", "structure_semantics", "color_contrast", "aria_dynamic"
    wcag_criterion: str  # e.g., "1.1.1", "2.4.4"
    check: str  # Specific check identifier (e.g., "missing_alt_text")
    message: str  # Human-readable description
    element: str | None = None  # HTML element that triggered violation
    suggested_fix: str | None = None  # Recommended remediation


@dataclass
class A11yResult:
    """Accessibility analysis result for a single page."""

    url: str
    overall_score: float  # 0-100
    wcag_level_achieved: str  # "A", "AA", "AAA", or "None"
    images_media_score: float
    forms_inputs_score: float
    navigation_links_score: float
    structure_semantics_score: float
    color_contrast_score: float  # Only with browser checks
    aria_dynamic_score: float  # Only with browser checks
    violations: list[A11yViolation]
    timestamp: datetime
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_a11y_models.py::test_a11y_violation_creation -v`

Expected: PASS

### Step 5: Write test for A11yResult model

Add to `tests/test_a11y_models.py`:

```python
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
```

### Step 6: Run test to verify it passes

Run: `pytest tests/test_a11y_models.py::test_a11y_result_creation -v`

Expected: PASS

### Step 7: Commit

```bash
git add site_health/models.py tests/test_a11y_models.py
git commit -m "feat(a11y): add A11yViolation and A11yResult models"
```

---

## Task 2: A11yChecker - Images & Media Checks

**Files:**
- Create: `site_health/a11y.py`
- Test: `tests/test_a11y.py` (new file)

### Step 1: Write failing test for missing alt text check

Create: `tests/test_a11y.py`

```python
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
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_a11y.py::test_missing_alt_text_detection -v`

Expected: FAIL with "cannot import name 'A11yChecker'"

### Step 3: Write minimal A11yChecker implementation

Create: `site_health/a11y.py`

```python
"""Accessibility analyzer for web pages."""

from bs4 import BeautifulSoup
from site_health.models import A11yViolation


class A11yChecker:
    """Static HTML accessibility checker."""

    def __init__(self, html: str):
        """
        Initialize checker with HTML content.

        Args:
            html: HTML content to analyze
        """
        self.html = html
        self.soup = BeautifulSoup(html, 'html.parser')

    def check_images_alt_text(self) -> list[A11yViolation]:
        """
        Check for images without alt attributes (WCAG 1.1.1 Level A).

        Returns:
            List of violations found
        """
        violations = []

        for img in self.soup.find_all('img'):
            if not img.has_attr('alt'):
                violations.append(A11yViolation(
                    severity="critical",
                    category="images_media",
                    wcag_criterion="1.1.1",
                    check="missing_alt_text",
                    message="Image is missing alt attribute",
                    element=str(img),
                    suggested_fix="Add alt attribute describing the image content"
                ))

        return violations
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_a11y.py::test_missing_alt_text_detection -v`

Expected: PASS

### Step 5: Write test for suspicious alt text (moderate issue)

Add to `tests/test_a11y.py`:

```python
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
```

### Step 6: Run test to verify it fails

Run: `pytest tests/test_a11y.py::test_suspicious_alt_text_detection -v`

Expected: FAIL with "A11yChecker has no attribute 'check_suspicious_alt_text'"

### Step 7: Implement suspicious alt text check

Add to `site_health/a11y.py` in A11yChecker class:

```python
def check_suspicious_alt_text(self) -> list[A11yViolation]:
    """
    Check for images with suspicious or empty alt text.

    Returns:
        List of violations found
    """
    violations = []
    suspicious_patterns = ['image', 'img', 'picture', 'pic', 'photo', 'graphic']

    for img in self.soup.find_all('img'):
        alt = img.get('alt', '')

        # Empty alt on what might not be decorative
        if alt == '' and img.has_attr('alt'):
            violations.append(A11yViolation(
                severity="moderate",
                category="images_media",
                wcag_criterion="1.1.1",
                check="suspicious_alt_text",
                message="Image has empty alt attribute - verify it's decorative",
                element=str(img),
                suggested_fix="If not decorative, add descriptive alt text"
            ))
        # Generic alt text
        elif alt.lower().strip() in suspicious_patterns:
            violations.append(A11yViolation(
                severity="moderate",
                category="images_media",
                wcag_criterion="1.1.1",
                check="suspicious_alt_text",
                message=f"Image has generic alt text: '{alt}'",
                element=str(img),
                suggested_fix="Use more descriptive alt text"
            ))

    return violations
```

### Step 8: Run test to verify it passes

Run: `pytest tests/test_a11y.py::test_suspicious_alt_text_detection -v`

Expected: PASS

### Step 9: Commit

```bash
git add site_health/a11y.py tests/test_a11y.py
git commit -m "feat(a11y): add image alt text checks"
```

---

## Task 3: A11yChecker - Form & Input Checks

**Files:**
- Modify: `site_health/a11y.py:45` (add methods to A11yChecker)
- Test: `tests/test_a11y.py`

### Step 1: Write failing test for inputs without labels

Add to `tests/test_a11y.py`:

```python
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
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_a11y.py::test_form_inputs_without_labels -v`

Expected: FAIL with "no attribute 'check_form_labels'"

### Step 3: Implement form labels check

Add to `site_health/a11y.py` in A11yChecker class:

```python
def check_form_labels(self) -> list[A11yViolation]:
    """
    Check for form inputs without labels (WCAG 1.3.1, 4.1.2 Level A).

    Returns:
        List of violations found
    """
    violations = []

    for input_elem in self.soup.find_all(['input', 'select', 'textarea']):
        # Skip hidden and submit/button types
        input_type = input_elem.get('type', 'text')
        if input_type in ['hidden', 'submit', 'button', 'reset']:
            continue

        has_label = False

        # Check for aria-label or aria-labelledby
        if input_elem.has_attr('aria-label') or input_elem.has_attr('aria-labelledby'):
            has_label = True

        # Check for associated <label>
        if input_elem.has_attr('id'):
            label = self.soup.find('label', attrs={'for': input_elem['id']})
            if label:
                has_label = True

        # Check if wrapped in label
        if input_elem.parent and input_elem.parent.name == 'label':
            has_label = True

        if not has_label:
            violations.append(A11yViolation(
                severity="critical",
                category="forms_inputs",
                wcag_criterion="1.3.1",
                check="input_without_label",
                message=f"Form {input_elem.name} without associated label",
                element=str(input_elem),
                suggested_fix="Add <label> element or aria-label attribute"
            ))

    return violations
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_a11y.py::test_form_inputs_without_labels -v`

Expected: PASS

### Step 5: Write test for empty buttons

Add to `tests/test_a11y.py`:

```python
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
```

### Step 6: Run test to verify it fails

Run: `pytest tests/test_a11y.py::test_empty_buttons_detection -v`

Expected: FAIL with "no attribute 'check_empty_buttons'"

### Step 7: Implement empty buttons check

Add to `site_health/a11y.py` in A11yChecker class:

```python
def check_empty_buttons(self) -> list[A11yViolation]:
    """
    Check for buttons without text content or labels (WCAG 4.1.2 Level A).

    Returns:
        List of violations found
    """
    violations = []

    for button in self.soup.find_all('button'):
        # Check for aria-label or aria-labelledby
        if button.has_attr('aria-label') or button.has_attr('aria-labelledby'):
            continue

        # Check for text content (strips whitespace)
        text_content = button.get_text(strip=True)
        if text_content:
            continue

        # Check for meaningful alt text in child images
        has_meaningful_content = False
        for img in button.find_all('img'):
            if img.has_attr('alt') and img['alt'].strip():
                has_meaningful_content = True
                break

        if not has_meaningful_content:
            violations.append(A11yViolation(
                severity="serious",
                category="forms_inputs",
                wcag_criterion="4.1.2",
                check="empty_button",
                message="Button has no accessible text or label",
                element=str(button),
                suggested_fix="Add text content or aria-label attribute"
            ))

    return violations
```

### Step 8: Run test to verify it passes

Run: `pytest tests/test_a11y.py::test_empty_buttons_detection -v`

Expected: PASS

### Step 9: Commit

```bash
git add site_health/a11y.py tests/test_a11y.py
git commit -m "feat(a11y): add form and button label checks"
```

---

## Task 4: A11yChecker - Link & Navigation Checks

**Files:**
- Modify: `site_health/a11y.py` (add methods to A11yChecker)
- Test: `tests/test_a11y.py`

### Step 1: Write failing test for empty links

Add to `tests/test_a11y.py`:

```python
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
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_a11y.py::test_empty_links_detection -v`

Expected: FAIL

### Step 3: Implement empty links check

Add to `site_health/a11y.py`:

```python
def check_empty_links(self) -> list[A11yViolation]:
    """
    Check for links without text content or labels (WCAG 2.4.4 Level A).

    Returns:
        List of violations found
    """
    violations = []

    for link in self.soup.find_all('a'):
        # Skip if has aria-label or aria-labelledby
        if link.has_attr('aria-label') or link.has_attr('aria-labelledby'):
            continue

        # Check for text content
        text_content = link.get_text(strip=True)
        if text_content:
            continue

        # Check for meaningful alt text in child images
        has_meaningful_content = False
        for img in link.find_all('img'):
            if img.has_attr('alt') and img['alt'].strip():
                has_meaningful_content = True
                break

        if not has_meaningful_content:
            violations.append(A11yViolation(
                severity="critical",
                category="navigation_links",
                wcag_criterion="2.4.4",
                check="empty_link",
                message="Link has no accessible text or label",
                element=str(link)[:100],
                suggested_fix="Add descriptive link text or aria-label"
            ))

    return violations
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_a11y.py::test_empty_links_detection -v`

Expected: PASS

### Step 5: Write test for generic link text

Add to `tests/test_a11y.py`:

```python
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
```

### Step 6: Run test to verify it fails

Run: `pytest tests/test_a11y.py::test_generic_link_text_detection -v`

Expected: FAIL

### Step 7: Implement generic link text check

Add to `site_health/a11y.py`:

```python
def check_generic_link_text(self) -> list[A11yViolation]:
    """
    Check for links with generic or unhelpful text.

    Returns:
        List of violations found
    """
    violations = []
    generic_patterns = [
        'click here', 'click', 'here', 'more', 'read more',
        'link', 'this', 'continue', 'go'
    ]

    for link in self.soup.find_all('a'):
        text = link.get_text(strip=True).lower()

        if text in generic_patterns:
            violations.append(A11yViolation(
                severity="moderate",
                category="navigation_links",
                wcag_criterion="2.4.4",
                check="generic_link_text",
                message=f"Link has generic text: '{text}'",
                element=str(link)[:100],
                suggested_fix="Use descriptive text that makes sense out of context"
            ))

    return violations
```

### Step 8: Run test to verify it passes

Run: `pytest tests/test_a11y.py::test_generic_link_text_detection -v`

Expected: PASS

### Step 9: Commit

```bash
git add site_health/a11y.py tests/test_a11y.py
git commit -m "feat(a11y): add link and navigation checks"
```

---

## Task 5: A11yChecker - Structure & Semantics Checks

**Files:**
- Modify: `site_health/a11y.py`
- Test: `tests/test_a11y.py`

### Step 1: Write failing test for missing page title

Add to `tests/test_a11y.py`:

```python
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
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_a11y.py::test_missing_page_title -v`

Expected: FAIL

### Step 3: Implement page structure checks

Add to `site_health/a11y.py`:

```python
def check_page_structure(self) -> list[A11yViolation]:
    """
    Check basic page structure (title, lang, headings).

    Returns:
        List of violations found
    """
    violations = []

    # Check for title tag
    title = self.soup.find('title')
    if not title or not title.string or not title.string.strip():
        violations.append(A11yViolation(
            severity="critical",
            category="structure_semantics",
            wcag_criterion="2.4.2",
            check="missing_title",
            message="Page is missing a title element",
            element="<head>",
            suggested_fix="Add <title> element with descriptive page title"
        ))

    # Check for lang attribute
    html_tag = self.soup.find('html')
    if not html_tag or not html_tag.has_attr('lang'):
        violations.append(A11yViolation(
            severity="critical",
            category="structure_semantics",
            wcag_criterion="3.1.1",
            check="missing_lang",
            message="HTML element missing lang attribute",
            element=str(html_tag)[:100] if html_tag else "<html>",
            suggested_fix="Add lang attribute (e.g., lang='en')"
        ))

    # Check for duplicate IDs
    ids_seen = {}
    for elem in self.soup.find_all(id=True):
        elem_id = elem.get('id')
        if elem_id in ids_seen:
            violations.append(A11yViolation(
                severity="critical",
                category="structure_semantics",
                wcag_criterion="4.1.1",
                check="duplicate_id",
                message=f"Duplicate ID found: '{elem_id}'",
                element=str(elem)[:100],
                suggested_fix="Ensure all IDs are unique on the page"
            ))
        else:
            ids_seen[elem_id] = True

    return violations
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_a11y.py::test_missing_page_title -v`

Expected: PASS

### Step 5: Write test for heading structure

Add to `tests/test_a11y.py`:

```python
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
```

### Step 6: Run test to verify it fails

Run: `pytest tests/test_a11y.py::test_heading_structure -v`

Expected: FAIL

### Step 7: Implement heading structure check

Add to `site_health/a11y.py`:

```python
def check_heading_structure(self) -> list[A11yViolation]:
    """
    Check for proper heading hierarchy (WCAG 1.3.1 Level A).

    Returns:
        List of violations found
    """
    violations = []

    headings = self.soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
    if not headings:
        return violations

    prev_level = 0
    for heading in headings:
        level = int(heading.name[1])

        # Check if we skipped levels (e.g., h1 -> h3)
        if prev_level > 0 and level > prev_level + 1:
            violations.append(A11yViolation(
                severity="serious",
                category="structure_semantics",
                wcag_criterion="1.3.1",
                check="skipped_heading_level",
                message=f"Heading level skipped from h{prev_level} to h{level}",
                element=str(heading),
                suggested_fix=f"Use h{prev_level + 1} instead of h{level}"
            ))

        prev_level = level

    return violations
```

### Step 8: Run test to verify it passes

Run: `pytest tests/test_a11y.py::test_heading_structure -v`

Expected: PASS

### Step 9: Commit

```bash
git add site_health/a11y.py tests/test_a11y.py
git commit -m "feat(a11y): add page structure and heading checks"
```

---

## Task 6: A11yAuditor - Scoring System

**Files:**
- Modify: `site_health/a11y.py` (add A11yAuditor class)
- Test: `tests/test_a11y_auditor.py` (new file)

### Step 1: Write failing test for score calculation

Create: `tests/test_a11y_auditor.py`

```python
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
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_a11y_auditor.py -v`

Expected: FAIL with "cannot import name 'A11yAuditor'"

### Step 3: Implement A11yAuditor with scoring

Add to `site_health/a11y.py`:

```python
from datetime import datetime
from site_health.models import A11yResult


class A11yAuditor:
    """Orchestrates accessibility checks and scoring."""

    # Severity penalties
    SEVERITY_PENALTIES = {
        "critical": 10,
        "serious": 5,
        "moderate": 2,
        "minor": 1,
    }

    def __init__(self, url: str, html: str):
        """
        Initialize auditor.

        Args:
            url: Page URL
            html: HTML content
        """
        self.url = url
        self.html = html
        self.checker = A11yChecker(html)

    def calculate_score(self, violations: list[A11yViolation]) -> float:
        """
        Calculate overall accessibility score.

        Args:
            violations: List of violations

        Returns:
            Score from 0-100
        """
        penalty = sum(
            self.SEVERITY_PENALTIES.get(v.severity, 0)
            for v in violations
        )

        return max(0.0, 100.0 - penalty)
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_a11y_auditor.py -v`

Expected: PASS

### Step 5: Write test for WCAG level determination

Add to `tests/test_a11y_auditor.py`:

```python
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
```

### Step 6: Run test to verify it fails

Run: `pytest tests/test_a11y_auditor.py::test_wcag_level_determination -v`

Expected: FAIL

### Step 7: Implement WCAG level determination

Add to A11yAuditor class in `site_health/a11y.py`:

```python
def determine_wcag_level(
    self,
    violations: list[A11yViolation],
    score: float
) -> str:
    """
    Determine WCAG conformance level achieved.

    Args:
        violations: List of violations
        score: Overall score

    Returns:
        "AAA", "AA", "A", or "None"
    """
    has_critical = any(v.severity == "critical" for v in violations)
    has_serious = any(v.severity == "serious" for v in violations)

    if has_critical:
        return "None"

    if has_serious:
        return "A"

    # No critical or serious violations
    if score >= 95.0:
        return "AAA"
    else:
        return "AA"
```

### Step 8: Run test to verify it passes

Run: `pytest tests/test_a11y_auditor.py::test_wcag_level_determination -v`

Expected: PASS

### Step 9: Commit

```bash
git add site_health/a11y.py tests/test_a11y_auditor.py
git commit -m "feat(a11y): add auditor with scoring and WCAG level logic"
```

---

## Task 7: A11yAuditor - Full Analysis

**Files:**
- Modify: `site_health/a11y.py` (add analyze method)
- Test: `tests/test_a11y_auditor.py`

### Step 1: Write failing test for full analysis

Add to `tests/test_a11y_auditor.py`:

```python
def test_full_analysis():
    """Test complete a11y analysis."""
    html = """
    <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Main Title</h1>
            <img src="logo.png">
            <form>
                <input type="text" name="username">
            </form>
            <a href="/page1"></a>
        </body>
    </html>
    """

    auditor = A11yAuditor("https://example.com", html)
    result = auditor.analyze()

    assert result.url == "https://example.com"
    assert result.overall_score < 100  # Has violations
    assert len(result.violations) > 0
    assert result.wcag_level_achieved in ["None", "A", "AA", "AAA"]

    # Should have critical violations (missing alt, no label, empty link)
    critical_violations = [v for v in result.violations if v.severity == "critical"]
    assert len(critical_violations) >= 3
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_a11y_auditor.py::test_full_analysis -v`

Expected: FAIL with "no attribute 'analyze'"

### Step 3: Implement analyze method

Add to A11yAuditor class in `site_health/a11y.py`:

```python
def analyze(self) -> A11yResult:
    """
    Run complete accessibility analysis.

    Returns:
        A11yResult with scores and violations
    """
    # Collect all violations
    all_violations = []

    # Images & Media checks
    all_violations.extend(self.checker.check_images_alt_text())
    all_violations.extend(self.checker.check_suspicious_alt_text())

    # Forms & Inputs checks
    all_violations.extend(self.checker.check_form_labels())
    all_violations.extend(self.checker.check_empty_buttons())

    # Navigation & Links checks
    all_violations.extend(self.checker.check_empty_links())
    all_violations.extend(self.checker.check_generic_link_text())

    # Structure & Semantics checks
    all_violations.extend(self.checker.check_page_structure())
    all_violations.extend(self.checker.check_heading_structure())

    # Calculate scores by category
    category_scores = self._calculate_category_scores(all_violations)

    # Calculate overall score
    overall_score = self.calculate_score(all_violations)

    # Determine WCAG level
    wcag_level = self.determine_wcag_level(all_violations, overall_score)

    return A11yResult(
        url=self.url,
        overall_score=overall_score,
        wcag_level_achieved=wcag_level,
        images_media_score=category_scores["images_media"],
        forms_inputs_score=category_scores["forms_inputs"],
        navigation_links_score=category_scores["navigation_links"],
        structure_semantics_score=category_scores["structure_semantics"],
        color_contrast_score=100.0,  # No browser checks yet
        aria_dynamic_score=100.0,  # No browser checks yet
        violations=sorted(
            all_violations,
            key=lambda x: {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}[x.severity]
        ),
        timestamp=datetime.now()
    )


def _calculate_category_scores(
    self,
    violations: list[A11yViolation]
) -> dict[str, float]:
    """Calculate scores for each category."""
    categories = [
        "images_media",
        "forms_inputs",
        "navigation_links",
        "structure_semantics",
        "color_contrast",
        "aria_dynamic"
    ]

    scores = {}
    for category in categories:
        category_violations = [v for v in violations if v.category == category]
        penalty = sum(
            self.SEVERITY_PENALTIES.get(v.severity, 0)
            for v in category_violations
        )
        scores[category] = max(0.0, 100.0 - penalty)

    return scores
```

### Step 4: Run test to verify it passes

Run: `pytest tests/test_a11y_auditor.py::test_full_analysis -v`

Expected: PASS

### Step 5: Run all a11y tests

Run: `pytest tests/test_a11y*.py -v`

Expected: All tests PASS

### Step 6: Commit

```bash
git add site_health/a11y.py tests/test_a11y_auditor.py
git commit -m "feat(a11y): implement full analysis with category scoring"
```

---

## Task 8: Configuration Support

**Files:**
- Modify: `site_health/config.py:20` (add a11y fields)
- Test: `tests/test_config.py`

### Step 1: Write failing test for a11y config

Add to `tests/test_config.py`:

```python
def test_config_with_a11y_options():
    """Test configuration with a11y audit options."""
    config = Config(
        url="https://example.com",
        run_a11y_audit=True,
        a11y_level="AA",
        a11y_use_browser=False
    )

    assert config.run_a11y_audit is True
    assert config.a11y_level == "AA"
    assert config.a11y_use_browser is False


def test_a11y_config_from_yaml(tmp_path):
    """Test loading a11y config from YAML."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
url: https://example.com
run_a11y_audit: true
a11y_level: "AAA"
a11y_use_browser: true
""")

    config = Config.from_yaml(str(config_file))

    assert config.run_a11y_audit is True
    assert config.a11y_level == "AAA"
    assert config.a11y_use_browser is True
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_config.py::test_config_with_a11y_options -v`

Expected: FAIL with "unexpected keyword argument"

### Step 3: Add a11y fields to Config

Modify `site_health/config.py` Config class:

```python
@dataclass
class Config:
    """Configuration for site health crawler."""

    url: Optional[str] = None
    depth: int = 2
    max_concurrent: int = 10
    timeout: float = 10.0
    respect_robots: bool = True
    output_format: str = "terminal"
    output_path: Optional[str] = None
    run_a11y_audit: bool = False
    a11y_level: str = "AA"  # "A", "AA", or "AAA"
    a11y_use_browser: bool = False
```

### Step 4: Update merge_with_args method

Modify the `merge_with_args` method in `site_health/config.py`:

```python
def merge_with_args(self, **kwargs) -> 'Config':
    """Create new config by merging with command-line arguments.

    Command-line arguments override config file values.
    """
    # Start with current config values
    merged = {
        'url': self.url,
        'depth': self.depth,
        'max_concurrent': self.max_concurrent,
        'timeout': self.timeout,
        'respect_robots': self.respect_robots,
        'output_format': self.output_format,
        'output_path': self.output_path,
        'run_a11y_audit': self.run_a11y_audit,
        'a11y_level': self.a11y_level,
        'a11y_use_browser': self.a11y_use_browser,
    }

    # Override with any non-None kwargs
    for key, value in kwargs.items():
        if value is not None:
            merged[key] = value

    return Config(**merged)
```

### Step 5: Run tests to verify they pass

Run: `pytest tests/test_config.py -v`

Expected: PASS

### Step 6: Commit

```bash
git add site_health/config.py tests/test_config.py
git commit -m "feat(a11y): add configuration support for a11y options"
```

---

## Task 9: CLI Integration

**Files:**
- Modify: `site_health/cli.py:26-28` (add a11y options)
- Modify: `site_health/cli.py:139-173` (add a11y analysis)
- Test: `tests/test_cli.py`

### Step 1: Write failing test for CLI a11y flags

Add to `tests/test_cli.py`:

```python
def test_cli_with_a11y_flag():
    """Test CLI accepts --a11y flag."""
    from typer.testing import CliRunner
    from site_health.cli import app

    runner = CliRunner()

    # This will fail to crawl but should accept the flag
    result = runner.invoke(app, [
        "crawl",
        "https://example.com",
        "--a11y",
        "--a11y-level", "AA"
    ])

    # Should not fail due to unrecognized arguments
    assert "--a11y" not in result.stdout or "Error" not in result.stdout
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_cli.py::test_cli_with_a11y_flag -v`

Expected: FAIL (or test may be too simple, adjust as needed)

### Step 3: Add --a11y CLI options

Modify `site_health/cli.py` crawl command signature (around line 16-28):

```python
@app.command()
def crawl(
    url: Optional[str] = typer.Argument(None, help="URL to crawl"),
    depth: Optional[int] = typer.Option(None, "--depth", "-d", help="Maximum crawl depth"),
    format: Optional[str] = typer.Option(None, "--format", "-f", help="Output format (terminal/html/json)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    config_file: Optional[str] = typer.Option(None, "--config", "-c", help="Config file path"),
    max_concurrent: Optional[int] = typer.Option(None, "--max-concurrent", help="Max concurrent requests"),
    timeout: Optional[float] = typer.Option(None, "--timeout", help="Request timeout in seconds"),
    no_robots: bool = typer.Option(False, "--no-robots", help="Ignore robots.txt"),
    vitals: bool = typer.Option(False, "--vitals", help="Measure Core Web Vitals (10% sample)"),
    seo: bool = typer.Option(False, "--seo", help="Run SEO audit on crawled pages"),
    a11y: bool = typer.Option(False, "--a11y", help="Run accessibility audit on crawled pages"),
    a11y_level: str = typer.Option("AA", "--a11y-level", help="WCAG level to target (A, AA, AAA)"),
    a11y_use_browser: bool = typer.Option(False, "--a11y-use-browser", help="Use browser for advanced a11y checks"),
    db_path: str = typer.Option("site_health.db", "--db", help="Database path"),
):
```

### Step 4: Update _crawl_async function signature

Modify `site_health/cli.py` _crawl_async (around line 31-43):

```python
"""Crawl a website and check for broken links."""
asyncio.run(_crawl_async(
    url=url,
    depth=depth,
    format=format,
    output=output,
    config_file=config_file,
    max_concurrent=max_concurrent,
    timeout=timeout,
    no_robots=no_robots,
    vitals=vitals,
    seo=seo,
    a11y=a11y,
    a11y_level=a11y_level,
    a11y_use_browser=a11y_use_browser,
    db_path=db_path,
))
```

And update the async function definition (around line 46):

```python
async def _crawl_async(
    url: Optional[str],
    depth: Optional[int],
    format: Optional[str],
    output: Optional[str],
    config_file: Optional[str],
    max_concurrent: Optional[int],
    timeout: Optional[float],
    no_robots: bool,
    vitals: bool,
    seo: bool,
    a11y: bool,
    a11y_level: str,
    a11y_use_browser: bool,
    db_path: str,
):
```

### Step 5: Add a11y analysis logic after SEO section

Add after the SEO analysis block (around line 173) in `site_health/cli.py`:

```python
# Run A11y analysis if requested
if a11y:
    typer.echo("\nRunning accessibility analysis...")
    from site_health.a11y import A11yAuditor
    import httpx

    # Get pages to analyze
    pages_to_analyze = crawler.get_pages_for_seo_analysis()  # Reuse same logic
    typer.echo(f"Analyzing {len(pages_to_analyze)} pages...")

    # Analyze each page
    a11y_count = 0
    async with httpx.AsyncClient(timeout=crawler.timeout) as client:
        for url in pages_to_analyze:
            try:
                response = await client.get(url)
                if response.status_code == 200 and 'text/html' in response.headers.get('content-type', ''):
                    auditor = A11yAuditor(
                        url=url,
                        html=response.text
                    )
                    a11y_result = auditor.analyze()
                    await db.save_a11y_result(crawl_id, a11y_result)
                    a11y_count += 1
            except Exception as e:
                typer.echo(f"Warning: Failed to analyze {url}: {e}", err=True)

    typer.echo(f"✓ Completed accessibility analysis of {a11y_count} pages")
```

### Step 6: Run test to verify CLI accepts flags

Run: `pytest tests/test_cli.py -v` (or manual test: `site-health crawl --help`)

Expected: Should see --a11y flags in help

### Step 7: Commit

```bash
git add site_health/cli.py tests/test_cli.py
git commit -m "feat(a11y): add CLI options for accessibility audit"
```

---

## Task 10: Database Schema & Storage

**Files:**
- Modify: `site_health/database.py:99` (add a11y table in initialize)
- Modify: `site_health/database.py:405` (add save/get methods)
- Test: `tests/test_database_a11y.py` (new file)

### Step 1: Write failing test for a11y database storage

Create: `tests/test_database_a11y.py`

```python
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
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_database_a11y.py -v`

Expected: FAIL with "no attribute 'save_a11y_result'"

### Step 3: Add a11y_results table to schema

Modify `site_health/database.py` initialize method (after seo_results table, around line 99):

```python
await conn.execute("""
    CREATE TABLE IF NOT EXISTS a11y_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crawl_id INTEGER NOT NULL,
        url TEXT NOT NULL,
        overall_score REAL,
        wcag_level_achieved TEXT,
        images_media_score REAL,
        forms_inputs_score REAL,
        navigation_links_score REAL,
        structure_semantics_score REAL,
        color_contrast_score REAL,
        aria_dynamic_score REAL,
        violations TEXT,
        timestamp TIMESTAMP NOT NULL,
        FOREIGN KEY (crawl_id) REFERENCES crawls(id)
    )
""")

await conn.execute("""
    CREATE INDEX IF NOT EXISTS idx_a11y_crawl_id
    ON a11y_results(crawl_id)
""")
```

### Step 4: Implement save_a11y_result method

Add to Database class in `site_health/database.py` (after get_seo_results, around line 405):

```python
async def save_a11y_result(self, crawl_id: int, result: A11yResult):
    """Save accessibility analysis result for a page."""
    import json

    # Serialize violations to JSON
    violations_json = json.dumps([
        {
            "severity": v.severity,
            "category": v.category,
            "wcag_criterion": v.wcag_criterion,
            "check": v.check,
            "message": v.message,
            "element": v.element,
            "suggested_fix": v.suggested_fix
        }
        for v in result.violations
    ])

    async with aiosqlite.connect(self.db_path) as conn:
        await conn.execute(
            """
            INSERT INTO a11y_results
            (crawl_id, url, overall_score, wcag_level_achieved,
             images_media_score, forms_inputs_score, navigation_links_score,
             structure_semantics_score, color_contrast_score, aria_dynamic_score,
             violations, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                crawl_id,
                result.url,
                result.overall_score,
                result.wcag_level_achieved,
                result.images_media_score,
                result.forms_inputs_score,
                result.navigation_links_score,
                result.structure_semantics_score,
                result.color_contrast_score,
                result.aria_dynamic_score,
                violations_json,
                result.timestamp
            )
        )
        await conn.commit()


async def get_a11y_results(self, crawl_id: int) -> list[A11yResult]:
    """Get all accessibility results for a crawl."""
    import json

    async with aiosqlite.connect(self.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            """
            SELECT * FROM a11y_results
            WHERE crawl_id = ?
            ORDER BY timestamp
            """,
            (crawl_id,)
        )
        rows = await cursor.fetchall()

        results = []
        for row in rows:
            # Deserialize violations from JSON
            violations_data = json.loads(row["violations"])
            violations = [
                A11yViolation(
                    severity=v["severity"],
                    category=v["category"],
                    wcag_criterion=v["wcag_criterion"],
                    check=v["check"],
                    message=v["message"],
                    element=v.get("element"),
                    suggested_fix=v.get("suggested_fix")
                )
                for v in violations_data
            ]

            results.append(A11yResult(
                url=row["url"],
                overall_score=row["overall_score"],
                wcag_level_achieved=row["wcag_level_achieved"],
                images_media_score=row["images_media_score"],
                forms_inputs_score=row["forms_inputs_score"],
                navigation_links_score=row["navigation_links_score"],
                structure_semantics_score=row["structure_semantics_score"],
                color_contrast_score=row["color_contrast_score"],
                aria_dynamic_score=row["aria_dynamic_score"],
                violations=violations,
                timestamp=datetime.fromisoformat(row["timestamp"])
            ))

        return results
```

Import A11yResult and A11yViolation at top of database.py:

```python
from site_health.models import LinkResult, CrawlSummary, PageVitals, SEOResult, SEOIssue, A11yResult, A11yViolation
```

### Step 5: Run test to verify it passes

Run: `pytest tests/test_database_a11y.py -v`

Expected: PASS

### Step 6: Commit

```bash
git add site_health/database.py tests/test_database_a11y.py
git commit -m "feat(a11y): add database schema and storage for a11y results"
```

---

## Task 11: Report Integration - Terminal Output

**Files:**
- Modify: `site_health/report.py` (add a11y terminal section)
- Test: `tests/test_report_a11y.py` (new file)

### Step 1: Write failing test for a11y terminal report

Create: `tests/test_report_a11y.py`

```python
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
    assert "WCAG Level: A" in report
    assert "Critical: 1" in report
    assert "Serious: 1" in report
    assert "Moderate: 1" in report
```

### Step 2: Run test to verify it fails

Run: `pytest tests/test_report_a11y.py -v`

Expected: FAIL (a11y section not in report)

### Step 3: Find and read the report.py structure

Run: `pytest tests/test_report.py -v` first to ensure existing tests still pass

Read: Look for where SEO section is added in report.py

### Step 4: Add a11y terminal report section

Modify `site_health/report.py` - find the _generate_terminal method and add a11y section similar to SEO:

```python
# Add after SEO section in _generate_terminal method

# A11y Audit section
a11y_results = await self.db.get_a11y_results(self.crawl_id)
if a11y_results:
    output.append("\n" + "=" * 50)
    output.append("=== Accessibility Audit ===")
    output.append("=" * 50)

    # Calculate aggregate stats
    total_score = sum(r.overall_score for r in a11y_results) / len(a11y_results)
    all_violations = [v for r in a11y_results for v in r.violations]

    violations_by_severity = {
        "critical": sum(1 for v in all_violations if v.severity == "critical"),
        "serious": sum(1 for v in all_violations if v.severity == "serious"),
        "moderate": sum(1 for v in all_violations if v.severity == "moderate"),
        "minor": sum(1 for v in all_violations if v.severity == "minor"),
    }

    # Determine overall WCAG level
    has_critical = violations_by_severity["critical"] > 0
    has_serious = violations_by_severity["serious"] > 0

    if has_critical:
        wcag_level = "None"
        wcag_status = "(Level A not achieved)"
    elif has_serious:
        wcag_level = "A"
        wcag_status = "(Level AA not achieved)"
    elif total_score >= 95:
        wcag_level = "AAA"
        wcag_status = ""
    else:
        wcag_level = "AA"
        wcag_status = ""

    output.append(f"\nOverall Score: {total_score:.0f}/100")
    output.append(f"WCAG Level: {wcag_level} {wcag_status}")

    output.append("\nViolations by Severity:")
    output.append(f"  Critical: {violations_by_severity['critical']}")
    output.append(f"  Serious: {violations_by_severity['serious']}")
    output.append(f"  Moderate: {violations_by_severity['moderate']}")
    output.append(f"  Minor: {violations_by_severity['minor']}")

    # Top issues
    if all_violations:
        output.append("\nTop Issues:")
        # Group by check type
        issue_counts = {}
        for v in all_violations:
            key = (v.severity, v.message.split(':')[0] if ':' in v.message else v.message)
            issue_counts[key] = issue_counts.get(key, 0) + 1

        # Sort by severity then count
        severity_order = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}
        sorted_issues = sorted(
            issue_counts.items(),
            key=lambda x: (severity_order[x[0][0]], -x[1])
        )

        for (severity, msg), count in sorted_issues[:5]:
            output.append(f"  • {count} {msg} ({severity})")
```

### Step 5: Add import for A11yResult and A11yViolation

At top of `site_health/report.py`:

```python
from site_health.models import (
    LinkResult, CrawlSummary, PageVitals, SEOResult, SEOIssue,
    A11yResult, A11yViolation
)
```

### Step 6: Run test to verify it passes

Run: `pytest tests/test_report_a11y.py -v`

Expected: PASS

### Step 7: Commit

```bash
git add site_health/report.py tests/test_report_a11y.py
git commit -m "feat(a11y): add terminal report section for accessibility"
```

---

## Task 12: Documentation & Example Config

**Files:**
- Modify: `README.md` (add a11y features and examples)
- Modify: `config.example.yaml` (add a11y options)

### Step 1: Update README with a11y feature

Add to README.md Features section (around line 10):

```markdown
- **Accessibility Audit**: WCAG compliance checking with configurable levels (A, AA, AAA) and severity-based scoring
```

Add to Quick Start section (around line 50):

```markdown
# Crawl with accessibility audit
site-health crawl https://example.com --a11y

# Crawl with specific WCAG level
site-health crawl https://example.com --a11y --a11y-level AAA

# Comprehensive audit (SEO + A11y + Vitals)
site-health crawl https://example.com --seo --a11y --vitals
```

### Step 2: Update config.example.yaml

Add to `config.example.yaml`:

```yaml
# Accessibility audit
run_a11y_audit: false
a11y_level: "AA"  # A, AA, or AAA
a11y_use_browser: false  # Enable browser-based checks (requires --vitals)
```

### Step 3: Verify changes

Run: `cat README.md | grep -A 2 "Accessibility"`
Run: `cat config.example.yaml | grep -A 3 "Accessibility"`

Expected: See the new content

### Step 4: Commit

```bash
git add README.md config.example.yaml
git commit -m "docs: add accessibility audit feature to README and example config"
```

---

## Task 13: Integration Test - End to End

**Files:**
- Create: `tests/test_integration_a11y.py`

### Step 1: Write end-to-end integration test

Create: `tests/test_integration_a11y.py`

```python
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
```

### Step 2: Run integration test

Run: `pytest tests/test_integration_a11y.py -v`

Expected: PASS

### Step 3: Run all tests

Run: `pytest tests/ -v`

Expected: All tests PASS

### Step 4: Commit

```bash
git add tests/test_integration_a11y.py
git commit -m "test(a11y): add end-to-end integration tests"
```

---

## Task 14: Final Verification

**Files:**
- All previously created/modified files

### Step 1: Run full test suite

Run: `pytest tests/ -v --cov=site_health --cov-report=term-missing`

Expected: All tests PASS with good coverage on new a11y code

### Step 2: Run linter

Run: `ruff check site_health/a11y.py site_health/models.py site_health/database.py site_health/cli.py site_health/config.py`

Expected: No errors (or fix any that appear)

### Step 3: Manual CLI test

Run: `site-health crawl https://example.com --a11y --depth 1`

Expected: Should run successfully and show a11y section in output

### Step 4: Verify help text

Run: `site-health crawl --help`

Expected: Should show --a11y, --a11y-level, --a11y-use-browser options

### Step 5: Final commit if any fixes needed

```bash
git add .
git commit -m "chore(a11y): final verification and cleanup"
```

---

## Summary

This implementation plan delivers:

1. ✅ A11y data models (A11yViolation, A11yResult)
2. ✅ Static HTML checker with 8+ WCAG checks across 4 categories
3. ✅ Scoring system with severity-based penalties
4. ✅ WCAG level determination (A, AA, AAA)
5. ✅ Configuration support (config file + CLI flags)
6. ✅ CLI integration (--a11y, --a11y-level flags)
7. ✅ Database storage with full schema
8. ✅ Terminal report integration
9. ✅ Comprehensive test coverage
10. ✅ Documentation updates

**Not included (future enhancements):**
- Browser-based checks (axe-core integration)
- HTML/JSON report sections (can follow SEO pattern)
- Additional static checks (tables, fieldsets, ARIA landmarks)

**Estimated implementation time:** 4-6 hours for experienced developer following this plan step-by-step with TDD approach.
