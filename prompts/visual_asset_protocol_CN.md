# 视觉资产协议

本协议描述 V4、Codex 或后续解析器传给前端的结构化视觉提示。V4 只给约束、来源和可视化方向，本地前端负责绘制并缓存资产。

## 建议 JSON 结构

```json
{
  "visual_assets": [
    {
      "kind": "npc | item | scene | map | monster | ecology",
      "id": "",
      "title": "",
      "detail": "",
      "source_memory": "",
      "certainty": "confirmed | clue | uncertain | placeholder",
      "display_zone": "gallery | map | portrait | log",
      "cache_policy": "stable | scene_only | rebuild_on_version"
    }
  ],
  "map_route": {
    "title": "",
    "nodes": [
      { "id": "", "label": "", "certainty": "confirmed | clue | inferred" }
    ],
    "edges": [
      { "from": "", "to": "", "kind": "route | blocked | trace | danger" }
    ],
    "markers": [
      { "label": "", "kind": "clue | pressure | hazard | resource", "certainty": "confirmed | uncertain" }
    ]
  }
}
```

## 边界

- 不要为未确认设定绘制或描述精确外观。
- 可疑痕迹、未验证怪物迹象、传闻、推断、玩家猜测使用 `certainty: clue`。
- 重复出现的 NPC、物品、地点和线索必须使用稳定 id。
- 视觉提示本身不能创造新的长期记忆事实。
- 如果视觉提示与 `forbidden_changes.json` 冲突，应忽略该提示并保留记忆边界。

## 地图提示

- `map_route.nodes` 应优先使用已确认地点或现场明显锚点。
- `map_route.markers` 可以包含压力、破坏、痕迹、阻断路线、天气、时间压力和资源点。
- 前端应优先绘制可读路线图，而不是追求写实地图。
- 标签必须足够短，能放进小尺寸 16:9 地图面板。

## 资产显示

- `display_zone` 决定资产默认出现位置，例如资料夹、地图、头像或日志。
- `cache_policy` 决定缓存策略：稳定资产复用，场景临时资产可随场景失效，绘制版本变化时允许重建。
- 前台展示使用缓存 PNG；Canvas 只作为隐藏生成来源。
