# ZJU-Charger API 接入说明

## 外部项目

ZJU-Charger 是已有的浙大充电桩查询项目：

```text
https://github.com/ZJU-Charger/ZJU-Charger
```

公开站点默认使用：

```text
https://charger.philfan.cn/
```

## 接入原则

本项目不重新实现完整充电桩查询系统，不复制 ZJU-Charger 大量源码。充电桩功能采用：

```text
1. API 接入优先；
2. iframe 嵌入作为备选；
3. 外链跳转作为最终兜底。
```

前端不直接请求 ZJU-Charger。推荐由本项目 FastAPI 后端代理 ZJU-Charger API，再转换为本项目稳定响应格式，避免 CORS、授权和外部响应结构变化直接影响页面。

## API 接入前必须确认

正式配置 ZJU-Charger API 前，需要确认：

```text
API base URL：公开 API 的基础地址
endpoint：站点列表、校区列表、站点详情等路径
请求参数：校区、服务商、站点 ID 等
响应字段：站点名称、服务商、总桩数、空闲数、占用数、故障数、更新时间、经纬度
授权方式：是否需要 token、cookie、特殊 header 或 Referer
CORS：是否允许浏览器跨域；本项目仍默认后端代理
限流：是否有请求频率限制
稳定性：公开 API 是否承诺稳定，是否可能变更
许可：是否允许课程项目调用和展示数据
```

当前项目代码不硬编码未知 endpoint。真实 endpoint 通过后端环境变量配置。

## 本项目后端接口

前端只调用本项目后端：

```text
GET /api/chargers/status
GET /api/chargers/stations
```

后端环境变量：

```text
ZJU_CHARGER_API_BASE_URL=
ZJU_CHARGER_STATIONS_PATH=/api/stations
ZJU_CHARGER_SITE_URL=https://charger.philfan.cn/
ZJU_CHARGER_API_TIMEOUT=8
```

如果 `ZJU_CHARGER_API_BASE_URL` 未配置，后端返回清晰提示和外链地址，不返回 500。

## iframe 备选

如果 API 不稳定或短时间无法确认，可尝试 iframe 嵌入公开站点。若 iframe 被安全策略拦截，必须回退到外链按钮。

前端环境变量可保留：

```text
VITE_CHARGER_URL=https://charger.philfan.cn/
VITE_CHARGER_EMBED_MODE=false
```

## 外链兜底

API 和 iframe 都不可用时，前端显示“打开 ZJU-Charger”的外链按钮：

```text
https://charger.philfan.cn/
```

页面文案应说明：

```text
充电桩查询数据由 ZJU-Charger 提供，本项目通过 API 或外部页面做课程集成展示。
```

## GPLv3 注意事项

ZJU-Charger 使用 GPLv3 许可证。课程项目应注意：

- 只调用公开 API、跳转或嵌入页面时，应在 README 或页面中注明来源和链接。
- 不要复制大量源码到本项目。
- 如果复制、修改或合并其源码，可能需要遵守 GPLv3 对衍生作品的开源要求。
- 为降低许可证和维护复杂度，本项目采用 API 代理和外链兜底，不改造 ZJU-Charger 源码。

## 失败兜底

ZJU-Charger API 不可用时：

- 后端返回 `ok: false`、错误说明和 `fallback_url`；
- 前端显示“充电桩数据暂不可用”；
- 前端提供公开站点外链；
- 页面不得白屏；
- 不创建本地充电桩 GeoJSON 或伪造点位。

