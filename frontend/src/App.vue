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

const mapContainer = ref(null)
const isLoading = ref(true)
const loadMessage = ref('')
const studyRooms = ref([])
const pois = ref([])
const activePanel = ref('study-rooms')
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

let map = null
let markerLayer = null
let chargerLayer = null
const markerRefs = new Map()

const campusCenter = [30.3046, 120.0869]
const EARTH_RADIUS = 6378245.0
const EE = 0.006693421622965943
const X_PI = (Math.PI * 3000.0) / 180.0

const modules = computed(() => [
  {
    key: 'study-rooms',
    title: '自习室',
    description: '展示紫金港校区自习室点位，后续接入 AI 推荐。',
    count: studyRooms.value.length,
    emptyText: '暂无自习室数据，等待数据组补充。'
  },
  {
    key: 'pois',
    title: '校园 POI',
    description: '展示图书馆、教学楼、食堂、服务设施等校园点位。',
    count: pois.value.length,
    emptyText: '暂无校园 POI 数据，等待数据组补充。'
  },
  {
    key: 'chargers',
    title: '充电桩',
    description: '优先通过本项目后端代理 ZJU-Charger API，失败时提供外链兜底。',
    count: chargerStations.value.length,
    emptyText: '充电桩 API 暂无可展示站点，将使用 ZJU-Charger 外链兜底。'
  }
])

const hasBusinessData = computed(() => studyRooms.value.length + pois.value.length > 0)

const topAvailableChargerStations = computed(() =>
  chargerStations.value
    .filter((station) => station.available_ports > 0 && getChargerCoordinate(station))
    .sort((a, b) => b.available_ports - a.available_ports)
    .slice(0, 5)
)

const activeItems = computed(() => {
  if (activePanel.value === 'study-rooms') {
    return studyRooms.value
  }

  if (activePanel.value === 'pois') {
    return pois.value
  }

  return []
})

const activeEmptyText = computed(() => {
  if (activePanel.value === 'study-rooms') {
    return '暂无自习室数据，等待数据组补充。'
  }

  if (activePanel.value === 'pois') {
    return '暂无校园 POI 数据，等待数据组补充。'
  }

  return '暂无数据，等待数据组补充。'
})

const activePanelTitle = computed(() =>
  activePanel.value === 'study-rooms' ? '自习室列表' : '校园 POI 列表'
)

function getFeatureId(feature, fallbackPrefix, index) {
  return feature?.properties?.id || `${fallbackPrefix}_${index}`
}

function getChargerId(station, index = 0) {
  return station?.id || `charger_${index}`
}

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

  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
    return null
  }

  return bd09ToWgs84({ latitude, longitude })
}

function buildChargerPopup(station) {
  return `
    <strong>${textOrUnknown(station.name)}</strong>
    <div>服务商：${textOrUnknown(station.provider)}</div>
    <div>校区：${textOrUnknown(station.campus_name || station.campus)}</div>
    <div>空闲/已用/总数：${textOrUnknown(station.available_ports)} / ${textOrUnknown(station.used_ports)} / ${textOrUnknown(station.total_ports)}</div>
    <div>故障数：${textOrUnknown(station.error_ports)}</div>
    <div>更新时间：${textOrUnknown(station.updated_at)}</div>
  `
}

function getChargerMarkerStyle(station, isSelected = false) {
  const hasAvailablePorts = Number(station?.available_ports) > 0

  return {
    radius: isSelected ? 12 : 8,
    color: isSelected ? '#111827' : hasAvailablePorts ? '#15803d' : '#b91c1c',
    weight: isSelected ? 4 : 2,
    fillColor: hasAvailablePorts ? '#22c55e' : '#ef4444',
    fillOpacity: isSelected ? 0.95 : 0.86
  }
}

function buildStudyRoomPopup(feature) {
  const properties = feature.properties || {}

  return `
    <strong>${textOrUnknown(properties.name)}</strong>
    <div>建筑：${textOrUnknown(properties.building)}</div>
    <div>楼层/房间：${textOrUnknown(properties.floor)} ${textOrUnknown(properties.room)}</div>
    <div>开放时间：${textOrUnknown(properties.open_time)} - ${textOrUnknown(properties.close_time)}</div>
    <div>可用座位：${textOrUnknown(properties.seat_available)} / ${textOrUnknown(properties.seat_total)}</div>
    <div>电源：${textOrUnknown(properties.has_power)}</div>
    <div>说明：${textOrUnknown(properties.description)}</div>
  `
}

function buildPoiPopup(feature) {
  const properties = feature.properties || {}

  return `
    <strong>${textOrUnknown(properties.name)}</strong>
    <div>类型：${textOrUnknown(properties.category)}</div>
    <div>适用人群：${textOrUnknown(properties.audience)}</div>
    <div>开放时间：${textOrUnknown(properties.open_time)}</div>
    <div>说明：${textOrUnknown(properties.description)}</div>
  `
}

function addPointMarkers(features, options) {
  features.forEach((feature, index) => {
    const coordinate = getFeatureCoordinate(feature)
    if (!coordinate) {
      return
    }

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

function resetSelectedChargerMarker() {
  if (!selectedChargerId.value) {
    return
  }

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
  if (!marker) {
    return
  }

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
  if (!chargerLayer) {
    return
  }

  chargerLayer.clearLayers()

  chargerStations.value.forEach((station, index) => {
    const coordinate = getChargerCoordinate(station)
    if (!coordinate) {
      return
    }

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

function focusChargerStation(station) {
  const coordinate = getChargerCoordinate(station)
  if (!coordinate || !map) {
    return
  }

  setSelectedCharger(station)
  map.flyTo([coordinate.latitude, coordinate.longitude], 17, {
    duration: 0.6
  })

  const marker = markerRefs.get(`chargers:${getChargerId(station)}`)
  if (marker) {
    marker.openPopup()
  }
}

function focusFeature(feature, index) {
  const coordinate = getFeatureCoordinate(feature)
  if (!coordinate || !map) {
    return
  }

  const markerKey = `${activePanel.value}:${getFeatureId(feature, activePanel.value, index)}`
  const marker = markerRefs.get(markerKey)

  map.flyTo([coordinate.latitude, coordinate.longitude], 17, {
    duration: 0.6
  })

  if (marker) {
    marker.openPopup()
  }
}

function findStudyRoomByRecommendation(recommendation) {
  const id = recommendation.study_room_id
  const name = recommendation.name

  const index = studyRooms.value.findIndex((feature) => {
    const properties = feature.properties || {}
    return (id && properties.id === id) || (name && properties.name === name)
  })

  if (index < 0) {
    return { feature: null, index: -1 }
  }

  return { feature: studyRooms.value[index], index }
}

function focusStudyRoomRecommendation(recommendation) {
  const { feature, index } = findStudyRoomByRecommendation(recommendation)
  if (!feature) {
    return
  }

  activePanel.value = 'study-rooms'
  focusFeature(feature, index)
}

function hasMatchedFeature(recommendation) {
  return Boolean(findStudyRoomByRecommendation(recommendation).feature)
}

async function submitAiRecommendation() {
  const query = aiQuery.value.trim()
  aiMessage.value = ''
  aiMode.value = ''
  aiRecommendations.value = []

  if (!query) {
    aiMessage.value = '请输入你的学习需求。'
    return
  }

  aiIsLoading.value = true
  try {
    const response = await recommendStudyRoom(query)
    aiMessage.value = response.data?.message || '已完成推荐。'
    aiMode.value = response.data?.mode || ''
    aiRecommendations.value = Array.isArray(response.data?.recommendations)
      ? response.data.recommendations
      : []
  } catch (error) {
    aiMessage.value = 'AI 推荐接口请求失败，请稍后重试；页面仍可继续使用。'
    aiRecommendations.value = []
  } finally {
    aiIsLoading.value = false
  }
}

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
    chargerMessage.value = '充电桩 API 暂不可用，请使用 ZJU-Charger 外链。'
    chargerStations.value = []
    renderChargerMarkers()
  } finally {
    chargerIsLoading.value = false
  }
}

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

  L.circle(campusCenter, {
    radius: 260,
    color: '#2563eb',
    weight: 2,
    fillColor: '#3b82f6',
    fillOpacity: 0.08
  })
    .addTo(map)
    .bindPopup('浙江大学紫金港校区示意中心')

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
    <aside class="side-panel">
      <p class="eyebrow">Zijingang WebGIS</p>
      <h1>紫金港校区信息点位展示平台</h1>
      <p class="summary">
        当前加载自习室与校园 POI GeoJSON 数据，并通过后端代理接入 ZJU-Charger 充电桩 API。
      </p>

      <section class="panel-section" aria-labelledby="module-title">
        <h2 id="module-title">功能模块</h2>
        <div class="module-list">
          <article v-for="item in modules" :key="item.key" class="module-card">
            <div class="module-heading">
              <h3>{{ item.title }}</h3>
              <span class="count-badge">{{ item.count }}</span>
            </div>
            <p>{{ item.description }}</p>
            <p v-if="item.count === 0" class="empty-state">
              {{ item.emptyText }}
            </p>
          </article>
        </div>
      </section>

      <section class="panel-section" aria-labelledby="list-title">
        <h2 id="list-title">{{ activePanelTitle }}</h2>
        <div class="tab-row" role="tablist" aria-label="点位类型切换">
          <button
            class="tab-button"
            :class="{ active: activePanel === 'study-rooms' }"
            type="button"
            @click="activePanel = 'study-rooms'"
          >
            自习室
          </button>
          <button
            class="tab-button"
            :class="{ active: activePanel === 'pois' }"
            type="button"
            @click="activePanel = 'pois'"
          >
            校园 POI
          </button>
        </div>

        <p v-if="activeItems.length === 0" class="empty-state list-empty">
          {{ activeEmptyText }}
        </p>
        <div v-else class="place-list">
          <button
            v-for="(feature, index) in activeItems"
            :key="getFeatureId(feature, activePanel, index)"
            class="place-item"
            type="button"
            @click="focusFeature(feature, index)"
          >
            <span class="place-name">{{ textOrUnknown(feature.properties?.name) }}</span>
            <span class="place-meta" v-if="activePanel === 'study-rooms'">
              {{ textOrUnknown(feature.properties?.building) }} ·
              可用座位 {{ textOrUnknown(feature.properties?.seat_available) }}
            </span>
            <span class="place-meta" v-else>
              {{ textOrUnknown(feature.properties?.category) }} ·
              {{ textOrUnknown(feature.properties?.audience) }}
            </span>
          </button>
        </div>
      </section>

      <section class="panel-section" aria-labelledby="ai-title">
        <h2 id="ai-title">AI 推荐自习室</h2>
        <form class="ai-form" @submit.prevent="submitAiRecommendation">
          <label class="sr-only" for="ai-query">学习需求</label>
          <textarea
            id="ai-query"
            v-model="aiQuery"
            rows="4"
            placeholder="例如：我想找一个安静、有插座、晚上十点以后还能学习的地方"
          ></textarea>
          <button class="primary-button" type="submit" :disabled="aiIsLoading">
            {{ aiIsLoading ? '推荐中...' : '提交需求' }}
          </button>
        </form>

        <p v-if="aiMessage" class="note ai-message" :class="{ warning: aiMode === 'empty' || aiMode === 'invalid' }">
          {{ aiMessage }}
        </p>

        <div v-if="aiRecommendations.length" class="recommendation-list">
          <article
            v-for="(item, index) in aiRecommendations"
            :key="`${item.study_room_id || item.name || 'recommendation'}_${index}`"
            class="recommendation-card"
          >
            <div class="module-heading">
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
              定位到地图点位
            </button>
            <p v-else class="place-meta">未匹配到现有地图点位，仅展示文字推荐。</p>
          </article>
        </div>
      </section>

      <section class="panel-section" aria-labelledby="charger-title">
        <h2 id="charger-title">充电桩查询</h2>
        <p v-if="chargerIsLoading" class="note">正在检查 ZJU-Charger API...</p>
        <p v-else class="note" :class="{ warning: chargerStations.length === 0 }">
          {{ chargerMessage || '充电桩模块已准备就绪。' }}
        </p>
        <p class="guardrail">
          API 状态：{{ chargerApiConfigured ? '已配置' : '未配置，使用外链兜底' }}
        </p>

        <p class="guardrail">
          当前列表显示紫金港校区空闲充电桩 Top 5；地图显示全部紫金港充电桩点位。
        </p>

        <div v-if="topAvailableChargerStations.length" class="charger-list">
          <button
            v-for="station in topAvailableChargerStations"
            :key="station.id"
            class="charger-card"
            type="button"
            @click="focusChargerStation(station)"
          >
            <h3>{{ textOrUnknown(station.name) }}</h3>
            <p>
              服务商：{{ textOrUnknown(station.provider) }} ·
              校区：{{ textOrUnknown(station.campus_name || station.campus) }}
            </p>
            <p>
              空闲/总数：{{ textOrUnknown(station.available_ports) }} /
              {{ textOrUnknown(station.total_ports) }}
            </p>
            <p>故障数：{{ textOrUnknown(station.error_ports) }}</p>
          </button>
        </div>
        <p v-else class="empty-state list-empty">
          暂无紫金港校区空闲充电桩数据，请使用 ZJU-Charger 外链查看。
        </p>
        <a
          class="external-link"
          :href="chargerFallbackUrl"
          target="_blank"
          rel="noreferrer"
        >
          打开 ZJU-Charger
        </a>
      </section>

      <section class="panel-section" aria-labelledby="status-title">
        <h2 id="status-title">当前状态</h2>
        <p v-if="isLoading" class="note">正在加载 GeoJSON 数据...</p>
        <p v-else-if="loadMessage" class="note warning">{{ loadMessage }}</p>
        <p v-else-if="!hasBusinessData" class="note">暂无数据，等待数据组补充。</p>
        <p v-else class="note success">
          已加载 {{ studyRooms.length }} 个自习室点位、{{ pois.length }} 个校园 POI 点位。
        </p>
        <p class="guardrail">不实现校园导航、路线规划或自习室筛选。</p>
      </section>

      <section class="panel-section" aria-labelledby="legend-title">
        <h2 id="legend-title">图例</h2>
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
      </section>
    </aside>

    <section class="map-area" aria-label="紫金港校区二维地图">
      <div ref="mapContainer" class="leaflet-map"></div>
    </section>
  </main>
</template>
