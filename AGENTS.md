# AGENTS.md

本文件是本项目的长期开发规则。后续所有 Codex 会话在修改代码或文档前，都必须先遵守这里的约束。

## 项目定位

本项目是“浙江大学紫金港校区 WebGIS 信息点位展示与智能自习室推荐平台”。

项目范围仅限浙江大学紫金港校区。核心目标是展示校区相关空间点位、接入已有充电桩查询能力、提供 AI 自习室推荐，并体现 GeoServer 与 Cesium 在 WebGIS 项目中的使用。

## 必做功能

- Leaflet 二维地图展示紫金港校区。
- 自习室点位展示、列表展示、详情弹窗和地图定位。
- 校园 POI 点位展示、列表展示、详情弹窗和地图定位。
- AI 自习室推荐查询：用户输入需求，后端结合自习室数据调用 DeepSeek 等大模型 API 推荐合适自习室。
- 充电桩查询优先通过本项目后端代理 ZJU-Charger API；iframe 备选；外链兜底。
- 部分展示数据可由 GeoServer 管理，并通过 WMS / WFS 供前端使用。
- 与主题相关的数据可在 Cesium 上展示。
- 所有业务数据允许为空，空数据时页面必须正常显示。

## 禁止事项

- 不实现校园导航。
- 不实现路线规划。
- 不实现路径推荐。
- 不实现一键导航。
- 不生成课堂汇报材料。
- 不做自习室筛选功能。
- 不复制 ZJU-Charger 大量源码。
- 不创建本地充电桩 GeoJSON 或伪造充电桩点位。
- 不在前端保存或暴露 AI API Key。
- 不把真实 API Key、Token、密码写入 Git 仓库。
- 不因为 GeoServer、Cesium、AI API 或 ZJU-Charger 不可用而让页面白屏。

## 技术栈

- 前端：Vue 3 + Vite + Leaflet。
- 三维展示：Cesium。
- 后端：FastAPI。
- Python：优先使用 `D:\env\miniconda\envs\webgis\python.exe`。
- 数据格式：GeoJSON，坐标系为 WGS84 / EPSG:4326。
- 空间服务：GeoServer WMS / WFS。
- AI：后端代理 DeepSeek 等大模型 API。
- 充电桩：ZJU-Charger API 优先，iframe 备选，外链兜底。

## 代码风格与开发方式

- 小步迭代，一次只实现一个明确功能。
- 优先保持项目简单，适合课程大作业演示。
- 前端数据加载、API 请求、地图图层管理应尽量封装，避免散落在组件中。
- 后端接口应返回清晰错误信息和稳定 JSON 结构。
- 所有接口和页面都要考虑空数据、字段缺失、服务不可用。
- 新增依赖前要说明用途，避免引入大型复杂框架。
- 修改前先阅读相关文档，尤其是 `docs/PROJECT_CONTEXT.md`、`docs/DATA_CONTRACT.md`、`docs/EMPTY_STATE_POLICY.md`、`docs/ZJU_CHARGER_INTEGRATION.md`。

## 环境约束

后端 Python 命令优先使用：

```powershell
D:\env\miniconda\envs\webgis\python.exe
```

AI API Key 只允许写在后端 `.env` 中，例如：

```text
DEEPSEEK_API_KEY=your_key_here
```

`.env` 不应提交到 Git。

