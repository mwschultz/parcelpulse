import asyncio
import logging
import re

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)

GEOAPIFY_PLACES_URL = "https://api.geoapify.com/v2/places"

# Geoapify category strings mapped to our internal categories in competitors.py
GEOAPIFY_CATEGORIES = [
    "commercial.supermarket",
    "commercial.convenience",
    "service.vehicle.fuel",
    "catering.fast_food",
    "catering.restaurant",
    "healthcare.pharmacy",
    "service.financial.bank",
    "healthcare.clinic_or_praxis",
    "commercial",  # catch-all for retail; specific subcategories above take priority
]

_CATEGORIES_PARAM = ",".join(GEOAPIFY_CATEGORIES)
_PAGE_SIZE = 100
_MAX_PAGES = 3

# Respect the free-tier 5 RPS limit across concurrent requests
_sem = asyncio.Semaphore(5)


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
    wait=wait_exponential(multiplier=2, min=2, max=8),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
async def _fetch_page(client: httpx.AsyncClient, lat: float, lng: float, radius_m: int, offset: int) -> list:
    async with _sem:
        try:
            resp = await client.get(
                GEOAPIFY_PLACES_URL,
                params={
                    "categories": _CATEGORIES_PARAM,
                    "filter": f"circle:{lng},{lat},{radius_m}",
                    "limit": _PAGE_SIZE,
                    "offset": offset,
                    "apiKey": settings.GEOAPIFY_API_KEY,
                },
            )
            resp.raise_for_status()
            return resp.json().get("features", [])
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Geoapify Places HTTP error (retryable=%s)",
                exc.response.status_code == 429 or exc.response.status_code >= 500,
                extra={
                    "status_code": exc.response.status_code,
                    "url": _redact_url(exc.request.url),
                    "body_preview": exc.response.text[:500],
                },
            )
            raise
        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            logger.warning(
                "Geoapify Places connection error",
                extra={"error_type": type(exc).__name__, "url": _redact_url(GEOAPIFY_PLACES_URL)},
            )
            raise


async def fetch_places(lat: float, lng: float, radius_m: int) -> list:
    """Fetch POI features from Geoapify Places, paginating up to _MAX_PAGES."""
    features: list = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(15.0, connect=5.0)) as client:
        for page in range(_MAX_PAGES):
            page_features = await _fetch_page(client, lat, lng, radius_m, offset=page * _PAGE_SIZE)
            features.extend(page_features)
            if len(page_features) < _PAGE_SIZE:
                break
    return features
