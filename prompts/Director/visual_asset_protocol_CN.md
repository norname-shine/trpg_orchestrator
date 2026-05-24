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
      "gallery_category": "prop | item | character | map | cg | registered_custom_filter_id",
      "detail": "",
      "source_memory": "",
      "certainty": "confirmed | clue | uncertain | placeholder",
      "display_zone": "gallery | map | portrait | log",
      "cache_policy": "stable | scene_only | rebuild_on_version",
      "canvas_spec": {
        "schema": "item_canvas_spec.v1 | actor_canvas_spec.v1",
        "archetype": "pendant | device | document | fragment | weapon | relic_box | custom",
        "silhouette": "triangle | round | rectangle | shard | blade | custom",
        "materials": ["silver", "purple_crystal"],
        "palette": { "base": "#c9c2b7", "accent": "#8c62d6", "glow": "#b892ff" },
        "parts": [
          { "kind": "chain" },
          { "kind": "gem", "shape": "round", "position": "center" },
          { "kind": "runes", "density": "medium" }
        ],
        "state_effects": [
          { "kind": "glow", "target": "gem", "intensity": 0.45 }
        ],
        "marks": ["ancient_runes"],
        "features": ["hooded", "masked", "scholar", "scarred"],
        "role_archetype": "guide | merchant | guard | scholar | monster | custom"
      },
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
- 资料夹资产 kind 固定为 `prop`、`item`、`character`、`map`、`cg`。NPC、怪物、BOSS、敌对首领、关键角色归入 `character`；地图/地点归入 `map`；线索/文献类物件归入 `item` 或 `prop`。
- `gallery_category` 必须复制自 Gallery Taxonomy Contract。运行时自定义筛选不得从正文或 `kind` 临时推断。
- 如果同一个有来源支撑的资产属于多个筛选，保持一个稳定 `id`，设置主分类 `gallery_category`，并用 `gallery_categories` 写入它归属的所有已登记筛选 ID。数组内必须包含主分类。
- 玩家要求每个资料夹筛选更新时，`payloads.visual_assets` 可以为每个允许的 `gallery_category` 携带一条候选，但前提是有真实来源支撑。没有来源就省略该筛选；不得用占位或虚构记录补齐。
- 主玩家、副玩家、伙伴头像属于独立角色卡/头像槽，不生成资料夹筛选。
- 可疑痕迹、未验证怪物迹象、传闻、推断、玩家猜测使用 `certainty: clue`。
- 重复出现的 NPC、物品、地点和线索必须使用稳定 id。
- 视觉提示本身不能创造新的长期记忆事实。
- 如果视觉提示与 `forbidden_changes.json` 冲突，应忽略该提示并保留记忆边界。

## 地图提示

- `map_route` 是纯剧情拓扑，使用已确认或明显锚点；剧情拓扑不变时不要每回合重构。
- `story_topology` 可以镜像同一套纯剧情图结构，保留固定字段复用。
- `map_canvas` 是绘图地图。玩家要求“更新地图”，或场景区位、通路、阻断、危险点位变化时生成。
- 当 `output_requests.map.mode` 是 `update_canvas` 时，`map_canvas.render_token` 必须严格为 `map_canvas.v1`。
- `map_canvas.ascii` 必须是字符串数组，会由后台规范化为 `grid_cols` x `grid_rows`，用于 Canvas 精准布局，不是正文。`points`、`routes`、`hazards` 必须是数组；`legend` 必须是对象。
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
- 本地 Canvas 资产必须提供声明式 `canvas_spec` JSON。不得输出 JavaScript、原始 Canvas 命令、函数体、SVG 或自由绘图代码。
- `canvas_spec` 应描述资产独特可见特征：archetype、silhouette、materials、key parts、palette、marks 和当前 state effects。这样同类资产也能画出差异。
- 物品状态变化时，更新同一稳定资产 id 的 `canvas_spec.state_effects`、`palette` 或 `marks`，不要创建重复资产。
- NPC、怪物、敌人与关键角色的 Canvas 头像也可以使用 `actor_canvas_spec.v1`；只描述玩家可见的轮廓、服装色、发色、面具、护甲、伤疤、随身符号和当前可见效果。
- 当前主玩家与当前伙伴 / 副玩家头像可以生成给左侧角色卡使用，但缓存 payload 必须使用 `gallery_category: hidden` 与 `display_zone: hidden`；不得创建资料夹筛选或资料卡。

## map_canvas 语义地图渲染协议

- `map_canvas` 是“绘图语义数据”，不是要在前端逐字符复刻的字符画。
- `ascii` 是场景地图的主要布局来源，表达空间结构、阻隔、可通行区域、异常液体、交互点、危险点、未知点、角色和相对几何；运行时应把它翻译为精致、扁平、可读的二维场景地图。
- 导演层负责给出语义布局意图：区域、点位、路线、阻断、危险、资源、未知点和简短标签。
- 后台/前端负责选择画布尺寸、归一化点阵、合并连续区域、选择图标、避免标签碰撞、缓存 PNG。
- `map_route` 和 `story_topology` 保持纯剧情拓扑，不放点阵、坐标、地形符号或图像提示词。
- `map_canvas` 的符号语义：`#` 墙体/边界/隔断；`.` 可通行地面；`~` 黑水/污染/异常流体；`+` 交互/资源；`!` 危险/异常/高风险；`?` 未知/待调查；`@` 玩家/当前位置；`N` NPC/角色。
- `points` / `hazards` 的 `label`、`kind`、`symbol` 和 `certainty` 应优先用于语义分类；中文标签只作为短标签和语义提示，不要求逐字嵌入地图。
- 地图生成后必须保存为当前团的缓存 PNG；前台展示 PNG，不直接展示原始 ASCII。
