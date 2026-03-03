"""Unit tests for app.services.demographics."""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.demographics import get_demographics, _transform_acs


LAT = 35.8304
LNG = -78.6679

BLOCK_GROUP_FIPS = {
    "level": "block_group",
    "state": "37",
    "county": "183",
    "tract": "052601",
    "block_group": "1",
    "county_name": "Wake County",
}

SAMPLE_ACS_RAW = {
    "B01003_001E": "3000",
    "B01002_001E": "35.2",
    "B19013_001E": "65000",
    "B25077_001E": "300000",
    "B25064_001E": "1200",
    "B11001_001E": "1200",
    "B15003_017E": "200",
    "B15003_018E": "150",  # hs_diploma = 350
    "B15003_019E": "100",
    "B15003_020E": "80",
    "B15003_021E": "75",
    "B15003_022E": "200",
    "B15003_023E": "60",
    "B15003_024E": "20",
    "B15003_025E": "15",
    "B02001_002E": "2000",
    "B02001_003E": "500",
    "B02001_004E": "50",
    "B02001_005E": "400",
    "B02001_006E": "50",
}


@pytest.mark.asyncio
async def test_unavailable_fips_returns_zeros(mock_db):
    with patch("app.services.demographics._get_fips", new_callable=AsyncMock,
               return_value={"level": "unavailable"}):
        result = await get_demographics(LAT, LNG, mock_db)

    assert result["geography_level"] == "unavailable"
    assert result["population"] == 0
    assert result["households"] == 0
    assert result["median_household_income"] == 0
    assert all(v == 0 for v in result["education"].values())
    assert all(v == 0 for v in result["race"].values())


@pytest.mark.asyncio
async def test_block_group_level_returns_correct_geography(mock_db):
    sample_acs = _transform_acs(SAMPLE_ACS_RAW)

    with (
        patch("app.services.demographics._get_fips", new_callable=AsyncMock,
              return_value=BLOCK_GROUP_FIPS),
        patch("app.services.demographics._get_acs", new_callable=AsyncMock,
              return_value=sample_acs),
        patch("app.services.demographics._get_boundary", new_callable=AsyncMock,
              return_value=None),
    ):
        result = await get_demographics(LAT, LNG, mock_db)

    assert result["geography_level"] == "block_group"
    assert "Block Group" in result["geography_label"]
    assert result["population"] == 3000


def test_transform_acs_sums_education_buckets():
    """hs_diploma = B15003_017E + B15003_018E."""
    result = _transform_acs(SAMPLE_ACS_RAW)
    assert result["education"]["hs_diploma"] == 200 + 150  # 350


def test_transform_acs_clamps_negative_values():
    """Census suppressed value -666666666 → 0."""
    raw = {k: "-666666666" for k in SAMPLE_ACS_RAW}
    result = _transform_acs(raw)
    assert result["population"] == 0
    assert result["median_household_income"] == 0
    assert all(v == 0 for v in result["education"].values())
    assert all(v == 0 for v in result["race"].values())
