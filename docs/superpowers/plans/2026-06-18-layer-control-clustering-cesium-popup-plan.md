# Layer Control, Clustering, Cesium Popup & Campus Boundary — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add layer toggle (全部/自习室/POI/充电桩) in both 2D/3D views, marker clustering, unified Cesium popup cards, 2D campus boundary, and 3D charger entity loading.

**Architecture:** Coordinate transforms move from App.vue → geojsonData.js (shared between 2D and 3D). A new `activeLayer` ref drives layer visibility in both views. Clustering via `leaflet.markercluster` grouped by layer. Cesium InfoBox content replaced with popupBuilders.js HTML. No backend changes — all APIs already exist.

**Tech Stack:** Vue 3, Leaflet 1.9.x, leaflet.markercluster, Cesium 1.142, Python backend (unchanged)

## Global Constraints

- No emoji in any marker or popup — pure SVG geometry and CSS typography
- No external icon/image files
- No backend or data file changes
- Install Python packages into `D:\env\miniconda\envs\webgis\python.exe`
- No changes to GeoServer integration or AI recommendation logic

---

## File Mapping

| File | Action | Responsibility |
|---|---|---|
| `frontend/package.json` | Modify | Add `leaflet.markercluster` dependency |
| `frontend/src/services/geojsonData.js` | Modify | Move in `bd09ToGcj02`/`gcj02ToWgs84`/`bd09ToWgs84` |
| `frontend/src/App.vue` | Modify | Remove coord transforms, add `activeLayer` + layer toggle + clustering + boundary |
| `frontend/src/components/CesiumView.vue` | Modify | Import coord transforms + popupBuilders, load chargers, layer toggle, InfoBox restyling |
| `frontend/src/styles/base.css` | Modify | Layer toggle button styles, cluster CSS overrides, Cesium InfoBox overrides |

---

### Task 1: Extract coordinate transforms + install leaflet.markercluster

**Files:**
- Modify: `frontend/src/services/geojsonData.js` (append at end)
- Modify: `frontend/package.json` (add dependency)
- Modify: `frontend/src/App.vue` (remove transforms, import from geojsonData)

**Interfaces:**
- Produces: `bd09ToGcj02(latitude, longitude) → {latitude, longitude}` exported from geojsonData.js
- Produces: `gcj02ToWgs84(latitude, longitude) → {latitude, longitude}` exported from geojsonData.js
- Produces: `bd09ToWgs84(coordinate) → {latitude, longitude}` exported from geojsonData.js

- [ ] **Step 1: Install leaflet.markercluster**

```bash
cd frontend && npm install leaflet.markercluster
```

Expected: package.json and package-lock.json updated. Verify: `node -e "require('leaflet.markercluster'); console.log('OK')"`

- [ ] **Step 2: Append coordinate transforms to geojsonData.js**

Append to `frontend/src/services/geojsonData.js`:

```javascript
/* ── Coordinate transforms (BD-09 ↔ GCJ-02 ↔ WGS84) ───── */

const EARTH_RADIUS = 6378245.0
const EE = 0.006693421622965943
const X_PI = (Math.PI * 3000.0) / 180.0

function transformLat(lng, lat) {
  let r = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * Math.sqrt(Math.abs(lng))
  r += ((20.0 * Math.sin(6.0 * lng * Math.PI) + 20.0 * Math.sin(2.0 * lng * Math.PI)) * 2.0) / 3.0
  r += ((20.0 * Math.sin(lat * Math.PI) + 40.0 * Math.sin((lat / 3.0) * Math.PI)) * 2.0) / 3.0
  r += ((160.0 * Math.sin((lat / 12.0) * Math.PI) + 320 * Math.sin((lat * Math.PI) / 30.0)) * 2.0) / 3.0
  return r
}

function transformLon(lng, lat) {
  let r = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * Math.sqrt(Math.abs(lng))
  r += ((20.0 * Math.sin(6.0 * lng * Math.PI) + 20.0 * Math.sin(2.0 * lng * Math.PI)) * 2.0) / 3.0
  r += ((20.0 * Math.sin(lng * Math.PI) + 40.0 * Math.sin((lng / 3.0) * Math.PI)) * 2.0) / 3.0
  r += ((150.0 * Math.sin((lng / 12.0) * Math.PI) + 300.0 * Math.sin((lng / 30.0) * Math.PI)) * 2.0) / 3.0
  return r
}

export function gcj02ToWgs84(latitude, longitude) {
  const dLat = transformLat(longitude - 105.0, latitude - 35.0)
  const dLon = transformLon(longitude - 105.0, latitude - 35.0)
  const radLat = (latitude / 180.0) * Math.PI
  let magic = Math.sin(radLat)
  magic = 1 - EE * magic * magic
  const sqrtMagic = Math.sqrt(magic)
  const adjustedLat = (dLat * 180.0) / (((EARTH_RADIUS * (1 - EE)) / (magic * sqrtMagic)) * Math.PI)
  const adjustedLon = (dLon * 180.0) / ((EARTH_RADIUS / sqrtMagic) * Math.cos(radLat) * Math.PI)
  return {
    latitude: latitude * 2 - (latitude + adjustedLat),
    longitude: longitude * 2 - (longitude + adjustedLon)
  }
}

export function bd09ToGcj02(latitude, longitude) {
  const x = longitude - 0.0065
  const y = latitude - 0.006
  const z = Math.sqrt(x * x + y * y) - 0.00002 * Math.sin(y * X_PI)
  const theta = Math.atan2(y, x) - 0.000003 * Math.cos(x * X_PI)
  return { latitude: z * Math.sin(theta), longitude: z * Math.cos(theta) }
}

export function bd09ToWgs84(coordinate) {
  const gcj = bd09ToGcj02(coordinate.latitude, coordinate.longitude)
  return gcj02ToWgs84(gcj.latitude, gcj.longitude)
}
```

- [ ] **Step 3: In App.vue, remove coord transforms and import from geojsonData**

In `frontend/src/App.vue`:

Delete lines 249-341 (everything from `/* ── Coordinate transforms ── */` through the end of `getChargerCoordinate`).

Add to the geojsonData import block (line 5-10), append `bd09ToWgs84`:

```javascript
import {
  getFeatureCoordinate,
  loadMapDatasets,
  normalizeFeatureCollection,
  textOrUnknown,
  bd09ToWgs84
} from './services/geojsonData'
```

Also delete the constants `EARTH_RADIUS`, `EE`, `X_PI` on lines 156-158.

Rewrite `getChargerCoordinate` (which stays in App.vue since it's specific to charger station data extraction) compactly:

```javascript
function getChargerCoordinate(station) {
  const latitude = Number(station?.latitude)
  const longitude = Number(station?.longitude)
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null
  return bd09ToWgs84({ latitude, longitude })
}
```

- [ ] **Step 4: Verify build**

```bash
cd frontend && npm run build
```

Expected: 74+ modules, no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/services/geojsonData.js frontend/src/App.vue
git commit -m "refactor: extract coordinate transforms to geojsonData, add leaflet.markercluster"
```

---

### Task 2: Add layer toggle UI to App.vue 2D toolbar

**Files:**
- Modify: `frontend/src/App.vue` (script + template)
- Modify: `frontend/src/styles/base.css` (append layer toggle styles)

**Interfaces:**
- Produces: `activeLayer` ref (`'all' | 'study-rooms' | 'pois' | 'chargers'`)
- Produces: `LAYER_OPTIONS` constant `[{value, label}]` used by both 2D and 3D

- [ ] **Step 1: Add activeLayer ref and LAYER_OPTIONS constant to App.vue script**

After the `viewMode` ref (line 46), add:

```javascript
const activeLayer = ref('all') // 'all' | 'study-rooms' | 'pois' | 'chargers'
```

- [ ] **Step 2: Add layer toggle buttons to App.vue template**

In `frontend/src/App.vue`, inside the `map-toolbar` div (around line 823), after the `view-mode-toggle` div, add:

```html
<div class="layer-toggle">
  <button
    class="layer-btn"
    :class="{ active: activeLayer === 'all' }"
    type="button"
    @click="activeLayer = 'all'"
  >全部</button>
  <button
    class="layer-btn"
    :class="{ active: activeLayer === 'study-rooms' }"
    type="button"
    @click="activeLayer = 'study-rooms'"
  >自习室</button>
  <button
    class="layer-btn"
    :class="{ active: activeLayer === 'pois' }"
    type="button"
    @click="activeLayer = 'pois'"
  >POI</button>
  <button
    class="layer-btn"
    :class="{ active: activeLayer === 'chargers' }"
    type="button"
    @click="activeLayer = 'chargers'"
  >充电桩</button>
</div>
```

- [ ] **Step 3: Add CSS for layer toggle buttons**

Append to `frontend/src/styles/base.css`:

```css
/* ── Layer toggle ─────────────────────────────────────── */

.layer-toggle {
  display: flex;
  gap: 3px;
  margin-left: 8px;
}

.layer-btn {
  padding: 3px 8px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 10px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.15s ease;
}

.layer-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.layer-btn.active {
  border-color: var(--color-accent);
  background: var(--color-accent-light);
  color: var(--color-accent);
  font-weight: 600;
}
```

- [ ] **Step 4: Verify build**

```bash
cd frontend && npm run build
```

Expected: no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.vue frontend/src/styles/base.css
git commit -m "feat: add layer toggle UI to 2D map toolbar"
```

---

### Task 3: Implement clustering + wire layer toggle visibility

**Files:**
- Modify: `frontend/src/App.vue` (marker rendering, map init, switchTo3D)

**Interfaces:**
- Consumes: `activeLayer` ref from Task 2
- Consumes: `leaflet.markercluster` plugin
- Produces: `studyClusterGroup`, `poiClusterGroup` — two `L.markerClusterGroup` instances

- [ ] **Step 1: Add import for MarkerCluster**

In App.vue, after `import L from 'leaflet'`, add:

```javascript
import 'leaflet.markercluster'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'
```

- [ ] **Step 2: Replace markerLayer with two cluster groups**

In App.vue, replace `let markerLayer = null` and the related state with:

```javascript
let studyClusterGroup = null
let poiClusterGroup = null
```

- [ ] **Step 3: Rewrite renderMarkers to use cluster groups + layer toggle**

Replace the current `addPointMarkers` and `renderMarkers` (lines 345-373) with:

```javascript
function createClusterGroup() {
  return L.markerClusterGroup({
    maxClusterRadius: 50,
    spiderfyOnMaxZoom: true,
    showCoverageOnHover: false,
    zoomToBoundsOnClick: true,
    iconCreateFunction: function (cluster) {
      const count = cluster.getChildCount()
      return L.divIcon({
        html: `<div class="cluster-icon"><span>${count}</span></div>`,
        className: 'custom-cluster-icon',
        iconSize: L.point(40, 40)
      })
    }
  })
}

function renderMarkers() {
  // Clear and rebuild study room cluster
  if (studyClusterGroup) { map.removeLayer(studyClusterGroup) }
  studyClusterGroup = createClusterGroup()
  studyRooms.value.forEach((feature, index) => {
    const coordinate = getFeatureCoordinate(feature)
    if (!coordinate) return
    const marker = L.marker([coordinate.latitude, coordinate.longitude], {
      icon: getStudyRoomIcon()
    }).bindPopup(buildStudyRoomPopup(feature))
    studyClusterGroup.addLayer(marker)
    markerRefs.set(`study-rooms:${getFeatureId(feature, 'study_room', index)}`, marker)
  })

  // Clear and rebuild POI cluster
  if (poiClusterGroup) { map.removeLayer(poiClusterGroup) }
  poiClusterGroup = createClusterGroup()
  displayPois.value.forEach((feature, index) => {
    const coordinate = getFeatureCoordinate(feature)
    if (!coordinate) return
    const marker = L.marker([coordinate.latitude, coordinate.longitude], {
      icon: getPoiIcon((feature.properties || {}).category)
    }).bindPopup(buildPoiPopup(feature))
    poiClusterGroup.addLayer(marker)
    markerRefs.set(`pois:${getFeatureId(feature, 'poi', index)}`, marker)
  })

  applyLayerVisibility()
}

function applyLayerVisibility() {
  if (!map) return
  const layer = activeLayer.value

  // Study rooms
  if (layer === 'all' || layer === 'study-rooms') {
    if (!map.hasLayer(studyClusterGroup)) map.addLayer(studyClusterGroup)
  } else {
    if (map.hasLayer(studyClusterGroup)) map.removeLayer(studyClusterGroup)
  }

  // POIs
  if (layer === 'all' || layer === 'pois') {
    if (!map.hasLayer(poiClusterGroup)) map.addLayer(poiClusterGroup)
  } else {
    if (map.hasLayer(poiClusterGroup)) map.removeLayer(poiClusterGroup)
  }

  // Chargers
  if (layer === 'all' || layer === 'chargers') {
    if (!map.hasLayer(chargerLayer)) map.addLayer(chargerLayer)
  } else {
    if (map.hasLayer(chargerLayer)) map.removeLayer(chargerLayer)
  }
}
```

- [ ] **Step 4: Update init2DMap to use new variables**

In `init2DMap()`, replace `markerLayer = L.layerGroup().addTo(map)` with:

```javascript
studyClusterGroup = createClusterGroup()
poiClusterGroup = createClusterGroup()
```

Remove the line that adds markerLayer to the map — instead cluster groups are added during `renderMarkers()`.

- [ ] **Step 5: Update switchTo3D to clean up new variables**

In `switchTo3D()`, replace `markerLayer = null` with:

```javascript
studyClusterGroup = null
poiClusterGroup = null
```

- [ ] **Step 6: Add watch on activeLayer to re-apply visibility**

After the `watch(viewMode, ...)` block (around line 579), add:

```javascript
watch(activeLayer, () => {
  applyLayerVisibility()
})
```

- [ ] **Step 7: Add cluster icon CSS**

Append to `frontend/src/styles/base.css`:

```css
/* ── Cluster icon ──────────────────────────────────────── */

.custom-cluster-icon {
  background: transparent;
  border: none;
}

.cluster-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--color-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(194, 100, 79, 0.3);
}

.cluster-icon span {
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
  font-family: var(--font-body);
}
```

- [ ] **Step 8: Verify build**

```bash
cd frontend && npm run build
```

Expected: no errors.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/App.vue frontend/src/styles/base.css
git commit -m "feat: implement marker clustering with layer toggle visibility"
```

---

### Task 4: Add campus boundary to 2D map

**Files:**
- Modify: `frontend/src/App.vue` (init2DMap)

**Interfaces:**
- Consumes: `fetch` to `/api/zjg-boundary` (backend endpoint already exists)

- [ ] **Step 1: Add boundary loading to init2DMap**

In `frontend/src/App.vue`, inside `init2DMap()`, after the tile layer creation and before `await loadData()`, add:

```javascript
// Load campus boundary
try {
  const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
  const boundaryRes = await fetch(`${apiBase}/api/zjg-boundary`)
  if (boundaryRes.ok) {
    const boundaryData = await boundaryRes.json()
    L.geoJSON(boundaryData, {
      style: {
        fillColor: '#c2644f',
        fillOpacity: 0.08,
        color: '#c2644f',
        weight: 2.5
      },
      interactive: false
    }).addTo(map).bringToBack()
  }
} catch { /* boundary unavailable — silently skip */ }
```

- [ ] **Step 2: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat: add campus boundary overlay to 2D map"
```

---

### Task 5: Update CesiumView — layer toggle, unified popup, charger entities, InfoBox restyling

**Files:**
- Modify: `frontend/src/components/CesiumView.vue`
- Modify: `frontend/src/styles/base.css` (append InfoBox overrides)

**Interfaces:**
- Consumes: `bd09ToWgs84` from `geojsonData.js`
- Consumes: `buildStudyRoomPopup`, `buildPoiPopup`, `buildChargerPopup` from `popupBuilders.js`
- Consumes: `getChargerStations` from `api.js`
- Consumes: `activeLayer` via `defineProps` from parent
- Produces: Layer toggle buttons in cesium-top-bar, entity groups with `show` controlled by `activeLayer`

- [ ] **Step 1: Add imports and props to CesiumView**

In `frontend/src/components/CesiumView.vue`, modify the import block (lines 2-5):

```javascript
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as Cesium from 'cesium'
import { getStudyRooms, getPois, getBuildings, getChargerStations } from '../services/api'
import { normalizeFeatureCollection, textOrUnknown, getFeatureCoordinate, bd09ToWgs84 } from '../services/geojsonData'
import { buildStudyRoomPopup, buildPoiPopup, buildChargerPopup } from '../services/popupBuilders'
```

Change `defineEmits` + add `defineProps`:

```javascript
const props = defineProps({
  activeLayer: { type: String, default: 'all' }
})

const emit = defineEmits(['back'])
```

- [ ] **Step 2: Replace buildDescription with popupBuilders and add entity tracking**

Delete the `buildDescription` function (lines 161-180).

Add entity tracking arrays (after `const dataSources = []`):

```javascript
const studyRoomEntities = []
const poiEntities = []
const chargerEntities = []
```

- [ ] **Step 3: Rewrite addPointEntities to use popupBuilders + entity arrays**

Replace `addPointEntities` (lines 184-218) with:

```javascript
function addPointEntities(features, options) {
  if (!features.length) return

  features.forEach((feature) => {
    const coord = getFeatureCoordinate(feature)
    if (!coord) return

    const props = feature.properties || {}
    const name = props.name || '未知地点'

    const entity = viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(coord.longitude, coord.latitude),
      billboard: {
        image: createPinCanvas(options.color, options.label),
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        scale: 0.75,
        distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 12000)
      },
      label: {
        text: name,
        font: '12px "Microsoft YaHei", sans-serif',
        fillColor: Cesium.Color.fromCssColorString('#1a1a2e'),
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 2.5,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.TOP,
        pixelOffset: new Cesium.Cartesian2(0, 18),
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 1000)
      },
      description: options.popupBuilder(feature),
      properties: { layerType: options.layerType }
    })

    options.entityArray.push(entity)
  })
}
```

- [ ] **Step 4: Update renderData to use new addPointEntities + add charger loading**

Replace `loadGeoJsonData` to also return chargers, and replace `renderData`:

In `loadGeoJsonData`, add a `chargers` result array:

```javascript
async function loadGeoJsonData() {
  const results = { studyRooms: [], pois: [], chargers: [], buildings: [], campusBoundary: [] }
  // ... existing studyRooms/pois/buildings/boundary loading ...

  // Load charger stations
  try {
    const chargerRes = await getChargerStations()
    if (chargerRes.data?.ok && Array.isArray(chargerRes.data.stations)) {
      results.chargers = chargerRes.data.stations
    }
  } catch { /* fall through */ }

  return results
}
```

Replace `renderData` (lines 317-338) with:

```javascript
function addChargerEntities(stations) {
  if (!stations.length) return
  stations.forEach((station) => {
    const lat = Number(station?.latitude)
    const lng = Number(station?.longitude)
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return

    const wgsCoord = bd09ToWgs84({ latitude: lat, longitude: lng })
    const hasAvailable = Number(station?.available_ports) > 0
    const color = hasAvailable ? '#22c55e' : '#ef4444'
    const label = '⚡'

    const entity = viewer.entities.add({
      position: Cesium.Cartesian3.fromDegrees(wgsCoord.longitude, wgsCoord.latitude),
      billboard: {
        image: createPinCanvas(color, label),
        verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        scale: 0.75,
        distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 12000)
      },
      label: {
        text: station.name || '未知站点',
        font: '12px "Microsoft YaHei", sans-serif',
        fillColor: Cesium.Color.fromCssColorString('#1a1a2e'),
        outlineColor: Cesium.Color.WHITE,
        outlineWidth: 2.5,
        style: Cesium.LabelStyle.FILL_AND_OUTLINE,
        verticalOrigin: Cesium.VerticalOrigin.TOP,
        pixelOffset: new Cesium.Cartesian2(0, 18),
        heightReference: Cesium.HeightReference.CLAMP_TO_GROUND,
        distanceDisplayCondition: new Cesium.DistanceDisplayCondition(0, 1000)
      },
      description: buildChargerPopup(station),
      properties: { layerType: 'chargers' }
    })

    chargerEntities.push(entity)
  })
}

async function renderData() {
  isLoading.value = true
  loadMessage.value = '正在加载三维数据...'

  const { studyRooms, pois, chargers, buildings, campusBoundary } = await loadGeoJsonData()

  const total = studyRooms.length + pois.length + chargers.length + buildings.length + campusBoundary.length
  if (total === 0) {
    dataEmpty.value = true
    loadMessage.value = '暂无可用于三维展示的数据。'
    isLoading.value = false
    return
  }

  addCampusBoundary(campusBoundary)
  addBuildingEntities(buildings)
  addPointEntities(studyRooms, { type: 'study-room', color: '#3b82f6', label: '📖', popupBuilder: buildStudyRoomPopup, layerType: 'study-rooms', entityArray: studyRoomEntities })
  addPointEntities(pois, { type: 'poi', color: '#10b981', label: '📍', popupBuilder: buildPoiPopup, layerType: 'pois', entityArray: poiEntities })
  addChargerEntities(chargers)

  loadMessage.value = `已加载 ${studyRooms.length} 自习室 · ${pois.length} POI · ${chargers.length} 充电桩 · ${buildings.length} 建筑 · ${campusBoundary.length} 校区边界`
  isLoading.value = false
}
```

- [ ] **Step 5: Add layer visibility control function + watch**

After `renderData`, add:

```javascript
function applyLayerVisibility() {
  const layer = props.activeLayer
  const showStudy = layer === 'all' || layer === 'study-rooms'
  const showPoi = layer === 'all' || layer === 'pois'
  const showCharger = layer === 'all' || layer === 'chargers'

  studyRoomEntities.forEach(e => { e.show = showStudy })
  poiEntities.forEach(e => { e.show = showPoi })
  chargerEntities.forEach(e => { e.show = showCharger })
}
```

- [ ] **Step 6: Add activeLayer watch in CesiumView**

In the `<script setup>`, add:

```javascript
watch(() => props.activeLayer, () => {
  applyLayerVisibility()
})
```

- [ ] **Step 7: Add InfoBox styling to customize popup appearance**

In `initCesium()`, after viewer creation, add InfoBox customization:

```javascript
// Customize InfoBox to use popup-card styles
viewer.infoBox.container.classList.add('cesium-infobox-custom')
```

- [ ] **Step 8: Add Cesium InfoBox CSS overrides**

Append to `frontend/src/styles/base.css`:

```css
/* ── Cesium InfoBox override ───────────────────────────── */

.cesium-infobox-custom {
  max-width: 260px;
  border: none;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 3px 16px rgba(0,0,0,0.12);
  background: transparent;
}

.cesium-infobox-custom .cesium-infoBox {
  border: none;
  border-radius: 8px;
  overflow: hidden;
  background: transparent;
}

.cesium-infobox-custom .cesium-infoBox-title {
  display: none;
}

.cesium-infobox-custom .cesium-infoBox-description {
  padding: 0;
  font-family: var(--font-body);
}

.cesium-infobox-custom .cesium-infoBox-description .popup-card {
  box-shadow: none;
  border-radius: 0;
}

.cesium-infobox-custom .cesium-infoBox-iframe {
  display: none;
}

/* Make the InfoBox close button smaller */
.cesium-infobox-custom .cesium-infoBox-close {
  top: 8px;
  right: 8px;
  z-index: 2;
}
```

- [ ] **Step 9: Add layer toggle buttons to CesiumView template**

In `frontend/src/components/CesiumView.vue`, inside `cesium-top-bar` (after the basemap switcher div), add:

```html
<div class="layer-toggle cesium-layer-toggle">
  <button
    class="layer-btn"
    :class="{ active: activeLayer === 'all' }"
    type="button"
    @click="$emit('update:activeLayer', 'all')"
  >全部</button>
  <button
    class="layer-btn"
    :class="{ active: activeLayer === 'study-rooms' }"
    type="button"
    @click="$emit('update:activeLayer', 'study-rooms')"
  >自习室</button>
  <button
    class="layer-btn"
    :class="{ active: activeLayer === 'pois' }"
    type="button"
    @click="$emit('update:activeLayer', 'pois')"
  >POI</button>
  <button
    class="layer-btn"
    :class="{ active: activeLayer === 'chargers' }"
    type="button"
    @click="$emit('update:activeLayer', 'chargers')"
  >充电桩</button>
</div>
```

- [ ] **Step 10: Add additional emit in CesiumView**

Change:

```javascript
const emit = defineEmits(['back', 'update:activeLayer'])
```

Change:

```javascript
const emit = defineEmits(['back', 'update:activeLayer'])
```

Add to the layer toggle CSS section in `base.css`:

```css
.cesium-layer-toggle {
  margin-left: 0;
}

.cesium-layer-toggle .layer-btn {
  color: #a0c8e8;
  border-color: rgba(97, 200, 255, 0.25);
  background: rgba(10, 20, 34, 0.5);
}

.cesium-layer-toggle .layer-btn:hover {
  color: #ffffff;
  border-color: #61c8ff;
}

.cesium-layer-toggle .layer-btn.active {
  color: #ffffff;
  border-color: #61c8ff;
  background: rgba(97, 200, 255, 0.2);
}
```

But wait — `.layer-btn` from Task 2 uses `var()` values that won't work in the Cesium dark context. I need the Cesium-specific layer-btn styles to override. The CSS specificity from `.cesium-layer-toggle .layer-btn` will beat `.layer-btn`. Let me use that.

- [ ] **Step 12: Update App.vue CesiumView binding**

In App.vue template, change:

```html
<CesiumView v-else @back="switchTo2D" :active-layer="activeLayer" @update:active-layer="activeLayer = $event" />
```

- [ ] **Step 13: Verify build**

```bash
cd frontend && npm run build
```

- [ ] **Step 14: Commit**

```bash
git add frontend/src/components/CesiumView.vue frontend/src/styles/base.css frontend/src/App.vue
git commit -m "feat: add Cesium layer toggle, unified popup cards, charger entities, InfoBox restyling"
```

---

### Task 6: Verify end-to-end

- [ ] **Step 1: Start backend**

```bash
cd backend && D:\env\miniconda\envs\webgis\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 &
```

- [ ] **Step 2: Start frontend dev server**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: Visual verification checklist**

Open `http://localhost:5173` and verify:
- [ ] 2D map-toolbar shows layer toggle buttons (全部/自习室/POI/充电桩)
- [ ] Click "自习室" — only study room markers visible on map
- [ ] Click "POI" — only POI markers visible
- [ ] Click "充电桩" — only charger markers visible
- [ ] Click "全部" — all markers visible
- [ ] Zoom out — markers cluster into numbered circles
- [ ] Click cluster circle — map zooms in/spiders out
- [ ] Campus boundary visible as subtle red-brown outline
- [ ] Switch to 3D — layer toggle appears in Cesium top bar
- [ ] 3D layer toggle works (show/hide study room, POI, charger entities)
- [ ] Click entity in Cesium — InfoBox shows popup-card style content matching 2D
- [ ] Charger entities visible in 3D with green/red pin colors
- [ ] Switch back to 2D — layer selection state preserved
- [ ] No console errors

- [ ] **Step 4: Final commit if fixups needed**

```bash
git add -A && git commit -m "chore: final verification fixes"
```
