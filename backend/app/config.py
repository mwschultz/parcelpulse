from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    FRONTEND_URL: str = "http://localhost:5173"

    GEOAPIFY_API_KEY: str
    CENSUS_API_KEY: str
    NCONEMAP_BASE_URL: str = "https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer"
    NCONEMAP_DAILY_CAP: int = 500
    GEOAPIFY_DAILY_CAP: int = 2500

    model_config = {"env_file": ".env"}


settings = Settings()
