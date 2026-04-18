"""Unit tests for app.services.competitors (Geoapify Places backend)."""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.competitors import get_competitor_data, _transform_competitor, _categorize_feature

from conftest import make_cache_hit, make_cache_miss


LAT = 35.8304
LNG = -78.6679


def make_feature(categories: list[str], lat: float = LAT, lng: float = LNG, name: str = "Test") -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
        "properties": {"lat": lat, "lon": lng, "name": name, "categories": categories},
    }


# ─── get_competitor_data — cache hit ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_hit_returns_categories(mock_db):
    """Cached Geoapify features → categories and density_score returned without HTTP."""
    features = [
        make_feature(["commercial.supermarket", "commercial"], name="Grocery A"),
        make_feature(["commercial.supermarket", "commercial"], name="Grocery B"),
        make_feature(["catering.restaurant", "catering"], name="Rest A"),
    ]
    mock_db.execute.return_value = make_cache_hit({"features": features})

    result = await get_competitor_data(LAT, LNG, mock_db)

    assert result["density_score"] in ("Low", "Medium", "High")
    keys = [c["key"] for c in result["categories"]]
    assert "grocery" in keys
    assert "restaurant" in keys
    grocery = next(c for c in result["categories"] if c["key"] == "grocery")
    assert grocery["count"] == 2


# ─── get_competitor_data — cache miss ────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_miss_fetches_and_caches(mock_db):
    """Cache miss → fetch_places called → set_cached called → result returned."""
    mock_db.execute.return_value = make_cache_miss()

    features = [make_feature(["service.financial.bank"])]

    with (
        patch("app.services.competitors.fetch_places", new_callable=AsyncMock, return_value=features),
        patch("app.services.competitors.set_cached", new_callable=AsyncMock) as mock_set,
    ):
        result = await get_competitor_data(LAT, LNG, mock_db)

    assert result["categories"][0]["key"] == "bank"
    mock_set.assert_awaited_once()
    # Verify raw features are cached, not transformed results
    _, call_kwargs = mock_set.call_args
    cached_data = mock_set.call_args.args[3]
    assert "features" in cached_data


@pytest.mark.asyncio
async def test_empty_features_low_density(mock_db):
    """No features in cache → density_score is 'Low'."""
    mock_db.execute.return_value = make_cache_hit({"features": []})

    result = await get_competitor_data(LAT, LNG, mock_db)
    assert result["density_score"] == "Low"
    assert result["categories"] == []


# ─── _categorize_feature ─────────────────────────────────────────────────────

@pytest.mark.parametrize("categories,expected", [
    (["commercial.supermarket", "commercial"], "grocery"),
    (["commercial.convenience", "commercial"], "convenience"),
    (["catering.fast_food", "catering"], "fast_food"),
    (["catering.restaurant", "catering"], "restaurant"),
    (["healthcare.pharmacy"], "pharmacy"),
    (["service.financial.bank"], "bank"),
    (["service.vehicle.fuel", "service.vehicle", "service"], "gas_station"),
    (["healthcare.clinic_or_praxis"], "medical"),
    (["commercial.clothing", "commercial"], "retail"),
    ([], None),
])
def test_categorize_feature_mappings(categories, expected):
    assert _categorize_feature(categories) == expected


# ─── _transform_competitor ──────────────────────────────────────────────────

def test_high_density_score():
    """More than 50 density-eligible items → density_score = 'High'."""
    features = [
        make_feature(["catering.restaurant", "catering"], lat=LAT + i * 0.001)
        for i in range(51)
    ]
    result = _transform_competitor(features, 1609)
    assert result["density_score"] == "High"
