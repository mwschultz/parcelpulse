"""Unit tests for _get_fips in app.services.demographics."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.demographics import _get_fips


def _make_response(geographies: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"result": {"geographies": geographies}}
    return mock_resp


BG_GEO = {
    "Census Block Groups": [{"STATE": "37", "COUNTY": "183", "TRACT": "052601", "BLKGRP": "1"}],
    "Counties": [{"STATE": "37", "COUNTY": "183", "NAME": "Wake County"}],
}

TRACT_GEO = {
    "Census Block Groups": [],
    "Census Tracts": [{"STATE": "37", "COUNTY": "183", "TRACT": "052601"}],
    "Counties": [{"STATE": "37", "COUNTY": "183", "NAME": "Wake County"}],
}

COUNTY_GEO = {
    "Census Block Groups": [],
    "Census Tracts": [],
    "Counties": [{"STATE": "37", "COUNTY": "183", "NAME": "Wake County"}],
}

EMPTY_GEO: dict = {
    "Census Block Groups": [],
    "Census Tracts": [],
    "Counties": [],
}


@pytest.mark.asyncio
async def test_returns_block_group_level():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_make_response(BG_GEO)):
        result = await _get_fips(35.83, -78.67)

    assert result["level"] == "block_group"
    assert result["state"] == "37"
    assert result["county"] == "183"
    assert result["tract"] == "052601"
    assert result["block_group"] == "1"


@pytest.mark.asyncio
async def test_falls_back_to_tract():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_make_response(TRACT_GEO)):
        result = await _get_fips(35.83, -78.67)

    assert result["level"] == "tract"
    assert result["tract"] == "052601"


@pytest.mark.asyncio
async def test_falls_back_to_county():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_make_response(COUNTY_GEO)):
        result = await _get_fips(35.83, -78.67)

    assert result["level"] == "county"
    assert result["county"] == "183"


@pytest.mark.asyncio
async def test_returns_unavailable_when_empty():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_make_response(EMPTY_GEO)):
        result = await _get_fips(35.83, -78.67)

    assert result["level"] == "unavailable"


@pytest.mark.asyncio
async def test_pulls_county_name_from_counties_layer():
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=_make_response(BG_GEO)):
        result = await _get_fips(35.83, -78.67)

    assert result["county_name"] == "Wake County"
