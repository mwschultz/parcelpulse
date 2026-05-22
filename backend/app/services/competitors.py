import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.cache import get_cached, set_cached
from app.services.geoapify_places import fetch_places
from app.services.rate_limiter import check_and_increment

logger = logging.getLogger(__name__)

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


def _categorize_feature(categories: list[str]) -> str | None:
    """Map a Geoapify categories array to an internal category key, in priority order."""
    cat_set = set(categories)
    if "commercial.supermarket" in cat_set:
        return "grocery"
    if "service.vehicle.fuel" in cat_set:
        return "gas_station"
    if "commercial.convenience" in cat_set:
        return "convenience"
    if "catering.fast_food" in cat_set:
        return "fast_food"
    if "catering.restaurant" in cat_set:
        return "restaurant"
    if "healthcare.pharmacy" in cat_set:
        return "pharmacy"
    if "service.financial.bank" in cat_set:
        return "bank"
    if "healthcare.clinic_or_praxis" in cat_set:
        return "medical"
    if any(c.startswith("commercial") for c in cat_set):
        return "retail"
    return None


def _transform_competitor(features: list, radius_m: int) -> dict:
    items = []
    for feature in features:
        props = feature.get("properties", {})
        category = _categorize_feature(props.get("categories", []))
        if category is None:
            continue

        lat = props.get("lat")
        lng = props.get("lon")
        if lat is None or lng is None:
            continue

        items.append({
            "lat": lat,
            "lng": lng,
            "name": props.get("name", ""),
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


async def get_competitor_data(lat: float, lng: float, db: AsyncSession, radius_m: int = 1609) -> dict:
    # Bump the version token whenever GEOAPIFY_CATEGORIES or other request
    # parameters change shape — the new key orphans stale cache rows so the
    # next search refetches with the updated request.
    cache_key = f"geoapify_places:v2:{round(lat, 3)}:{round(lng, 3)}:{radius_m}"

    cached = await get_cached(db, cache_key)
    if cached:
        return _transform_competitor(cached["features"], radius_m)

    allowed = await check_and_increment("geoapify_places", settings.GEOAPIFY_DAILY_CAP, db)
    if not allowed:
        return {"items": [], "categories": [], "density_score": "Low", "radius_m": radius_m, "rate_limited": True}

    features = await fetch_places(lat, lng, radius_m)

    await set_cached(db, cache_key, "geoapify_places", {"features": features}, expires_days=7)
    return _transform_competitor(features, radius_m)
