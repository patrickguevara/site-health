# site_health/config.py
"""Configuration management for site-health."""

import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Config:
    """Configuration for site health crawler."""

    url: Optional[str] = None
    depth: int = 2
    max_concurrent: int = 10
    timeout: float = 10.0
    respect_robots: bool = True
    output_format: str = "terminal"
    output_path: Optional[str] = None

    @classmethod
    def from_yaml(cls, filepath: str) -> 'Config':
        """Load configuration from YAML file."""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {filepath}")

        with open(filepath, 'r') as f:
            data = yaml.safe_load(f) or {}

        return cls(**data)

    def merge_with_args(self, **kwargs) -> 'Config':
        """Create new config by merging with command-line arguments.

        Command-line arguments override config file values.
        """
        # Start with current config values
        merged = {
            'url': self.url,
            'depth': self.depth,
            'max_concurrent': self.max_concurrent,
            'timeout': self.timeout,
            'respect_robots': self.respect_robots,
            'output_format': self.output_format,
            'output_path': self.output_path,
        }

        # Override with any non-None kwargs
        for key, value in kwargs.items():
            if value is not None:
                merged[key] = value

        return Config(**merged)
