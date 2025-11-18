# tests/test_crawler.py
import pytest
import httpx
from unittest.mock import AsyncMock, patch
from site_health.crawler import SiteCrawler

def test_normalize_url():
    crawler = SiteCrawler("https://example.com", max_depth=1)

    # Test various URL formats
    assert crawler._normalize_url("page.html") == "https://example.com/page.html"
    assert crawler._normalize_url("/about") == "https://example.com/about"
    assert crawler._normalize_url("https://example.com/test") == "https://example.com/test"
    assert crawler._normalize_url("https://example.com/test#anchor") == "https://example.com/test"

@pytest.mark.asyncio
async def test_check_link_success():
    crawler = SiteCrawler("https://example.com", max_depth=1)

    # Mock successful response
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.elapsed.total_seconds = lambda: 0.5

    async def mock_head(*args, **kwargs):
        return mock_response

    with patch.object(httpx.AsyncClient, 'head', side_effect=mock_head):
        result = await crawler._check_link(
            "https://example.com",
            "https://example.com/page"
        )

    assert result.status_code == 200
    assert result.severity == "success"
    assert result.link_type == "page"

@pytest.mark.asyncio
async def test_check_link_404():
    crawler = SiteCrawler("https://example.com", max_depth=1)

    # Mock 404 response
    mock_response = AsyncMock()
    mock_response.status_code = 404
    mock_response.elapsed.total_seconds = lambda: 0.3

    async def mock_head(*args, **kwargs):
        return mock_response

    with patch.object(httpx.AsyncClient, 'head', side_effect=mock_head):
        result = await crawler._check_link(
            "https://example.com",
            "https://example.com/missing"
        )

    assert result.status_code == 404
    assert result.severity == "error"
