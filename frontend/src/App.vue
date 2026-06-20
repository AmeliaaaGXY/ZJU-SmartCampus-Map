<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import 'leaflet.markercluster'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'
import CesiumView from './components/CesiumView.vue'
import {
  getFeatureCoordinate,
  loadMapDatasets,
  normalizeFeatureCollection,
  textOrUnknown,
  bd09ToWgs84
} from './services/geojsonData'
import { getStudyRoomIcon, getPoiIcon, getChargerIcon } from './services/markerIcons'
import { buildStudyRoomPopup, buildPoiPopup, buildChargerPopup } from './services/popupBuilders'
import {
  getChargerStations,
  getChargerStatus,
  recommendStudyRoom
} from './services/api'
import {
  checkGeoServerStatus,
  fetchWfsFeatures,
  getWmsBaseUrl,
  getWmsLayerOptions
} from './services/geoServerService'

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
const viewMode = ref('2d') // '2d' | '3d'
const activeLayer = ref('all') // 'all' | 'study-rooms' | 'pois' | 'chargers'

function switchTo2D() {
  viewMode.value = '2d'
}

function switchTo3D() {
  // 切换到 3D 前，先主动销毁 2D 地图实例
  if (map) {
    map.remove()
    map = null
    studyClusterGroup = null
    poiClusterGroup = null
    chargerLayer = null
    markerRefs.clear()
    wmsLayer = null
  }
  viewMode.value = '3d'
}

/* ── GeoServer state ─────────────────────────────────── */

const geoServerEnabled = ref(false)
const geoServerReachable = ref(false)
const geoServerMessage = ref('')
const geoServerPois = ref([])
const geoServerLayerReady = ref(false)

async function toggleGeoServer() {
  geoServerEnabled.value = !geoServerEnabled.value

  if (!geoServerEnabled.value) {
    removeWmsLayer()
    geoServerPois.value = []
    geoServerMessage.value = ''
    geoServerLayerReady.value = false
    return
  }

  geoServerMessage.value = '正在连接 GeoServer...'
  const status = await checkGeoServerStatus()
  geoServerReachable.value = status.reachable

  if (!status.reachable) {
    geoServerMessage.value = 'GeoServer 图层暂不可用，当前使用本地数据展示。'
    geoServerLayerReady.value = false
    return
  }

  addWmsLayer()
  geoServerLayerReady.value = true

  const wfsResult = await fetchWfsFeatures()
  if (wfsResult.ok && wfsResult.data.features?.length) {
    geoServerPois.value = wfsResult.data.features
    geoServerMessage.value = `已通过 GeoServer 加载 ${wfsResult.data.features.length} 个 POI`
  } else {
    geoServerMessage.value = wfsResult.message || 'GeoServer WFS 暂不可用，WMS 叠加层已加载。'
  }
}

/* ── GeoServer WMS layer ──────────────────────────────── */

let wmsLayer = null

function addWmsLayer() {
  if (!map || wmsLayer) return
  const url = getWmsBaseUrl()
  if (!url) return
  wmsLayer = L.tileLayer
    .wms(url, {
      ...getWmsLayerOptions(),
      styles: '',
      zIndex: 5
    })
    .addTo(map)
    .bringToBack()
}

function removeWmsLayer() {
  if (wmsLayer && map) {
    map.removeLayer(wmsLayer)
    wmsLayer = null
  }
}

/* ── Computed: pois list uses GeoServer data when available ── */

const displayPois = computed(() => {
  if (geoServerEnabled.value && geoServerPois.value.length) {
    return geoServerPois.value
  }
  return pois.value
})

/* ── Watch: re-render markers when GeoServer POI data changes ── */

watch([geoServerEnabled, geoServerPois], () => {
  if (map && markerLayer) {
    renderMarkers()
  }
})

/* ── Map state ───────────────────────────────────────── */

let map = null
let studyClusterGroup = null
let poiClusterGroup = null
let chargerLayer = null
const markerRefs = new Map()

const campusCenter = [30.3046, 120.0869]

/* ── Computed ────────────────────────────────────────── */

const activeItems = computed(() => {
  if (activePanel.value === 'study-rooms') return studyRooms.value
  if (activePanel.value === 'pois') return displayPois.value
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
  if (activePanel.value === 'pois') {
    if (geoServerEnabled.value && !geoServerReachable.value) {
      return 'GeoServer 图层暂不可用，当前使用本地数据或空数据展示。'
    }
    return '暂无校园 POI 数据，等待数据组补充。'
  }
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

function getChargerCoordinate(station) {
  const latitude = Number(station?.latitude)
  const longitude = Number(station?.longitude)
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null
  return bd09ToWgs84({ latitude, longitude })
}

/* ── Marker rendering ────────────────────────────────── */

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
  // Rebuild study room cluster
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

  // Rebuild POI cluster
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

  if (layer === 'all' || layer === 'study-rooms') {
    if (studyClusterGroup && !map.hasLayer(studyClusterGroup)) map.addLayer(studyClusterGroup)
  } else {
    if (studyClusterGroup && map.hasLayer(studyClusterGroup)) map.removeLayer(studyClusterGroup)
  }

  if (layer === 'all' || layer === 'pois') {
    if (poiClusterGroup && !map.hasLayer(poiClusterGroup)) map.addLayer(poiClusterGroup)
  } else {
    if (poiClusterGroup && map.hasLayer(poiClusterGroup)) map.removeLayer(poiClusterGroup)
  }

  if (layer === 'all' || layer === 'chargers') {
    if (chargerLayer && !map.hasLayer(chargerLayer)) map.addLayer(chargerLayer)
  } else {
    if (chargerLayer && map.hasLayer(chargerLayer)) map.removeLayer(chargerLayer)
  }
}

/* ── Charger marker interactions ─────────────────────── */

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

/* ── Focus / navigation ──────────────────────────────── */

const cesiumViewRef = ref(null)

function ensureLayerVisible(layer) {
  if (activeLayer.value !== 'all' && activeLayer.value !== layer) {
    activeLayer.value = layer
  }
}

function zoomToShowAndOpenPopup(marker, clusterGroup, latlng) {
  // If the marker is clustered, zoom to show it individually first
  if (clusterGroup) {
    clusterGroup.zoomToShowLayer(marker, function () {
      marker.openPopup()
    })
  } else {
    marker.openPopup()
  }
}

function focusChargerStation(station) {
  if (viewMode.value === '3d') {
    const stationId = getChargerId(station)
    ensureLayerVisible('chargers')
    if (cesiumViewRef.value) {
      cesiumViewRef.value.focus3DEntity(`chargers:${stationId}`)
    }
    return
  }

  const coordinate = getChargerCoordinate(station)
  if (!coordinate || !map) return
  ensureLayerVisible('chargers')
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

  // 3D mode: delegate to CesiumView
  if (viewMode.value === '3d') {
    const featureId = getFeatureId(item, activePanel.value, index)
    const layer = activePanel.value === 'study-rooms' ? 'study-rooms' : 'pois'
    ensureLayerVisible(layer)
    if (cesiumViewRef.value) {
      cesiumViewRef.value.focus3DEntity(`${layer}:${featureId}`)
    }
    return
  }

  // 2D mode
  const coordinate = getFeatureCoordinate(item)
  if (!coordinate || !map) return

  const layer = activePanel.value === 'study-rooms' ? 'study-rooms' : 'pois'
  ensureLayerVisible(layer)

  const markerKey = `${layer}:${getFeatureId(item, layer, index)}`
  const marker = markerRefs.get(markerKey)
  const clusterGroup = layer === 'study-rooms' ? studyClusterGroup : poiClusterGroup

  map.flyTo([coordinate.latitude, coordinate.longitude], 17, { duration: 0.6 })
  if (marker) {
    zoomToShowAndOpenPopup(marker, clusterGroup, [coordinate.latitude, coordinate.longitude])
  }
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

async function init2DMap() {
  if (!mapContainer.value) return

  map = L.map(mapContainer.value, {
    center: campusCenter,
    zoom: 16,
    zoomControl: true
  })

  studyClusterGroup = createClusterGroup()
  poiClusterGroup = createClusterGroup()
  chargerLayer = L.layerGroup()

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map)

  // Load campus boundary overlay
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

  await loadData()
  await loadChargers()

  // Re-add WMS layer if GeoServer was enabled
  if (geoServerEnabled.value && geoServerReachable.value) {
    addWmsLayer()
  }
}

onMounted(async () => {
  await init2DMap()
})

// Apply layer visibility when activeLayer changes
watch(activeLayer, () => {
  applyLayerVisibility()
})

// Re-initialize 2D map when switching back from 3D
watch(viewMode, async (mode) => {
  if (mode === '2d' && !map) {
    // Wait for DOM update
    await new Promise((resolve) => requestAnimationFrame(resolve))
    await init2DMap()
  }
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
          <span>{{ displayPois.length }} 个 POI</span>
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
          :aria-expanded="legendExpanded"
        >
          图例 {{ legendExpanded ? '▲' : '▼' }}
        </button>
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
      </section>

      <!-- GeoServer toggle -->
      <section class="panel-section geoserver-section">
        <div class="geoserver-toggle-row">
          <label class="toggle-label">
            <input
              type="checkbox"
              :checked="geoServerEnabled"
              @change="toggleGeoServer"
            />
            <span>GeoServer 图层</span>
          </label>
          <span v-if="geoServerEnabled && geoServerReachable" class="geoserver-badge on">已连接</span>
          <span v-else-if="geoServerEnabled && !geoServerReachable" class="geoserver-badge off">不可用</span>
        </div>
        <p v-if="geoServerMessage" class="note geoserver-note" :class="{ warning: !geoServerReachable }">
          {{ geoServerMessage }}
        </p>
      </section>
    </aside>

    <!-- ═══════════════ MAP AREA ═══════════════ -->
    <section class="map-area" aria-label="紫金港校区地图">
      <!-- 2D Map View -->
      <template v-if="viewMode === '2d'">
        <div class="map-toolbar">
          <div>
            <p class="toolbar-label">当前视图</p>
            <strong>浙江大学紫金港校区</strong>
          </div>
          <div class="view-mode-toggle">
            <button
              class="view-mode-btn active"
              type="button"
              aria-label="二维地图视图（当前）"
            >
              2D
            </button>
            <button
              class="view-mode-btn"
              type="button"
              @click="switchTo3D"
              aria-label="切换到三维视图"
            >
              🌍 3D
            </button>
          </div>
          <div class="layer-toggle">
            <button class="layer-btn" :class="{ active: activeLayer === 'all' }" type="button" @click="activeLayer = 'all'">全部</button>
            <button class="layer-btn" :class="{ active: activeLayer === 'study-rooms' }" type="button" @click="activeLayer = 'study-rooms'">自习室</button>
            <button class="layer-btn" :class="{ active: activeLayer === 'pois' }" type="button" @click="activeLayer = 'pois'">POI</button>
            <button class="layer-btn" :class="{ active: activeLayer === 'chargers' }" type="button" @click="activeLayer = 'chargers'">充电桩</button>
          </div>
        </div>
        <div ref="mapContainer" class="leaflet-map"></div>

        <!-- Map legend overlay (always visible) -->
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
      </template>

      <!-- 3D Cesium View -->
      <CesiumView v-else ref="cesiumViewRef" @back="switchTo2D" :active-layer="activeLayer" @update:active-layer="activeLayer = $event" />
    </section>
  </main>
</template>
