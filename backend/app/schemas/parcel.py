from pydantic import BaseModel


class Parcel(BaseModel):
    parno: str
    address: str
    city: str
    owner: str
    owner_type: str
    land_value: int
    improvement_value: int
    total_value: int
    use_description: str
    acres: float
    has_structure: bool
    year_built: int | None
    sale_date: str | None
    distance_mi: float | None = None
    geometry: dict | None


class ParcelResponse(BaseModel):
    coverage: bool
    state: str
    message: str | None = None
    parcels: list[Parcel] = []
    rate_limited: bool = False
    unavailable: bool = False
