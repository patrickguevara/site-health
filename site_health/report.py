# site_health/report.py
"""Report generation for crawl results."""

import json
from pathlib import Path
from typing import Optional
from jinja2 import Environment, PackageLoader, select_autoescape
from site_health.database import Database
from site_health.models import CrawlSummary, LinkResult


class ReportGenerator:
    """Generate reports in various formats."""

    def __init__(self, crawl_id: int, db: Database):
        self.crawl_id = crawl_id
        self.db = db

    async def generate(self, format: str = 'terminal') -> str:
        """Generate report in specified format."""
        if format == 'terminal':
            return await self._generate_terminal()
        elif format == 'html':
            return await self._generate_html()
        elif format == 'json':
            return await self._generate_json()
        else:
            raise ValueError(f"Unknown format: {format}")

    async def _generate_terminal(self) -> str:
        """Generate colorized terminal output."""
        summary = await self.db.get_crawl_summary(self.crawl_id)
        if not summary:
            return "Crawl not found"

        # ANSI color codes
        RED = '\033[91m'
        YELLOW = '\033[93m'
        GREEN = '\033[92m'
        BOLD = '\033[1m'
        RESET = '\033[0m'

        lines = []
        lines.append(f"\n{BOLD}=== Site Health Report ==={RESET}\n")
        lines.append(f"URL: {summary.start_url}")
        lines.append(f"Status: {summary.status}")
        lines.append(f"Crawl Depth: {summary.max_depth}")
        lines.append(f"Pages Crawled: {summary.total_pages}")
        lines.append(f"Total Links Checked: {summary.total_links}")

        if summary.completed_at:
            duration = summary.completed_at - summary.started_at
            lines.append(f"Duration: {duration.total_seconds():.1f}s")

        lines.append("")

        # Summary statistics
        lines.append(f"{BOLD}Summary:{RESET}")
        lines.append(f"  {RED}Errors: {summary.errors}{RESET}")
        lines.append(f"  {YELLOW}Warnings: {summary.warnings}{RESET}")
        lines.append(f"  {GREEN}Success: {summary.total_links - summary.errors - summary.warnings}{RESET}")
        lines.append("")

        # Errors section
        if summary.errors > 0:
            lines.append(f"{BOLD}{RED}=== Errors ==={RESET}")
            errors = await self.db.get_link_results(self.crawl_id, severity='error')

            for result in errors[:20]:  # Limit to first 20
                lines.append(f"\n{RED}✗{RESET} {result.target_url}")
                lines.append(f"  Source: {result.source_url}")
                lines.append(f"  Type: {result.link_type}")
                if result.status_code:
                    lines.append(f"  Status: {result.status_code}")
                if result.error_message:
                    lines.append(f"  Error: {result.error_message}")

            if len(errors) > 20:
                lines.append(f"\n... and {len(errors) - 20} more errors")

            lines.append("")

        # Warnings section
        if summary.warnings > 0:
            lines.append(f"{BOLD}{YELLOW}=== Warnings ==={RESET}")
            warnings = await self.db.get_link_results(self.crawl_id, severity='warning')

            for result in warnings[:10]:  # Limit to first 10
                lines.append(f"\n{YELLOW}⚠{RESET} {result.target_url}")
                lines.append(f"  Source: {result.source_url}")
                if result.status_code:
                    lines.append(f"  Status: {result.status_code}")
                if result.response_time > 5.0:
                    lines.append(f"  Slow response: {result.response_time:.1f}s")

            if len(warnings) > 10:
                lines.append(f"\n... and {len(warnings) - 10} more warnings")

            lines.append("")

        # Statistics by type
        all_results = await self.db.get_link_results(self.crawl_id)
        by_type = {}
        for result in all_results:
            by_type[result.link_type] = by_type.get(result.link_type, 0) + 1

        if by_type:
            lines.append(f"{BOLD}Links by Type:{RESET}")
            for link_type, count in sorted(by_type.items()):
                lines.append(f"  {link_type}: {count}")

        # Core Web Vitals section
        vitals = await self.db.get_page_vitals(self.crawl_id)

        if vitals:
            lines.append("")
            lines.append(f"{BOLD}=== Core Web Vitals ==={RESET}")

            successful_vitals = [v for v in vitals if v.status == "success"]
            failed_vitals = [v for v in vitals if v.status == "failed"]

            if successful_vitals:
                # Calculate summary statistics
                lcp_values = [v.lcp for v in successful_vitals if v.lcp is not None]
                cls_values = [v.cls for v in successful_vitals if v.cls is not None]
                inp_values = [v.inp for v in successful_vitals if v.inp is not None]

                if lcp_values:
                    avg_lcp = sum(lcp_values) / len(lcp_values)
                    lines.append(f"\nAverage LCP: {self._colorize_vitals(avg_lcp, 'lcp', RED, YELLOW, GREEN, RESET)}")

                if cls_values:
                    avg_cls = sum(cls_values) / len(cls_values)
                    lines.append(f"Average CLS: {self._colorize_vitals(avg_cls, 'cls', RED, YELLOW, GREEN, RESET)}")

                if inp_values:
                    avg_inp = sum(inp_values) / len(inp_values)
                    lines.append(f"Average INP: {self._colorize_vitals(avg_inp, 'inp', RED, YELLOW, GREEN, RESET)}")

                lines.append(f"\nPages measured: {len(successful_vitals)}")

                # Show individual measurements
                lines.append(f"\n{BOLD}Individual Measurements:{RESET}")

                for v in successful_vitals[:10]:  # Show first 10
                    lines.append(f"\n{v.url}")
                    if v.lcp is not None:
                        lines.append(f"  LCP: {self._colorize_vitals(v.lcp, 'lcp', RED, YELLOW, GREEN, RESET)}")
                    if v.cls is not None:
                        lines.append(f"  CLS: {self._colorize_vitals(v.cls, 'cls', RED, YELLOW, GREEN, RESET)}")
                    if v.inp is not None:
                        lines.append(f"  INP: {self._colorize_vitals(v.inp, 'inp', RED, YELLOW, GREEN, RESET)}")

                if len(successful_vitals) > 10:
                    lines.append(f"\n... and {len(successful_vitals) - 10} more pages")

            if failed_vitals:
                lines.append(f"\n{RED}Failed measurements: {len(failed_vitals)}{RESET}")
                for v in failed_vitals[:5]:
                    lines.append(f"  {v.url}: {v.error_message}")

        return "\n".join(lines)

    def _colorize_vitals(self, value: float, metric: str, RED: str, YELLOW: str, GREEN: str, RESET: str) -> str:
        """
        Colorize vitals value based on Google thresholds.

        Args:
            value: Metric value
            metric: 'lcp', 'cls', or 'inp'
            RED, YELLOW, GREEN, RESET: ANSI color codes

        Returns:
            Colorized string with value and rating
        """
        # Determine rating and color
        if metric == 'lcp':
            # LCP in seconds
            if value <= 2.5:
                color = GREEN
                rating = "GOOD"
            elif value <= 4.0:
                color = YELLOW
                rating = "NEEDS IMPROVEMENT"
            else:
                color = RED
                rating = "POOR"
            formatted_value = f"{value:.2f}s"

        elif metric == 'cls':
            # CLS is unitless score
            if value <= 0.1:
                color = GREEN
                rating = "GOOD"
            elif value <= 0.25:
                color = YELLOW
                rating = "NEEDS IMPROVEMENT"
            else:
                color = RED
                rating = "POOR"
            formatted_value = f"{value:.3f}"

        elif metric == 'inp':
            # INP in milliseconds
            if value <= 200:
                color = GREEN
                rating = "GOOD"
            elif value <= 500:
                color = YELLOW
                rating = "NEEDS IMPROVEMENT"
            else:
                color = RED
                rating = "POOR"
            formatted_value = f"{value:.0f}ms"

        else:
            return f"{value}"

        return f"{color}{formatted_value} ({rating}){RESET}"

    async def _generate_json(self) -> str:
        """Generate JSON output."""
        summary = await self.db.get_crawl_summary(self.crawl_id)
        if not summary:
            return json.dumps({"error": "Crawl not found"})

        results = await self.db.get_link_results(self.crawl_id)
        vitals = await self.db.get_page_vitals(self.crawl_id)

        data = {
            "crawl_id": self.crawl_id,
            "summary": {
                "start_url": summary.start_url,
                "status": summary.status,
                "started_at": summary.started_at.isoformat(),
                "completed_at": summary.completed_at.isoformat() if summary.completed_at else None,
                "max_depth": summary.max_depth,
                "total_pages": summary.total_pages,
                "total_links": summary.total_links,
                "errors": summary.errors,
                "warnings": summary.warnings,
            },
            "results": [
                {
                    "source_url": r.source_url,
                    "target_url": r.target_url,
                    "link_type": r.link_type,
                    "status_code": r.status_code,
                    "response_time": r.response_time,
                    "severity": r.severity,
                    "error_message": r.error_message,
                }
                for r in results
            ],
            "vitals": [
                {
                    "url": v.url,
                    "lcp": v.lcp,
                    "cls": v.cls,
                    "inp": v.inp,
                    "lcp_rating": v.get_lcp_rating(),
                    "cls_rating": v.get_cls_rating(),
                    "inp_rating": v.get_inp_rating(),
                    "measured_at": v.measured_at.isoformat(),
                    "status": v.status,
                    "error_message": v.error_message,
                }
                for v in vitals
            ] if vitals else []
        }

        return json.dumps(data, indent=2)

    async def _generate_html(self) -> str:
        """Generate HTML report and save to reports directory."""
        from pathlib import Path

        summary = await self.db.get_crawl_summary(self.crawl_id)
        if not summary:
            return "Crawl not found"

        results = await self.db.get_link_results(self.crawl_id)
        vitals = await self.db.get_page_vitals(self.crawl_id)

        # Setup Jinja2
        env = Environment(
            loader=PackageLoader('site_health', 'templates'),
            autoescape=select_autoescape(['html'])
        )
        template = env.get_template('report.html')

        # Prepare results by severity for template
        errors = [r for r in results if r.severity == 'error']
        warnings = [r for r in results if r.severity == 'warning']
        successes = [r for r in results if r.severity == 'success']

        # Render template
        html = template.render(
            summary=summary,
            results=results,
            vitals=vitals,
            errors=errors,
            warnings=warnings,
            successes=successes
        )

        # Save to reports directory
        reports_dir = Path('reports')
        reports_dir.mkdir(exist_ok=True)

        timestamp = summary.started_at.strftime('%Y%m%d_%H%M%S')
        filename = f"crawl_{self.crawl_id}_{timestamp}.html"
        filepath = reports_dir / filename

        filepath.write_text(html)

        return str(filepath)
