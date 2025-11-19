# site_health/seo_analyzer.py
"""SEO analysis engine for web pages."""

from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional
from site_health.models import SEOResult, SEOIssue, PageVitals


class SEOAnalyzer:
    """Analyzes a web page for SEO issues and generates scores."""

    # Category weights (must sum to 1.0)
    WEIGHTS = {
        "technical": 0.25,
        "content": 0.20,
        "performance": 0.30,
        "mobile": 0.15,
        "structured_data": 0.10,
    }

    def __init__(
        self,
        url: str,
        html: str,
        status_code: int,
        vitals: Optional[PageVitals] = None
    ):
        """
        Initialize analyzer with page data.

        Args:
            url: Page URL
            html: HTML content
            status_code: HTTP status code
            vitals: Optional Core Web Vitals data
        """
        self.url = url
        self.html = html
        self.status_code = status_code
        self.vitals = vitals
        self.soup = BeautifulSoup(html, 'html.parser')
        self.issues: list[SEOIssue] = []

    def analyze(self) -> SEOResult:
        """
        Run all SEO checks and return results.

        Returns:
            SEOResult with scores and issues
        """
        # Run category checks
        technical_score = self._check_technical()
        content_score = self._check_content()
        performance_score = self._check_performance()
        mobile_score = self._check_mobile()
        structured_data_score = self._check_structured_data()

        # Calculate weighted overall score
        overall_score = (
            technical_score * self.WEIGHTS["technical"] +
            content_score * self.WEIGHTS["content"] +
            performance_score * self.WEIGHTS["performance"] +
            mobile_score * self.WEIGHTS["mobile"] +
            structured_data_score * self.WEIGHTS["structured_data"]
        )

        return SEOResult(
            url=self.url,
            overall_score=round(overall_score, 1),
            technical_score=round(technical_score, 1),
            content_score=round(content_score, 1),
            performance_score=round(performance_score, 1),
            mobile_score=round(mobile_score, 1),
            structured_data_score=round(structured_data_score, 1),
            issues=sorted(
                self.issues,
                key=lambda x: {"CRITICAL": 0, "WARNING": 1, "INFO": 2}[x.severity]
            ),
            timestamp=datetime.now()
        )

    def _check_technical(self) -> float:
        """Check technical SEO factors. Returns score 0-100."""
        checks_passed = 0
        total_checks = 7

        # Title tag
        title = self.soup.find('title')
        if not title or not title.string:
            self.issues.append(SEOIssue(
                severity="CRITICAL",
                category="technical",
                check="missing_title",
                message="Page is missing a title tag"
            ))
        else:
            checks_passed += 1
            title_len = len(title.string)
            if title_len < 30 or title_len > 60:
                self.issues.append(SEOIssue(
                    severity="WARNING",
                    category="technical",
                    check="title_length",
                    message=f"Title length is {title_len} chars (optimal: 50-60)"
                ))

        # Meta description
        meta_desc = self.soup.find('meta', attrs={'name': 'description'})
        if not meta_desc or not meta_desc.get('content'):
            self.issues.append(SEOIssue(
                severity="WARNING",
                category="technical",
                check="missing_meta_description",
                message="Page is missing a meta description"
            ))
        else:
            checks_passed += 1
            desc_len = len(meta_desc['content'])
            if desc_len < 120 or desc_len > 160:
                self.issues.append(SEOIssue(
                    severity="INFO",
                    category="technical",
                    check="meta_description_length",
                    message=f"Meta description is {desc_len} chars (optimal: 150-160)"
                ))

        # Canonical URL
        canonical = self.soup.find('link', attrs={'rel': 'canonical'})
        if canonical:
            checks_passed += 1
        else:
            self.issues.append(SEOIssue(
                severity="INFO",
                category="technical",
                check="missing_canonical",
                message="Page lacks canonical URL"
            ))

        # Heading structure
        h1_tags = self.soup.find_all('h1')
        if len(h1_tags) == 0:
            self.issues.append(SEOIssue(
                severity="CRITICAL",
                category="technical",
                check="missing_h1",
                message="Page has no H1 tag"
            ))
        elif len(h1_tags) > 1:
            self.issues.append(SEOIssue(
                severity="WARNING",
                category="technical",
                check="multiple_h1",
                message=f"Page has {len(h1_tags)} H1 tags (should have 1)"
            ))
        else:
            checks_passed += 1

        # Check heading hierarchy
        # Get all heading tags in document order
        all_headings = self.soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        headings = [(int(tag.name[1]), tag) for tag in all_headings]

        if headings:
            prev_level = 0
            for level, tag in headings:
                if level > prev_level + 1:
                    self.issues.append(SEOIssue(
                        severity="WARNING",
                        category="technical",
                        check="heading_hierarchy",
                        message=f"Heading hierarchy skip: H{prev_level} to H{level}"
                    ))
                    break
                prev_level = level
            else:
                checks_passed += 1

        # Robots meta tag
        robots = self.soup.find('meta', attrs={'name': 'robots'})
        if robots:
            content = robots.get('content', '').lower()
            if 'noindex' in content or 'nofollow' in content:
                self.issues.append(SEOIssue(
                    severity="CRITICAL",
                    category="technical",
                    check="blocking_robots",
                    message=f"Robots meta tag blocks indexing: {content}"
                ))
            else:
                checks_passed += 1
        else:
            checks_passed += 1

        # HTTPS check
        if self.url.startswith('https://'):
            checks_passed += 1
        else:
            self.issues.append(SEOIssue(
                severity="CRITICAL",
                category="technical",
                check="no_https",
                message="Page is not served over HTTPS"
            ))

        return (checks_passed / total_checks) * 100

    def _check_content(self) -> float:
        """Check content quality factors. Returns score 0-100."""
        checks_passed = 0
        total_checks = 3

        # Word count
        text = self.soup.get_text()
        words = text.split()
        word_count = len(words)

        if word_count < 300:
            self.issues.append(SEOIssue(
                severity="WARNING",
                category="content",
                check="low_word_count",
                message=f"Page has only {word_count} words (recommended: 300+)"
            ))
        else:
            checks_passed += 1

        # Image alt text
        images = self.soup.find_all('img')
        missing_alt = 0
        for img in images:
            if not img.get('alt') or not img['alt'].strip():
                missing_alt += 1

        if images and missing_alt > 0:
            self.issues.append(SEOIssue(
                severity="WARNING",
                category="content",
                check="missing_alt_text",
                message=f"{missing_alt} of {len(images)} images missing alt text"
            ))
        elif images:
            checks_passed += 1
        else:
            checks_passed += 1  # No images is fine

        # Content-to-HTML ratio (simple check)
        html_size = len(self.html)
        text_size = len(text)
        if html_size > 0:
            ratio = text_size / html_size
            if ratio < 0.1:
                self.issues.append(SEOIssue(
                    severity="INFO",
                    category="content",
                    check="low_content_ratio",
                    message=f"Content-to-HTML ratio is low: {ratio:.1%}"
                ))
            else:
                checks_passed += 1

        return (checks_passed / total_checks) * 100

    def _check_performance(self) -> float:
        """Check performance factors. Returns score 0-100."""
        # If we have vitals data, use it
        if self.vitals and self.vitals.status == "success":
            checks_passed = 0
            total_checks = 3

            # LCP check
            if self.vitals.lcp is not None:
                if self.vitals.lcp <= 2.5:
                    checks_passed += 1
                elif self.vitals.lcp <= 4.0:
                    checks_passed += 0.5
                    self.issues.append(SEOIssue(
                        severity="WARNING",
                        category="performance",
                        check="lcp_needs_improvement",
                        message=f"LCP is {self.vitals.lcp:.2f}s (target: ≤2.5s)"
                    ))
                else:
                    self.issues.append(SEOIssue(
                        severity="WARNING",
                        category="performance",
                        check="lcp_poor",
                        message=f"LCP is {self.vitals.lcp:.2f}s (target: ≤2.5s)"
                    ))

            # CLS check
            if self.vitals.cls is not None:
                if self.vitals.cls <= 0.1:
                    checks_passed += 1
                elif self.vitals.cls <= 0.25:
                    checks_passed += 0.5
                    self.issues.append(SEOIssue(
                        severity="WARNING",
                        category="performance",
                        check="cls_needs_improvement",
                        message=f"CLS is {self.vitals.cls:.3f} (target: ≤0.1)"
                    ))
                else:
                    self.issues.append(SEOIssue(
                        severity="WARNING",
                        category="performance",
                        check="cls_poor",
                        message=f"CLS is {self.vitals.cls:.3f} (target: ≤0.1)"
                    ))

            # INP check
            if self.vitals.inp is not None:
                if self.vitals.inp <= 200:
                    checks_passed += 1
                elif self.vitals.inp <= 500:
                    checks_passed += 0.5
                    self.issues.append(SEOIssue(
                        severity="WARNING",
                        category="performance",
                        check="inp_needs_improvement",
                        message=f"INP is {self.vitals.inp:.0f}ms (target: ≤200ms)"
                    ))
                else:
                    self.issues.append(SEOIssue(
                        severity="WARNING",
                        category="performance",
                        check="inp_poor",
                        message=f"INP is {self.vitals.inp:.0f}ms (target: ≤200ms)"
                    ))

            return (checks_passed / total_checks) * 100
        else:
            # Without vitals, just check HTTPS and page size
            checks_passed = 0
            total_checks = 2

            if self.url.startswith('https://'):
                checks_passed += 1

            # Basic page size check
            html_size = len(self.html)
            if html_size < 500000:  # 500KB
                checks_passed += 1
            else:
                self.issues.append(SEOIssue(
                    severity="INFO",
                    category="performance",
                    check="large_page_size",
                    message=f"Page size is {html_size // 1024}KB"
                ))

            # Add info about running vitals
            self.issues.append(SEOIssue(
                severity="INFO",
                category="performance",
                check="vitals_not_measured",
                message="Run with --vitals flag for detailed performance analysis"
            ))

            return (checks_passed / total_checks) * 100

    def _check_mobile(self) -> float:
        """Check mobile-friendliness. Returns score 0-100."""
        checks_passed = 0
        total_checks = 1

        # Viewport meta tag
        viewport = self.soup.find('meta', attrs={'name': 'viewport'})
        if viewport and viewport.get('content'):
            checks_passed += 1
        else:
            self.issues.append(SEOIssue(
                severity="WARNING",
                category="mobile",
                check="missing_viewport",
                message="Page lacks viewport meta tag for mobile"
            ))

        return (checks_passed / total_checks) * 100

    def _check_structured_data(self) -> float:
        """Check for structured data. Returns score 0-100."""
        # Look for JSON-LD
        json_ld = self.soup.find_all('script', type='application/ld+json')

        if json_ld:
            self.issues.append(SEOIssue(
                severity="INFO",
                category="structured_data",
                check="has_json_ld",
                message=f"Found {len(json_ld)} JSON-LD structured data blocks"
            ))
            return 100.0
        else:
            self.issues.append(SEOIssue(
                severity="INFO",
                category="structured_data",
                check="no_structured_data",
                message="No structured data found (Schema.org recommended)"
            ))
            return 50.0
