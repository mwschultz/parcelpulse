# ParcelPulse — MVP Specification

## Vision

**"Enter an address. Understand the opportunity."**

ParcelPulse is a commercial real estate intelligence tool that takes a street address and instantly delivers:

1. Nearby property/parcel data (ownership, valuations, characteristics)
2. Detailed demographic breakdown of the surrounding Census block group
3. Competitor/POI density analysis
4. Consumer spending potential estimates

This is a portfolio project demonstrating CRE analytics capability for real estate analyst roles.

**Coverage**: Parcel data covers all of North Carolina via NC OneMap. Demographics, POI, and spending data work nationwide. Non-NC addresses gracefully degrade — showing a coverage notice on the Property tab while the other three tabs function normally. The property service uses a provider interface, making it straightforward to add national parcel sources (ATTOM, CoreLogic) later.

---

## Tech Stack

| Layer           | Technology                                | Notes                                                    |
| --------------- | ----------------------------------------- | -------------------------------------------------------- |
| Backend         | Python 3.11+ / FastAPI                    | Consistent with SiteTracker patterns                     |
| Frontend        | React + Vite, Tailwind CSS, react-leaflet | Consistent with SiteTracker patterns                     |
| ORM             | SQLAlchemy + Alembic                      | Models + migrations, consistent with SiteTracker         |
| Schemas         | Pydantic                                  | Request/response validation, consistent with SiteTracker |
| Geocoding       | Geoapify API                              | Free tier, already familiar                              |
| Property Data   | NC OneMap Parcels (ArcGIS REST)           | Free, statewide NC, no key required                      |
| Demographics    | Census Bureau API (ACS 5-Year)            | Free, block group level                                  |
| Geo Boundaries  | TIGERweb (ArcGIS REST)                    | Free, no key required — Census boundary polygons         |
| POI/Competitors | Overpass API (OpenStreetMap)              | Free, no key required                                    |
| Spending Data   | BLS Consumer Expenditure Survey           | Free, static dataset                                     |
| Database        | PostgreSQL                                | Cache API responses, production-ready                    |
| Charts          | Chart.js (via react-chartjs-2)            | Demographic visualizations                               |

---

## Architecture

```
parcelpulse/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, CORS config
│   │   ├── config.py                # Settings, env vars
│   │   ├── database.py              # DB connection, session
│   │   ├── models/                  # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   └── cache.py             # ApiCache, ApiUsage models
│   │   ├── schemas/                 # Pydantic request/response models
│   │   │   ├── __init__.py
│   │   │   ├── search.py            # Search request/response schemas
│   │   │   └── property.py          # Property/parcel response schemas
│   │   ├── routes/                  # API endpoint routers
│   │   │   ├── __init__.py
│   │   │   └── api.py               # Data API endpoints (search, property, demographics, etc.)
│   │   └── services/                # Business logic layer
│   │       ├── __init__.py
│   │       ├── geocoding.py         # Geoapify integration (async)
│   │       ├── property.py          # Property provider interface + NC OneMap (async)
│   │       ├── demographics.py      # Census Bureau integration (async)
│   │       ├── poi.py               # Overpass/OSM integration (async)
│   │       ├── spending.py          # BLS Consumer Expenditure logic
│   │       └── rate_limiter.py      # API call counter & request pacing
│   ├── alembic/                     # Database migrations
│   │   ├── versions/
│   │   └── env.py
│   ├── alembic.ini
│   ├── data/
│   │   └── bls_spending.json        # Pre-processed BLS spending data
│   ├── tests/
│   │   ├── test_services.py
│   │   └── test_routes.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/              # Reusable UI components
│   │   │   ├── Map.jsx              # react-leaflet map with parcel polygons
│   │   │   ├── SearchBar.jsx        # Address autocomplete (Geoapify)
│   │   │   ├── Sidebar.jsx          # Tabbed right panel container
│   │   │   ├── PropertyPanel.jsx    # Parcel cards + fallback banner
│   │   │   ├── DemoPanel.jsx        # Demographics + Chart.js visualizations
│   │   │   ├── POIPanel.jsx         # Competitor counts + density score
│   │   │   └── SpendingPanel.jsx    # BLS spending estimates
│   │   ├── pages/                   # Route-level page components
│   │   │   └── HomePage.jsx         # Main map + search interface
│   │   ├── hooks/                   # Custom React hooks
│   │   │   └── useSearch.js         # Orchestrates API calls on address search
│   │   ├── api/                     # API client functions
│   │   │   └── client.js            # Fetch wrapper for backend API
│   │   ├── utils/                   # Helpers, constants
│   │   │   └── formatters.js        # Currency, acreage, date formatting
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css                # Tailwind imports + custom styles
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Data Source Integration Details

### 1. Geoapify (Geocoding + Autocomplete)

- **Endpoint**: `https://api.geoapify.com/v1/geocode/search`
- **Purpose**: Convert street address → lat/lng coordinates
- **Also use**: Autocomplete API for search-as-you-type
- **Free tier**: 3,000 requests/day
- **Auth**: API key in query param

### 2. NC OneMap Parcels (Property/Parcel Intelligence)

- **Base URL**: `https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer`
- **Layers**:
  - Layer 0: `Parcels (pts)` — Point centroids for each parcel
  - Layer 1: `Parcels (polys)` — Polygon boundaries for each parcel
- **Query method**: ArcGIS REST API spatial query (POST)
  - Use `geometryType=esriGeometryPoint` with `geometry={x},{y}` and `spatialRel=esriSpatialRelIntersects` for point lookups
  - Use `geometry` with an envelope/buffer for radius searches
  - Use `where=cntyname='WAKE'` to filter by county
  - `outFields=*` to return all fields, or specify fields for performance
  - `outSR=4326` to get results in standard lat/lng
  - `f=json` for JSON response
- **Coverage**: All 100 NC counties + Eastern Band of Cherokee Indians
- **Max records per query**: 5,000
- **Auth**: None required — public REST endpoint
- **Cost**: $0 forever
- **Rate limiting**: No published rate limit, but be respectful (1-2 req/sec)
- **Available fields**:
  - **Ownership**: `ownname` (full owner), `ownfrst`/`ownlast`, `ownname2`, `owntype` (taxable/exempt), `subowntype`
  - **Valuations**: `improvval` (improvement value), `landval` (land value), `parval` (total value = improvval + landval), `presentval`, `parvaltype`
  - **Land Use**: `parusecode` (use code), `parusedesc` (use description, e.g. "Commercial"), `parusecd2`/`parusedsc2` (secondary use)
  - **Physical**: `gisacres` (acreage), `struct` (has structure Y/N), `multistruc` (multiple structures Y/N), `structno` (# structures), `structyear` (year built)
  - **Address**: `siteadd` (full site address), `saddno`, `saddstname`, `scity`, `sstate`, `szip` (parsed components)
  - **Mailing**: `mailadd`, `mcity`, `mstate`, `mzip` (owner mailing address)
  - **Transactions**: `saledate`/`saledatetx` (last sale date), `legdecfull` (legal description)
  - **Geography**: `cntyname`, `cntyfips`, `stfips`, `stcntyfips`, `subdivisio`, `gnisid`
  - **Metadata**: `sourceref`, `sourcedate`, `revisedate`, `reviseyear`
- **Example query** (parcels within ~0.25 mi of a point):
  ```
  POST /FeatureServer/1/query
  where: 1=1
  geometry: {"xmin":-78.642,"ymin":35.776,"xmax":-78.634,"ymax":35.784,"spatialReference":{"wkid":4326}}
  geometryType: esriGeometryEnvelope
  spatialRel: esriSpatialRelIntersects
  outFields: parno,ownname,owntype,improvval,landval,parval,parusedesc,gisacres,struct,structyear,siteadd,scity,saledate
  outSR: 4326
  returnGeometry: true
  f: json
  ```
- **Caching strategy**: Cache results by bounding box coordinates (rounded to 3 decimals). Parcel data changes infrequently — 30 day cache expiration.
- **State detection & fallback logic**:
  - Geoapify geocode response includes `state` (or `state_code`) in the result
  - `property.py` checks the state before querying:
    - If NC → query NC OneMap, return full parcel data
    - If non-NC → return a structured `{"coverage": false, "state": "TX", "message": "..."}` response
  - UI handles the fallback gracefully:
    - Property tab shows: "Parcel data is currently available for North Carolina addresses. Demographics, market, and spending data are shown below."
    - Other three tabs (Demographics, POI, Spending) work normally — they all use national data sources
  - **Why this design matters**: The property service uses a provider interface pattern. NC OneMap is the first provider. Swapping in a national source (ATTOM, CoreLogic, BatchData) later means adding a new provider class — the routes, UI, caching, and other services stay untouched. This is the story to tell in interviews.

### 3. Census Bureau API (Demographics)

- **Base URL**: `https://api.census.gov/data/2023/acs/acs5`
- **Library**: `census` Python package (pip install census us)
- **Geography fallback chain**: Block group → tract → county → unavailable
  - Try block group first (most granular with rich data)
  - If Census Geocoder fails to resolve block group (water, parks, federal land, new developments, rural areas, geocoder timeout), fall back to tract level
  - If tract also fails, fall back to county level with a note: "Showing county-level data"
  - If all fail (e.g., coordinates outside the US), show: "Demographic data unavailable for this location"
  - The resolved geography level is passed to TIGERweb for polygon overlay (see section 3b)
- **Flow**:
  1. Take lat/lng from geocoding
  2. Use Census Geocoder to get FIPS code (state + county + tract + block group)
     - `https://geocoding.geo.census.gov/geocoder/geographies/coordinates`
  3. If block group resolved → query ACS at block group level
  4. If only tract resolved → query ACS at tract level
  5. If only county resolved → query ACS at county level
  6. Query TIGERweb for boundary polygon at whichever level resolved
- **Key variable tables to pull**:
  - **B01003**: Total population
  - **B01002**: Median age
  - **B19013**: Median household income
  - **B25077**: Median home value
  - **B15003**: Educational attainment
  - **B25064**: Median gross rent
  - **B08301**: Means of transportation to work
  - **B25001**: Housing units
  - **B02001**: Race/ethnicity
  - **B25024**: Units in structure (housing density proxy)
  - **B23025**: Employment status
  - **DP03**: Economic characteristics (Data Profile — tract level)
- **Auth**: Free API key from https://api.census.gov/data/key_signup.html

### 3b. TIGERweb (Census Geography Boundaries)

- **Base URL**: `https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2023/MapServer`
- **Purpose**: Fetch boundary polygons for the resolved Census geography (block group, tract, or county)
- **Layers**:
  - Block Groups: Layer 10
  - Census Tracts: Layer 8
  - Counties: Layer 84
- **Query method**: ArcGIS REST API (same pattern as NC OneMap)
  - `geometryType=esriGeometryPoint` with `geometry={lng},{lat}`
  - `spatialRel=esriSpatialRelIntersects`
  - `outFields=GEOID,NAME` (or relevant identifier)
  - `outSR=4326`
  - `returnGeometry=true`
  - `f=geojson` (returns GeoJSON directly for easy Leaflet rendering)
- **Auth**: None required — public REST endpoint
- **Cost**: $0 forever
- **Caching**: Cache by FIPS code + geography level. Boundaries change rarely — 90 day cache expiration.
- **Integration with demographics service**: After Census Geocoder returns FIPS and the ACS data is pulled, fetch the matching polygon from TIGERweb at the same geography level. Return both the demographic data and the GeoJSON polygon to the frontend in a single response.

### 4. Overpass API (POI/Competitor Density)

- **Endpoint**: `https://overpass-api.de/api/interpreter`
- **Query method**: POST with Overpass QL query
- **Purpose**: Count and map nearby businesses by category
- **Categories to query** (with OSM tags):
  - Grocery/Supermarket: `shop=supermarket`
  - Convenience: `shop=convenience`
  - Restaurant: `amenity=restaurant`
  - Fast food/QSR: `amenity=fast_food`
  - Pharmacy: `amenity=pharmacy`
  - Bank: `amenity=bank`
  - Gas station: `amenity=fuel`
  - Medical/Clinic: `amenity=clinic` or `amenity=doctors`
  - Retail general: `shop=*`
- **Example query**:
  ```
  [out:json][timeout:25];
  (
    node["shop"="supermarket"](around:1600,35.7796,-78.6382);
    way["shop"="supermarket"](around:1600,35.7796,-78.6382);
  );
  out center count;
  ```
- **Radius**: 1 mile (1609m) default, user-adjustable
- **No auth required**, but respect rate limits (1 req/sec)
- **Caching**: Cache results by lat/lng rounded to 3 decimal places + radius

### 5. BLS Consumer Expenditure Survey (Spending Estimates)

- **Source**: Pre-downloaded and processed into `data/bls_spending.json`
- **Data**: Average annual consumer expenditure by category and income bracket
- **Logic**: Map Census median household income to BLS income bracket → estimate total spending potential per category for the block group population
- **Categories**: Food at home, food away from home, apparel, healthcare, entertainment, personal care, education, transportation
- **Formula**: `spending_potential = (households_in_block_group) × (avg_expenditure_for_income_bracket_in_category)`
- **This is a modeled estimate** — label clearly in UI as "Estimated Spending Potential"

---

## MVP Features (Phase 1)

### Search & Map

- [ ] Full-page map (Leaflet + OpenStreetMap tiles) with search bar overlay
- [ ] Address autocomplete using Geoapify
- [ ] On search: geocode → center map → trigger all data pulls
- [ ] Pin dropped at searched location with address label

### Property Panel (right sidebar)

- [ ] List of nearby parcels within adjustable radius (default 0.25 mi bounding box)
- [ ] Property cards showing: address, land use description, total assessed value (land + improvement), acreage, year built, owner name, owner type
- [ ] Parcel polygons drawn on map (semi-transparent fill with border)
- [ ] Click a parcel polygon → highlight card in sidebar
- [ ] Color-code parcels by land use type (commercial = blue, residential = gray, vacant = orange)
- [ ] **Non-NC fallback state**: If address is outside NC, show info banner with coverage message and prompt to try an NC address. Banner includes a "Try: 4325 Glenwood Ave, Raleigh, NC" quick-link to demo the full experience.

### Demographics Panel

- [ ] Translucent polygon overlay on map for whichever Census geography resolved (block group, tract, or county) — fetched from TIGERweb
- [ ] Label on polygon indicating geography level (e.g., "Block Group 372010101.001" or "Tract 372010101" or "Wake County")
- [ ] Key stats displayed as cards: population, median income, median age, median home value
- [ ] Bar charts show **percentages** (not raw counts): age distribution, income distribution, educational attainment
- [ ] Chart tooltips show **raw numbers** on mouse-over
- [ ] Donut chart: housing type breakdown (single family vs multi-family vs rental) — also percentages with raw count tooltips
- [ ] If geography fell back to tract or county, show subtle info banner: "Showing [tract/county]-level data — block group unavailable for this location"
- [ ] If demographics unavailable entirely, show message: "Demographic data unavailable for this location"

### POI/Competitor Panel

- [ ] Category-grouped counts (e.g., "Grocery: 4 within 1 mi")
- [ ] POI markers on map, color-coded by category
- [ ] Toggle categories on/off on map
- [ ] Simple density score: "High / Medium / Low retail density"

### Spending Potential Panel

- [ ] Estimated annual spending by category for the trade area
- [ ] Horizontal bar chart comparing categories
- [ ] Labeled clearly as "Modeled Estimate based on Census + BLS data"

### Rate Limiter / Request Manager

- [ ] `rate_limiter.py` tracks daily API calls per service in PostgreSQL
- [ ] IP-based request throttling to prevent abuse (no auth needed)
- [ ] Configurable daily cap per service via environment variable (default: NC OneMap 500/day, Geoapify 2500/day)
- [ ] Returns cached data if available before making API call
- [ ] Respectful request pacing: 1-2 requests/sec to NC OneMap, 1 req/sec to Overpass
- [ ] Graceful degradation: if cap reached, show message "Request limit reached — please try again tomorrow" but still show cached/other panel data
- [ ] Admin endpoint to check current usage: `/api/usage`

---

## UI/UX Design Direction

### Aesthetic: "Professional Intelligence Tool"

- **Dark sidebar** on right with data panels (tabbed: Property | Demographics | Market | Spending)
- **Full-bleed map** taking up ~65% of viewport
- **Color palette**: Dark navy (#1a1f36) sidebar, white cards, teal (#0ea5e9) accents, warm amber (#f59e0b) for spending/financial data
- **Typography**: Clean, data-focused. Use a professional sans-serif (e.g., DM Sans for headings, Source Sans 3 for body/data)
- **Map style**: Use CartoDB Positron (light) or Voyager tile layer for clean, professional look
- **Charts**: react-chartjs-2 with consistent color scheme, no chartjunk
- **Responsive**: Desktop-first (this is a professional tool), but panels should stack on mobile

### Key UI Patterns

- Search bar with subtle shadow, centered top of map
- Tabbed sidebar that slides in from right after search
- Loading skeleton states while APIs return
- Subtle animations on panel transitions
- "Powered by" footer showing data sources (Census Bureau, OpenStreetMap, NC OneMap)
- Export button: generate PDF report of the analysis (Phase 2)

---

## Local Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for local PostgreSQL)

### Database

```bash
docker compose up -d
```

This starts a PostgreSQL container on port 5432 with a persistent volume.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file in the backend directory:

```
DATABASE_URL=postgresql+asyncpg://parcelpulse:devpassword@localhost:5432/parcelpulse
SECRET_KEY=any-random-string-for-dev
FRONTEND_URL=http://localhost:5173
GEOAPIFY_API_KEY=your-geoapify-key
CENSUS_API_KEY=your-census-key
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
VITE_GEOAPIFY_KEY=your-geoapify-api-key
```

Start the dev server:

```bash
npm run dev
```

The app is available at `http://localhost:5173`.

---

## API Response Caching Strategy

Every external API call should be cached in PostgreSQL to:

1. **Be respectful** of public data services (NC OneMap, Overpass)
2. **Improve performance** on repeat searches
3. **Demonstrate good engineering practice**

Cache schema:

```sql
CREATE TABLE api_cache (
    id INTEGER PRIMARY KEY,
    cache_key TEXT UNIQUE NOT NULL,  -- e.g., "nconemap:35.780:-78.638:0.25"
    service TEXT NOT NULL,            -- "nconemap", "census", "tigerweb", "overpass"
    response_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP             -- Census: 30 days, NC OneMap: 30 days, Overpass: 7 days, TIGERweb: 90 days
);

CREATE TABLE api_usage (
    id INTEGER PRIMARY KEY,
    service TEXT NOT NULL,
    calls_today INTEGER DEFAULT 0,
    date TEXT NOT NULL,               -- "2026-02-27"
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(service, date)
);
```

---

## Development Sequence (Recommended Build Order)

### Sprint 1: Foundation

1. FastAPI app (main.py, config.py, database.py) + CORS config
2. SQLAlchemy models/ directory + Alembic migrations (ApiCache, ApiUsage)
3. Pydantic schemas/ directory for request/response validation
4. React + Vite frontend scaffold with Tailwind CSS
5. react-leaflet Map component with CartoDB Positron tiles
6. SearchBar component with Geoapify address autocomplete
7. Tabbed Sidebar component shell (Property | Demographics | Market | Spending)

### Sprint 2: Demographics (Free — build confidence)

6. Census Geocoder (lat/lng → FIPS) with fallback chain: block group → tract → county → unavailable
7. Census ACS data pull at whichever geography level resolved
8. TIGERweb boundary polygon fetch for resolved geography (async)
9. Translucent polygon overlay rendered on react-leaflet map with geography label
10. DemoPanel component with react-chartjs-2 visualizations — charts display percentages, tooltips show raw counts
11. Fallback info banner when geography degrades from block group
12. Cache layer for Census + TIGERweb responses

### Sprint 3: POI Layer (Free — more confidence)

10. Overpass API integration — async backend service
11. POI markers on react-leaflet map with category colors
12. POIPanel component with counts and density score
13. Category toggle controls

### Sprint 4: Property Data (Free — the parcel layer)

14. Property provider interface with state detection (check geocode result → route to provider)
15. NC OneMap ArcGIS REST implementation with spatial queries
16. Parcel search by bounding box around geocoded point
17. Parcel polygon rendering on react-leaflet map (GeoJSON from ArcGIS response)
18. PropertyPanel component with assessed values and land use cards
19. Non-NC fallback UI state (coverage banner + demo link)
20. Cache layer for NC OneMap responses

### Sprint 5: Spending Estimates + Polish

21. BLS data processing and spending model
22. SpendingPanel component
23. UI polish, loading skeletons, error boundaries
24. README and documentation

### Sprint 6: Production Hardening

25. Cache cleanup — FastAPI background task that runs on startup and periodically (e.g., every 6 hours) to `DELETE FROM api_cache WHERE expires_at < NOW()`
26. Database size monitoring — `/api/usage` endpoint should also return total cache row count and approximate size (`pg_total_relation_size`)
27. Cache eviction fallback — if total cache size exceeds a configurable threshold (e.g., 500MB), delete oldest expired rows first, then oldest rows regardless of expiration
28. Request logging — log each search (address, timestamp, cache hit/miss per service) to a `search_log` table for usage analytics
29. Error handling audit — ensure all five external API services fail gracefully (timeout, bad response, rate limit) without crashing the app
30. Security pass — CORS lockdown to frontend origin, rate limit by IP (SlowAPI), input sanitization on search endpoint

---

## Claude Code Prompt (Use This to Start Building)

```
I'm building ParcelPulse, a commercial real estate intelligence web app.
This is a monorepo with backend/ and frontend/ as separate applications,
matching the structure of my SiteTracker project. Reference SiteTracker's
codebase for conventions on project structure and coding style.

Backend: FastAPI, SQLAlchemy + Alembic, Pydantic schemas, PostgreSQL.
No auth — this is a public demo tool. Structure: app/main.py, app/config.py,
app/database.py, app/models/ (directory), app/schemas/ (directory),
app/routes/ (directory), app/services/ (directory).

Frontend: React + Vite, Tailwind CSS, react-leaflet for mapping,
react-chartjs-2 for demographic visualizations. Structure: src/components/,
src/pages/, src/hooks/, src/api/ (fetch wrapper), src/utils/.

Start by setting up the project foundation:
1. backend/ — FastAPI app (main.py with CORS config, config.py, database.py)
2. models/ directory with ApiCache, ApiUsage models
3. schemas/ directory for request/response validation
4. routes/ directory (api.py)
5. Alembic migration setup
6. frontend/ — React + Vite scaffold with Tailwind CSS
7. react-leaflet Map component with CartoDB Positron tiles
8. SearchBar component with Geoapify address autocomplete
9. Tabbed Sidebar component (Property | Demographics | Market | Spending)

When a user searches an address, it geocodes the location, centers the map,
and populates four data tabs via backend API calls.

Property data comes from NC OneMap Parcels (free ArcGIS REST API). The property
service uses a provider pattern: it checks the state from the geocode result,
routes NC addresses to the NC OneMap provider, and returns a structured fallback
response for non-NC addresses. The UI handles the fallback gracefully — showing
a coverage banner on the Property tab while the other three tabs (Demographics,
POI, Spending) still work since they use national data sources.

All external API calls should be async (httpx.AsyncClient) and cached in
PostgreSQL. Use the same coding style and project conventions as SiteTracker.

Design: dark navy (#1a1f36) sidebar, teal (#0ea5e9) accents, CartoDB Positron
map tiles. Typography: DM Sans for headings, Source Sans 3 for body text.

Set up both backend and frontend scaffolds, get the map + geocoding working first.
```

---

## Success Criteria

A hiring manager at JLL, CBRE, or a retail REIT should be able to:

1. Visit the app URL
2. Type in a commercial address (e.g., "4325 Glenwood Ave, Raleigh, NC")
3. Immediately see nearby properties, demographics, competitor landscape, and spending potential
4. Think: "This person understands how we evaluate locations"

---

## Data Source Signup Links

- **NC OneMap Parcels**: No signup required — public ArcGIS REST endpoint
  - FeatureServer: `https://services.nconemap.gov/secure/rest/services/NC1Map_Parcels/FeatureServer`
  - Parcel info page: https://www.nconemap.gov/pages/parcels
- **Census Bureau**: https://api.census.gov/data/key_signup.html — instant, free
- **TIGERweb**: No signup required — public ArcGIS REST endpoint
  - MapServer: `https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2023/MapServer`
- **Geoapify**: https://myprojects.geoapify.com — you likely already have this
- **Overpass API**: No signup needed
- **BLS CEX**: https://www.bls.gov/cex/tables.htm — download tables, pre-process
