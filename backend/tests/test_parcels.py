"""Unit tests for app.services.parcels."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.parcels import get_parcel_data, _transform_parcel


LAT = 35.8304
LNG = -78.6679

# Minimal GeoJSON feature for testing
def make_feature(parno: str, lat: float, lng: float) -> dict:
    return {
        "type": "Feature",
        "properties": {
            "parno": parno,
            "siteadd": f"{parno} Main St",
            "scity": "Raleigh",
            "ownname": "Test Owner",
            "owntype": "",
            "landval": "100000",
            "improvval": "200000",
            "parval": "300000",
            "parusedesc": "Commercial",
            "gisacres": "0.5",
            "struct": "Y",
            "structyear": "2000",
            "saledatetx": None,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[lng - 0.001, lat - 0.001], [lng + 0.001, lat - 0.001],
                             [lng + 0.001, lat + 0.001], [lng - 0.001, lat + 0.001],
                             [lng - 0.001, lat - 0.001]]],
        },
    }


@pytest.mark.asyncio
async def test_non_nc_returns_coverage_false(mock_db):
    result = await get_parcel_data(LAT, LNG, "TX", mock_db)
    assert result["coverage"] is False
    assert result["state"] == "TX"
    assert result["parcels"] == []
    # No HTTP call should be made for non-NC
    mock_db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_nc_cache_hit_returns_parcels(mock_db):
    feature = make_feature("ABC123", LAT, LNG)
    cache_row = MagicMock()
    cache_row.expires_at = None
    import json
    cache_row.response_json = json.dumps({"features": [feature]})

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = cache_row
    mock_db.execute.return_value = result_mock

    result = await get_parcel_data(LAT, LNG, "NC", mock_db)

    assert result["coverage"] is True
    assert result["state"] == "NC"
    assert len(result["parcels"]) == 1
    assert result["parcels"][0]["parno"] == "ABC123"


@pytest.mark.asyncio
async def test_nc_api_call_and_cache_set(mock_db):
    """Cache miss → POST to NC OneMap → set_cached called → parcels returned."""
    # Cache miss
    miss_result = MagicMock()
    miss_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = miss_result

    feature = make_feature("XYZ999", LAT, LNG)
    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = {"features": [feature]}

    with (
        patch("app.services.parcels.check_and_increment", new_callable=AsyncMock, return_value=True),
        patch("app.services.parcels.set_cached", new_callable=AsyncMock) as mock_set,
        patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response),
    ):
        result = await get_parcel_data(LAT, LNG, "NC", mock_db)

    assert result["coverage"] is True
    assert len(result["parcels"]) == 1
    assert result["parcels"][0]["parno"] == "XYZ999"
    mock_set.assert_awaited_once()


@pytest.mark.asyncio
async def test_nc_rate_limited_returns_empty(mock_db):
    """Rate limiter returns False → rate_limited=True, empty parcels."""
    miss_result = MagicMock()
    miss_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = miss_result

    with patch("app.services.parcels.check_and_increment", new_callable=AsyncMock, return_value=False):
        result = await get_parcel_data(LAT, LNG, "NC", mock_db)

    assert result["rate_limited"] is True
    assert result["parcels"] == []


def test_transform_parcel_sorts_by_distance():
    """Parcels sorted nearest-first by haversine distance."""
    # Feature A is slightly farther (0.01° offset) than feature B (0.001° offset)
    feature_far = make_feature("FAR", LAT + 0.01, LNG + 0.01)
    feature_near = make_feature("NEAR", LAT + 0.001, LNG + 0.001)

    result = _transform_parcel([feature_far, feature_near], LAT, LNG)
    assert result["parcels"][0]["parno"] == "NEAR"
    assert result["parcels"][1]["parno"] == "FAR"
