from pydantic import BaseModel


class SpendingCategory(BaseModel):
    key: str
    label: str
    per_unit: int    # average annual $ per consumer unit (BLS source)
    total: int       # per_unit × households (trade area estimate)


class SpendingResponse(BaseModel):
    bracket: str          # e.g. "50000_69999"
    bracket_label: str    # e.g. "$50,000–$69,999"
    households: int
    categories: list[SpendingCategory]
    is_estimated: bool = False
