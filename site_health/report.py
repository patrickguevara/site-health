# site_health/report.py
"""Report generation for crawl results."""

from pathlib import Path
from typing import Optional
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

        return "\n".join(lines)
