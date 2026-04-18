import os

# Set required env vars before any app module is imported (pydantic-settings reads at class instantiation)
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("GEOAPIFY_API_KEY", "test-key")
os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")
os.environ.setdefault("CENSUS_API_KEY", "test-key")

import json
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_db():
    """Minimal AsyncSession stand-in for cache read/write tests."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def make_cache_hit(data: dict) -> AsyncMock:
    """Return a mock db.execute result that simulates a cache hit."""
    cache_row = MagicMock()
    cache_row.expires_at = None
    cache_row.response_json = json.dumps(data)
    result = MagicMock()
    result.scalar_one_or_none.return_value = cache_row
    return result


def make_cache_miss() -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    return result
