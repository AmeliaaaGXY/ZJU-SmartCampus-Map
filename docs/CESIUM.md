# Cesium 主题数据展示方案

## 目标

本项目需要让与主题相关的数据可在 Cesium 上展示。Cesium 用于体现三维 WebGIS 能力，不用于实现导航或路线规划。

至少展示以下一类数据：

- 自习室点位。
- 校园 POI 点位。
- 建筑轮廓。

## 推荐实现方式

推荐做一个轻量三维视图：

```text
Leaflet 二维地图页
  -> “三维展示”按钮
  -> Cesium 视图
  -> 展示同一批 GeoJSON 数据
```

优先级：

```text
1. campus_pois 点位；
2. study_rooms 点位；
3. buildings 建筑轮廓；
4. 更多三维效果。
```

## Token 策略

如果使用 Cesium ion 地形、影像或资产，需要手动申请 Token。

环境变量示例：

```text
VITE_CESIUM_ION_TOKEN=your_token_here
```

不要把真实 Token 写入 Git。

如果没有 Token：

- 使用不需要 Token 的基础方案；
- 或显示清晰提示；
- 不得白屏。

## 展示内容

点位展示至少包括：

- 名称；
- 类型；
- 描述；
- 坐标；
- 点击弹窗。

建筑展示至少包括：

- 建筑名称；
- 类型；
- 楼层或高度；
- 描述。

## 禁止事项

- 不实现三维路线规划。
- 不实现校园导航。
- 不把 Cesium 做成复杂三维系统。
- 不因 Token 缺失或数据为空导致页面崩溃。

