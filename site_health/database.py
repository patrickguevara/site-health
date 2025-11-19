# site_health/database.py
"""Database layer for storing crawl results."""

import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from site_health.models import LinkResult, CrawlSummary, PageVitals, SEOResult, SEOIssue


class Database:
    """SQLite database for crawl history and results."""

    def __init__(self, db_path: str = "site_health.db"):
        self.db_path = db_path

    async def initialize(self):
        """Create database schema if it doesn't exist."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS crawls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_url TEXT NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    max_depth INTEGER,
                    total_pages INTEGER DEFAULT 0,
                    total_links_checked INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'running'
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS link_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    crawl_id INTEGER NOT NULL,
                    source_url TEXT NOT NULL,
                    target_url TEXT NOT NULL,
                    link_type TEXT NOT NULL,
                    status_code INTEGER,
                    response_time REAL,
                    severity TEXT NOT NULL,
                    error_message TEXT,
                    checked_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (crawl_id) REFERENCES crawls(id)
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_crawl_id
                ON link_results(crawl_id)
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_severity
                ON link_results(severity)
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS page_vitals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    crawl_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    lcp REAL,
                    cls REAL,
                    inp REAL,
                    measured_at TIMESTAMP NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    FOREIGN KEY (crawl_id) REFERENCES crawls(id)
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_vitals_crawl_id
                ON page_vitals(crawl_id)
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS seo_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    crawl_id INTEGER NOT NULL,
                    url TEXT NOT NULL,
                    overall_score REAL,
                    technical_score REAL,
                    content_score REAL,
                    performance_score REAL,
                    mobile_score REAL,
                    structured_data_score REAL,
                    issues TEXT,
                    timestamp TIMESTAMP NOT NULL,
                    FOREIGN KEY (crawl_id) REFERENCES crawls(id)
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_seo_crawl_id
                ON seo_results(crawl_id)
            """)

            await conn.commit()

    async def create_crawl(self, start_url: str, max_depth: int) -> int:
        """Create a new crawl session and return its ID."""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute(
                """
                INSERT INTO crawls (start_url, started_at, max_depth, status)
                VALUES (?, ?, ?, 'running')
                """,
                (start_url, datetime.now(), max_depth)
            )
            await conn.commit()
            return cursor.lastrowid

    async def save_link_result(self, crawl_id: int, result: LinkResult):
        """Save a single link check result."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT INTO link_results
                (crawl_id, source_url, target_url, link_type, status_code,
                 response_time, severity, error_message, checked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    crawl_id,
                    result.source_url,
                    result.target_url,
                    result.link_type,
                    result.status_code,
                    result.response_time,
                    result.severity,
                    result.error_message,
                    datetime.now()
                )
            )
            await conn.commit()

    async def save_page_vitals(self, crawl_id: int, vitals: PageVitals):
        """Save Core Web Vitals measurement for a page."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT INTO page_vitals
                (crawl_id, url, lcp, cls, inp, measured_at, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    crawl_id,
                    vitals.url,
                    vitals.lcp,
                    vitals.cls,
                    vitals.inp,
                    vitals.measured_at,
                    vitals.status,
                    vitals.error_message
                )
            )
            await conn.commit()

    async def complete_crawl(
        self,
        crawl_id: int,
        total_pages: int,
        total_links: int,
        status: str = "completed"
    ):
        """Mark crawl as completed and update statistics."""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                UPDATE crawls
                SET completed_at = ?, total_pages = ?,
                    total_links_checked = ?, status = ?
                WHERE id = ?
                """,
                (datetime.now(), total_pages, total_links, status, crawl_id)
            )
            await conn.commit()

    async def get_crawl_summary(self, crawl_id: int) -> Optional[CrawlSummary]:
        """Get summary information for a crawl."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                """
                SELECT
                    c.*,
                    SUM(CASE WHEN lr.severity = 'error' THEN 1 ELSE 0 END) as errors,
                    SUM(CASE WHEN lr.severity = 'warning' THEN 1 ELSE 0 END) as warnings
                FROM crawls c
                LEFT JOIN link_results lr ON c.id = lr.crawl_id
                WHERE c.id = ?
                GROUP BY c.id
                """,
                (crawl_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return None

            return CrawlSummary(
                id=row["id"],
                start_url=row["start_url"],
                started_at=datetime.fromisoformat(row["started_at"]),
                completed_at=datetime.fromisoformat(row["completed_at"])
                    if row["completed_at"] else None,
                max_depth=row["max_depth"],
                total_pages=row["total_pages"],
                total_links=row["total_links_checked"],
                errors=row["errors"] or 0,
                warnings=row["warnings"] or 0,
                status=row["status"]
            )

    async def get_link_results(
        self,
        crawl_id: int,
        severity: Optional[str] = None
    ) -> List[LinkResult]:
        """Get link results for a crawl, optionally filtered by severity."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row

            if severity:
                cursor = await conn.execute(
                    """
                    SELECT * FROM link_results
                    WHERE crawl_id = ? AND severity = ?
                    ORDER BY checked_at
                    """,
                    (crawl_id, severity)
                )
            else:
                cursor = await conn.execute(
                    """
                    SELECT * FROM link_results
                    WHERE crawl_id = ?
                    ORDER BY severity DESC, checked_at
                    """,
                    (crawl_id,)
                )

            rows = await cursor.fetchall()
            return [
                LinkResult(
                    source_url=row["source_url"],
                    target_url=row["target_url"],
                    link_type=row["link_type"],
                    status_code=row["status_code"],
                    response_time=row["response_time"],
                    severity=row["severity"],
                    error_message=row["error_message"]
                )
                for row in rows
            ]

    async def list_crawls(self, limit: int = 50) -> List[CrawlSummary]:
        """List recent crawls."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                """
                SELECT
                    c.*,
                    SUM(CASE WHEN lr.severity = 'error' THEN 1 ELSE 0 END) as errors,
                    SUM(CASE WHEN lr.severity = 'warning' THEN 1 ELSE 0 END) as warnings
                FROM crawls c
                LEFT JOIN link_results lr ON c.id = lr.crawl_id
                GROUP BY c.id
                ORDER BY c.started_at DESC
                LIMIT ?
                """,
                (limit,)
            )
            rows = await cursor.fetchall()

            return [
                CrawlSummary(
                    id=row["id"],
                    start_url=row["start_url"],
                    started_at=datetime.fromisoformat(row["started_at"]),
                    completed_at=datetime.fromisoformat(row["completed_at"])
                        if row["completed_at"] else None,
                    max_depth=row["max_depth"],
                    total_pages=row["total_pages"],
                    total_links=row["total_links_checked"],
                    errors=row["errors"] or 0,
                    warnings=row["warnings"] or 0,
                    status=row["status"]
                )
                for row in rows
            ]

    async def get_page_vitals(self, crawl_id: int) -> List[PageVitals]:
        """Get all Core Web Vitals measurements for a crawl."""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                """
                SELECT * FROM page_vitals
                WHERE crawl_id = ?
                ORDER BY measured_at
                """,
                (crawl_id,)
            )
            rows = await cursor.fetchall()

            return [
                PageVitals(
                    url=row["url"],
                    lcp=row["lcp"],
                    cls=row["cls"],
                    inp=row["inp"],
                    measured_at=datetime.fromisoformat(row["measured_at"]),
                    status=row["status"],
                    error_message=row["error_message"]
                )
                for row in rows
            ]

    async def save_seo_result(self, crawl_id: int, result: SEOResult):
        """Save SEO analysis result for a page."""
        import json

        # Serialize issues to JSON
        issues_json = json.dumps([
            {
                "severity": issue.severity,
                "category": issue.category,
                "check": issue.check,
                "message": issue.message
            }
            for issue in result.issues
        ])

        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT INTO seo_results
                (crawl_id, url, overall_score, technical_score, content_score,
                 performance_score, mobile_score, structured_data_score,
                 issues, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    crawl_id,
                    result.url,
                    result.overall_score,
                    result.technical_score,
                    result.content_score,
                    result.performance_score,
                    result.mobile_score,
                    result.structured_data_score,
                    issues_json,
                    result.timestamp
                )
            )
            await conn.commit()

    async def get_seo_results(self, crawl_id: int) -> List[SEOResult]:
        """Get all SEO results for a crawl."""
        import json

        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                """
                SELECT * FROM seo_results
                WHERE crawl_id = ?
                ORDER BY timestamp
                """,
                (crawl_id,)
            )
            rows = await cursor.fetchall()

            results = []
            for row in rows:
                # Deserialize issues from JSON
                issues_data = json.loads(row["issues"])
                issues = [
                    SEOIssue(
                        severity=issue["severity"],
                        category=issue["category"],
                        check=issue["check"],
                        message=issue["message"]
                    )
                    for issue in issues_data
                ]

                results.append(SEOResult(
                    url=row["url"],
                    overall_score=row["overall_score"],
                    technical_score=row["technical_score"],
                    content_score=row["content_score"],
                    performance_score=row["performance_score"],
                    mobile_score=row["mobile_score"],
                    structured_data_score=row["structured_data_score"],
                    issues=issues,
                    timestamp=datetime.fromisoformat(row["timestamp"])
                ))

            return results
