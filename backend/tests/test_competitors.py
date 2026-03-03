"""Unit tests for app.services.competitors."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.competitors import get_competitor_data, _transform_competitor, _categorize


LAT = 35.8304
LNG = -78.6679


def make_node(amenity: str | None = None, shop: str | None = None, name: str = "Test") -> dict:
    tags: dict = {"name": name}
    if amenity:
        tags["amenity"] = amenity
    if shop:
        tags["shop"] = shop
    return {"type": "node", "lat": LAT + 0.001, "lon": LNG + 0.001, "tags": tags}


@pytest.mark.asyncio
async def test_cache_hit_returns_categories(mock_db):
    """Cached OSM elements → categories and density_score returned."""
    elements = [
        make_node(shop="supermarket", name="Grocery A"),
        make_node(shop="supermarket", name="Grocery B"),
        make_node(amenity="restaurant", name="Rest A"),
    ]
    cache_row = MagicMock()
    cache_row.expires_at = None
    cache_row.response_json = json.dumps({"elements": elements})

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = cache_row
    mock_db.execute.return_value = result_mock

    result = await get_competitor_data(LAT, LNG, mock_db)

    assert result["density_score"] in ("Low", "Medium", "High")
    keys = [c["key"] for c in result["categories"]]
    assert "grocery" in keys
    assert "restaurant" in keys
    grocery = next(c for c in result["categories"] if c["key"] == "grocery")
    assert grocery["count"] == 2


@pytest.mark.asyncio
async def test_api_call_fetches_and_caches(mock_db):
    """Cache miss → Overpass POST → set_cached called → result returned."""
    miss_result = MagicMock()
    miss_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = miss_result

    elements = [make_node(amenity="bank")]
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"elements": elements}

    with (
        patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp),
        patch("app.services.competitors.set_cached", new_callable=AsyncMock) as mock_set,
    ):
        result = await get_competitor_data(LAT, LNG, mock_db)

    assert result["categories"][0]["key"] == "bank"
    mock_set.assert_awaited_once()


@pytest.mark.asyncio
async def test_empty_elements_low_density(mock_db):
    """No OSM elements → density_score is 'Low'."""
    cache_row = MagicMock()
    cache_row.expires_at = None
    cache_row.response_json = json.dumps({"elements": []})

    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = cache_row
    mock_db.execute.return_value = result_mock

    result = await get_competitor_data(LAT, LNG, mock_db)
    assert result["density_score"] == "Low"
    assert result["categories"] == []


@pytest.mark.parametrize("tags,expected", [
    ({"shop": "supermarket"}, "grocery"),
    ({"amenity": "fuel"}, "gas_station"),
    ({"amenity": "clinic"}, "medical"),
    ({"shop": "clothing"}, "retail"),
    ({}, None),
])
def test_categorize_maps_tags(tags, expected):
    assert _categorize(tags) == expected


def test_high_density_score():
    """More than 50 density-eligible items → density_score = 'High'."""
    # 51 restaurants (density category) → High
    elements = [make_node(amenity="restaurant", name=f"R{i}") for i in range(51)]
    result = _transform_competitor(elements, 1609)
    assert result["density_score"] == "High"
