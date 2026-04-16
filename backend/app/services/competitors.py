import logging
import re

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
    wait_random,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cache import get_cached, set_cached

logger = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

CATEGORIES = {
    "grocery":     {"label": "Grocery",     "color": "#22c55e"},
    "convenience": {"label": "Convenience", "color": "#eab308"},
    "restaurant":  {"label": "Restaurant",  "color": "#f97316"},
    "fast_food":   {"label": "Fast Food",   "color": "#ef4444"},
    "pharmacy":    {"label": "Pharmacy",    "color": "#ec4899"},
    "bank":        {"label": "Bank",        "color": "#3b82f6"},
    "gas_station": {"label": "Gas Station", "color": "#6b7280"},
    "medical":     {"label": "Medical",     "color": "#a855f7"},
    "retail":      {"label": "Retail",      "color": "#0ea5e9"},
}

DENSITY_CATEGORIES = {"grocery", "convenience", "restaurant", "fast_food", "pharmacy", "bank", "gas_station", "medical", "retail"}


def _categorize(tags: dict) -> str | None:
    shop = tags.get("shop", "")
    amenity = tags.get("amenity", "")

    if shop == "supermarket":
        return "grocery"
    if shop == "convenience":
        return "convenience"
    if amenity == "restaurant":
        return "restaurant"
    if amenity == "fast_food":
        return "fast_food"
    if amenity == "pharmacy":
        return "pharmacy"
    if amenity == "bank":
        return "bank"
    if amenity == "fuel":
        return "gas_station"
    if amenity in ("clinic", "doctors"):
        return "medical"
    if shop:
        return "retail"
    return None


def _build_query(lat: float, lng: float, radius_m: int) -> str:
    r = radius_m
    return f"""[out:json][timeout:30];
(
  node["shop"="supermarket"](around:{r},{lat},{lng});
  way["shop"="supermarket"](around:{r},{lat},{lng});
  node["shop"="convenience"](around:{r},{lat},{lng});
  way["shop"="convenience"](around:{r},{lat},{lng});
  node["amenity"="restaurant"](around:{r},{lat},{lng});
  way["amenity"="restaurant"](around:{r},{lat},{lng});
  node["amenity"="fast_food"](around:{r},{lat},{lng});
  way["amenity"="fast_food"](around:{r},{lat},{lng});
  node["amenity"="pharmacy"](around:{r},{lat},{lng});
  way["amenity"="pharmacy"](around:{r},{lat},{lng});
  node["amenity"="bank"](around:{r},{lat},{lng});
  way["amenity"="bank"](around:{r},{lat},{lng});
  node["amenity"="fuel"](around:{r},{lat},{lng});
  way["amenity"="fuel"](around:{r},{lat},{lng});
  node["amenity"="clinic"](around:{r},{lat},{lng});
  way["amenity"="clinic"](around:{r},{lat},{lng});
  node["amenity"="doctors"](around:{r},{lat},{lng});
  way["amenity"="doctors"](around:{r},{lat},{lng});
  node["shop"](around:{r},{lat},{lng});
  way["shop"](around:{r},{lat},{lng});
);
out center;
"""


def _transform_competitor(elements: list, radius_m: int) -> dict:
    """Transform raw Overpass elements into categorized competitor response."""
    items = []
    for element in elements:
        tags = element.get("tags", {})
        category = _categorize(tags)
        if category is None:
            continue

        if element["type"] == "node":
            item_lat = element["lat"]
            item_lng = element["lon"]
        elif element["type"] == "way":
            center = element.get("center", {})
            item_lat = center.get("lat")
            item_lng = center.get("lon")
            if item_lat is None or item_lng is None:
                continue
        else:
            continue

        items.append({
            "lat": item_lat,
            "lng": item_lng,
            "name": tags.get("name", ""),
            "category": category,
        })

    counts: dict[str, int] = {key: 0 for key in CATEGORIES}
    for item in items:
        counts[item["category"]] = counts.get(item["category"], 0) + 1

    categories = [
        {
            "key": key,
            "label": CATEGORIES[key]["label"],
            "color": CATEGORIES[key]["color"],
            "count": counts[key],
        }
        for key in CATEGORIES
        if counts[key] > 0
    ]
    categories.sort(key=lambda c: c["count"], reverse=True)

    density_total = sum(counts[k] for k in DENSITY_CATEGORIES)
    if density_total > 50:
        density_score = "High"
    elif density_total >= 20:
        density_score = "Medium"
    else:
        density_score = "Low"

    return {
        "items": items,
        "categories": categories,
        "density_score": density_score,
        "radius_m": radius_m,
    }


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return isinstance(exc, (httpx.TimeoutException, httpx.ConnectError))


def _redact_url(url: object) -> str:
    return re.sub(
        r'(?i)([?&](?:api[_-]?key|key|token|secret|password)=)[^&]*',
        r'\1[redacted]',
        str(url),
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10) + wait_random(0, 1),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
async def _fetch_overpass(query: str) -> dict:
    async with httpx.AsyncClient(timeout=httpx.Timeout(35.0, connect=5.0)) as client:
        try:
            resp = await client.post(OVERPASS_URL, data={"data": query})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            log_extra: dict = {
                "status_code": status_code,
                "url": _redact_url(exc.request.url),
                "body_preview": exc.response.text[:500],
            }
            retry_after = exc.response.headers.get("Retry-After")
            if retry_after:
                log_extra["retry_after"] = retry_after
            logger.warning(
                "Overpass HTTP error (retryable=%s)",
                status_code == 429 or status_code >= 500,
                extra=log_extra,
            )
            raise
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            logger.warning(
                "Overpass connection error",
                extra={"error_type": type(exc).__name__, "url": OVERPASS_URL},
            )
            raise


async def get_competitor_data(lat: float, lng: float, db: AsyncSession, radius_m: int = 1609) -> dict:
    cache_key = f"overpass:{round(lat, 3)}:{round(lng, 3)}:{radius_m}"

    cached = await get_cached(db, cache_key)
    if cached:
        return _transform_competitor(cached["elements"], radius_m)

    query = _build_query(lat, lng, radius_m)
    data = await _fetch_overpass(query)

    raw = {"elements": data.get("elements", [])}
    await set_cached(db, cache_key, "overpass", raw, expires_days=7)
    return _transform_competitor(raw["elements"], radius_m)
