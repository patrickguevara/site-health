# site_health/cli.py
"""Command-line interface for site-health."""

import asyncio
import typer
from pathlib import Path
from typing import Optional
from site_health.config import Config
from site_health.crawler import SiteCrawler
from site_health.database import Database
from site_health.report import ReportGenerator

app = typer.Typer(help="Crawl websites and check for broken links")


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
    db_path: str = typer.Option("site_health.db", "--db", help="Database path"),
):
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
        db_path=db_path,
    ))


async def _crawl_async(
    url: Optional[str],
    depth: Optional[int],
    format: Optional[str],
    output: Optional[str],
    config_file: Optional[str],
    max_concurrent: Optional[int],
    timeout: Optional[float],
    no_robots: bool,
    db_path: str,
):
    """Async implementation of crawl command."""
    # Load config file if provided
    if config_file:
        config = Config.from_yaml(config_file)
    else:
        config = Config()

    # Merge with CLI arguments (CLI takes precedence)
    config = config.merge_with_args(
        url=url,
        depth=depth,
        output_format=format,
        output_path=output,
        max_concurrent=max_concurrent,
        timeout=timeout,
        respect_robots=not no_robots,
    )

    # Validate required fields
    if not config.url:
        typer.echo("Error: URL is required (provide via argument or config file)", err=True)
        raise typer.Exit(1)

    typer.echo(f"Starting crawl of {config.url}...")
    typer.echo(f"Max depth: {config.depth}")

    # Initialize database
    db = Database(db_path)
    await db.initialize()

    # Create crawl session
    crawl_id = await db.create_crawl(config.url, config.depth)

    try:
        # Run crawler
        crawler = SiteCrawler(
            start_url=config.url,
            max_depth=config.depth,
            max_concurrent=config.max_concurrent,
            timeout=config.timeout,
            respect_robots=config.respect_robots,
        )

        results = await crawler.crawl()

        # Save results to database
        for result in results:
            await db.save_link_result(crawl_id, result)

        # Mark crawl as complete
        await db.complete_crawl(
            crawl_id,
            total_pages=crawler.pages_crawled,
            total_links=len(results),
        )

        typer.echo(f"\nCrawl complete! Pages crawled: {crawler.pages_crawled}, Links checked: {len(results)}")

        # Generate report
        generator = ReportGenerator(crawl_id, db)
        report = await generator.generate(config.output_format)

        if config.output_format == 'terminal':
            typer.echo(report)
        elif config.output_format == 'html':
            typer.echo(f"\nHTML report saved to: {report}")
        elif config.output_format == 'json':
            if config.output_path:
                Path(config.output_path).write_text(report)
                typer.echo(f"\nJSON report saved to: {config.output_path}")
            else:
                typer.echo(report)

    except Exception as e:
        # Mark crawl as failed
        await db.complete_crawl(crawl_id, total_pages=0, total_links=0, status="failed")
        typer.echo(f"Error during crawl: {e}", err=True)
        raise typer.Exit(1)


@app.command()
def list(
    db_path: str = typer.Option("site_health.db", "--db", help="Database path"),
    limit: int = typer.Option(50, "--limit", "-n", help="Number of crawls to show"),
):
    """List previous crawls."""
    asyncio.run(_list_async(db_path, limit))


async def _list_async(db_path: str, limit: int):
    """Async implementation of list command."""
    db = Database(db_path)
    await db.initialize()

    crawls = await db.list_crawls(limit)

    if not crawls:
        typer.echo("No crawls found")
        return

    # Print table header
    typer.echo("\n{:<5} {:<40} {:<20} {:<10} {:<8} {:<8}".format(
        "ID", "URL", "Date", "Status", "Errors", "Warnings"
    ))
    typer.echo("-" * 100)

    # Print crawls
    for crawl in crawls:
        date_str = crawl.started_at.strftime("%Y-%m-%d %H:%M")
        url_short = crawl.start_url[:37] + "..." if len(crawl.start_url) > 40 else crawl.start_url

        typer.echo("{:<5} {:<40} {:<20} {:<10} {:<8} {:<8}".format(
            crawl.id,
            url_short,
            date_str,
            crawl.status,
            crawl.errors,
            crawl.warnings,
        ))


@app.command()
def report(
    crawl_id: int = typer.Argument(..., help="Crawl ID to generate report for"),
    format: str = typer.Option("terminal", "--format", "-f", help="Output format"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    db_path: str = typer.Option("site_health.db", "--db", help="Database path"),
):
    """Generate report for a previous crawl."""
    asyncio.run(_report_async(crawl_id, format, output, db_path))


async def _report_async(crawl_id: int, format: str, output: Optional[str], db_path: str):
    """Async implementation of report command."""
    db = Database(db_path)
    await db.initialize()

    generator = ReportGenerator(crawl_id, db)
    report_output = await generator.generate(format)

    if format == 'terminal':
        typer.echo(report_output)
    elif format == 'html':
        typer.echo(f"HTML report saved to: {report_output}")
    elif format == 'json':
        if output:
            Path(output).write_text(report_output)
            typer.echo(f"JSON report saved to: {output}")
        else:
            typer.echo(report_output)


@app.command()
def serve(
    port: int = typer.Option(8000, "--port", "-p", help="Port to run server on"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to"),
    db_path: str = typer.Option("site_health.db", "--db", help="Database path"),
):
    """Start web interface."""
    import uvicorn
    from site_health.web.app import create_app

    app = create_app(db_path)

    typer.echo(f"Starting web server on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    app()
