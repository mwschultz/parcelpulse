from pydantic import BaseModel, Field

from app.schemas.demographics import DemographicsResponse
from app.schemas.competitor import CompetitorResponse
from app.schemas.parcel import ParcelResponse
from app.schemas.spending import SpendingResponse


class SearchRequest(BaseModel):
    address: str = Field(..., min_length=1, max_length=500)
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    state: str = Field(..., min_length=2, max_length=2)


class SearchResponse(BaseModel):
    address: str
    lat: float
    lng: float
    state: str
    demographics: DemographicsResponse | None = None
    competitors: CompetitorResponse | None = None
    parcels: ParcelResponse | None = None
    spending: SpendingResponse | None = None
