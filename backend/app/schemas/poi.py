from pydantic import BaseModel


class POIItem(BaseModel):
    lat: float
    lng: float
    name: str
    category: str


class POICategory(BaseModel):
    key: str
    label: str
    color: str
    count: int


class POIResponse(BaseModel):
    items: list[POIItem]
    categories: list[POICategory]
    density_score: str
    radius_m: int
