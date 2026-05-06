# 跑团数据生命周期与多团并行规则

本规则约束本地跑团数据、ChatGPT 输入输出、实体档案和前台资产的生成与保存。它适用于怪物团、Fate、COC、DnD 和原创团。

## 1. 多团隔离

- 每个跑团必须以 `campaign_id` 作为主隔离键，并以 `asset_seed` 作为视觉资产和可复现生成的辅助种子。
- 任何输入、输出、记录、资产、实体档案都不得只依赖全局 `outbox/`。
- 当前标准路径：
  - `campaigns/<campaign_id>/outbox/chatgpt_input.md`
  - `campaigns/<campaign_id>/outbox/chatgpt_raw_output.md`
  - `campaigns/<campaign_id>/outbox/chatgpt_blocks.json`
  - `campaigns/<campaign_id>/logs/*_turn.json`
  - `campaigns/<campaign_id>/assets/manifest.json`
- 全局 `outbox/` 只能作为手动 ChatGPT 流程的镜像与兼容入口，不能作为长期事实来源。

## 2. 回合记录

- 每次跑团回合都要在本地保留可追踪记录。
- 回合记录至少包含：
  - `campaign_id`
  - `turn_index`
  - `asset_seed`
  - `player_action`
  - `pressure_pack`
  - `chatgpt_input_path`
  - `chatgpt_raw_output_path`
  - `parsed_blocks`
  - `state_writeback`
  - `audit_result`
  - `generated_or_updated_entities`
- `logs/*_turn.json` 是审计记录；`run_records.json` 是可供前端和后续压缩读取的轻量索引。

## 3. 本地实体档案

- NPC、伙伴、从者、怪物、物品、线索、地图节点、地点和任务都应进入本地实体档案。
- 推荐通用实体结构：
```json
{
  "id": "",
  "kind": "player | companion | npc | servant | monster | item | clue | map | location | quest",
  "display_name": "",
  "campaign_id": "",
  "asset_key": "",
  "status": "active | hidden | archived | unknown",
  "first_seen_turn": 0,
  "last_seen_turn": 0,
  "confirmed": {},
  "uncertain": [],
  "personality": [],
  "background": [],
  "relationships": {},
  "update_policy": ""
}
```
- NPC 档案必须支持性格、动机、背景、说话边界、知识边界、关系变化和前台头像资产。
- 伙伴 / 副玩家 / 从者档案必须独立于 NPC 档案保存，因为它们会随剧情推进更新能力、伤势、信任、真名、契约状态或隐藏身份。

## 4. 动态实体更新

- Fate 团的从者、怪物团的艾露猫、DnD 的队友、COC 的协助调查员都属于同一类“伙伴/副玩家”抽象。
- 像 Fate 团的 `井匣`、`Assassin` 这类核心对象，不是一次性物品或静态 NPC，必须允许随剧情推进更新：
  - 新确认事实写入 `confirmed`
  - 尚未确认内容写入 `uncertain`
  - 视觉变化写入 asset metadata
  - 状态变化写入 `status` 或专属字段
- 禁止在前端或绘图层硬编码它们的长期事实。

## 5. 视觉资产与实体绑定

- 每个实体如果需要前台展示，应拥有稳定 `asset_key`。
- `asset_key` 必须派生自 `campaign_id / asset_seed / entity_id / kind / generator_version`。
- Canvas 只负责本地生成 PNG；前台展示必须使用 IMG 引用缓存 PNG。
- 物品和线索第一次出现时必须先语义分析，再进入对应 Canvas 绘制分支。
- 正式生图成品中截取到的角色头像可以覆盖 Canvas 默认头像，但必须写入对应实体档案的视觉基准，而不是只替换临时图片。
- 视觉基准建议包含：脸型、五官风格、发型、服饰调性、主色、画风气质、识别物、禁止漂移点、来源图片 asset_key 和截取区域 metadata。
- 主角、NPC、伙伴/从者、怪物都使用同一套实体绑定规则；不得为某一团类型写死独立逻辑。

## 6. 写回边界

- ChatGPT 只返回结构化正文和建议写回。
- V4 或审核层决定哪些写回可进入长期档案。
- 本地系统负责把写回拆分到：
  - `npc_profiles.json`
  - `companion_profiles.json`
  - `equipment_history.json`
  - `clue_history.json`
  - `map_history.json`
  - `entity_index.json`
  - `main_threads.json`
  - `recent_context.json`
- 不确认的秘密、推测和误判不能写成 confirmed。
