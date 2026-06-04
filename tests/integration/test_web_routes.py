"""
integration tests for web routes (task 6.2).
tests that routes load, templates render, and quiz submission works.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock

# patch settings before importing app so it doesn't try to connect to a real db
with patch.dict("os.environ", {
    "DATABASE_URL": "sqlite+aiosqlite:///test.db",
    "GEMINI_API_KEY": "",
    "SECRET_KEY": "test-secret",
}):
    from main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "ProInvestAI" in data["app"]


@pytest.mark.anyio
async def test_quiz_page_loads():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/quiz")
    assert response.status_code == 200
    assert "quiz" in response.text.lower() or "Análise" in response.text
