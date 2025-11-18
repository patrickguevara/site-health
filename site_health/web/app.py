# site_health/web/app.py
"""FastAPI web application."""

import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, List
from site_health.database import Database
from site_health.crawler import SiteCrawler
from site_health.report import ReportGenerator


# Request/Response models
class CrawlRequest(BaseModel):
    url: str
    depth: int = 2
    max_concurrent: int = 10
    timeout: float = 10.0


class CrawlResponse(BaseModel):
    crawl_id: int
    message: str


def create_app(db_path: str = "site_health.db") -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(title="Site Health", version="0.1.0")

    # Initialize database
    db = Database(db_path)

    # Setup templates and static files
    templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

    @app.on_event("startup")
    async def startup():
        await db.initialize()

    @app.get("/")
    async def home(request: Request):
        """Serve home page."""
        return templates.TemplateResponse("index.html", {"request": request})

    @app.post("/api/crawl", response_model=CrawlResponse)
    async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
        """Start a new crawl."""
        # Create crawl session
        crawl_id = await db.create_crawl(request.url, request.depth)

        # Start crawl in background
        background_tasks.add_task(
            run_crawl,
            crawl_id=crawl_id,
            url=request.url,
            depth=request.depth,
            max_concurrent=request.max_concurrent,
            timeout=request.timeout,
            db=db,
        )

        return CrawlResponse(
            crawl_id=crawl_id,
            message=f"Crawl started for {request.url}"
        )

    @app.get("/api/crawls")
    async def list_crawls(limit: int = 50):
        """List all crawls."""
        crawls = await db.list_crawls(limit)
        return [
            {
                "id": c.id,
                "start_url": c.start_url,
                "started_at": c.started_at.isoformat(),
                "completed_at": c.completed_at.isoformat() if c.completed_at else None,
                "status": c.status,
                "total_pages": c.total_pages,
                "total_links": c.total_links,
                "errors": c.errors,
                "warnings": c.warnings,
            }
            for c in crawls
        ]

    @app.get("/api/crawls/{crawl_id}")
    async def get_crawl(crawl_id: int):
        """Get details for a specific crawl."""
        summary = await db.get_crawl_summary(crawl_id)
        if not summary:
            raise HTTPException(status_code=404, detail="Crawl not found")

        results = await db.get_link_results(crawl_id)

        return {
            "summary": {
                "id": summary.id,
                "start_url": summary.start_url,
                "started_at": summary.started_at.isoformat(),
                "completed_at": summary.completed_at.isoformat() if summary.completed_at else None,
                "status": summary.status,
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
            ]
        }

    @app.get("/api/crawls/{crawl_id}/report")
    async def get_crawl_report(crawl_id: int, format: str = "json"):
        """Get report for a crawl in specified format."""
        summary = await db.get_crawl_summary(crawl_id)
        if not summary:
            raise HTTPException(status_code=404, detail="Crawl not found")

        generator = ReportGenerator(crawl_id, db)

        if format == "html":
            filepath = await generator.generate('html')
            return FileResponse(filepath, media_type="text/html")
        elif format == "json":
            report = await generator.generate('json')
            return report
        else:
            raise HTTPException(status_code=400, detail="Invalid format")

    # Serve static reports
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)
    app.mount("/reports", StaticFiles(directory="reports"), name="reports")

    return app


async def run_crawl(
    crawl_id: int,
    url: str,
    depth: int,
    max_concurrent: int,
    timeout: float,
    db: Database,
):
    """Run crawl in background task."""
    try:
        crawler = SiteCrawler(
            start_url=url,
            max_depth=depth,
            max_concurrent=max_concurrent,
            timeout=timeout,
        )

        results = await crawler.crawl()

        # Save results
        for result in results:
            await db.save_link_result(crawl_id, result)

        # Mark complete
        await db.complete_crawl(
            crawl_id,
            total_pages=crawler.pages_crawled,
            total_links=len(results),
        )

    except Exception as e:
        # Mark as failed
        await db.complete_crawl(crawl_id, total_pages=0, total_links=0, status="failed")
