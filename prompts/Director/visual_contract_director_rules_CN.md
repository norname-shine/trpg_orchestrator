# 导演层视觉契约规则

导演层输出的是绑定本团的视觉意图，不是最终绘图实现。

- 当玩家可见实体或初始化必需实体需要稳定视觉身份时，使用 `visual_contract_candidates`。
- 候选契约可以描述主角、同伴、物品、地图、场景、怪物、CG 或团内自定义实体类型。
- 不要硬写渲染器专用字段。只有当坐标属于剧情空间事实时才可写入，例如地图点位、路线节点、危险区或地标。
- 未揭示身份、未登场怪物全貌、秘密 NPC 外观、玩家自定义细节，不得提前固化。
- 已知时，每个候选项应包含 `entity_key`、`entity_type`、`display_name`、`memory_refs`、`visual_identity`、`render_intent`、`style_constraints`、`negative_constraints`、`update_policy`。
- `visual_identity` 表示该实体在本团中“是什么”。`render_intent` 表示它可以如何展示。`style_constraints` 表示团级风格约束。
- 后台会校验并归并候选项到本团 `visual_contracts.json`；导演层不能假定候选项会直接生成图片。
- 演员正文层只接收可见摘要。图像演员层可以接收由已保存契约派生出的可渲染提示词。
