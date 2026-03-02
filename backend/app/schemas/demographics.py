from pydantic import BaseModel


class EducationBreakdown(BaseModel):
    hs_diploma: int
    some_college: int
    associates: int
    bachelors: int
    graduate: int


class RaceBreakdown(BaseModel):
    white: int
    black: int
    american_indian: int
    asian: int
    pacific_islander: int


class DemographicsResponse(BaseModel):
    population: int
    median_age: float
    median_household_income: int
    median_home_value: int
    median_gross_rent: int
    households: int
    education: EducationBreakdown
    race: RaceBreakdown
    fips: dict
    geography_level: str        # "block_group", "tract", "county", "unavailable"
    geography_label: str        # human-readable, e.g. "Block Group 1 · Tract 052601"
    boundary: dict | None       # GeoJSON Feature for map overlay
