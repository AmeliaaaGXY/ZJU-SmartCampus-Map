<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import L from 'leaflet'
import {
  getFeatureCoordinate,
  loadMapDatasets,
  textOrUnknown
} from './services/geojsonData'
import {
  getChargerStations,
  getChargerStatus,
  recommendStudyRoom
} from './services/api'

/* ── Refs ────────────────────────────────────────────── */

const mapContainer = ref(null)
const isLoading = ref(true)
const loadMessage = ref('')
const studyRooms = ref([])
const pois = ref([])
const activePanel = ref('study-rooms')
const searchQuery = ref('')
const aiQuery = ref('')
const aiIsLoading = ref(false)
const aiMessage = ref('')
const aiMode = ref('')
const aiRecommendations = ref([])
const chargerIsLoading = ref(true)
const chargerMessage = ref('')
const chargerStations = ref([])
const chargerFallbackUrl = ref('https://charger.philfan.cn/')
const chargerApiConfigured = ref(false)
const selectedChargerId = ref('')
const legendExpanded = ref(false)

/* ── Map state ───────────────────────────────────────── */

let map = null
let markerLayer = null
let chargerLayer = null
const markerRefs = new Map()

const campusCenter = [30.3046, 120.0869]
const EARTH_RADIUS = 6378245.0
const EE = 0.006693421622965943
const X_PI = (Math.PI * 3000.0) / 180.0

/* ── Computed ────────────────────────────────────────── */

const activeItems = computed(() => {
  if (activePanel.value === 'study-rooms') return studyRooms.value
  if (activePanel.value === 'pois') return pois.value
  if (activePanel.value === 'chargers') return chargerStations.value
  return []
})

const filteredActiveItems = computed(() => {
  let items = [...activeItems.value]
  const q = searchQuery.value.trim().toLowerCase()

  if (q) {
    items = items.filter((item) => {
      if (activePanel.value === 'chargers') {
        return String(item.name || '').toLowerCase().includes(q)
      }
      const name = (item.properties || {}).name || ''
      return String(name).toLowerCase().includes(q)
    })
  }

  if (activePanel.value === 'chargers') {
    items.sort((a, b) => (b.available_ports || 0) - (a.available_ports || 0))
  }

  return items
})

const activeEmptyText = computed(() => {
  if (activePanel.value === 'study-rooms') return '暂无自习室数据，等待数据组补充。'
  if (activePanel.value === 'pois') return '暂无校园 POI 数据，等待数据组补充。'
  if (activePanel.value === 'chargers') return '充电桩 API 暂不可用，可使用 ZJU-Charger 外链兜底。'
  return '暂无数据。'
})

/* ── Helpers ─────────────────────────────────────────── */

function switchPanel(panel) {
  activePanel.value = panel
  searchQuery.value = ''
}

function getFeatureId(feature, fallbackPrefix, index) {
  return feature?.properties?.id || `${fallbackPrefix}_${index}`
}

function getChargerId(station, index = 0) {
  return station?.id || `charger_${index}`
}

function getItemName(item) {
  if (activePanel.value === 'chargers') return item.name
  return (item.properties || {}).name
}

function getItemMeta(item) {
  if (activePanel.value === 'study-rooms') {
    const p = item.properties || {}
    return `${textOrUnknown(p.building)} · 可用座位 ${textOrUnknown(p.seat_available)}`
  }
  if (activePanel.value === 'pois') {
    const p = item.properties || {}
    return `${textOrUnknown(p.category)} · ${textOrUnknown(p.audience)}`
  }
  if (activePanel.value === 'chargers') {
    return `${textOrUnknown(item.provider)} · 空闲/总数 ${textOrUnknown(item.available_ports)}/${textOrUnknown(item.total_ports)}`
  }
  return ''
}

function getItemId(item, index) {
  if (activePanel.value === 'chargers') return getChargerId(item, index)
  return getFeatureId(item, activePanel.value, index)
}

function getItemCssClass() {
  if (activePanel.value === 'study-rooms') return 'study-room'
  if (activePanel.value === 'pois') return 'poi'
  if (activePanel.value === 'chargers') return 'charger'
  return ''
}

/* ── Coordinate transforms ───────────────────────────── */

function transformLat(longitudeOffset, latitudeOffset) {
  let result =
    -100.0 +
    2.0 * longitudeOffset +
    3.0 * latitudeOffset +
    0.2 * latitudeOffset * latitudeOffset +
    0.1 * longitudeOffset * latitudeOffset +
    0.2 * Math.sqrt(Math.abs(longitudeOffset))
  result +=
    ((20.0 * Math.sin(6.0 * longitudeOffset * Math.PI) +
      20.0 * Math.sin(2.0 * longitudeOffset * Math.PI)) *
      2.0) /
    3.0
  result +=
    ((20.0 * Math.sin(latitudeOffset * Math.PI) +
      40.0 * Math.sin((latitudeOffset / 3.0) * Math.PI)) *
      2.0) /
    3.0
  result +=
    ((160.0 * Math.sin((latitudeOffset / 12.0) * Math.PI) +
      320 * Math.sin((latitudeOffset * Math.PI) / 30.0)) *
      2.0) /
    3.0
  return result
}

function transformLon(longitudeOffset, latitudeOffset) {
  let result =
    300.0 +
    longitudeOffset +
    2.0 * latitudeOffset +
    0.1 * longitudeOffset * longitudeOffset +
    0.1 * longitudeOffset * latitudeOffset +
    0.1 * Math.sqrt(Math.abs(longitudeOffset))
  result +=
    ((20.0 * Math.sin(6.0 * longitudeOffset * Math.PI) +
      20.0 * Math.sin(2.0 * longitudeOffset * Math.PI)) *
      2.0) /
    3.0
  result +=
    ((20.0 * Math.sin(longitudeOffset * Math.PI) +
      40.0 * Math.sin((longitudeOffset / 3.0) * Math.PI)) *
      2.0) /
    3.0
  result +=
    ((150.0 * Math.sin((longitudeOffset / 12.0) * Math.PI) +
      300.0 * Math.sin((longitudeOffset / 30.0) * Math.PI)) *
      2.0) /
    3.0
  return result
}

function gcj02ToWgs84(latitude, longitude) {
  const dLat = transformLat(longitude - 105.0, latitude - 35.0)
  const dLon = transformLon(longitude - 105.0, latitude - 35.0)
  const radLat = (latitude / 180.0) * Math.PI
  let magic = Math.sin(radLat)
  magic = 1 - EE * magic * magic
  const sqrtMagic = Math.sqrt(magic)
  const adjustedLat =
    (dLat * 180.0) / (((EARTH_RADIUS * (1 - EE)) / (magic * sqrtMagic)) * Math.PI)
  const adjustedLon =
    (dLon * 180.0) / ((EARTH_RADIUS / sqrtMagic) * Math.cos(radLat) * Math.PI)
  return {
    latitude: latitude * 2 - (latitude + adjustedLat),
    longitude: longitude * 2 - (longitude + adjustedLon)
  }
}

function bd09ToGcj02(latitude, longitude) {
  const x = longitude - 0.0065
  const y = latitude - 0.006
  const z = Math.sqrt(x * x + y * y) - 0.00002 * Math.sin(y * X_PI)
  const theta = Math.atan2(y, x) - 0.000003 * Math.cos(x * X_PI)
  return {
    latitude: z * Math.sin(theta),
    longitude: z * Math.cos(theta)
  }
}

function bd09ToWgs84(coordinate) {
  const gcjCoordinate = bd09ToGcj02(coordinate.latitude, coordinate.longitude)
  return gcj02ToWgs84(gcjCoordinate.latitude, gcjCoordinate.longitude)
}

function getChargerCoordinate(station) {
  const latitude = Number(station?.latitude)
  const longitude = Number(station?.longitude)
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null
  return bd09ToWgs84({ latitude, longitude })
}

/* ── Popup builders ──────────────────────────────────── */

function buildChargerPopup(station) {
  return `
    <strong>${textOrUnknown(station.name)}</strong>
    <div>服务商：${textOrUnknown(station.provider)}</div>
    <div>校区：${textOrUnknown(station.campus_name || station.campus)}</div>
    <div>空闲 / 已用 / 总数：${textOrUnknown(station.available_ports)} / ${textOrUnknown(station.used_ports)} / ${textOrUnknown(station.total_ports)}</div>
    <div>故障数：${textOrUnknown(station.error_ports)}</div>
    <div>更新时间：${textOrUnknown(station.updated_at)}</div>
  `
}

function buildStudyRoomPopup(feature) {
  const properties = feature.properties || {}
  return `
    <strong>${textOrUnknown(properties.name)}</strong>
    <div>建筑：${textOrUnknown(properties.building)}</div>
    <div>楼层 / 房间：${textOrUnknown(properties.floor)} ${textOrUnknown(properties.room)}</div>
    <div>开放时间：${textOrUnknown(properties.open_time)} - ${textOrUnknown(properties.close_time)}</div>
    <div>可用座位：${textOrUnknown(properties.seat_available)} / ${textOrUnknown(properties.seat_total)}</div>
    <div>是否有插座：${textOrUnknown(properties.has_power)}</div>
    <div>说明：${textOrUnknown(properties.description)}</div>
  `
}

function buildPoiPopup(feature) {
  const properties = feature.properties || {}
  return `
    <strong>${textOrUnknown(properties.name)}</strong>
    <div>类别：${textOrUnknown(properties.category)}</div>
    <div>适用人群：${textOrUnknown(properties.audience)}</div>
    <div>开放时间：${textOrUnknown(properties.open_time)}</div>
    <div>说明：${textOrUnknown(properties.description)}</div>
  `
}

/* ── Marker rendering ────────────────────────────────── */

function getChargerMarkerStyle(station, isSelected = false) {
  const hasAvailablePorts = Number(station?.available_ports) > 0
  return {
    radius: isSelected ? 12 : 8,
    color: isSelected ? '#0f172a' : hasAvailablePorts ? '#047857' : '#b91c1c',
    weight: isSelected ? 4 : 2,
    fillColor: hasAvailablePorts ? '#22c55e' : '#ef4444',
    fillOpacity: isSelected ? 0.95 : 0.86
  }
}

function addPointMarkers(features, options) {
  features.forEach((feature, index) => {
    const coordinate = getFeatureCoordinate(feature)
    if (!coordinate) return
    const marker = L.circleMarker([coordinate.latitude, coordinate.longitude], {
      radius: 8,
      color: options.color,
      weight: 2,
      fillColor: options.fillColor,
      fillOpacity: 0.85
    })
      .addTo(markerLayer)
      .bindPopup(options.popupBuilder(feature))
    markerRefs.set(options.markerKey(feature, index), marker)
  })
}

function renderMarkers() {
  markerLayer.clearLayers()
  markerRefs.clear()

  addPointMarkers(studyRooms.value, {
    color: '#1d4ed8',
    fillColor: '#3b82f6',
    popupBuilder: buildStudyRoomPopup,
    markerKey: (feature, index) => `study-rooms:${getFeatureId(feature, 'study_room', index)}`
  })

  addPointMarkers(pois.value, {
    color: '#047857',
    fillColor: '#10b981',
    popupBuilder: buildPoiPopup,
    markerKey: (feature, index) => `pois:${getFeatureId(feature, 'poi', index)}`
  })
}

/* ── Charger marker interactions ─────────────────────── */

function resetSelectedChargerMarker() {
  if (!selectedChargerId.value) return
  const previousMarker = markerRefs.get(`chargers:${selectedChargerId.value}`)
  const previousStation = chargerStations.value.find(
    (station) => getChargerId(station) === selectedChargerId.value
  )
  if (previousMarker && previousStation) {
    previousMarker.setStyle(getChargerMarkerStyle(previousStation))
    previousMarker.setRadius(8)
    previousMarker.unbindTooltip()
  }
}

function setSelectedCharger(station) {
  resetSelectedChargerMarker()
  selectedChargerId.value = getChargerId(station)
  const marker = markerRefs.get(`chargers:${selectedChargerId.value}`)
  if (!marker) return
  marker.setStyle(getChargerMarkerStyle(station, true))
  marker.setRadius(12)
  marker
    .bindTooltip(textOrUnknown(station.name), {
      permanent: true,
      direction: 'top',
      offset: [0, -10],
      className: 'charger-name-tooltip'
    })
    .openTooltip()
}

function renderChargerMarkers() {
  if (!chargerLayer) return
  chargerLayer.clearLayers()
  chargerStations.value.forEach((station, index) => {
    const coordinate = getChargerCoordinate(station)
    if (!coordinate) return
    const marker = L.circleMarker(
      [coordinate.latitude, coordinate.longitude],
      getChargerMarkerStyle(station)
    )
      .addTo(chargerLayer)
      .bindPopup(buildChargerPopup(station))
      .on('click', () => setSelectedCharger(station))
    markerRefs.set(`chargers:${getChargerId(station, index)}`, marker)
  })
}

/* ── Focus / navigation ──────────────────────────────── */

function focusChargerStation(station) {
  const coordinate = getChargerCoordinate(station)
  if (!coordinate || !map) return
  setSelectedCharger(station)
  map.flyTo([coordinate.latitude, coordinate.longitude], 17, { duration: 0.6 })
  const marker = markerRefs.get(`chargers:${getChargerId(station)}`)
  if (marker) marker.openPopup()
}

function focusFeature(item, index) {
  if (activePanel.value === 'chargers') {
    focusChargerStation(item)
    return
  }

  const coordinate = getFeatureCoordinate(item)
  if (!coordinate || !map) return

  const markerKey = `${activePanel.value}:${getFeatureId(item, activePanel.value, index)}`
  const marker = markerRefs.get(markerKey)

  map.flyTo([coordinate.latitude, coordinate.longitude], 17, { duration: 0.6 })
  if (marker) marker.openPopup()
}

function findStudyRoomByRecommendation(recommendation) {
  const id = recommendation.study_room_id
  const name = recommendation.name
  const index = studyRooms.value.findIndex((feature) => {
    const properties = feature.properties || {}
    return (id && properties.id === id) || (name && properties.name === name)
  })
  if (index < 0) return { feature: null, index: -1 }
  return { feature: studyRooms.value[index], index }
}

function focusStudyRoomRecommendation(recommendation) {
  const { feature, index } = findStudyRoomByRecommendation(recommendation)
  if (!feature) return
  activePanel.value = 'study-rooms'
  searchQuery.value = ''
  focusFeature(feature, index)
}

function hasMatchedFeature(recommendation) {
  return Boolean(findStudyRoomByRecommendation(recommendation).feature)
}

/* ── AI recommendation ───────────────────────────────── */

async function submitAiRecommendation() {
  const query = aiQuery.value.trim()
  aiMessage.value = ''
  aiMode.value = ''
  aiRecommendations.value = []

  if (!query) {
    aiMessage.value = '请先输入你的学习需求。'
    return
  }

  aiIsLoading.value = true
  try {
    const response = await recommendStudyRoom(query)
    aiMessage.value = response.data?.message || '已生成自习室推荐。'
    aiMode.value = response.data?.mode || ''
    aiRecommendations.value = Array.isArray(response.data?.recommendations)
      ? response.data.recommendations
      : []
  } catch (error) {
    aiMessage.value = 'AI 推荐接口暂不可用，请稍后再试。页面仍可正常查看地图点位。'
    aiRecommendations.value = []
  } finally {
    aiIsLoading.value = false
  }
}

/* ── Data loading ────────────────────────────────────── */

async function loadData() {
  isLoading.value = true
  const datasets = await loadMapDatasets()
  studyRooms.value = datasets.studyRooms.data.features
  pois.value = datasets.pois.data.features
  const errors = [datasets.studyRooms.error, datasets.pois.error].filter(Boolean)
  loadMessage.value = errors.length ? errors[0] : ''
  renderMarkers()
  isLoading.value = false
}

async function loadChargers() {
  chargerIsLoading.value = true
  chargerStations.value = []
  selectedChargerId.value = ''

  try {
    const statusResponse = await getChargerStatus()
    chargerApiConfigured.value = Boolean(statusResponse.data?.api_configured)
    chargerFallbackUrl.value =
      statusResponse.data?.fallback_url || 'https://charger.philfan.cn/'

    const stationsResponse = await getChargerStations()
    chargerMessage.value =
      stationsResponse.data?.message || statusResponse.data?.message || ''
    chargerFallbackUrl.value =
      stationsResponse.data?.fallback_url || chargerFallbackUrl.value
    chargerStations.value = Array.isArray(stationsResponse.data?.stations)
      ? stationsResponse.data.stations
      : []
    renderChargerMarkers()
  } catch (error) {
    chargerMessage.value = '充电桩 API 暂不可用，当前显示兜底入口。'
    chargerStations.value = []
    renderChargerMarkers()
  } finally {
    chargerIsLoading.value = false
  }
}

/* ── Lifecycle ───────────────────────────────────────── */

onMounted(async () => {
  map = L.map(mapContainer.value, {
    center: campusCenter,
    zoom: 16,
    zoomControl: true
  })

  markerLayer = L.layerGroup().addTo(map)
  chargerLayer = L.layerGroup().addTo(map)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map)

  await loadData()
  await loadChargers()
})

onBeforeUnmount(() => {
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<template>
  <main class="app-shell">
    <!-- ═══════════════ SIDE PANEL ═══════════════ -->
    <aside class="side-panel">
      <!-- Hero -->
      <header class="panel-hero">
        <h1>紫金港 WebGIS 信息平台</h1>
        <div class="status-strip" aria-label="项目状态摘要">
          <span>{{ studyRooms.length }} 个自习室</span>
          <span>{{ pois.length }} 个 POI</span>
          <span>{{ chargerStations.length }} 个充电桩</span>
        </div>
      </header>

      <!-- Unified Panel -->
      <section class="panel-section unified-panel" aria-label="点位信息面板">
        <!-- Tabs -->
        <div class="tab-row" role="tablist" aria-label="点位类型切换">
          <button
            class="tab-button"
            :class="{ active: activePanel === 'study-rooms' }"
            type="button"
            @click="switchPanel('study-rooms')"
          >
            自习室
          </button>
          <button
            class="tab-button"
            :class="{ active: activePanel === 'pois' }"
            type="button"
            @click="switchPanel('pois')"
          >
            校园 POI
          </button>
          <button
            class="tab-button"
            :class="{ active: activePanel === 'chargers' }"
            type="button"
            @click="switchPanel('chargers')"
          >
            充电桩
          </button>
        </div>

        <!-- Search (not for chargers tab) -->
        <input
          v-if="activePanel !== 'chargers'"
          v-model="searchQuery"
          class="search-input"
          :placeholder="activePanel === 'study-rooms' ? '搜索自习室名称...' : '搜索 POI 名称...'"
        >

        <!-- AI area (study rooms only) -->
        <div v-if="activePanel === 'study-rooms'" class="ai-area">
          <p class="eyebrow compact">AI Study Room</p>
          <p class="ai-intro">
            输入学习需求，后端会结合当前自习室数据推荐合适地点。
          </p>
          <form class="ai-form" @submit.prevent="submitAiRecommendation">
            <label class="sr-only" for="ai-query">学习需求</label>
            <textarea
              id="ai-query"
              v-model="aiQuery"
              rows="4"
              placeholder="例如：想找安静、有插座、晚上开放、离东区近的自习室"
            ></textarea>
            <button class="primary-button" type="submit" :disabled="aiIsLoading">
              {{ aiIsLoading ? '正在推荐...' : '推荐自习室' }}
            </button>
          </form>

          <p
            v-if="aiMessage"
            class="note ai-message"
            :class="{ warning: aiMode === 'empty' || aiMode === 'invalid' }"
          >
            {{ aiMessage }}
          </p>

          <div v-if="aiRecommendations.length" class="recommendation-list">
            <article
              v-for="(item, index) in aiRecommendations"
              :key="`${item.study_room_id || item.name || 'recommendation'}_${index}`"
              class="recommendation-card"
            >
              <div class="rec-head">
                <h3>{{ textOrUnknown(item.name) }}</h3>
                <span class="count-badge">{{ index + 1 }}</span>
              </div>
              <p>{{ textOrUnknown(item.reason) }}</p>
              <p class="place-meta">匹配需求：{{ textOrUnknown(item.matched_needs) }}</p>
              <p class="place-meta">注意事项：{{ textOrUnknown(item.notes) }}</p>
              <button
                v-if="hasMatchedFeature(item)"
                class="secondary-button"
                type="button"
                @click="focusStudyRoomRecommendation(item)"
              >
                在地图上查看
              </button>
              <p v-else class="place-meta">
                该推荐暂未匹配到地图点位，仅展示文字结果。
              </p>
            </article>
          </div>
        </div>

        <!-- Charger info (chargers tab only) -->
        <div v-if="activePanel === 'chargers'" class="charger-info">
          <p v-if="chargerIsLoading" class="note">正在请求 ZJU-Charger API...</p>
          <p
            v-else
            class="note"
            :class="{ warning: chargerStations.length === 0 }"
          >
            {{ chargerMessage || '已加载紫金港校区充电桩数据。' }}
          </p>
          <a
            class="external-link"
            :href="chargerFallbackUrl"
            target="_blank"
            rel="noreferrer"
          >
            打开 ZJU-Charger
          </a>
        </div>

        <!-- Unified list -->
        <p
          v-if="filteredActiveItems.length === 0 && !(activePanel === 'chargers' && chargerIsLoading)"
          class="empty-state"
        >
          {{ searchQuery ? '未找到匹配项。' : activeEmptyText }}
        </p>
        <div v-else-if="filteredActiveItems.length" class="scrollable-list">
          <div class="place-list">
            <button
              v-for="(item, index) in filteredActiveItems"
              :key="getItemId(item, index)"
              class="place-item"
              :class="getItemCssClass()"
              type="button"
              @click="focusFeature(item, index)"
            >
              <span class="place-name">{{ textOrUnknown(getItemName(item)) }}</span>
              <span class="place-meta">{{ getItemMeta(item) }}</span>
            </button>
          </div>
        </div>
      </section>

      <!-- Legend (compact, collapsible) -->
      <section class="panel-section legend-compact">
        <button
          class="legend-toggle"
          @click="legendExpanded = !legendExpanded"
          aria-expanded="false"
        >
          图例 {{ legendExpanded ? '▲' : '▼' }}
        </button>
        <div v-show="legendExpanded" class="legend-grid">
          <div class="legend-row">
            <span class="legend-dot study-room-dot"></span>
            <span>自习室</span>
          </div>
          <div class="legend-row">
            <span class="legend-dot poi-dot"></span>
            <span>校园 POI</span>
          </div>
          <div class="legend-row">
            <span class="legend-dot charger-available-dot"></span>
            <span>有空闲充电桩</span>
          </div>
          <div class="legend-row">
            <span class="legend-dot charger-full-dot"></span>
            <span>无空闲充电桩</span>
          </div>
        </div>
      </section>
    </aside>

    <!-- ═══════════════ MAP AREA ═══════════════ -->
    <section class="map-area" aria-label="紫金港校区二维地图">
      <div class="map-toolbar">
        <div>
          <p class="toolbar-label">当前视图</p>
          <strong>浙江大学紫金港校区</strong>
        </div>
        <span>Leaflet 二维地图</span>
      </div>
      <div ref="mapContainer" class="leaflet-map"></div>

      <!-- Map legend overlay (always visible) -->
      <div class="map-legend-overlay">
        <span><span class="legend-dot study-room-dot"></span> 自习室</span>
        <span><span class="legend-dot poi-dot"></span> POI</span>
        <span><span class="legend-dot charger-available-dot"></span> 有空闲</span>
        <span><span class="legend-dot charger-full-dot"></span> 无空闲</span>
      </div>
    </section>
  </main>
</template>
