# AI 自习室推荐查询

## 目标

自习室不做筛选功能。用户通过自然语言输入需求，由 AI 根据当前自习室数据推荐最适合的自习室。

示例用户输入：

```text
我想找一个安静、有插座、晚上十点以后还能学习、适合一个人复习的地方。
```

## 推荐架构

```text
前端输入框
  -> POST /api/ai/recommend-study-room
  -> 后端读取 study_rooms.geojson
  -> 后端调用 DeepSeek 等大模型 API
  -> 返回推荐结果和理由
```

前端不得直接调用大模型 API。

## 后端接口

接口：

```text
POST /api/ai/recommend-study-room
```

请求体：

```json
{
  "query": "我想找一个安静、有插座、晚上十点以后还能学习的地方"
}
```

成功响应：

```json
{
  "ok": true,
  "mode": "ai",
  "recommendations": [
    {
      "study_room_id": "sr_demo_001",
      "name": "示例自习室",
      "reason": "该自习室较安静，插座较多，并且开放时间符合需求。",
      "matched_needs": ["安静", "插座", "晚上学习"],
      "notes": "当前数据为演示数据，实际可用情况需以现场为准。"
    }
  ]
}
```

兜底响应：

```json
{
  "ok": false,
  "mode": "fallback",
  "message": "暂无自习室数据，无法推荐。",
  "recommendations": []
}
```

## API Key 安全策略

AI API Key 必须放在后端环境变量中。

`.env` 示例：

```text
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
AI_RECOMMENDER_ENABLED=true
```

禁止：

- 把真实 Key 写入前端。
- 把真实 Key 写入 Git。
- 在 README 或文档中展示真实 Key。
- 让浏览器直接请求 DeepSeek API。

## 推荐提示词策略

后端发送给 AI 的提示词应包含：

```text
你是浙江大学紫金港校区自习室推荐助手。
你只能基于提供的自习室候选数据推荐，不要编造不存在的自习室。
如果数据为空，请说明无法推荐。
如果字段缺失，请说明数据有限。
请根据用户需求推荐 1-3 个最合适的自习室，并给出理由。
不要提供路线规划或导航建议。
```

候选数据应尽量压缩，只发送必要字段：

- id
- name
- building
- floor
- type
- open_time
- close_time
- seat_available
- has_power
- noise_level
- power_outlet_level
- group_study
- overnight_available
- nearby_facilities
- tags
- description

## 本地规则兜底

没有 API Key 或 AI 请求失败时，可使用本地规则：

1. 优先 `seat_available > 0`。
2. 用户提到“安静”，优先 `noise_level=quiet` 或 `type=quiet`。
3. 用户提到“讨论/小组”，优先 `group_study=true` 或 `type=discussion`。
4. 用户提到“通宵/晚上”，优先 `overnight_available=true` 或 `type=overnight`。
5. 用户提到“插座/充电”，优先 `has_power=true` 或 `power_outlet_level=many`。
6. 最后按 `seat_available` 从高到低排序。

## 空数据兜底

如果 `study_rooms.geojson` 为：

```json
{
  "type": "FeatureCollection",
  "features": []
}
```

则后端应返回：

```text
暂无自习室数据，无法推荐。
```

前端应显示该提示，不得报错。

## 前端展示要求

前端应包含：

- 用户需求输入框；
- 提交按钮；
- 加载状态；
- 推荐结果列表；
- 推荐理由；
- 错误或空数据提示。

如果推荐结果能匹配现有地图点位，则点击结果定位到 marker。

如果无法匹配地图点位，只展示文字推荐，不强制定位。

