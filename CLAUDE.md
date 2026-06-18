# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Zijingang Campus WebGIS platform — a course project for Zhejiang University. Displays study rooms, campus POIs, charger stations, and building outlines on both 2D (Leaflet) and 3D (Cesium) maps, with AI-powered study room recommendations.

- **Frontend**: Vue 3 + Vite + Leaflet + Cesium (main UI in `App.vue`, 3D view in `CesiumView.vue`)
- **Backend**: Python FastAPI (`backend/main.py`, single file)
- **Data**: GeoJSON FeatureCollections in `data/` (WGS84, `[longitude, latitude]`)
- **Map tiles**: OpenStreetMap standard tiles (2D); OSM / ESRI satellite / local fallback (3D)
- **Deployment**: GitHub Actions → GitHub Pages at `https://ameliaagxy.github.io/ZJU-SmartCampus-Map/`

The app supports a 2D/3D view toggle — Leaflet for 2D, Cesium for 3D — switching via `viewMode` ref in `App.vue`.

## Run the project locally

Both backend and frontend must run simultaneously:

**Backend** (port 8000):

```bash
cd backend
python -m pip install -r requirements.txt
cp .env.example .env    # edit .env to add DEEPSEEK_API_KEY if available
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

**Frontend** (port 5173, connects to backend at `http://127.0.0.1:8000`):

```bash
cd frontend
npm install
npm run dev
```

**Build frontend for production**:

```bash
cd frontend
npm run build      # output to dist/
npm run preview    # preview the build
```

## Deployment

Pushing to `main` triggers [`.github/workflows/deploy-pages.yml`](.github/workflows/deploy-pages.yml): builds the frontend with `VITE_API_BASE_URL=""` (empty — production uses no backend, only static GeoJSON via build-time data or GeoServer WFS), then deploys `frontend/dist` to GitHub Pages.

The Vite config sets `base: '/ZJU-SmartCampus-Map/'` — all asset paths are relative to this base URL.

## Architecture

### Backend (`backend/main.py`)

A single-file FastAPI app. All state is file-based — reads GeoJSON from `../data/`, proxies external APIs (ZJU-Charger, DeepSeek, GeoServer), never uses a database.

**Endpoints**:

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Liveness check |
| `GET /api/study-rooms` | Returns `study_rooms.geojson` |
| `GET /api/pois` | Returns `campus_pois.geojson` |
| `GET /api/buildings` | Returns `buildings.geojson` (Polygon/MultiPolygon, for Cesium 3D extrusion) |
| `GET /api/zjg-boundary` | Returns `zjg.geojson` (campus boundary polygon) |
| `GET /api/config` | Charger URL, AI recommender enabled flag |
| `GET /api/chargers/status` | Whether ZJU-Charger API is configured |
| `GET /api/chargers/stations` | Proxies ZJU-Charger API, normalizes, filters to Zijingang campus |
| `GET /api/geoserver/status` | Whether GeoServer is reachable |
| `GET /api/geoserver/wfs?layer=…` | Proxies GeoServer WFS GetFeature, returns GeoJSON |
| `POST /api/ai/recommend-study-room` | Body: `{"query": "..."}`. Uses DeepSeek if configured, else keyword-based fallback |

**AI recommendation flow**: DeepSeek (if `DEEPSEEK_API_KEY` + `AI_RECOMMENDER_ENABLED=true`) → keyword rule-based fallback → returns `mode: "ai"` / `"fallback"` / `"empty"`.

**Charger data flow**: Backend proxies ZJU-Charger API → normalizes field names → filters to `campus_id=2` (Zijingang) → returns normalized stations. The frontend then converts coordinates BD-09 → GCJ-02 → WGS84.

**GeoServer proxy**: The backend has two proxy endpoints (`/api/geoserver/status`, `/api/geoserver/wfs`) that the frontend calls through `geoServerService.js` to avoid browser CORS issues. GeoServer is optional — `VITE_USE_GEOSERVER=false` by default.

**Environment variables** (from `backend/.env`): `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`, `AI_RECOMMENDER_ENABLED`, `ZJU_CHARGER_API_BASE_URL`, `ZJU_CHARGER_STATIONS_PATH`, `ZJU_CHARGER_SITE_URL`, `ZJU_CHARGER_API_TIMEOUT`, `CHARGER_URL`, `GEOSERVER_URL`, `GEOSERVER_WORKSPACE`.

### Frontend

The frontend has two main view components and several service modules:

- `src/App.vue` — 2D Leaflet map, side panel with tabs (study rooms, POIs, chargers), AI input form, recommendation cards, legend. Manages a `viewMode` ref (`'2d'` / `'3d'`) that toggles between Leaflet and Cesium views.
- `src/components/CesiumView.vue` — Full 3D Cesium viewer. Loads study rooms, POIs, buildings, and campus boundary from backend APIs. Renders point entities (billboards with canvas-drawn pins), extruded building polygons, and campus boundary. Has its own basemap switcher (OSM / ESRI satellite / local TMS fallback) with error recovery. Emits `back` event to return to 2D.
- `src/services/api.js` — Axios instance with `baseURL` from `VITE_API_BASE_URL`, all API call wrappers
- `src/services/geojsonData.js` — `loadMapDatasets()`, `getFeatureCoordinate()`, `normalizeFeatureCollection()`, `textOrUnknown()` (empty→"未知"), `EMPTY_FEATURE_COLLECTION` constant
- `src/services/geoServerService.js` — `getWmsBaseUrl()`, `getWmsLayerOptions()`, `fetchWfsFeatures()`, `checkGeoServerStatus()`. All guarded by `VITE_USE_GEOSERVER` — returns empty/fallback when disabled.
- `src/styles/base.css` — All styles, responsive breakpoints at 860px and 520px
- `src/main.js` — App entry point, mounts Vue app, imports Leaflet CSS

**2D/3D switch**: `App.vue`'s template uses `v-if="viewMode === '3d'"` to show `CesiumView` instead of the Leaflet map container. The 3D view is a full-page takeover; the "← 返回二维地图" button emits `back` which calls `switchTo2D()`. Only data loaded by `App.vue`'s `loadData()` is passed to 2D markers; `CesiumView` loads its own data independently.

**Frontend env vars** (from `frontend/.env`): `VITE_API_BASE_URL`, `VITE_CHARGER_URL`, `VITE_CHARGER_EMBED_MODE`, `VITE_GEOSERVER_URL`, `VITE_GEOSERVER_WORKSPACE`, `VITE_GEOSERVER_LAYER`, `VITE_USE_GEOSERVER`, `VITE_CESIUM_ION_TOKEN`.

### Data format

All spatial data uses GeoJSON `FeatureCollection` with `[longitude, latitude]` coordinate order. Fields: `snake_case`, null becomes `"未知"` in UI. Empty data is always valid: `{"type":"FeatureCollection","features":[]}`.

**Data files**:

| File | Geometry | Purpose |
|---|---|---|
| `study_rooms.geojson` | Point | Study room markers + AI recommendation data |
| `campus_pois.geojson` | Point | Campus POI markers |
| `buildings.geojson` | Polygon / MultiPolygon | 3D extruded buildings in Cesium; GeoServer WMS/WFS source |
| `zjg.geojson` | Polygon | Zijingang campus boundary outline in 3D |

**Coordinate system**:

- Study rooms, POIs, buildings, boundary: WGS84 (matches OSM tiles directly)
- Charger stations: BD-09 (from ZJU-Charger API) → frontend converts to WGS84 via `bd09ToGcj02()` then `gcj02ToWgs84()`

Full field schemas are documented in [`docs/DATA_CONTRACT.md`](docs/DATA_CONTRACT.md) and [`data/README.md`](data/README.md).

### Defense-in-depth design

Every external dependency can fail gracefully:

- **GeoJSON data**: missing files → empty FeatureCollection, never 500
- **DeepSeek API**: not configured → keyword fallback; configured but fails → keyword fallback; no data → "暂无数据" message
- **ZJU-Charger API**: not configured → shows external link; configured but unreachable → shows external link
- **GeoServer**: `VITE_USE_GEOSERVER=false` disables all GeoServer calls; when enabled but unreachable → falls back to local GeoJSON data, shows status message
- **Cesium 3D**: empty data → overlay message "暂无可用于三维展示的数据"; basemap tile failure → auto-fallback to local offline TMS with warning toast
- **Empty data**: all panels show context-appropriate empty-state messages (detailed in [`docs/EMPTY_STATE_POLICY.md`](docs/EMPTY_STATE_POLICY.md)), map still renders

### Unsupported features (explicitly out of scope)

No navigation, route planning, one-click navigation, visitor route recommendations, nearest study room geo-location, study room filtering, or classroom presentation material generation. Charger data comes only from ZJU-Charger API — no local charger GeoJSON.

## Common tasks

**Add a new GeoJSON data type**:
1. Add the `.geojson` file in `data/`
2. Add a `GET /api/<name>` endpoint in `backend/main.py` (use `read_geojson()`)
3. Add an API call in `frontend/src/services/api.js`
4. Add a loader entry in `frontend/src/services/geojsonData.js` `datasetLoaders`
5. Load in `App.vue`'s `loadData()` and render markers in `renderMarkers()`
6. If the data should also appear in 3D: load in `CesiumView.vue`'s `loadGeoJsonData()` and render in `renderData()`

**Add a new panel/module**:
1. Add to the `modules` computed array in `App.vue`
2. Add a tab button and list section in the template
3. Add marker rendering for the new data type in `renderMarkers()`

**Add a new 3D layer in Cesium**:
1. Import the relevant API function in `CesiumView.vue`
2. Add loading logic in `loadGeoJsonData()`
3. Add entity/datasource rendering in `renderData()` (use `addPointEntities()` for points, `addBuildingEntities()` pattern for polygons)

**Change AI model or provider**:
1. Update `backend/.env` with new `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`, `DEEPSEEK_API_KEY`
2. Modify `call_deepseek()` in `backend/main.py` if the API format differs
3. Update `build_ai_messages()` if the prompt structure needs to change
