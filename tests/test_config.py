# tests/test_config.py
import pytest
from pathlib import Path
from site_health.config import Config

def test_load_config_from_yaml(tmp_path):
    config_file = tmp_path / "test.yaml"
    config_file.write_text("""
url: https://example.com
depth: 3
max_concurrent: 5
timeout: 15.0
respect_robots: false
output_format: json
""")

    config = Config.from_yaml(str(config_file))

    assert config.url == "https://example.com"
    assert config.depth == 3
    assert config.max_concurrent == 5
    assert config.timeout == 15.0
    assert config.respect_robots == False
    assert config.output_format == "json"

def test_merge_config_with_cli_args(tmp_path):
    config_file = tmp_path / "test.yaml"
    config_file.write_text("""
url: https://example.com
depth: 2
output_format: html
""")

    config = Config.from_yaml(str(config_file))

    # CLI args should override config file
    merged = config.merge_with_args(depth=5, output_format="json")

    assert merged.url == "https://example.com"  # From config
    assert merged.depth == 5  # Overridden by CLI
    assert merged.output_format == "json"  # Overridden by CLI
