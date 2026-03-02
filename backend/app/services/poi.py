import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cache import get_cached, set_cached

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

# Categories included in density score (exclude retail catch-all)
DENSITY_CATEGORIES = {"grocery", "convenience", "restaurant", "fast_food", "pharmacy", "bank", "gas_station", "medical"}


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


def _transform_poi(elements: list, radius_m: int) -> dict:
    """Transform raw Overpass elements into categorized POI response."""
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


async def get_poi(lat: float, lng: float, db: AsyncSession, radius_m: int = 1609) -> dict:
    cache_key = f"overpass:{round(lat, 3)}:{round(lng, 3)}:{radius_m}"

    cached = await get_cached(db, cache_key)
    if cached:
        return _transform_poi(cached["elements"], radius_m)

    query = _build_query(lat, lng, radius_m)
    async with httpx.AsyncClient(timeout=35.0) as client:
        resp = await client.post(OVERPASS_URL, data={"data": query})
        resp.raise_for_status()
        data = resp.json()

    raw = {"elements": data.get("elements", [])}
    await set_cached(db, cache_key, "overpass", raw, expires_days=7)
    return _transform_poi(raw["elements"], radius_m)
