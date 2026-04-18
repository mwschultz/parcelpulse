import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.rate_limit import limiter, WRITE_LIMIT
from app.schemas.search import SearchRequest, SearchResponse
from app.schemas.demographics import DemographicsResponse
from app.schemas.competitor import CompetitorResponse
from app.schemas.spending import SpendingResponse
from app.services.demographics import get_demographics
from app.services.competitors import get_competitor_data
from app.services.parcels import get_parcel_data
from app.services.spending import get_spending
from app.schemas.parcel import ParcelResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/geocode")
@limiter.limit(WRITE_LIMIT)
async def geocode(
    request: Request,
    text: str = Query(..., min_length=3, max_length=200),
):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://api.geoapify.com/v1/geocode/autocomplete",
            params={
                "text": text,
                "apiKey": settings.GEOAPIFY_API_KEY,
                "limit": 5,
                "filter": "countrycode:us",
            },
        )
        resp.raise_for_status()
        return resp.json()


@router.post("/search", response_model=SearchResponse)
@limiter.limit(WRITE_LIMIT)
async def search(
    request: Request,
    payload: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        demographics = await get_demographics(payload.lat, payload.lng, db)
    except Exception as e:
        logger.warning("Demographics lookup failed: %s", type(e).__name__)
        demographics = None

    try:
        competitors = await get_competitor_data(payload.lat, payload.lng, db)
    except httpx.HTTPStatusError as e:
        logger.warning(
            "Competitor lookup abandoned",
            extra={"status_code": e.response.status_code},
        )
        competitors = None
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning(
            "Competitor lookup abandoned",
            extra={"error_type": type(e).__name__},
        )
        competitors = None
    except Exception as e:
        logger.warning("Competitor lookup failed: %s", type(e).__name__)
        competitors = None

    try:
        spending = get_spending(
            demographics.get("median_household_income", 0) if demographics else 0,
            demographics.get("households", 0) if demographics else 0,
        )
    except Exception as e:
        logger.warning("Spending calculation failed: %s", type(e).__name__)
        spending = None

    try:
        return SearchResponse(
            address=payload.address,
            lat=payload.lat,
            lng=payload.lng,
            state=payload.state,
            demographics=demographics,
            competitors=competitors,
            spending=spending,
        )
    except Exception as e:
        logger.error("Response serialization failed: %s", type(e).__name__)
        raise HTTPException(status_code=500, detail="Failed to build response")


@router.get("/demographics", response_model=DemographicsResponse)
@limiter.limit(WRITE_LIMIT)
async def demographics(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    db: AsyncSession = Depends(get_db),
):
    return await get_demographics(lat, lng, db)


@router.get("/competitors", response_model=CompetitorResponse)
@limiter.limit(WRITE_LIMIT)
async def competitors(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await get_competitor_data(lat, lng, db)
    except httpx.HTTPStatusError as e:
        logger.warning("Competitor lookup abandoned: status %s", e.response.status_code)
        raise HTTPException(status_code=502, detail="Competitor data unavailable")
    except (httpx.TimeoutException, httpx.ConnectError) as e:
        logger.warning("Competitor lookup abandoned: %s", type(e).__name__)
        raise HTTPException(status_code=503, detail="Competitor data unavailable")
    except Exception as e:
        logger.warning("Competitor lookup failed: %s", type(e).__name__)
        raise HTTPException(status_code=502, detail="Competitor data unavailable")


@router.get("/spending", response_model=SpendingResponse)
@limiter.limit(WRITE_LIMIT)
async def spending(
    request: Request,
    income: float = Query(0, ge=0),
    households: int = Query(0, ge=0),
):
    return get_spending(income, households)


@router.get("/parcels", response_model=ParcelResponse)
@limiter.limit(WRITE_LIMIT)
async def parcels(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    state: str = Query(..., min_length=2, max_length=2),
    db: AsyncSession = Depends(get_db),
):
    return await get_parcel_data(lat, lng, state, db)


@router.get("/usage")
@limiter.limit(WRITE_LIMIT)
async def usage(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return {"usage": []}
