from pydantic import BaseModel


class CompetitorItem(BaseModel):
    lat: float
    lng: float
    name: str
    category: str


class CompetitorCategory(BaseModel):
    key: str
    label: str
    color: str
    count: int


class CompetitorResponse(BaseModel):
    items: list[CompetitorItem]
    categories: list[CompetitorCategory]
    density_score: str
    radius_m: int
    rate_limited: bool = False
