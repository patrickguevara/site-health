from typer.testing import CliRunner
from site_health.cli import app

runner = CliRunner()

def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Crawl websites" in result.output

def test_crawl_missing_url():
    result = runner.invoke(app, ["crawl"])
    assert result.exit_code == 1
    assert "Error" in result.output
