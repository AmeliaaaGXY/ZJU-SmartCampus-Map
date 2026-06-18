# 图层控制、聚类、Cesium 弹窗与校园边界 — 设计规格

## 背景

上一轮完成了 marker 图标和弹窗视觉升级。本轮涵盖四个互补需求：图层切换控制、marker 聚类、Cesium 弹窗统一、2D 校园边界叠加，外加 3D 充电桩数据加载。

## 范围

### 包含

1. 图层切换分段按钮（2D + 3D 视图中均显示）
2. Leaflet markercluster 按分组聚合（`leaflet.markercluster` 插件）
3. Cesium InfoBox 样式改造，内容与 2D 弹窗统一（深色头部卡片）
4. 2D 地图叠加校园边界（`L.geoJSON` + `/api/zjg-boundary`）
5. 3D Cesium 加载充电桩实体

### 排除

- 数据补全（队友负责）
- 后端改动（`/api/zjg-boundary` 和 `/api/chargers/stations` 已存在）
- 3D 视图不做聚类（Cesium 没有原生聚类方案，超出课程范围）

---

## 1. 图层切换组件

### 交互

- 2D 视图的 `map-toolbar` 中、3D 视图的 `cesium-top-bar` 中各放一组分段按钮
- 四个选项：全部 / 自习室 / 校园 POI / 充电桩
- 选中项高亮（复用 `.view-mode-btn.active` 样式）
- `activeLayer` 为全局 ref（`'all' | 'study-rooms' | 'pois' | 'chargers'`），2D/3D 切换时保持

### 2D 行为

- 监听 `activeLayer`，调用 marker 图层和充电桩图层的 add/remove
- 自习室层和 POI 层合并为 `markerClusterGroup`（见聚类部分）
- 充电桩层为独立 `L.layerGroup`（不做聚类）
- 切换时只显示对应层的 markers

### 3D 行为

- CesiumView 通过 prop 接收 `activeLayer`
- 对应切换 entity 的 `show` 属性：
  - 自习室 entity 组：`studyRoomEntities`
  - POI entity 组：`poiEntities`
  - 充电桩 entity 组：`chargerEntities`
- "全部"时全部显示

### 实现

- 新建 `frontend/src/services/layerControl.js`：导出 `LAYER_OPTIONS` 常量数组和图层切换逻辑（可选，因为核心状态仍在 App.vue）

---

## 2. Marker 聚类

### 方案

引入 `leaflet.markercluster`（npm 包，MIT 许可），按图层分组聚类。

### 配置

```javascript
const markerClusterGroup = L.markerClusterGroup({
  maxClusterRadius: 50,
  spiderfyOnMaxZoom: true,
  showCoverageOnHover: false,
  zoomToBoundsOnClick: true
})
```

### 行为

- 自习室和 POI 两个图层各用一个独立的 `markerClusterGroup`
- 充电桩不做聚类（数量少，~5 个站点）
- 聚类圆颜色：自习室蓝色 `#4a7c8c`，POI 色与分类主色一致（取 POI 占多数的颜色）
- 新增依赖：`leaflet.markercluster` + 其 CSS

### 图层切换与聚类的配合

- 切换图层时，通过 `map.addLayer()` / `map.removeLayer()` 控制显示
- "全部" → 所有 cluster group 添加
- "自习室" → 只添加自习室 cluster group，移除其他
- "POI" → 同理
- "充电桩" → 添加充电桩普通 layerGroup

---

## 3. Cesium 弹窗统一

### 方案

改造 Cesium 自带 InfoBox（右上角白色容器），使用自定义 CSS 样式使其与 2D 弹窗风格一致。

### 具体改动

- `CesiumView.vue` 的 `initCesium()` 中保留 `infoBox: true`
- 使用 `viewer.infoBox.frame` 设置 iframe 内容或直接操作 DOM
- 弹窗内容由 `popupBuilders.js` 的三个函数生成：
  - 自习室 entity → `buildStudyRoomPopup(feature)`
  - POI entity → `buildPoiPopup(feature)`
  - 充电桩 entity → `buildChargerPopup(station)`
- 在 `viewer.selectedEntityChanged` 事件中，关闭默认 InfoBox 的 iframe，改为自定义 HTML 内容

### CSS

- 复用 `.popup-card` 系列样式（从 `base.css` 导入）
- InfoBox 外框去边框、去阴影、去圆角 → 让内容卡自行控制
- 背景透明，宽度 250px，右对齐

---

## 4. 2D 校园边界

### 方案

在 `init2DMap()` 中调用 `/api/zjg-boundary`，用 `L.geoJSON` 渲染：

```javascript
const boundaryResponse = await fetch(`${apiBase}/api/zjg-boundary`)
if (boundaryResponse.ok) {
  const boundaryData = await boundaryResponse.json()
  L.geoJSON(boundaryData, {
    style: {
      fillColor: '#c2644f',
      fillOpacity: 0.08,
      color: '#c2644f',
      weight: 2.5
    }
  }).addTo(map).bringToBack()
}
```

- 渲染在 marker 图层之下、背景瓦片之上
- `/api/zjg-boundary` （后端已存在，返回 `zjg.geojson`）不可用时静默跳过
- 无需后端改动

---

## 5. 3D 充电桩数据加载

### 方案

`CesiumView.vue` 的 `loadGeoJsonData()` 中增加充电桩数据加载：

- 调用 `getChargerStations()`（API 已存在）
- 坐标转换：复用 2D 的 `bd09ToWgs84` 逻辑。为避免代码重复，将 `bd09ToGcj02()` 和 `gcj02ToWgs84()` 从 `App.vue` 抽出到 `geojsonData.js`，然后 CesiumView 中 import
- 按有空闲/无空闲用不同颜色的 billboard 渲染（绿色 `#22c55e` / 红色 `#ef4444`）
- 闪电 SVG 图案（复用 `markerIcons.js` 的 `ICONS.charger`）
- entity 设置 `description: buildChargerPopup(station)`

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|---|---|---|
| `frontend/package.json` | 修改 | 新增 `leaflet.markercluster` 依赖 |
| `frontend/src/services/geojsonData.js` | 修改 | 移入 `bd09ToGcj02`/`gcj02ToWgs84`/`bd09ToWgs84` 坐标转换函数 |
| `frontend/src/services/layerControl.js` | 新建 | 图层选项常量，`activeLayer` 相关工具 |
| `frontend/src/App.vue` | 修改 | 添加图层切换按钮、clustering、边界层；移除本地坐标转换函数改为 import |
| `frontend/src/components/CesiumView.vue` | 修改 | 接收 `activeLayer` prop、改造 InfoBox、加载充电桩、添加图层切换按钮 |
| `frontend/src/styles/base.css` | 修改 | 图层切换按钮样式、cluster 图标样式覆盖、Cesius InfoBox 覆盖样式 |

---

## 不变更

- 后端无改动（所有 API 已存在）
- 数据文件无改动
- GeoServer 集成无改动
- AI 推荐逻辑无改动
