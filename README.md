# 浙江大学紫金港校区 WebGIS 信息点位展示与智能自习室推荐平台

这是一个课程大作业项目，范围限定为浙江大学紫金港校区。项目用于展示校园自习室、校园 POI、充电桩等空间点位，并提供 AI 自习室推荐、GeoServer 图层接入和 Cesium 三维展示能力。

项目不实现校园导航、路线规划、路径推荐、一键导航、自习室筛选或课堂汇报材料生成。

## 项目结构

```text
frontend/   前端页面，Vue 3 + Vite + Leaflet + Cesium
backend/    后端接口，FastAPI
data/       GeoJSON 演示数据与数据说明
docs/       项目背景、数据规范、空状态策略、GeoServer、AI、充电桩接入文档
```

## 当前功能状态

当前项目已经具备以下功能：

- Leaflet 二维地图展示紫金港校区，并叠加校区边界。
- 自习室点位展示、列表展示、详情弹窗和点击列表定位。
- 校园 POI 点位展示、列表展示、详情弹窗和点击列表定位。
- 充电桩数据通过后端代理 ZJU-Charger API 获取，并在地图和列表中展示。
- AI 自习室推荐：前端输入自然语言需求，后端结合 `study_rooms.geojson` 调用 DeepSeek；未配置 API Key 或 AI 服务异常时使用本地规则兜底。
- GeoServer 可选接入：通过后端代理检测 GeoServer 状态，通过 WMS / WFS 展示指定图层；未启用或不可用时回退到本地数据。
- Cesium 三维视图：展示自习室、POI、充电桩、建筑轮廓和校区边界，支持 2D / 3D 切换。
- 空数据和外部服务不可用兜底：业务数据为空、GeoServer 不可用、AI 不可用或充电桩接口不可用时，页面不应白屏。

当前仓库包含演示数据：

```text
data/study_rooms.geojson   自习室点位演示数据
data/campus_pois.geojson   校园 POI 演示数据
data/buildings.geojson     建筑轮廓演示数据
data/zjg.geojson           紫金港校区边界演示数据
```

充电桩数据不在本地创建 GeoJSON 文件，优先通过 ZJU-Charger API 获取，失败时提供外链兜底。

## 环境要求

本地运行需要：

1. Git
2. Node.js 18 或更高版本
3. Python 3.10 或更高版本
4. conda 或 venv

本项目后端推荐使用课程环境：

```powershell
D:\env\miniconda\envs\webgis\python.exe
```

## 下载项目

```powershell
git clone https://github.com/AmeliaaaGXY/ZJU-SmartCampus-Map.git
cd ZJU-SmartCampus-Map
```

如果仓库地址以后变化，请以 GitHub 页面 `Code -> HTTPS` 中显示的地址为准。

## 后端运行

进入后端目录并安装依赖：

```powershell
cd backend
D:\env\miniconda\envs\webgis\python.exe -m pip install -r requirements.txt
```

复制环境变量模板：

```powershell
copy .env.example .env
```

启动后端：

```powershell
D:\env\miniconda\envs\webgis\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

验证后端：

```text
http://127.0.0.1:8000/api/health
```

正常响应示例：

```json
{"ok": true, "project": "zijingang-webgis"}
```

## 前端运行

新开一个终端，进入前端目录：

```powershell
cd frontend
npm install
npm run dev
```

Vite 启动后打开终端中显示的地址，通常为：

```text
http://localhost:5173/
```

前端默认请求后端：

```text
http://127.0.0.1:8000
```

因此要体验完整功能，需要同时运行：

- 后端：`http://127.0.0.1:8000`
- 前端：`http://localhost:5173`

## 后端接口

主要接口：

```text
GET  /api/health
GET  /api/study-rooms
GET  /api/pois
GET  /api/buildings
GET  /api/zjg-boundary
GET  /api/config
GET  /api/chargers/status
GET  /api/chargers/stations
GET  /api/geoserver/status
GET  /api/geoserver/wfs
POST /api/ai/recommend-study-room
```

AI 推荐请求示例：

```json
{
  "query": "想找安静、有插座、晚上开放的自习室"
}
```

## 环境变量配置

后端环境变量位于 `backend/.env`，可从 `backend/.env.example` 复制。

常用配置：

```text
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
AI_RECOMMENDER_ENABLED=true

ZJU_CHARGER_API_BASE_URL=https://charger.philfan.cn
ZJU_CHARGER_STATIONS_PATH=/api/status
ZJU_CHARGER_SITE_URL=https://charger.philfan.cn/
ZJU_CHARGER_API_TIMEOUT=8
```

注意：

- `.env` 只应保存在本地。
- 不要提交真实 API Key、Token 或密码。
- 不要把 AI API Key 写入前端代码。
- 未配置 `DEEPSEEK_API_KEY` 时，AI 推荐接口会使用本地规则兜底。
- 未配置或无法访问 ZJU-Charger API 时，充电桩模块会显示外链兜底。

前端可选环境变量位于 `frontend/.env`，可从 `frontend/.env.example` 复制。

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_GEOSERVER_URL=http://127.0.0.1:8080/geoserver
VITE_GEOSERVER_WORKSPACE=webgis
VITE_GEOSERVER_LAYER=campus_pois
VITE_USE_GEOSERVER=false
```

默认 `VITE_USE_GEOSERVER=false`，避免未启动 GeoServer 时影响页面运行。需要演示 GeoServer 时，再改为 `true` 并启动本地 GeoServer。

## GeoServer 说明

GeoServer 是可选外部服务，不是项目启动的必要条件。

推荐发布图层：

```text
workspace: webgis
layer: campus_pois
```

前端启用 GeoServer 后会：

- 检查 `/api/geoserver/status`；
- 通过 WMS 叠加地图图层；
- 通过 WFS 获取 GeoJSON 要素；
- GeoServer 不可用时显示提示，并回退到本地数据或空数据。

详细方案见：

```text
docs/GEOSERVER.md
```

## Cesium 说明

前端已接入 Cesium 三维视图。点击页面右上方 `3D` 按钮后，会加载：

- 自习室点位；
- 校园 POI 点位；
- ZJU-Charger 充电桩点位；
- 建筑轮廓；
- 校区边界。

三维视图支持 OSM 街道、卫星影像和本地离线底图切换。在线底图不可用时，应回退到本地离线底图或显示提示。

## GitHub Pages 说明

GitHub Pages 只能部署前端静态页面，不能运行 FastAPI 后端。

因此：

- 可以浏览前端页面效果；
- 后端接口、AI 推荐、ZJU-Charger API 代理、GeoServer 代理等能力需要本地或公网后端支持；
- 完整演示建议本地同时运行前端和后端。

前端部署地址通常为：

```text
https://ameliaagxy.github.io/ZJU-SmartCampus-Map/
```

## 当前限制与可改进点

当前项目已经具备课程演示所需的主要功能，但仍有以下不足：

- 自习室演示数据中 `seat_available` 当前均为 0，AI 推荐和列表展示的真实说服力有限。
- GeoServer 默认未启用，需要本地额外启动和配置后才能展示 WMS / WFS 效果。
- 手机端页面先展示完整侧栏，地图位置较靠后，移动端 WebGIS 使用效率仍可优化。
- 图例在侧栏和地图上重复出现，桌面端可接受，但小屏幕上占用地图空间。
- 充电桩站点来自外部 API，字段结构和可用性依赖 ZJU-Charger 服务稳定性。
- 目前未提供自动化端到端测试，功能验证主要依赖手动运行和浏览器检查。

## 不要提交这些文件

```text
.env
backend/.env
frontend/.env
node_modules/
frontend/dist/
```

## 相关文档

```text
docs/PROJECT_CONTEXT.md
docs/DATA_CONTRACT.md
docs/EMPTY_STATE_POLICY.md
docs/ZJU_CHARGER_INTEGRATION.md
docs/GEOSERVER.md
docs/AI_STUDY_ROOM_RECOMMENDER.md
data/README.md
```
