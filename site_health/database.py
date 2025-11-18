# site_health/database.py
"""Database layer for storing crawl results."""

import aiosqlite
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from site_health.models import LinkResult, CrawlSummary


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
