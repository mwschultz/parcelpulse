import json
import logging
import math

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.cache import get_cached, set_cached
from app.services.rate_limiter import check_and_increment

logger = logging.getLogger(__name__)

NCONEMAP_LAYER1 = f"{settings.NCONEMAP_BASE_URL}/1/query"
BBOX_DEGREES = 0.004  # ~0.25 mi radius
UNAVAILABLE_MESSAGE = "Parcel data is temporarily unavailable — NC OneMap is not responding."

PARCEL_FIELDS = (
    "parno,ownname,owntype,improvval,landval,parval,"
    "parusedesc,gisacres,struct,structyear,siteadd,scity,saledatetx"
)


def _centroid(geometry: dict | None) -> tuple[float, float] | tuple[None, None]:
    if not geometry:
        return None, None
    gtype = geometry.get("type", "")
    coords = geometry.get("coordinates", [])
    if gtype == "Polygon":
        ring = coords[0] if coords else []
    elif gtype == "MultiPolygon":
        ring = [pt for poly in coords for pt in (poly[0] if poly else [])]
    else:
        return None, None
    if not ring:
        return None, None
    return sum(c[1] for c in ring) / len(ring), sum(c[0] for c in ring) / len(ring)


def _haversine_mi(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 3958.8
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _to_int(v) -> int:
    try:
        return max(int(float(v)), 0)
    except (TypeError, ValueError):
        return 0


def _to_float(v) -> float:
    try:
        return max(float(v), 0.0)
    except (TypeError, ValueError):
        return 0.0


def _parse_parcel(feature: dict, search_lat: float, search_lng: float) -> dict:
    props = feature.get("properties") or {}
    geometry = feature.get("geometry")
    clat, clng = _centroid(geometry)
    distance_mi = round(_haversine_mi(search_lat, search_lng, clat, clng), 2) if clat is not None else None
    return {
        "parno": props.get("parno") or "",
        "address": props.get("siteadd") or "",
        "city": props.get("scity") or "",
        "owner": props.get("ownname") or "",
        "owner_type": props.get("owntype") or "",
        "land_value": _to_int(props.get("landval")),
        "improvement_value": _to_int(props.get("improvval")),
        "total_value": _to_int(props.get("parval")),
        "use_description": props.get("parusedesc") or "",
        "acres": _to_float(props.get("gisacres")),
        "has_structure": props.get("struct") == "Y",
        "year_built": _to_int(props.get("structyear")) or None,
        "sale_date": (props.get("saledatetx") or "").split("T")[0].split(" ")[0] or None,
        "distance_mi": distance_mi,
        "geometry": geometry,
    }


def _unavailable() -> dict:
    return {
        "coverage": True,
        "state": "NC",
        "message": UNAVAILABLE_MESSAGE,
        "parcels": [],
        "rate_limited": False,
        "unavailable": True,
    }


def _error_envelope(data) -> str | None:
    """Describe an ArcGIS error payload served with a 200 status, else None.

    ArcGIS Server returns HTTP 200 with an error body in at least two shapes: a
    site-level {"status": "error", "messages": [...]} — e.g. "Could not access
    any server machines", seen 2026-08-20 — and a REST-level
    {"error": {"code", "message"}}. raise_for_status() passes both, and reading
    .features off them yields an empty list, which would tell the user there are
    no parcels here *and* get cached as an empty result for 30 days.
    """
    if not isinstance(data, dict):
        return f"unexpected payload type {type(data).__name__}"
    if data.get("status") == "error":
        messages = data.get("messages") or []
        return "; ".join(str(m) for m in messages) or "unspecified error"
    err = data.get("error")
    if isinstance(err, dict):
        return f"code {err.get('code')}: {err.get('message')}"
    return None


def _transform_parcel(features: list, lat: float, lng: float) -> dict:
    parcels = [_parse_parcel(f, lat, lng) for f in features]
    parcels.sort(key=lambda p: p["distance_mi"] if p["distance_mi"] is not None else float("inf"))
    return {"coverage": True, "state": "NC", "parcels": parcels, "rate_limited": False}


async def _get_nc_parcels(lat: float, lng: float, db: AsyncSession) -> dict:
    cache_key = f"nconemap:{round(lat, 3)}:{round(lng, 3)}"

    cached = await get_cached(db, cache_key)
    if cached:
        return _transform_parcel(cached["features"], lat, lng)

    allowed = await check_and_increment("nconemap", settings.NCONEMAP_DAILY_CAP, db)
    if not allowed:
        return {"coverage": True, "state": "NC", "parcels": [], "rate_limited": True}

    bbox = {
        "xmin": lng - BBOX_DEGREES,
        "ymin": lat - BBOX_DEGREES,
        "xmax": lng + BBOX_DEGREES,
        "ymax": lat + BBOX_DEGREES,
        "spatialReference": {"wkid": 4326},
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(NCONEMAP_LAYER1, data={
                "where": "1=1",
                "geometry": json.dumps(bbox),
                "geometryType": "esriGeometryEnvelope",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": PARCEL_FIELDS,
                "outSR": "4326",
                "returnGeometry": "true",
                "f": "geojson",
            })
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.warning("NC OneMap abandoned: status %s", e.response.status_code)
        return _unavailable()
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning("NC OneMap abandoned: %s", type(e).__name__)
        return _unavailable()
    except Exception as e:
        logger.warning("NC OneMap failed: %s", type(e).__name__)
        return _unavailable()

    problem = _error_envelope(data)
    if problem:
        logger.warning("NC OneMap error payload: %s", problem)
        return _unavailable()

    raw = {"features": data.get("features", [])}
    await set_cached(db, cache_key, "nconemap", raw, expires_days=30)
    return _transform_parcel(raw["features"], lat, lng)


async def get_parcel_data(lat: float, lng: float, state: str, db: AsyncSession) -> dict:
    if state.upper() != "NC":
        return {
            "coverage": False,
            "state": state,
            "message": "Parcel data is available for North Carolina addresses.",
            "parcels": [],
            "rate_limited": False,
        }
    return await _get_nc_parcels(lat, lng, db)
