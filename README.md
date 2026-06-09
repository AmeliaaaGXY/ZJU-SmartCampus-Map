# 紫金港校区 WebGIS 信息点位展示与智能自习室推荐平台

本项目是课程大作业的基础工程骨架，范围仅限浙江大学紫金港校区。

## 项目范围

本项目用于展示紫金港校区自习室、校园 POI 等空间点位，并提供 AI 自习室推荐、ZJU-Charger 充电桩 API 接入、GeoServer 图层管理和 Cesium 三维展示能力。

明确不做：

- 校园导航
- 路线规划
- 路径推荐
- 一键导航
- 自习室筛选
- 课堂汇报材料生成
- 本地重写充电桩查询系统
- 复制或改造 ZJU-Charger 大量源码

## 目录结构

```text
frontend/   Vue 3 + Vite + Leaflet 前端
backend/    FastAPI 后端，负责数据读取、配置和 AI API 代理
data/       GeoJSON mock 数据，允许空 features
docs/       项目规范和设计文档
```

## 后端 Python 环境

后端命令优先使用：

```powershell
D:\env\miniconda\envs\webgis\python.exe
```

## 安装依赖

前端：

```powershell
cd frontend
npm install
```

后端：

```powershell
cd backend
D:\env\miniconda\envs\webgis\python.exe -m pip install -r requirements.txt
```

## 启动命令

前端：

```powershell
cd frontend
npm run dev
```

后端：

```powershell
cd backend
D:\env\miniconda\envs\webgis\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## 环境变量

前端环境变量参考：

```text
frontend/.env.example
```

后端环境变量参考：

```text
backend/.env.example
```

真实 API Key 只能写入本地 `.env`，不要提交到 Git。

## 当前状态

当前包含基础项目结构、依赖说明、GeoJSON 示例数据、AI 自习室推荐接口，以及 ZJU-Charger API 代理的配置化接入骨架。后续请按 `项目搭建指南.md` 小步完善功能。
