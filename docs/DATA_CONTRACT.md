# 数据格式规范

## 总体要求

所有空间数据统一使用 GeoJSON `FeatureCollection`。

统一要求：

```text
坐标系：自习室、POI、建筑轮廓使用 WGS84；ZJU-Charger 充电桩坐标按 BD-09 单独转换
坐标顺序：[longitude, latitude]
字段命名：英文小写 + 下划线
缺失值：null、unknown、0、false 或 []
空数据：{"type":"FeatureCollection","features":[]}
```

当前前端二维地图使用 OSM 标准瓦片。数据组采集的自习室、POI、建筑轮廓坐标应使用 WGS84，可直接叠加到底图；ZJU-Charger 返回的充电桩坐标按 BD-09 处理，前端仅对充电桩执行 `BD-09 -> GCJ-02 -> WGS84` 转换。GeoJSON 数组顺序仍为 `[longitude, latitude]`。

任何业务数据都允许为空数组。前端和后端不得因为 `features: []` 报错。

## study_rooms.geojson

用途：自习室点位展示和 AI 自习室推荐。

Geometry：

```json
{
  "type": "Point",
  "coordinates": [120.086, 30.305]
}
```

Properties 字段：

```text
id：唯一标识，字符串
name：自习室名称
building：所在建筑
floor：楼层
room：房间号或区域名
type：自习室类型，quiet / discussion / overnight / unknown
open_time：开放时间，例如 08:00
close_time：关闭时间，例如 22:30
seat_total：总座位数，数字
seat_available：可用座位数，数字
has_power：是否有电源，布尔值
noise_level：quiet / normal / lively / unknown
power_outlet_level：none / limited / many / unknown
group_study：是否适合小组学习，布尔值
overnight_available：是否支持通宵，布尔值
nearby_facilities：附近设施，字符串或字符串数组
tags：标签数组，例如 ["安静", "插座多"]
description：描述
```

示例：

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [120.086, 30.305]
      },
      "properties": {
        "id": "sr_demo_001",
        "name": "示例自习室",
        "building": "示例教学楼",
        "floor": "2F",
        "room": "201",
        "type": "quiet",
        "open_time": "08:00",
        "close_time": "22:30",
        "seat_total": 100,
        "seat_available": 20,
        "has_power": true,
        "noise_level": "quiet",
        "power_outlet_level": "many",
        "group_study": false,
        "overnight_available": false,
        "nearby_facilities": ["图书馆", "食堂"],
        "tags": ["安静", "插座多"],
        "description": "演示用虚假数据"
      }
    }
  ]
}
```

## campus_pois.geojson

用途：校园 POI 点位展示。

Properties 字段：

```text
id：唯一标识
name：名称
category：library / teaching / canteen / scenic / service / museum / other
audience：student / visitor / both
open_time：开放时间
description：描述
```

示例：

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [120.087, 30.304]
      },
      "properties": {
        "id": "poi_demo_001",
        "name": "示例校园 POI",
        "category": "library",
        "audience": "both",
        "open_time": "unknown",
        "description": "演示用虚假数据"
      }
    }
  ]
}
```

## buildings.geojson

用途：建筑轮廓展示，可用于 Cesium 或 GeoServer。

Geometry：

```text
Polygon 或 MultiPolygon
```

Properties 字段：

```text
id：唯一标识
name：建筑名称
type：building / library / teaching / dorm / service / other
height：建筑高度，可为空
floors：楼层数，可为空
description：描述
```

## 面向 AI 推荐的数据要求

AI 推荐越依赖语义字段，推荐越稳定。建议自习室数据尽量补充：

- `noise_level`
- `power_outlet_level`
- `group_study`
- `overnight_available`
- `nearby_facilities`
- `tags`
- `description`

如果这些字段缺失，AI 推荐仍应可运行，但推荐理由要提示“数据有限”。
