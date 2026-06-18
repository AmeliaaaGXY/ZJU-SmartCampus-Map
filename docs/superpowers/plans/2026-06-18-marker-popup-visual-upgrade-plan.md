# Marker 图标与弹窗卡片视觉升级 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Leaflet circleMarker with custom SVG divIcon markers (10 types) and restructure popups as dark-header card layouts.

**Architecture:** Two new service files (`markerIcons.js`, `popupBuilders.js`) extracted from `App.vue`. Markers use `L.divIcon` with inline SVG; popups use HTML strings with new CSS classes. No backend or data changes.

**Tech Stack:** Leaflet 1.9.x `L.divIcon`, inline SVG paths, Vue 3 SFC

## Global Constraints

- No emoji in any marker or popup — pure SVG geometry and CSS typography
- No external icon/image files — all SVG inline in JS
- No backend or data file changes
- No changes to Cesium 3D view
- `textOrUnknown()` handles all null/undefined field values as before

---

## File Mapping

| File | Action | Responsibility |
|---|---|---|
| `frontend/src/services/markerIcons.js` | **Create** | 10 SVG icon definitions + 3 exported factory functions |
| `frontend/src/services/popupBuilders.js` | **Create** | 3 popup HTML builder functions |
| `frontend/src/styles/base.css` | **Modify** | Add `.popup-card-*` CSS block |
| `frontend/src/App.vue` | **Modify** | Delete old marker/popup code, import new services, update legend |

---

### Task 1: Create `markerIcons.js` — SVG icon system

**Files:**
- Create: `frontend/src/services/markerIcons.js`

**Interfaces:**
- Produces: `getStudyRoomIcon()` → `L.divIcon`
- Produces: `getPoiIcon(category: string)` → `L.divIcon`
- Produces: `getChargerIcon(hasAvailable: boolean, isSelected: boolean)` → `L.divIcon`

- [ ] **Step 1: Create the file with full implementation**

```javascript
import L from 'leaflet'

/* ── Color palette ──────────────────────────────────── */

const COLORS = {
  studyRoom: '#3b82f6',
  library: '#8b5cf6',
  teaching: '#f59e0b',
  canteen: '#ef4444',
  scenic: '#10b981',
  service: '#6366f1',
  museum: '#ec4899',
  other: '#6b7280',
  chargerAvailable: '#22c55e',
  chargerUnavailable: '#ef4444'
}

const CATEGORY_COLORS = {
  library: COLORS.library,
  teaching: COLORS.teaching,
  canteen: COLORS.canteen,
  scenic: COLORS.scenic,
  service: COLORS.service,
  museum: COLORS.museum,
  other: COLORS.other
}

/* ── Shared pin template ────────────────────────────── */

function buildPinSvg(colorHex, iconSvgContent) {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="40" viewBox="0 0 32 40">
    <circle cx="16" cy="14" r="16" fill="${colorHex}" opacity="0.2"/>
    <circle cx="16" cy="14" r="11" fill="none" stroke="#ffffff" stroke-width="2.5"/>
    <circle cx="16" cy="14" r="10" fill="${colorHex}"/>
    ${iconSvgContent}
    <polygon points="16,40 12,31 20,31" fill="${colorHex}"/>
  </svg>`
}

function makeDivIcon(svgContent, className) {
  return L.divIcon({
    html: svgContent,
    className: className || '',
    iconSize: [32, 40],
    iconAnchor: [16, 40],
    popupAnchor: [0, -36]
  })
}

/* ── Icon paths ─────────────────────────────────────── */

const ICONS = {
  studyRoom: '<path d="M10 10 Q13 7 16 10 Q19 7 22 10 L22 19 Q19 16 16 19 Q13 16 10 19 Z" fill="none" stroke="#ffffff" stroke-width="1.4" stroke-linejoin="round"/>',

  library: '<rect x="11" y="7.5" width="10" height="2" rx="0.5" fill="#ffffff" opacity="0.9"/>'
    + '<rect x="10" y="10.5" width="12" height="2" rx="0.5" fill="#ffffff" opacity="0.9"/>'
    + '<rect x="11" y="13.5" width="10" height="2" rx="0.5" fill="#ffffff" opacity="0.9"/>'
    + '<rect x="10" y="16.5" width="12" height="2" rx="0.5" fill="#ffffff" opacity="0.9"/>',

  teaching: '<rect x="9" y="8" width="14" height="13" rx="1" fill="none" stroke="#ffffff" stroke-width="1.3"/>'
    + '<rect x="12.5" y="13" width="7" height="8" fill="none" stroke="#ffffff" stroke-width="1" opacity="0.8"/>'
    + '<rect x="11.5" y="10" width="3" height="2.5" fill="#ffffff" opacity="0.85"/>'
    + '<rect x="17.5" y="10" width="3" height="2.5" fill="#ffffff" opacity="0.85"/>',

  canteen: '<path d="M10 13 Q10 20 16 20 Q22 20 22 13" fill="none" stroke="#ffffff" stroke-width="1.4"/>'
    + '<path d="M13 8 Q13.5 5 14.5 6.5" fill="none" stroke="#ffffff" stroke-width="1" stroke-linecap="round"/>'
    + '<path d="M16 7 Q16.5 4 17.5 5.5" fill="none" stroke="#ffffff" stroke-width="1" stroke-linecap="round"/>'
    + '<path d="M19 8.5 Q20 6 21 7.5" fill="none" stroke="#ffffff" stroke-width="1" stroke-linecap="round"/>',

  scenic: '<path d="M16 6.5 Q13 13 8 14 Q13 15 16 20" fill="#ffffff" opacity="0.9"/>'
    + '<path d="M16 6.5 Q19 13 24 14 Q19 15 16 20" fill="#ffffff" opacity="0.9"/>'
    + '<rect x="15" y="18" width="2" height="4" fill="#ffffff" opacity="0.75"/>',

  service: '<rect x="9" y="10" width="14" height="9" rx="1" fill="none" stroke="#ffffff" stroke-width="1.3"/>'
    + '<path d="M9 10 L16 15 L23 10" fill="none" stroke="#ffffff" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>',

  museum: '<rect x="11" y="7.5" width="10" height="2" rx="1" fill="#ffffff" opacity="0.9"/>'
    + '<rect x="12" y="9.5" width="8" height="11" rx="0.5" fill="none" stroke="#ffffff" stroke-width="1.2"/>'
    + '<line x1="12" y1="11.5" x2="20" y2="11.5" stroke="#ffffff" stroke-width="0.8"/>'
    + '<line x1="12" y1="14.5" x2="20" y2="14.5" stroke="#ffffff" stroke-width="0.8"/>'
    + '<line x1="12" y1="17.5" x2="20" y2="17.5" stroke="#ffffff" stroke-width="0.8"/>',

  other: '<circle cx="16" cy="13" r="3" fill="none" stroke="#ffffff" stroke-width="1.5"/>'
    + '<line x1="16" y1="16" x2="16" y2="19" stroke="#ffffff" stroke-width="1.5" stroke-linecap="round"/>',

  charger: '<polygon points="17,7 12,15 15.5,15 13,22 20,13 16.5,13 19,7" fill="#ffffff"/>'
}

/* ── Exported factory functions ──────────────────────── */

export function getStudyRoomIcon() {
  return makeDivIcon(
    buildPinSvg(COLORS.studyRoom, ICONS.studyRoom),
    'custom-marker-icon study-room-icon'
  )
}

export function getPoiIcon(category) {
  const color = CATEGORY_COLORS[category] || COLORS.other
  const iconPath = ICONS[category] || ICONS.other
  return makeDivIcon(
    buildPinSvg(color, iconPath),
    `custom-marker-icon poi-icon poi-${category || 'other'}`
  )
}

export function getChargerIcon(hasAvailable, isSelected) {
  const color = hasAvailable ? COLORS.chargerAvailable : COLORS.chargerUnavailable
  // Selected: larger outer glow via opacity boost
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="40" viewBox="0 0 32 40">
    <circle cx="16" cy="14" r="16" fill="${color}" opacity="${isSelected ? 0.35 : 0.2}"/>
    <circle cx="16" cy="14" r="11" fill="none" stroke="#ffffff" stroke-width="${isSelected ? 3 : 2.5}"/>
    <circle cx="16" cy="14" r="10" fill="${color}"/>
    ${ICONS.charger}
    <polygon points="16,40 12,31 20,31" fill="${color}"/>
  </svg>`
  return makeDivIcon(svg, `custom-marker-icon charger-icon ${isSelected ? 'charger-selected' : ''}`)
}

/* ── Color map export (for legend / popup headers) ───── */

export const POI_CATEGORY_COLORS = CATEGORY_COLORS
export { COLORS as MARKER_COLORS }
```

- [ ] **Step 2: Verify the file parses cleanly**

```bash
node -e "import('./frontend/src/services/markerIcons.js').then(m => console.log(Object.keys(m)))"
```
Expected output: `[ 'getStudyRoomIcon', 'getPoiIcon', 'getChargerIcon', 'POI_CATEGORY_COLORS', 'MARKER_COLORS' ]`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/markerIcons.js
git commit -m "feat: add SVG divIcon marker system with 10 category icons"
```

---

### Task 2: Create `popupBuilders.js` — Card-style popup HTML builders

**Files:**
- Create: `frontend/src/services/popupBuilders.js`

**Interfaces:**
- Produces: `buildStudyRoomPopup(feature)` → HTML string
- Produces: `buildPoiPopup(feature)` → HTML string
- Produces: `buildChargerPopup(station)` → HTML string

- [ ] **Step 1: Create the file with full implementation**

```javascript
import { textOrUnknown } from './geojsonData'
import { MARKER_COLORS, POI_CATEGORY_COLORS } from './markerIcons'

/* ── Helpers ────────────────────────────────────────── */

function esc(text) {
  return String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function headerColor(category) {
  return POI_CATEGORY_COLORS[category] || MARKER_COLORS.other
}

function attrRow(label, value) {
  return `<span class="attr-label">${esc(label)}</span><span class="attr-value">${esc(value)}</span>`
}

/* ── Study room popup ───────────────────────────────── */

export function buildStudyRoomPopup(feature) {
  const p = feature.properties || {}
  const name = esc(textOrUnknown(p.name))
  const type = esc(textOrUnknown(p.type))
  const building = esc(textOrUnknown(p.building))
  const floor = esc(textOrUnknown(p.floor))
  const room = esc(textOrUnknown(p.room))
  const location = [floor, room].filter(Boolean).join(' · ') || '未知'
  const openTime = esc(textOrUnknown(p.open_time))
  const closeTime = esc(textOrUnknown(p.close_time))
  const seatAvail = esc(textOrUnknown(p.seat_available))
  const seatTotal = esc(textOrUnknown(p.seat_total))
  const hasPower = esc(textOrUnknown(p.has_power))
  const noiseLevel = esc(textOrUnknown(p.noise_level))
  const tags = esc(textOrUnknown(p.tags))
  const desc = esc(textOrUnknown(p.description))

  return `<div class="popup-card">
    <div class="popup-card-header" style="background:${MARKER_COLORS.studyRoom};">
      <div class="popup-card-title">${name}</div>
      <div class="popup-card-subtitle">${type}</div>
    </div>
    <div class="popup-card-body">
      <div class="attr-grid">
        ${attrRow('所在建筑', building)}
        ${attrRow('楼层房间', location)}
        ${attrRow('开放时间', openTime + ' — ' + closeTime)}
        ${attrRow('可用座位', seatAvail + ' / ' + seatTotal)}
        ${attrRow('插座条件', hasPower)}
        ${attrRow('安静程度', noiseLevel)}
        ${attrRow('标签', tags)}
      </div>
    </div>
    <div class="popup-card-desc">${desc}</div>
  </div>`
}

/* ── POI popup ──────────────────────────────────────── */

export function buildPoiPopup(feature) {
  const p = feature.properties || {}
  const category = p.category || 'other'
  const name = esc(textOrUnknown(p.name))
  const catLabel = esc(textOrUnknown(category))
  const audience = esc(textOrUnknown(p.audience))
  const openTime = esc(textOrUnknown(p.open_time))
  const desc = esc(textOrUnknown(p.description))

  const catNames = {
    library: '图书馆', teaching: '教学楼', canteen: '食堂',
    scenic: '景观', service: '服务设施', museum: '博物馆', other: '其他'
  }
  const catDisplay = catNames[category] || catLabel

  return `<div class="popup-card">
    <div class="popup-card-header" style="background:${headerColor(category)};">
      <div class="popup-card-title">${name}</div>
      <div class="popup-card-subtitle">${catDisplay}</div>
    </div>
    <div class="popup-card-body">
      <div class="attr-grid">
        ${attrRow('类别', catDisplay)}
        ${attrRow('适用人群', audience)}
        ${attrRow('开放时间', openTime)}
      </div>
    </div>
    <div class="popup-card-desc">${desc}</div>
  </div>`
}

/* ── Charger popup ──────────────────────────────────── */

export function buildChargerPopup(station) {
  const name = esc(textOrUnknown(station.name))
  const provider = esc(textOrUnknown(station.provider))
  const campus = esc(textOrUnknown(station.campus_name || station.campus))
  const available = esc(textOrUnknown(station.available_ports))
  const used = esc(textOrUnknown(station.used_ports))
  const total = esc(textOrUnknown(station.total_ports))
  const faults = esc(textOrUnknown(station.error_ports))
  const updated = esc(textOrUnknown(station.updated_at))

  const hasAvailable = Number(station?.available_ports) > 0
  const headerBg = hasAvailable ? MARKER_COLORS.chargerAvailable : MARKER_COLORS.chargerUnavailable

  return `<div class="popup-card">
    <div class="popup-card-header" style="background:${headerBg};">
      <div class="popup-card-title">${name}</div>
      <div class="popup-card-subtitle">充电桩</div>
    </div>
    <div class="popup-card-body">
      <div class="attr-grid">
        ${attrRow('服务商', provider)}
        ${attrRow('校区', campus)}
        ${attrRow('空闲端口', available)}
        ${attrRow('已用端口', used)}
        ${attrRow('总端口数', total)}
        ${attrRow('故障数', faults)}
        ${attrRow('更新时间', updated)}
      </div>
    </div>
  </div>`
}
```

- [ ] **Step 2: Verify import resolution**

```bash
node -e "import('./frontend/src/services/popupBuilders.js').then(m => console.log(Object.keys(m)))"
```
Expected output: `[ 'buildStudyRoomPopup', 'buildPoiPopup', 'buildChargerPopup' ]`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/popupBuilders.js
git commit -m "feat: add card-style popup HTML builders"
```

---

### Task 3: Add popup card CSS to `base.css`

**Files:**
- Modify: `frontend/src/styles/base.css` (append at end)

**Interfaces:**
- Produces: CSS classes `.popup-card`, `.popup-card-header`, `.popup-card-body`, `.popup-card-desc`, `.attr-grid`, `.attr-label`, `.attr-value`, `.custom-marker-icon`

- [ ] **Step 1: Append popup card and custom marker styles**

Append to `frontend/src/styles/base.css`:

```css
/* ── Popup card system ──────────────────────────────── */

.popup-card {
  max-width: 240px;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 3px 16px rgba(0, 0, 0, 0.1);
  font-family: var(--font-body);
  line-height: 1.5;
}

.popup-card-header {
  padding: 10px 14px;
  color: #ffffff;
}

.popup-card-title {
  font-size: 14px;
  font-weight: 700;
  line-height: 1.3;
}

.popup-card-subtitle {
  margin-top: 2px;
  font-size: 10px;
  opacity: 0.85;
}

.popup-card-body {
  padding: 12px 14px;
  background: #ffffff;
}

.attr-grid {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 6px 12px;
  font-size: 11px;
}

.attr-label {
  color: var(--color-text-muted);
  white-space: nowrap;
}

.attr-value {
  color: var(--color-text);
  font-weight: 500;
}

.popup-card-desc {
  padding: 8px 14px 10px;
  border-top: 1px solid var(--color-border);
  background: #ffffff;
  color: var(--color-text-muted);
  font-size: 10px;
  line-height: 1.55;
  font-style: italic;
}

/* ── Custom marker icons ─────────────────────────────── */

.custom-marker-icon {
  background: transparent;
  border: none;
}

/* Override Leaflet's default divIcon background */
.leaflet-div-icon.custom-marker-icon {
  background: transparent;
  border: none;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/styles/base.css
git commit -m "feat: add popup card and custom marker icon CSS"
```

---

### Task 4: Update `App.vue` — Script section

**Files:**
- Modify: `frontend/src/App.vue`

**Interfaces:**
- Consumes: `getStudyRoomIcon`, `getPoiIcon`, `getChargerIcon` from `markerIcons.js`
- Consumes: `buildStudyRoomPopup`, `buildPoiPopup`, `buildChargerPopup` from `popupBuilders.js`
- Produces: `renderMarkers()`, `renderChargerMarkers()`, `setSelectedCharger()`, `resetSelectedChargerMarker()` updated signatures

**Important:** The `addPointMarkers` signature changes from `{color, fillColor, popupBuilder, markerKey}` to `{getIcon, popupBuilder, markerKey}`. The charger markers switch from `L.circleMarker` to `L.marker` with divIcon.

- [ ] **Step 1: Add new imports to App.vue**

At line 10 (after the `geojsonData` import block), add:

```javascript
import { getStudyRoomIcon, getPoiIcon, getChargerIcon, POI_CATEGORY_COLORS, MARKER_COLORS } from './services/markerIcons'
import { buildStudyRoomPopup, buildPoiPopup, buildChargerPopup } from './services/popupBuilders'
```

If `geojsonData` import already occupies lines 5-9 and `api` import lines 11-14, insert between the existing import groups:

```javascript
import {
  getChargerStations,
  getChargerStatus,
  recommendStudyRoom
} from './services/api'
import { getStudyRoomIcon, getPoiIcon, getChargerIcon, POI_CATEGORY_COLORS, MARKER_COLORS } from './services/markerIcons'
import { buildStudyRoomPopup, buildPoiPopup, buildChargerPopup } from './services/popupBuilders'
import {
  checkGeoServerStatus,
```

- [ ] **Step 2: Replace `addPointMarkers` function**

Replace the existing `addPointMarkers` function (approximately lines 391-406) with:

```javascript
function addPointMarkers(features, options) {
  features.forEach((feature, index) => {
    const coordinate = getFeatureCoordinate(feature)
    if (!coordinate) return
    const marker = L.marker([coordinate.latitude, coordinate.longitude], {
      icon: options.getIcon(feature)
    })
      .addTo(markerLayer)
      .bindPopup(options.popupBuilder(feature))
    markerRefs.set(options.markerKey(feature, index), marker)
  })
}
```

- [ ] **Step 3: Replace `renderMarkers` call sites**

Replace the two `addPointMarkers` calls inside `renderMarkers()`:

```javascript
  addPointMarkers(studyRooms.value, {
    getIcon: () => getStudyRoomIcon(),
    popupBuilder: buildStudyRoomPopup,
    markerKey: (feature, index) => `study-rooms:${getFeatureId(feature, 'study_room', index)}`
  })

  addPointMarkers(displayPois.value, {
    getIcon: (feature) => getPoiIcon((feature.properties || {}).category),
    popupBuilder: buildPoiPopup,
    markerKey: (feature, index) => `pois:${getFeatureId(feature, 'poi', index)}`
  })
```

- [ ] **Step 4: Replace `getChargerMarkerStyle` with icon-based selection, then update `renderChargerMarkers`**

Replace the `getChargerMarkerStyle` function (lines 380-389) with nothing (delete it). Then replace the `renderChargerMarkers` function body (lines 459-473) — the `L.circleMarker` creation loop — with `L.marker`:

```javascript
function renderChargerMarkers() {
  if (!chargerLayer) return
  chargerLayer.clearLayers()
  chargerStations.value.forEach((station, index) => {
    const coordinate = getChargerCoordinate(station)
    if (!coordinate) return
    const hasAvailable = Number(station?.available_ports) > 0
    const marker = L.marker(
      [coordinate.latitude, coordinate.longitude],
      { icon: getChargerIcon(hasAvailable, false) }
    )
      .addTo(chargerLayer)
      .bindPopup(buildChargerPopup(station))
      .on('click', () => setSelectedCharger(station))
    markerRefs.set(`chargers:${getChargerId(station, index)}`, marker)
  })
}
```

- [ ] **Step 5: Update `resetSelectedChargerMarker` and `setSelectedCharger`**

Update `resetSelectedChargerMarker` (lines 429-439) — replace `setStyle`/`setRadius` with `setIcon`:

```javascript
function resetSelectedChargerMarker() {
  if (!selectedChargerId.value) return
  const previousMarker = markerRefs.get(`chargers:${selectedChargerId.value}`)
  const previousStation = chargerStations.value.find(
    (station) => getChargerId(station) === selectedChargerId.value
  )
  if (previousMarker && previousStation) {
    const hasAvail = Number(previousStation?.available_ports) > 0
    previousMarker.setIcon(getChargerIcon(hasAvail, false))
    previousMarker.unbindTooltip()
  }
}
```

Update `setSelectedCharger` (lines 442-457) — replace `setStyle`/`setRadius` with `setIcon`:

```javascript
function setSelectedCharger(station) {
  resetSelectedChargerMarker()
  selectedChargerId.value = getChargerId(station)
  const marker = markerRefs.get(`chargers:${selectedChargerId.value}`)
  if (!marker) return
  const hasAvail = Number(station?.available_ports) > 0
  marker.setIcon(getChargerIcon(hasAvail, true))
  marker
    .bindTooltip(textOrUnknown(station.name), {
      permanent: true,
      direction: 'top',
      offset: [0, -10],
      className: 'charger-name-tooltip'
    })
    .openTooltip()
}
```

- [ ] **Step 6: Delete old popup builder functions**

Delete the three old functions entirely:
- `buildChargerPopup` (lines 343-351)
- `buildStudyRoomPopup` (lines 354-364)
- `buildPoiPopup` (lines 367-375)

These are now provided by `popupBuilders.js`.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/App.vue
git commit -m "refactor: wire divIcon markers and card popups into App.vue"
```

---

### Task 5: Update App.vue legend templates

**Files:**
- Modify: `frontend/src/App.vue` template section

- [ ] **Step 1: Replace sidebar legend grid**

Replace the sidebar legend block (`.legend-grid` div, around lines 806-823) with the full 10-category version:

```html
<div v-show="legendExpanded" class="legend-grid">
  <div class="legend-row">
    <span class="legend-dot" style="background:#3b82f6;border-color:#3b82f6;"></span>
    <span>自习室</span>
  </div>
  <div class="legend-row">
    <span class="legend-dot" style="background:#8b5cf6;border-color:#8b5cf6;"></span>
    <span>图书馆</span>
  </div>
  <div class="legend-row">
    <span class="legend-dot" style="background:#f59e0b;border-color:#f59e0b;"></span>
    <span>教学楼</span>
  </div>
  <div class="legend-row">
    <span class="legend-dot" style="background:#ef4444;border-color:#ef4444;"></span>
    <span>食堂</span>
  </div>
  <div class="legend-row">
    <span class="legend-dot" style="background:#10b981;border-color:#10b981;"></span>
    <span>景观</span>
  </div>
  <div class="legend-row">
    <span class="legend-dot" style="background:#6366f1;border-color:#6366f1;"></span>
    <span>服务设施</span>
  </div>
  <div class="legend-row">
    <span class="legend-dot" style="background:#ec4899;border-color:#ec4899;"></span>
    <span>博物馆</span>
  </div>
  <div class="legend-row">
    <span class="legend-dot" style="background:#6b7280;border-color:#6b7280;"></span>
    <span>其他</span>
  </div>
  <div class="legend-row">
    <span class="legend-dot" style="background:#22c55e;border-color:#22c55e;"></span>
    <span>有空闲充电桩</span>
  </div>
  <div class="legend-row">
    <span class="legend-dot" style="background:#ef4444;border-color:#ef4444;"></span>
    <span>无空闲充电桩</span>
  </div>
</div>
```

- [ ] **Step 2: Replace map overlay legend**

Replace the map overlay legend block (`.map-legend-overlay` div, lines 876-881) with the full version:

```html
<div class="map-legend-overlay">
  <span><span class="legend-dot" style="background:#3b82f6;border-color:#3b82f6;"></span> 自习室</span>
  <span><span class="legend-dot" style="background:#8b5cf6;border-color:#8b5cf6;"></span> 图书馆</span>
  <span><span class="legend-dot" style="background:#f59e0b;border-color:#f59e0b;"></span> 教学</span>
  <span><span class="legend-dot" style="background:#ef4444;border-color:#ef4444;"></span> 食堂</span>
  <span><span class="legend-dot" style="background:#10b981;border-color:#10b981;"></span> 景观</span>
  <span><span class="legend-dot" style="background:#6366f1;border-color:#6366f1;"></span> 服务</span>
  <span><span class="legend-dot" style="background:#ec4899;border-color:#ec4899;"></span> 博物馆</span>
  <span><span class="legend-dot" style="background:#6b7280;border-color:#6b7280;"></span> 其他</span>
  <span><span class="legend-dot" style="background:#22c55e;border-color:#22c55e;"></span> 空闲桩</span>
  <span><span class="legend-dot" style="background:#ef4444;border-color:#ef4444;"></span> 无空闲桩</span>
</div>
```

- [ ] **Step 3: Remove now-unused CSS classes**

Remove these CSS classes in `base.css` since we now use inline styles for legend dots:
- Lines 672-690: `.study-room-dot`, `.poi-dot`, `.charger-available-dot`, `.charger-full-dot`

Keep the `.legend-dot` base class (width/height/border-radius) since inline styles inherit it, and the old dot classes' `background`/`border` are overridden by inline styles anyway. Just delete the four specific color class definitions to avoid confusion.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.vue frontend/src/styles/base.css
git commit -m "feat: update legend to 10-category color scheme"
```

---

### Task 6: Verify — run dev server and check

- [ ] **Step 1: Start backend**

```bash
cd backend && python -m uvicorn main:app --host 127.0.0.1 --port 8000 &
```

- [ ] **Step 2: Start frontend dev server**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: Visual checks in browser**

Open `http://localhost:5173` and verify:
- [ ] Study room markers render as blue open-book pin icons
- [ ] POI markers render with category-specific colors and shapes
- [ ] Charger markers render with green (available) or red (unavailable) lightning icons
- [ ] Click a study room marker → popup shows dark blue header card, `attr-grid` layout
- [ ] Click a POI marker → popup shows category-colored header card
- [ ] Click a charger marker → popup shows green/red header card
- [ ] Click a charger list item → marker grows/glows, tooltip appears
- [ ] Switch to 3D → Cesium view still works (unchanged)
- [ ] Switch back to 2D → markers re-render correctly
- [ ] Sidebar legend shows 10 items with correct colors
- [ ] Map overlay legend shows 10 abbreviated items
- [ ] No console errors on page load

- [ ] **Step 4: Final commit if any fixups were needed**

```bash
git add -A
git commit -m "chore: final visual verification tweaks"
```
