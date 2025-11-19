# tests/test_web.py
import pytest
from site_health.web.app import create_app
from site_health.database import Database

@pytest.mark.asyncio
async def test_list_crawls_endpoint(tmp_path):
    db_path = tmp_path / "test.db"
    app = create_app(str(db_path))

    # Initialize database
    db = Database(str(db_path))
    await db.initialize()

    from fastapi.testclient import TestClient

    # Use TestClient for synchronous tests with async endpoints
    with TestClient(app) as client:
        response = client.get("/api/crawls")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

@pytest.mark.asyncio
async def test_start_crawl_endpoint(tmp_path):
    db_path = tmp_path / "test.db"
    app = create_app(str(db_path))

    db = Database(str(db_path))
    await db.initialize()

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        response = client.post(
            "/api/crawl",
            json={"url": "https://example.com", "depth": 1}
        )
        assert response.status_code == 200
        data = response.json()
        assert "crawl_id" in data
        assert data["crawl_id"] > 0
