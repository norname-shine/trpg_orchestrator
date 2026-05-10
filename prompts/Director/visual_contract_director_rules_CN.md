# 导演层视觉契约规则

导演层视觉输出是绑定本团的视觉意图，不是最终渲染器指令。

- 当玩家可见实体或初始化必需实体需要稳定视觉身份时，使用 `visual_contract_candidates`。
- `entity_type` 是闭合集合：只能使用 `player`、`companion`、`character`、`map`、`cg`、`item`、`prop`。
- 主角必须使用 `entity_type="player"`；伙伴必须使用 `entity_type="companion"`。
- NPC、怪物、敌人和关键人物统一使用 `entity_type="character"`，并用 `actor_role="npc"`、或 `actor_role="key_character"` 区分。
- 地图和地点必须使用 `entity_type="map"`；开场或剧情画面必须使用 `entity_type="cg"`。
- 不得输出 `entity_type="player_character"`、`entity_type="npc"`、`entity_type="scene"` 或 `entity_type="location"`。
- NPC 头像必须使用 `render_intent.primary="character_portrait"` 并设置 `actor_role="npc"`；不得输出 `npc_portrait`。
- 不要硬写渲染器专用字段。坐标只有在属于剧情空间事实时才允许写入，例如地图点位、路线节点、危险区或地标。
- 未揭示身份、未登场怪物全貌、秘密 NPC 外观、玩家自定义细节，不得提前固化。
- 已知时，每个候选项应包含 `entity_key`、`entity_type`、`display_name`、`memory_refs`、`visual_identity`、`render_intent`、`style_constraints`、`negative_constraints`、`update_policy`；NPC、怪物和关键人物还应包含 `actor_role`。
- `visual_identity` 表示实体在本团中“是什么”。`render_intent` 表示它可以如何展示。`style_constraints` 表示团级风格约束。
- 后台会校验并合并候选项到本团 `visual_contracts.json`；导演层不能假定候选项会直接生成图片。
- 演员正文层只接收可见摘要。图像演员层可以接收由已保存契约派生出的可渲染提示词。
