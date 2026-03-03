"""Tests for app.services.cache — all mock-based, no real DB."""
import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.services.cache import get_cached, set_cached
from app.models.cache import ApiCache


def _future_dt():
    return datetime.now(timezone.utc) + timedelta(days=1)


def _past_dt():
    return datetime.now(timezone.utc) - timedelta(days=1)


# ---------------------------------------------------------------------------
# get_cached
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_cached_miss(mock_db):
    """scalar_one_or_none returns None → get_cached returns None."""
    result = await get_cached(mock_db, "missing-key")
    assert result is None


@pytest.mark.asyncio
async def test_get_cached_hit_not_expired(mock_db):
    """Row with future expires_at → returns deserialized JSON."""
    data = {"foo": "bar", "num": 42}
    row = MagicMock(spec=ApiCache)
    row.expires_at = _future_dt()
    row.response_json = json.dumps(data)

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = row
    mock_db.execute.return_value = result_mock

    result = await get_cached(mock_db, "my-key")
    assert result == data


@pytest.mark.asyncio
async def test_get_cached_expired(mock_db):
    """Row with past expires_at → returns None and db.delete called."""
    row = MagicMock(spec=ApiCache)
    row.expires_at = _past_dt()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = row
    mock_db.execute.return_value = result_mock

    result = await get_cached(mock_db, "expired-key")
    assert result is None
    mock_db.delete.assert_awaited_once_with(row)
    mock_db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# set_cached
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_set_cached_new_row(mock_db):
    """No existing row → db.add called with ApiCache instance, db.commit called."""
    result = await set_cached(mock_db, "new-key", "test-service", {"x": 1})
    mock_db.add.assert_called_once()
    added = mock_db.add.call_args[0][0]
    assert isinstance(added, ApiCache)
    assert added.cache_key == "new-key"
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_cached_updates_existing(mock_db):
    """Existing row → row.response_json updated, db.add NOT called, db.commit called."""
    row = MagicMock(spec=ApiCache)
    row.response_json = json.dumps({"old": True})

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = row
    mock_db.execute.return_value = result_mock

    new_data = {"new": True}
    await set_cached(mock_db, "existing-key", "svc", new_data)

    assert json.loads(row.response_json) == new_data
    mock_db.add.assert_not_called()
    mock_db.commit.assert_awaited_once()


# ---------------------------------------------------------------------------
# Behavioral tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_set_then_get_returns_stored_value(mock_db):
    """
    Simulate set_cached then get_cached on the same mock:
    db.add is a plain MagicMock (not AsyncMock) because set_cached calls it
    without await — side_effect only fires when the call is synchronous.
    """
    stored: list = []

    # db.add is synchronous in SQLAlchemy — use MagicMock so side_effect fires
    def capture_add(row):
        stored.append(row)
    mock_db.add = MagicMock(side_effect=capture_add)

    async def execute_side_effect(stmt):
        result = MagicMock()
        if stored:
            result.scalar_one_or_none.return_value = stored[-1]
        else:
            result.scalar_one_or_none.return_value = None
        return result

    mock_db.execute.side_effect = execute_side_effect

    data = {"sensor": "value", "count": 7}
    await set_cached(mock_db, "behavioral-key", "svc", data)

    # Now get_cached should find the stored row
    result = await get_cached(mock_db, "behavioral-key")
    assert result == data


@pytest.mark.asyncio
async def test_set_twice_updates_not_duplicates(mock_db):
    """Second set_cached for same key updates row, does not call db.add again."""
    row = MagicMock(spec=ApiCache)
    row.expires_at = _future_dt()
    row.response_json = json.dumps({"v": 1})

    # First call: cache miss (for set_cached's internal select)
    # Second call: row found
    miss_result = MagicMock()
    miss_result.scalar_one_or_none.return_value = None
    hit_result = MagicMock()
    hit_result.scalar_one_or_none.return_value = row

    mock_db.execute.side_effect = [miss_result, hit_result]

    await set_cached(mock_db, "dup-key", "svc", {"v": 1})
    await set_cached(mock_db, "dup-key", "svc", {"v": 2})

    # db.add was only called once (for the first set_cached)
    assert mock_db.add.call_count == 1
    # row.response_json updated to v=2
    assert json.loads(row.response_json) == {"v": 2}
