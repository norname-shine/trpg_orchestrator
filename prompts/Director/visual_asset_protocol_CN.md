# 视觉资产协议

本协议描述 V4、Codex 或后续解析器传给前端的结构化视觉与地图数据。V4 负责语义布局和图像意图；后台负责画布默认值、坐标规范化、缓存 key 和绘制器默认参数。

## 建议 JSON 结构

```json
{
  "visual_assets": [
    {
      "kind": "prop | item | character | scene | cg",
      "id": "",
      "title": "",
      "detail": "",
      "source_memory": "",
      "certainty": "confirmed | clue | uncertain | placeholder",
      "display_zone": "gallery | map | portrait | log",
      "cache_policy": "stable | scene_only | rebuild_on_version",
      "character_targets": [
        {
          "actor_id": "",
          "avatar_key": "",
          "role": "player | npc | companion | servant | monster | key_character",
          "portrait_asset_kind": "portrait | npc_portrait | companion_portrait | monster_portrait",
          "crop_policy": "auto_face | auto_bust | keep_existing_if_uncertain",
          "update_visual_baseline": true
        }
      ],
      "positive_prompt": "",
      "negative_prompt": "",
      "aspect_ratio": "1:1 | 16:9 | 3:4 | 4:3",
      "style_preset": "",
      "quality": {
        "steps": 30,
        "cfg_scale": 6.5,
        "sampler": "DPM++ 2M Karras",
        "size": "1024x1024"
      }
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
  },
  "story_topology": {
    "nodes": [
      { "id": "", "label": "", "certainty": "confirmed | clue | uncertain", "status": "active | blocked | unknown", "story_role": "anchor | exit | threat | resource | clue" }
    ],
    "edges": [
      { "from": "", "to": "", "kind": "known_route | possible_route | blocked_route | pressure_link" }
    ],
    "fixed_fields": {}
  },
  "map_canvas": {
    "canvas": { "width": 1280, "height": 720, "grid_cols": 32, "grid_rows": 18 },
    "legend": { "#": "wall_or_block", ".": "walkable", "~": "water_or_anomaly", "!": "hazard", "?": "clue", "+": "resource" },
    "ascii": [],
    "points": [
      { "id": "", "label": "", "x": 0, "y": 0, "symbol": "+", "certainty": "confirmed | clue | uncertain" }
    ],
    "routes": [
      { "from": "", "to": "", "kind": "route | blocked | trace | danger" }
    ],
    "hazards": [
      { "id": "", "label": "", "x": 0, "y": 0, "symbol": "!", "kind": "hazard | clue | pressure | resource", "certainty": "confirmed | uncertain" }
    ]
  }
}
```

## 边界

- 不要为未确认设定绘制或描述精确外观。
- 资料夹资产 kind 固定为 `prop`、`item`、`character`、`scene`、`cg`。NPC、怪物、BOSS、敌对首领、关键角色归入 `character`；地图/地点归入 `scene`；线索/文献类物件归入 `item` 或 `prop`。
- 主玩家、副玩家、伙伴头像属于独立角色卡/头像槽，不生成资料夹筛选。
- 可疑痕迹、未验证怪物迹象、传闻、推断、玩家猜测使用 `certainty: clue`。
- 重复出现的 NPC、物品、地点和线索必须使用稳定 id。
- 视觉提示本身不能创造新的长期记忆事实。
- 如果视觉提示与 `forbidden_changes.json` 冲突，应忽略该提示并保留记忆边界。

## 地图提示

- `map_route` 是纯剧情拓扑，使用已确认或明显锚点；剧情拓扑不变时不要每回合重构。
- `story_topology` 可以镜像同一套纯剧情图结构，保留固定字段复用。
- `map_canvas` 是绘图地图。玩家要求“更新地图”，或场景区位、通路、阻断、危险点位变化时生成。
- `map_canvas.ascii` 会由后台规范化为 `grid_cols` x `grid_rows`，用于 Canvas 精准布局，不是正文。
- 后台可以选择或规范化画布尺寸、符号和坐标。V4 保持标签简短，并保留语义意图。

## 生图提示

- 玩家要求“执行生图”“生图”或重绘时，至少输出一条完整提示词。
- 除非玩家要求多图，否则一张可直接喂绘图模型的提示词即可。
- 生图结果必须走独立的第二轮 ChatGPT 生图会话；不得要求剧情 JSON 和图片同轮返回。
- 不要用视觉提示确认未知设定细节。
- 如果生图画面预期包含已有玩家、NPC、伙伴、从者、怪物或关键角色，`visual_assets` 应列出 `character_targets`，方便运行时从完整成品图里自动截取对应头像。
- `character_targets` 只描述已知角色和目标资产槽，不等同于确认未知外观；具体头像以成品图截取和运行时识别为准。

## 资产显示

- `display_zone` 决定资产默认出现位置，例如资料夹、地图、头像或日志。
- `cache_policy` 决定缓存策略：稳定资产复用，场景临时资产可随场景失效，绘制版本变化时允许重建。
- 前台展示使用缓存 PNG；Canvas 只作为隐藏生成来源。
- 正式生图成品图优先于 Canvas 默认头像。运行时可从多角色大图中拆分头像，并把截取结果和角色视觉基准写入对应角色配置。

## map_canvas 语义地图渲染协议

- `map_canvas` 是“绘图语义数据”，不是要在前端逐字符复刻的字符画。
- `ascii` 只表达空间结构、阻隔、可通行区域、异常液体、交互点、危险点、未知点等几何关系；运行时应把它翻译为精致、扁平、可读的二维场景地图。
- 导演层负责给出语义布局意图：区域、点位、路线、阻断、危险、资源、未知点和简短标签。
- 后台/前端负责选择画布尺寸、归一化点阵、合并连续区域、选择图标、避免标签碰撞、缓存 PNG。
- `map_route` 和 `story_topology` 保持纯剧情拓扑，不放点阵、坐标、地形符号或图像提示词。
- `map_canvas` 的符号语义：`#` 墙体/边界/隔断；`.` 可通行地面；`~` 黑水/污染/异常流体；`+` 交互/资源；`!` 危险/异常/高风险；`?` 未知/待调查。
- `points` / `hazards` 的 `label`、`kind`、`symbol` 和 `certainty` 应优先用于语义分类；中文标签只作为短标签和语义提示，不要求逐字嵌入地图。
- 地图生成后必须保存为当前团的缓存 PNG；前台展示 PNG，不直接展示原始 ASCII。
