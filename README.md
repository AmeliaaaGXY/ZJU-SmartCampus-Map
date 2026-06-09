# 紫金港校区 WebGIS 信息点位展示平台

这是一个课程大作业项目，范围仅限浙江大学紫金港校区。项目用于展示自习室、校园 POI、充电桩等信息，并提供 AI 自习室推荐功能。

项目组成部分：

```text
frontend/   前端页面，Vue 3 + Vite + Leaflet
backend/    后端接口，Python FastAPI
data/       GeoJSON 示例数据
docs/       项目文档
```

**充电桩数据已通过 ZJU-Charger API 接入，不需要自己采集充电桩数据。**


## 项目当前主要功能

- 紫金港校区二维地图展示；
- 自习室点位展示；
- 校园 POI 点位展示；
- 充电桩 API 接入与地图展示；
- AI 自习室推荐接口；

## 待实现功能：

- 自习室、校园POI皆为虚拟数据，真实数据尚未采集
- GeoServer 与 Cesium 功能尚未实现，仅预留文档
- UI及许多具体功能尚待完善

## 一、如何下载项目

先安装 Git，然后在想保存项目的位置打开 PowerShell 或终端：

```powershell
git clone https://github.com/AmeliaaaGXY/ZJU-SmartCampus-Map.git
cd ZJU-SmartCampus-Map
```

如果仓库地址以后变了，请以 GitHub 页面上的 `Code -> HTTPS` 地址为准。

## 二、需要提前安装什么

本地运行需要：

1. Git
2. Node.js 18 或更高版本
3. Python 3.10 或更高版本
4. conda 或 venv，二选一即可

检查是否安装成功：

```powershell
git --version
node -v
npm -v
python --version
```

如果使用 conda，也可以检查：

```powershell
conda --version
```

## 三、后端运行方式

后端使用 FastAPI。

### 方法 A：使用 conda（推荐）

在项目根目录执行：

```powershell
conda create -n webgis python=3.10 -y
conda activate webgis
cd backend
python -m pip install -r requirements.txt
```

复制后端环境变量模板：

```powershell
copy .env.example .env
```

然后启动后端：

```powershell
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

启动成功后，浏览器打开：

```text
http://127.0.0.1:8000/api/health
```

如果看到类似：

```json
{"ok": true, "project": "zijingang-webgis"}
```

说明后端运行成功。

### 方法 B：使用 venv

如果不用 conda，也可以用 Python 自带虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\activate
cd backend
python -m pip install -r requirements.txt
copy .env.example .env
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

## 四、前端运行方式

新开一个 PowerShell 或终端窗口，进入项目根目录：

```powershell
cd frontend
npm install
npm run dev
```

启动成功后，终端会显示类似：

```text
http://localhost:5173/
```

浏览器打开这个地址即可查看页面。

前端默认请求后端地址：

```text
http://127.0.0.1:8000
```

所以要看完整功能，请同时运行：

- 后端：`http://127.0.0.1:8000`
- 前端：`http://localhost:5173`

## 五、AI 推荐功能怎么配置

不配置 API Key 也可以运行项目。
如果 `backend/.env` 里没有 `DEEPSEEK_API_KEY`，后端会自动使用本地规则兜底推荐，页面不会崩溃。

第一次运行时，只需要执行：

```powershell
cd backend
copy .env.example .env
```

这样就能启动后端和前端。

如果需要测试真实大模型推荐，请向负责人索要本地 `.env` 文件，放到自己的 `backend/` 目录下：

```text
backend/.env
```

`.env` 文件内容类似：

```text
DEEPSEEK_API_KEY=这里填写项目负责人私下提供的 key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
AI_RECOMMENDER_ENABLED=true
```

注意：

- `.env` 只放在自己电脑本地；
- 不要提交 `.env` 到 GitHub；
- 不要把 API Key 发到公开仓库、issue、群公告或截图里；
- 没有 API Key 时，本地兜底推荐仍然可用。

## 六、GitHub Pages 网页说明

GitHub Pages 只能部署前端静态网页，不能运行 FastAPI 后端。

也就是说：

- 打开 GitHub Pages 链接，可以看到前端页面；
- 但如果没有公网后端，AI 推荐和后端接口功能可能不可用；
- 要看完整功能，请在本地同时运行前端和后端。

如果只想浏览页面效果，可以打开：

```text
https://ameliaagxy.github.io/ZJU-SmartCampus-Map/
```

如果地址变了，请以 GitHub 仓库 Pages 页面显示的网址为准。

## 七、日常开发流程

开始修改前，先拉取最新代码：

```powershell
git pull
```

修改代码后，查看改动：

```powershell
git status
```

提交修改：

```powershell
git add .
git commit -m "说明本次修改内容"
git push
```

例如：

```powershell
git add .
git commit -m "更新自习室数据展示"
git push
```

## 八、常见问题

### 后端打开根路径显示 Not Found 正常吗？

正常。

后端主要提供 API，不是网页。请打开：

```text
http://127.0.0.1:8000/api/health
```

### 前端页面显示后端不可用怎么办？

请确认后端已经启动，并且地址是：

```text
http://127.0.0.1:8000
```

## 不要提交这些文件：

以下文件不要提交到 GitHub：

```text
.env
backend/.env
frontend/.env
node_modules/
frontend/dist/
```
