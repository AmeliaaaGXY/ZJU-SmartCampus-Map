# Marker 图标与弹窗卡片视觉升级 — 设计规格

## 背景

当前项目地图标记点使用纯色 `circleMarker`（自习室蓝色、POI 绿色），POI 内部 7 个分类无区分；弹窗为纯文字 `<div>` 拼接，无信息层次。本次改进聚焦**可视化表现层**，不改数据、不改交互逻辑。

## 范围

### 本 spec 包含

- 10 种自定义 SVG marker 图标（替换 circleMarker）
- 弹窗卡片重构为深色头部 + 两列网格布局
- 图例同步更新
- 相关代码从 App.vue 抽出到独立 service 文件

### 显式排除

- 数据补全（队友负责）
- marker 聚类、搜索增强、分类筛选（下一轮迭代）
- 充电桩坐标转换移至后端（不在本轮）
- Cesium 3D 视图改动（本轮仅改 2D）

## Marker 图标设计

### 视觉结构

每种图标统一为 **双圆环 + 底部尖角** 结构（32×40px 视口），由三部分组成：

```
┌─────────────────┐
│  外环：白色描边   │  ← 2.5px stroke，隔离地图底色
│  光晕：分类色 20%  │  ← 外圆 16px 半径，透明度光晕
│  内圆：分类色实心   │  ← 半径 10px，承载图标
│  中心：白色 SVG   │  ← 纯几何路径，无文字/emoji
└────────┬────────┘
         ▼
    底部三角尖角       ← 指向实际坐标
```

### 10 种图标定义

| 图层 | 分类 | 中心图案 | 颜色 | 色值 |
|---|---|---|---|---|
| 自习室 | — | 翻开的书（open book path） | 蓝 | `#3b82f6` |
| POI | `library` | 层叠书脊（四条横线） | 紫 | `#8b5cf6` |
| POI | `teaching` | 建筑立面 + 窗户 | 琥珀 | `#f59e0b` |
| POI | `canteen` | 碗 + 三道热气弧线 | 红 | `#ef4444` |
| POI | `scenic` | 树冠（对称弧形 + 树干） | 绿 | `#10b981` |
| POI | `service` | 信封（矩形 + 折线） | 靛 | `#6366f1` |
| POI | `museum` | 古典柱式（横纹 + 竖线） | 粉 | `#ec4899` |
| POI | `other` | 定位标记（圆 + 十字线） | 灰 | `#6b7280` |
| 充电桩 | 有空闲 | 闪电多边形 | 绿 | `#22c55e` |
| 充电桩 | 无空闲 | 闪电多边形 | 红 | `#ef4444` |

### 渲染方式

使用 Leaflet `L.divIcon`，SVG 内联为 `html` 属性字符串。不依赖外部图片文件。

实现文件：**新建 `frontend/src/services/markerIcons.js`**

导出函数：
- `getStudyRoomIcon()` → `L.divIcon`
- `getPoiIcon(category)` → `L.divIcon`（按 category 查表返回对应颜色和 SVG）
- `getChargerIcon(hasAvailable)` → `L.divIcon`（hasAvailable 为 true 时绿色，false 时红色）

## 弹窗卡片设计

### 视觉结构（风格 C：深色头部）

```
┌─────────────────────────┐
│ ▓▓▓▓▓▓ 分类色块背景 ▓▓▓▓▓▓ │  ← 分类色实底
│  基础图书馆                │  ← 白色 14px bold
│  图书馆 · 安静             │  ← 白色 9px 副标题
├─────────────────────────┤
│  建筑    基础图书馆       │  ← 两列 grid
│  时间    08:00-22:30     │     标签: 灰色 10px
│  座位    0/0             │     值: 深色 11px
│  插座    未知             │
├─────────────────────────┤
│  东区核心图书馆，大量...  │  ← 灰色 10px 斜体
└─────────────────────────┘
```

### 弹窗类型

| 弹窗 | 分类色来源 | 显示字段 |
|---|---|---|
| 自习室 | 统一蓝色 `#3b82f6` | 名称、类型、建筑、楼层房间、开放时间、可用座位、插座、安静程度、标签、描述 |
| POI | 按 category 查表 | 名称、分类、适用人群、开放时间、描述 |
| 充电桩 | 有空闲绿/无空闲红 | 名称、服务商、校区、空闲/已用/故障数、更新时间 |

无 emoji，纯排版区分层次。

实现文件：**新建 `frontend/src/services/popupBuilders.js`**

导出函数：
- `buildStudyRoomPopup(feature)` → HTML string
- `buildPoiPopup(feature)` → HTML string
- `buildChargerPopup(station)` → HTML string

## CSS 新增

在 `frontend/src/styles/base.css` 中新增以下样式块：

- `.popup-card` — 弹窗卡片容器（圆角、阴影、overflow hidden）
- `.popup-card-header` — 深色头部（分类色背景、白字）
- `.popup-card-body` — 属性网格区域
- `.popup-card-desc` — 描述文字行（分隔线 + 灰字斜体）
- `.popup-card .attr-grid` — 两列 grid 布局
- `.popup-card .attr-label` — 标签样式（`var(--color-text-muted)` 10px）
- `.popup-card .attr-value` — 值样式（`var(--color-text)` 11px）

## 代码结构调整

### App.vue 变更

- **删除** `buildStudyRoomPopup()` 函数
- **删除** `buildPoiPopup()` 函数
- **删除** `buildChargerPopup()` 函数
- **删除** `getChargerMarkerStyle()` 函数（圆形 marker 样式不再需要）
- **修改** `renderMarkers()` — 改用 `markerIcons.js` 的图标函数创建 `L.marker`（divIcon）替代 `L.circleMarker`
- **修改** `renderChargerMarkers()` — 同上，改用 `getChargerIcon()`
- **修改** `addPointMarkers()` — 参数签名调整，接收 `getIcon` 函数而非 color/fillColor
- **新增 import** — `markerIcons.js` 和 `popupBuilders.js`

### 新建文件

- `frontend/src/services/markerIcons.js`（~120 行，10 组 SVG 模板 + 3 个导出函数）
- `frontend/src/services/popupBuilders.js`（~90 行，3 个弹窗 HTML 构建函数）

### 图例更新

- 侧边栏 `.legend-grid` 和地图覆盖层 `.map-legend-overlay` 均更新为新的 10 项分类颜色
- legend 从 4 项（自习室/POI/有空闲/无空闲）扩展为 10 项

## 错误处理

本 spec 不改动数据加载和错误兜底逻辑。`textOrUnknown()` 将继续处理所有 null/undefined 值，弹窗中缺失字段显示"未知"。

## 不变更项

- 后端无改动
- 数据文件无改动
- Leaflet 地图初始化和图层管理逻辑不重构
- Cesium 3D 视图不改动
- `geojsonData.js` 不改动
- `api.js` 不改动
- `geoServerService.js` 不改动
- Vite 配置不改动
