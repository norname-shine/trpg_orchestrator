# 演员层 Prompt 索引

演员层 Prompt 负责玩家可见正文、对白、可见检定、证据候选，以及独立演员层生图回合。演员层正文 Prompt 不得接收原始导演/后台调度元数据。

## 运行时核心

- `chatgpt_host_prompt.md`：演员层剧情 JSON 契约。
- `chatgpt_style_rules.md`：正文风格。
- `chatgpt_npc_voice_rules.md`：NPC 对话。
- `chatgpt_image_rules.md`：演员侧生图回合边界。

## 演员层懒加载模块

- `actor_context_rules.md`：可见上下文纪律。
- `actor_writeback_rules.md`：证据写回边界。
- `actor_dice_check_rules.md`：玩家可见系统检定处理。
- `actor_inventory_rules.md`：物品证据候选。
- `actor_dossier_rules.md`：档案证据候选。
- `actor_map_rules.md`：玩家可见地图叙事边界。
- `actor_character_evidence_rules.md`：角色状态证据候选。

## 演员控制归档文件

- `character_card_json_rules.md`：角色卡控制/输出规则；不注入普通演员正文 Prompt。
- `chatgpt_monster_rules.md`：旧版怪物向演员正文规则；保留归档，直到重新引入运行时触发。

## 引用规则

- 演员正文 Prompt 接收场景简报和证据/检定标签，不接收原始 `output_requests` 或 `payloads`。
- 演员层生图 Prompt 可以接收清理后的生图指令和可见场景上下文。
- `_CN.md` 中文包必须与英文文件放在同一目录。

