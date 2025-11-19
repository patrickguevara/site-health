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


def test_cli_with_a11y_flag():
    """Test CLI accepts --a11y flag."""
    # Test that help shows a11y options
    result = runner.invoke(app, ["crawl", "--help"])
    assert result.exit_code == 0
    assert "--a11y" in result.output
    assert "--a11y-level" in result.output
    assert "--a11y-use-browser" in result.output
