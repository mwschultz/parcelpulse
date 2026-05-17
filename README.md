# ParcelPulse

A commercial real estate intelligence tool that turns a street address into a one-page opportunity briefing. Enter an address and ParcelPulse pulls together parcel data, demographics, competitor density, and household spending estimates — the kind of cross-reference a CRE analyst would otherwise stitch together from five different tabs.

**Live Demo:** [TBD](TBD)

## Features

**Address Search** — Geoapify-powered autocomplete with 5-result dropdown, filtered to US addresses. The Geoapify key is proxied server-side so it never ships in the frontend bundle.

**Interactive Map** — Leaflet map with CartoDB Positron base tiles, occupying ~65% of the viewport. Renders the searched location, parcel polygons, demographic boundaries, and color-coded competitor markers in stacked GeoJSON layers.

**Parcel Data** — NC OneMap integration returns owner name, land use classification, acreage, and the parcel polygon itself. Land use is color-coded on the map: blue for commercial, gray for residential, amber for vacant. Non-NC addresses get a graceful "coverage not available" response so the rest of the panels still work.

**Demographics Panel** — US Census ACS 5-Year data: median household income, household count, age distribution, and education attainment. A fallback chain tries block group → tract → county so dense urban and sparse rural addresses both return something usable. The chosen geography boundary is rendered on the map.

**Competitors** — Overpass API (OpenStreetMap) pulls nearby supermarkets, restaurants, gas stations, retail, and other categories. A density score (High > 50, Medium 20–50, Low < 20) gives a one-glance read on commercial saturation. Categories can be toggled individually from the sidebar.

**Spending Potential** — BLS Consumer Expenditure Survey data, joined to the demographics panel's income and household count, estimates annual household spending across categories (food, housing, transportation, etc.). Pre-processed BLS JSON ships with the app; null cells in the source data are filled via linear interpolation.

**Response Caching & Rate Limiting** — All external API responses are cached in PostgreSQL (`api_cache`) with per-service TTLs: 30 days for parcels, 7 days for competitors, etc. A daily-cap rate limiter (`api_usage`) enforces per-service budgets (500/day for NC OneMap, 2,500/day for Geoapify) to keep the app inside free-tier limits.

## Tech Stack

| Layer            | Technology                                                |
| ---------------- | --------------------------------------------------------- |
| Frontend         | React 19, Vite, TypeScript, Tailwind CSS v4               |
| Maps             | Leaflet, react-leaflet, CartoDB Positron tiles            |
| Charts           | Chart.js, react-chartjs-2                                 |
| Backend          | Python 3.12, FastAPI (async), SQLAlchemy 2.0, Alembic     |
| Database         | PostgreSQL 16 (asyncpg driver)                            |
| HTTP client      | httpx (async)                                             |
| Rate limiting    | SlowAPI                                                   |
| Data sources     | Geoapify, NC OneMap, Census Bureau ACS, TIGERweb, Overpass, BLS |
| Deployment       | Docker Compose for local Postgres                         |

## External APIs

ParcelPulse stitches together six external data sources. All are free; two require an API key.

| Service | Endpoint | Auth | Limits | Used For |
| --- | --- | --- | --- | --- |
| **Geoapify Geocoding Autocomplete** | `api.geoapify.com/v1/geocode/autocomplete` | API key (server-side proxy) | 3,000 req/day free tier; app-side cap 2,500/day | Address search / autocomplete dropdown |
| **NC OneMap Parcels (ArcGIS REST)** | `services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer` | None | App-side cap 500/day | Parcel polygons, owner, land use, acreage (NC only) |
| **US Census Bureau ACS 5-Year** | `api.census.gov/data` | API key | No published rate cap | Income, household count, age, education at block group / tract / county |
| **Census TIGERweb** | `tigerweb.geo.census.gov/arcgis/rest/services` | None | No published rate cap | Geography boundary polygons (block group=10, tract=8, county=84) |
| **Overpass API** (OpenStreetMap) | `overpass-api.de/api/interpreter` | None | Shared-instance fair-use | Nearby competitors / POI by category |
| **BLS Consumer Expenditure Survey** | Pre-processed static JSON (`backend/data/bls_spending.json`) | n/a | n/a | Household spending estimates by income tier |

Map tiles are served from CartoDB Positron (`{a,b,c}.basemaps.cartocdn.com/light_all/`) — not a JSON API, but worth flagging as an external dependency.

## Project Structure

This is a monorepo with the frontend and backend as separate applications.

```
parcelpulse/
├── backend/                # FastAPI app
│   ├── app/
│   │   ├── main.py         # App factory, JSON logging, CORS, rate limiter
│   │   ├── config.py       # Pydantic settings (env vars)
│   │   ├── database.py     # Async SQLAlchemy engine + session
│   │   ├── rate_limit.py   # SlowAPI limiter (30/minute global)
│   │   ├── models/         # SQLAlchemy: ApiCache, ApiUsage (only)
│   │   ├── schemas/        # Pydantic request/response models
│   │   ├── routes/api.py   # All /api/* endpoints
│   │   └── services/       # External API integrations + cache layer
│   ├── data/               # BLS spending JSON (pre-processed)
│   ├── alembic/            # Database migrations
│   └── tests/              # Pytest suite
├── frontend/               # React + Vite app
│   └── src/
│       ├── components/     # Map, SearchBar, Sidebar, *Panel components
│       ├── pages/          # HomePage
│       └── api/            # Fetch wrapper for the backend
├── docker-compose.yml      # Local Postgres
├── SPEC.md                 # Full product spec
└── CLAUDE.md               # Sprint progress + session notes
```

## Data Coverage

ParcelPulse is intentionally scoped: **parcel data is North Carolina only** (NC OneMap is the underlying source). Addresses outside NC return a `{coverage: false}` response on the parcel endpoint, but demographics, competitor density, and spending data work nationwide because they ride on Census, OpenStreetMap, and BLS — all national datasets. A non-NC search still gets a useful four-out-of-five panel briefing.

## Data Model

ParcelPulse is a stateless public demo — there are no users, no projects, no saved searches. The only persistent state is the integration scaffolding: an `api_cache` table (key, service, response JSON, expiry) and an `api_usage` table (service, calls\_today, date) that drives the daily rate limiter. All real data lives in the external APIs and is fetched on demand, then cached.

## Local Development Setup

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker (for local PostgreSQL)
- A free Geoapify API key and a free Census API key

### Database

```bash
docker compose up -d
```

This starts a PostgreSQL 16 container bound to `127.0.0.1:5432` with a persistent volume.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the backend directory (template in `backend/.env.example`):

```
DATABASE_URL=postgresql+asyncpg://parcelpulse:devpassword@localhost:5432/parcelpulse
FRONTEND_URL=http://localhost:5173
GEOAPIFY_API_KEY=your-geoapify-api-key
CENSUS_API_KEY=your-census-api-key
NCONEMAP_BASE_URL=https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer
NCONEMAP_DAILY_CAP=500
GEOAPIFY_DAILY_CAP=2500
```

Run migrations and start the server:

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
```

Create a `.env` file in the frontend directory:

```
VITE_API_URL=http://localhost:8000
```

Geoapify is proxied through the backend, so no API key is needed in the frontend bundle.

Start the dev server:

```bash
npm run dev
```

The app is available at `http://localhost:5173`.

## API Documentation

FastAPI auto-generates interactive API documentation. With the backend running, visit `/docs` for the Swagger UI. Endpoints:

- `GET /api/geocode` — Geoapify autocomplete proxy (server-side key)
- `POST /api/search` — Combined search; fans out to demographics, competitor, and spending services with graceful per-service fallback (a failing service returns `null` rather than breaking the response)
- `GET /api/demographics` — Census ACS data + TIGERweb boundary for a lat/lng
- `GET /api/competitors` — Overpass competitor data for a lat/lng
- `GET /api/parcels` — NC OneMap parcel data for a lat/lng + state code (NC only; other states return a no-coverage response)
- `GET /api/spending` — BLS spending estimates given income and household count
- `GET /api/usage` — Per-service daily call counts
- `GET /health` — Healthcheck

## Security

The app is stateless and has no auth surface, but it still ships with sensible defaults: SlowAPI rate limiting (30 requests/minute) on every endpoint, CORS locked to the configured frontend origin, GEOID values validated against `^\d{5,15}$` before being interpolated into ArcGIS queries, exception logs sanitized to error class names (no URL or PII leakage), no third-party API keys in the frontend bundle (Geoapify is proxied), and per-service daily caps that hard-stop requests when free-tier budgets are exhausted.

## Built With Claude Code

This app was designed, built, and deployed using [Claude Code](https://docs.anthropic.com/en/docs/claude-code) as an AI coding agent. `SPEC.md` served as the application blueprint, and the work was broken into sprints (map/geocoding → demographics → competitors → parcels → spending), each driven iteratively through Claude. The commit history reflects that incremental development process.
