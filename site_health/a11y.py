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
