# GeoServer 数据管理方案

## 目标

本项目需要通过 GeoServer 对部分展示数据进行管理。GeoServer 不要求管理全部数据，但至少应规划或实现一类数据图层。

推荐优先发布：

```text
campus_pois
study_rooms
buildings
```

优先级建议：

```text
1. campus_pois：点位简单，最适合快速发布和展示；
2. study_rooms：可体现业务主题；
3. buildings：适合轮廓或三维展示，但数据准备成本更高。
```

## 服务形式

GeoServer 可发布：

- WMS：用于前端地图叠加显示。
- WFS：用于前端获取矢量要素和属性。

## 前端配置建议

`.env` 示例：

```text
VITE_GEOSERVER_URL=http://127.0.0.1:8080/geoserver
VITE_GEOSERVER_WORKSPACE=webgis
VITE_GEOSERVER_LAYER=campus_pois
VITE_USE_GEOSERVER=false
```

默认 `VITE_USE_GEOSERVER=false`，避免 GeoServer 未启动时影响项目运行。

## 发布步骤建议

1. 安装 Java 和 GeoServer。
2. 启动 GeoServer。
3. 创建 workspace，例如 `webgis`。
4. 导入 GeoJSON 或 Shapefile。
5. 发布图层，例如 `campus_pois`。
6. 开启 WMS / WFS。
7. 在前端 `.env` 中配置服务地址。
8. 前端加载 WMS 图层或通过 WFS 获取要素。

## 兜底策略

GeoServer 不可用时：

- 前端不应白屏。
- 地图仍显示底图。
- 业务数据回退到后端 API 或本地 GeoJSON。
- 页面显示“GeoServer 图层暂不可用”的提示。

## 禁止事项

- 不硬编码不可用的 GeoServer 地址。
- 不让 GeoServer 成为前端启动的必要条件。
- 不因为 WMS / WFS 请求失败导致页面崩溃。

