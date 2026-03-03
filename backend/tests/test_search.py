"""Route-level integration tests for POST /api/search."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


SEARCH_PAYLOAD = {
    "address": "4325 Glenwood Ave, Raleigh, NC",
    "lat": 35.8304,
    "lng": -78.6679,
    "state": "NC",
}

MOCK_DEMOGRAPHICS = {
    "geography_level": "block_group",
    "geography_label": "Block Group 1 · Tract 052601",
    "boundary": None,
    "population": 3000,
    "median_age": 35.0,
    "median_household_income": 65000,
    "median_home_value": 300000,
    "median_gross_rent": 1200,
    "households": 1200,
    "education": {"hs_diploma": 400, "some_college": 300, "associates": 150, "bachelors": 250, "graduate": 100},
    "race": {"white": 2000, "black": 500, "american_indian": 50, "asian": 400, "pacific_islander": 50},
    "fips": {"level": "block_group", "state": "37", "county": "183", "tract": "052601", "block_group": "1"},
}

MOCK_COMPETITORS = {
    "items": [],
    "categories": [{"key": "grocery", "label": "Grocery", "color": "#22c55e", "count": 3}],
    "density_score": "Medium",
    "radius_m": 1609,
}

MOCK_PARCELS = {
    "coverage": True,
    "state": "NC",
    "parcels": [{"parno": "1234", "address": "4325 Glenwood Ave", "city": "Raleigh",
                 "owner": "Test Owner", "owner_type": "", "land_value": 100000,
                 "improvement_value": 200000, "total_value": 300000, "use_description": "Commercial",
                 "acres": 0.5, "has_structure": True, "year_built": 2000, "sale_date": None,
                 "distance_mi": 0.1, "geometry": None}],
    "rate_limited": False,
}

MOCK_SPENDING = {
    "bracket": "50000_69999",
    "bracket_label": "$50,000\u2013$69,999",
    "households": 1200,
    "categories": [{"key": "food_at_home", "label": "Food at Home", "per_unit": 5000, "total": 6000000}],
    "is_estimated": False,
}


@pytest.mark.asyncio
async def test_search_returns_200_with_all_fields(http_client):
    with (
        patch("app.routes.api.get_demographics", new_callable=AsyncMock, return_value=MOCK_DEMOGRAPHICS),
        patch("app.routes.api.get_competitor_data", new_callable=AsyncMock, return_value=MOCK_COMPETITORS),
        patch("app.routes.api.get_parcel_data", new_callable=AsyncMock, return_value=MOCK_PARCELS),
        patch("app.routes.api.get_spending", return_value=MOCK_SPENDING),
    ):
        resp = await http_client.post("/api/search", json=SEARCH_PAYLOAD)

    assert resp.status_code == 200
    body = resp.json()
    assert "demographics" in body
    assert "competitors" in body
    assert "parcels" in body
    assert "spending" in body
    assert body["demographics"]["population"] == 3000
    assert body["competitors"]["density_score"] == "Medium"
    assert body["parcels"]["coverage"] is True


@pytest.mark.asyncio
async def test_search_non_nc_parcels_coverage_false(http_client):
    non_nc_parcels = {
        "coverage": False,
        "state": "TX",
        "message": "Parcel data is available for North Carolina addresses.",
        "parcels": [],
        "rate_limited": False,
    }
    with (
        patch("app.routes.api.get_demographics", new_callable=AsyncMock, return_value=MOCK_DEMOGRAPHICS),
        patch("app.routes.api.get_competitor_data", new_callable=AsyncMock, return_value=MOCK_COMPETITORS),
        patch("app.routes.api.get_parcel_data", new_callable=AsyncMock, return_value=non_nc_parcels),
        patch("app.routes.api.get_spending", return_value=MOCK_SPENDING),
    ):
        resp = await http_client.post("/api/search", json={**SEARCH_PAYLOAD, "state": "TX"})

    assert resp.status_code == 200
    assert resp.json()["parcels"]["coverage"] is False


@pytest.mark.asyncio
async def test_search_service_failure_returns_null_field(http_client):
    with (
        patch("app.routes.api.get_demographics", new_callable=AsyncMock, side_effect=RuntimeError("census down")),
        patch("app.routes.api.get_competitor_data", new_callable=AsyncMock, return_value=MOCK_COMPETITORS),
        patch("app.routes.api.get_parcel_data", new_callable=AsyncMock, return_value=MOCK_PARCELS),
        patch("app.routes.api.get_spending", return_value=None),
    ):
        resp = await http_client.post("/api/search", json=SEARCH_PAYLOAD)

    assert resp.status_code == 200
    assert resp.json()["demographics"] is None


@pytest.mark.asyncio
async def test_search_missing_required_field_returns_422(http_client):
    resp = await http_client.post("/api/search", json={"lat": 35.83, "lng": -78.67, "state": "NC"})
    assert resp.status_code == 422
