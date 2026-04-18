"""Tests for the Geoapify Places client and competitor transform/scoring."""

import httpx
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.geoapify_places import fetch_places
from app.services.competitors import _categorize_feature, _transform_competitor


# ─── helpers ────────────────────────────────────────────────────────────────

def _mock_response(features: list, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = ""
    resp.headers = {}
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"features": features}
    return resp


def _make_feature(categories: list[str], lat: float, lng: float, name: str = "Test") -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
        "properties": {"lat": lat, "lon": lng, "name": name, "categories": categories},
    }


def _patched_client(mock_client: AsyncMock):
    """Context manager that replaces httpx.AsyncClient with mock_client."""
    patcher = patch("app.services.geoapify_places.httpx.AsyncClient")
    MockClient = patcher.start()
    MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
    return patcher


# ─── _categorize_feature ─────────────────────────────────────────────────────

def test_categorize_supermarket():
    assert _categorize_feature(["commercial.supermarket", "commercial"]) == "grocery"


def test_categorize_convenience():
    assert _categorize_feature(["commercial.convenience", "commercial"]) == "convenience"


def test_categorize_fast_food():
    assert _categorize_feature(["catering.fast_food", "catering"]) == "fast_food"


def test_categorize_restaurant():
    assert _categorize_feature(["catering.restaurant", "catering"]) == "restaurant"


def test_categorize_fast_food_beats_restaurant():
    assert _categorize_feature(["catering.fast_food", "catering.restaurant"]) == "fast_food"


def test_categorize_gas_beats_convenience():
    assert _categorize_feature(["service.vehicle.fuel", "commercial.convenience"]) == "gas_station"


def test_categorize_gas_station():
    assert _categorize_feature(["service.vehicle.fuel", "service.vehicle", "service"]) == "gas_station"


def test_categorize_pharmacy():
    assert _categorize_feature(["healthcare.pharmacy"]) == "pharmacy"


def test_categorize_bank():
    assert _categorize_feature(["service.financial.bank"]) == "bank"



def test_categorize_medical():
    assert _categorize_feature(["healthcare.clinic_or_praxis"]) == "medical"


def test_categorize_retail_fallback():
    assert _categorize_feature(["commercial.clothing", "commercial"]) == "retail"


def test_categorize_unknown_returns_none():
    assert _categorize_feature(["leisure.park"]) is None


def test_categorize_empty_returns_none():
    assert _categorize_feature([]) is None


# ─── _transform_competitor ──────────────────────────────────────────────────

def test_transform_empty_features():
    result = _transform_competitor([], 1609)
    assert result["items"] == []
    assert result["categories"] == []
    assert result["density_score"] == "Low"
    assert result["radius_m"] == 1609


def test_transform_output_shape():
    features = [_make_feature(["commercial.supermarket", "commercial"], 35.0, -80.0, "Walmart")]
    result = _transform_competitor(features, 1609)
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["lat"] == 35.0
    assert item["lng"] == -80.0
    assert item["name"] == "Walmart"
    assert item["category"] == "grocery"
    assert result["categories"][0]["key"] == "grocery"
    assert result["categories"][0]["count"] == 1


def test_transform_skips_missing_coords():
    feature = {
        "type": "Feature",
        "geometry": None,
        "properties": {"lat": None, "lon": -80.0, "name": "X", "categories": ["catering.restaurant"]},
    }
    result = _transform_competitor([feature], 1609)
    assert result["items"] == []


def test_transform_density_high():
    features = [
        _make_feature(["catering.restaurant", "catering"], 35.0 + i * 0.001, -80.0)
        for i in range(51)
    ]
    result = _transform_competitor(features, 1609)
    assert result["density_score"] == "High"


def test_transform_density_medium():
    features = [
        _make_feature(["catering.restaurant", "catering"], 35.0 + i * 0.001, -80.0)
        for i in range(25)
    ]
    result = _transform_competitor(features, 1609)
    assert result["density_score"] == "Medium"


def test_transform_density_low():
    features = [_make_feature(["catering.restaurant", "catering"], 35.0, -80.0)]
    result = _transform_competitor(features, 1609)
    assert result["density_score"] == "Low"


def test_transform_categories_sorted_by_count():
    features = [
        _make_feature(["catering.restaurant", "catering"], 35.0, -80.0),
        _make_feature(["catering.restaurant", "catering"], 35.1, -80.0),
        _make_feature(["commercial.supermarket", "commercial"], 35.2, -80.0),
    ]
    result = _transform_competitor(features, 1609)
    assert result["categories"][0]["key"] == "restaurant"
    assert result["categories"][0]["count"] == 2
    assert result["categories"][1]["key"] == "grocery"
    assert result["categories"][1]["count"] == 1


# ─── fetch_places ─────────────────────────────────────────────────────────────

async def test_fetch_places_single_page():
    features = [_make_feature(["catering.restaurant"], 35.0, -80.0)]
    mock_client = AsyncMock()
    mock_client.get.return_value = _mock_response(features)

    patcher = _patched_client(mock_client)
    try:
        result = await fetch_places(35.0, -80.0, 1609)
    finally:
        patcher.stop()

    assert result == features
    assert mock_client.get.call_count == 1


async def test_fetch_places_passes_correct_params():
    mock_client = AsyncMock()
    mock_client.get.return_value = _mock_response([])

    patcher = _patched_client(mock_client)
    try:
        await fetch_places(35.219, -80.853, 1609)
    finally:
        patcher.stop()

    params = mock_client.get.call_args.kwargs["params"]
    assert params["filter"] == "circle:-80.853,35.219,1609"
    assert params["limit"] == 100
    assert params["offset"] == 0
    assert "categories" in params
    assert params["apiKey"] == "test-key"


async def test_fetch_places_paginates_when_full_page():
    page1 = [_make_feature(["catering.restaurant"], 35.0 + i * 0.001, -80.0) for i in range(100)]
    page2 = [_make_feature(["catering.restaurant"], 36.0, -80.0)]
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(side_effect=[_mock_response(page1), _mock_response(page2)])

    patcher = _patched_client(mock_client)
    try:
        result = await fetch_places(35.0, -80.0, 1609)
    finally:
        patcher.stop()

    assert len(result) == 101
    assert mock_client.get.call_count == 2
    offsets = [call.kwargs["params"]["offset"] for call in mock_client.get.call_args_list]
    assert offsets == [0, 100]


async def test_fetch_places_stops_at_max_pages():
    full_page = [_make_feature(["catering.restaurant"], 35.0 + i * 0.001, -80.0) for i in range(100)]
    mock_client = AsyncMock()
    mock_client.get.return_value = _mock_response(full_page)

    patcher = _patched_client(mock_client)
    try:
        result = await fetch_places(35.0, -80.0, 1609)
    finally:
        patcher.stop()

    # _MAX_PAGES = 3, so at most 3 requests even if each returns a full page
    assert mock_client.get.call_count == 3
    assert len(result) == 300


async def test_fetch_places_propagates_http_error():
    with patch("app.services.geoapify_places._fetch_page", side_effect=httpx.ConnectError("timeout")):
        with pytest.raises(httpx.ConnectError):
            await fetch_places(35.0, -80.0, 1609)


async def test_fetch_places_propagates_status_error():
    request = httpx.Request("GET", "https://api.geoapify.com/v2/places")
    response = httpx.Response(502, request=request)
    exc = httpx.HTTPStatusError("Bad Gateway", request=request, response=response)

    with patch("app.services.geoapify_places._fetch_page", side_effect=exc):
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_places(35.0, -80.0, 1609)
