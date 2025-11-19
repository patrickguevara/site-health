# tests/test_crawler_seo.py
import pytest
from site_health.crawler import SiteCrawler


def test_crawler_has_seo_integration_method():
    """Test that crawler has method to get pages for SEO analysis."""
    crawler = SiteCrawler("https://example.com")

    # Should have method to get pages for SEO
    assert hasattr(crawler, 'get_pages_for_seo_analysis')


def test_get_pages_for_seo_returns_visited():
    """Test that get_pages_for_seo returns visited pages."""
    crawler = SiteCrawler("https://example.com")

    # Simulate visited pages
    crawler.visited.add("https://example.com")
    crawler.visited.add("https://example.com/page1")
    crawler.visited.add("https://example.com/page2")

    pages = crawler.get_pages_for_seo_analysis()

    assert len(pages) >= 3
    assert "https://example.com" in pages
