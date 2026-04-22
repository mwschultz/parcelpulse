"""Unit tests for _get_fips in app.services.demographics."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.demographics import _get_fips


def _make_response(data: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = data
    return mock_resp


VALID_FCC = {
    "Block": {"FIPS": "371830526011007"},
    "County": {"FIPS": "37183", "name": "Wake"},
    "State": {"FIPS": "37", "code": "NC", "name": "North Carolina"},
}

SHORT_FIPS_FCC = {
    "Block": {"FIPS": "3718305260"},
    "County": {"FIPS": "37183", "name": "Wake"},
    "State": {"FIPS": "37", "code": "NC", "name": "North Carolina"},
}

EMPTY_BLOCK_FCC = {
    "Block": {},
    "County": {"FIPS": "37183", "name": "Wake"},
    "State": {"FIPS": "37", "code": "NC", "name": "North Carolina"},
}


@pytest.mark.asyncio
async def test_returns_block_group_level():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_make_response(VALID_FCC)):
        result = await _get_fips(35.83, -78.67)

    assert result["level"] == "block_group"
    assert result["state"] == "37"
    assert result["county"] == "183"
    assert result["tract"] == "052601"
    assert result["block_group"] == "1"


@pytest.mark.asyncio
async def test_returns_unavailable_when_fips_short():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_make_response(SHORT_FIPS_FCC)):
        result = await _get_fips(35.83, -78.67)

    assert result["level"] == "unavailable"


@pytest.mark.asyncio
async def test_returns_unavailable_when_block_missing():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_make_response(EMPTY_BLOCK_FCC)):
        result = await _get_fips(35.83, -78.67)

    assert result["level"] == "unavailable"


@pytest.mark.asyncio
async def test_pulls_county_name_from_fcc():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_make_response(VALID_FCC)):
        result = await _get_fips(35.83, -78.67)

    assert result["county_name"] == "Wake"
