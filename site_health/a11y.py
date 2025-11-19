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
