import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.rate_limit import limiter, WRITE_LIMIT
from app.schemas.search import SearchRequest, SearchResponse
from app.services.demographics import get_demographics
from app.services.competitors import get_competitor_data
from app.services.parcels import get_parcel_data
from app.services.spending import get_spending

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api"])


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
        logger.warning(f"Demographics lookup failed: {e}")
        demographics = None

    try:
        competitors = await get_competitor_data(payload.lat, payload.lng, db)
    except Exception as e:
        logger.warning(f"Competitor lookup failed: {e}")
        competitors = None

    try:
        parcel_data = await get_parcel_data(payload.lat, payload.lng, payload.state, db)
    except Exception as e:
        logger.warning(f"Parcel lookup failed: {e}")
        parcel_data = None

    try:
        spending = get_spending(
            demographics.get("median_household_income", 0) if demographics else 0,
            demographics.get("households", 0) if demographics else 0,
        )
    except Exception as e:
        logger.warning(f"Spending calculation failed: {e}")
        spending = None

    try:
        return SearchResponse(
            address=payload.address,
            lat=payload.lat,
            lng=payload.lng,
            state=payload.state,
            demographics=demographics,
            competitors=competitors,
            parcels=parcel_data,
            spending=spending,
        )
    except Exception as e:
        logger.error(f"Response serialization failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to build response")


@router.get("/usage")
async def usage(
    db: AsyncSession = Depends(get_db),
):
    return {"usage": []}
