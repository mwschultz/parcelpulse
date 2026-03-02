import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.cache import get_cached, set_cached

CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/geographies/coordinates"
CENSUS_ACS_URL = "https://api.census.gov/data/2023/acs/acs5"
TIGERWEB_BASE = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2023/MapServer"

TIGERWEB_LAYERS = {
    "block_group": 10,
    "tract": 8,
    "county": 84,
}

ACS_VARIABLES = ",".join([
    "B01003_001E",  # Total population
    "B01002_001E",  # Median age
    "B19013_001E",  # Median household income
    "B25077_001E",  # Median home value
    "B25064_001E",  # Median gross rent
    "B11001_001E",  # Total households
    # Education: HS diploma, GED, some college (<1yr), some college (1+yr no degree),
    #            associates, bachelors, masters, professional, doctorate
    "B15003_017E", "B15003_018E", "B15003_019E", "B15003_020E",
    "B15003_021E", "B15003_022E", "B15003_023E", "B15003_024E", "B15003_025E",
    # Race: White, Black, American Indian, Asian, Pacific Islander
    "B02001_002E", "B02001_003E", "B02001_004E", "B02001_005E", "B02001_006E",
])


def _build_geoid(fips: dict, level: str) -> str:
    if level == "block_group":
        return f"{fips['state']}{fips['county']}{fips['tract']}{fips['block_group']}"
    elif level == "tract":
        return f"{fips['state']}{fips['county']}{fips['tract']}"
    else:
        return f"{fips['state']}{fips['county']}"


def _build_label(fips: dict, level: str) -> str:
    county = fips.get("county_name") or f"County {fips.get('county', '')}"
    if level == "block_group":
        parts = [f"Block Group {fips['block_group']}", f"Tract {fips['tract']}"]
        if fips.get("county_name"):
            parts.append(county)
        return " · ".join(parts)
    elif level == "tract":
        return f"Tract {fips['tract']} · {county}"
    else:
        return county


async def _get_fips(lat: float, lng: float) -> dict:
    """Convert lat/lng to FIPS with geography level via fallback chain."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(CENSUS_GEOCODER_URL, params={
            "x": lng,
            "y": lat,
            "benchmark": "Public_AR_Current",
            "vintage": "Current_Current",
            "layers": "10,8,84",
            "format": "json",
        })
        resp.raise_for_status()
        data = resp.json()

    geos = data.get("result", {}).get("geographies", {})

    # Pull county name from Counties layer if present (available at all levels)
    counties = geos.get("Counties", [])
    county_name = counties[0].get("NAME", "") if counties else ""

    # Block group (most granular)
    bgs = geos.get("Census Block Groups", [])
    if bgs:
        bg = bgs[0]
        return {
            "level": "block_group",
            "state": bg["STATE"],
            "county": bg["COUNTY"],
            "tract": bg["TRACT"],
            "block_group": bg["BLKGRP"],
            "county_name": county_name,
        }

    # Tract fallback
    tracts = geos.get("Census Tracts", [])
    if tracts:
        t = tracts[0]
        return {
            "level": "tract",
            "state": t["STATE"],
            "county": t["COUNTY"],
            "tract": t["TRACT"],
            "county_name": county_name,
        }

    # County fallback
    if counties:
        c = counties[0]
        return {
            "level": "county",
            "state": c["STATE"],
            "county": c["COUNTY"],
            "county_name": c.get("NAME", f"County {c['COUNTY']}"),
        }

    return {"level": "unavailable"}


async def _get_boundary(fips: dict, level: str, db: AsyncSession) -> dict | None:
    """Fetch Census boundary GeoJSON from TIGERweb, cached 90 days."""
    geoid = _build_geoid(fips, level)
    cache_key = f"tigerweb:{level}:{geoid}"

    cached = await get_cached(db, cache_key)
    if cached:
        return cached

    layer = TIGERWEB_LAYERS[level]
    url = f"{TIGERWEB_BASE}/{layer}/query"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(url, params={
            "where": f"GEOID='{geoid}'",
            "outFields": "GEOID,NAME",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson",
        })
        resp.raise_for_status()
        data = resp.json()

    features = data.get("features", [])
    if not features:
        return None

    feature = features[0]
    await set_cached(db, cache_key, "tigerweb", feature, expires_days=90)
    return feature


def _transform_acs(raw: dict) -> dict:
    """Transform flat Census variable dict into structured demographics dict."""
    def to_int(v: str) -> int:
        try:
            return max(int(v), 0)
        except (ValueError, TypeError):
            return 0

    def to_float(v: str) -> float:
        try:
            return max(float(v), 0.0)
        except (ValueError, TypeError):
            return 0.0

    return {
        "population": to_int(raw.get("B01003_001E")),
        "median_age": to_float(raw.get("B01002_001E")),
        "median_household_income": to_int(raw.get("B19013_001E")),
        "median_home_value": to_int(raw.get("B25077_001E")),
        "median_gross_rent": to_int(raw.get("B25064_001E")),
        "households": to_int(raw.get("B11001_001E")),
        "education": {
            "hs_diploma": to_int(raw.get("B15003_017E")) + to_int(raw.get("B15003_018E")),
            "some_college": to_int(raw.get("B15003_019E")) + to_int(raw.get("B15003_020E")),
            "associates": to_int(raw.get("B15003_021E")),
            "bachelors": to_int(raw.get("B15003_022E")),
            "graduate": (
                to_int(raw.get("B15003_023E")) +
                to_int(raw.get("B15003_024E")) +
                to_int(raw.get("B15003_025E"))
            ),
        },
        "race": {
            "white": to_int(raw.get("B02001_002E")),
            "black": to_int(raw.get("B02001_003E")),
            "american_indian": to_int(raw.get("B02001_004E")),
            "asian": to_int(raw.get("B02001_005E")),
            "pacific_islander": to_int(raw.get("B02001_006E")),
        },
    }


async def _get_acs(fips: dict, level: str, db: AsyncSession) -> dict | None:
    """Fetch ACS 5-Year data at the resolved geography level, cached 30 days."""
    geoid = _build_geoid(fips, level)
    cache_key = f"census:{level}:{geoid}"

    cached = await get_cached(db, cache_key)
    if cached:
        return _transform_acs(cached)

    if level == "block_group":
        geo_for = f"block group:{fips['block_group']}"
        geo_in = f"state:{fips['state']} county:{fips['county']} tract:{fips['tract']}"
    elif level == "tract":
        geo_for = f"tract:{fips['tract']}"
        geo_in = f"state:{fips['state']} county:{fips['county']}"
    else:
        geo_for = f"county:{fips['county']}"
        geo_in = f"state:{fips['state']}"

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(CENSUS_ACS_URL, params={
            "get": ACS_VARIABLES,
            "for": geo_for,
            "in": geo_in,
            "key": settings.CENSUS_API_KEY,
        })
        resp.raise_for_status()
        rows = resp.json()

    if len(rows) < 2:
        return None

    raw = dict(zip(rows[0], rows[1]))
    await set_cached(db, cache_key, "census", raw, expires_days=30)
    return _transform_acs(raw)


async def get_demographics(lat: float, lng: float, db: AsyncSession) -> dict:
    """Full demographics orchestration: FIPS → ACS + TIGERweb (concurrent)."""
    fips = await _get_fips(lat, lng)
    level = fips.get("level", "unavailable")

    if level == "unavailable":
        return {
            "geography_level": "unavailable",
            "geography_label": "",
            "boundary": None,
            "population": 0,
            "median_age": 0.0,
            "median_household_income": 0,
            "median_home_value": 0,
            "median_gross_rent": 0,
            "households": 0,
            "education": {k: 0 for k in ["hs_diploma", "some_college", "associates", "bachelors", "graduate"]},
            "race": {k: 0 for k in ["white", "black", "american_indian", "asian", "pacific_islander"]},
            "fips": fips,
        }

    # Fetch ACS data then boundary polygon (same DB session — must be sequential)
    acs_data = await _get_acs(fips, level, db)
    boundary = await _get_boundary(fips, level, db)

    if acs_data is None:
        acs_data = {
            "population": 0, "median_age": 0.0, "median_household_income": 0,
            "median_home_value": 0, "median_gross_rent": 0, "households": 0,
            "education": {k: 0 for k in ["hs_diploma", "some_college", "associates", "bachelors", "graduate"]},
            "race": {k: 0 for k in ["white", "black", "american_indian", "asian", "pacific_islander"]},
        }

    return {
        **acs_data,
        "geography_level": level,
        "geography_label": _build_label(fips, level),
        "boundary": boundary,
        "fips": fips,
    }
