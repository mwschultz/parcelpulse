import os

# Set env vars before any app imports so Settings() initialises with them
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("GEOAPIFY_API_KEY", "test-key")
os.environ.setdefault("CENSUS_API_KEY", "test-key")
os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock
from httpx import ASGITransport

from app.main import app
from app.database import get_db


@pytest.fixture
def mock_db():
    """AsyncMock DB session — cache miss by default (scalar_one_or_none returns None)."""
    db = AsyncMock()
    db.add = MagicMock()  # synchronous in SQLAlchemy — plain MagicMock prevents unawaited coroutine warnings
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute.return_value = result
    return db


@pytest.fixture
async def http_client(mock_db):
    """Async HTTP client wired to the FastAPI app with DB dependency overridden."""
    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
