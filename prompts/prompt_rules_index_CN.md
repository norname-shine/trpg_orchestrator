# Prompt 规则索引

本文档是运行时 Prompt 规则的人类维护索引。机器可读镜像为 `prompt_rules_index.json`。

## 导演层

导演层负责压力、节奏、边界、payload 请求和状态提示。导演层可以接收较宽的跑团记忆，但不应接收本地实现噪音。

- `v4_director_prompt.md`：严格压力包契约与宏观回合决策。
- `v4_campaign_context_prompt.md`：长期跑团上下文规则。
- `v4_payload_fulfillment_prompt.md`：导演专属 payload 补全回合。
- `v4_light_action_rules.md`：轻量行动的导演直出路径。
- `visual_asset_protocol.md`：视觉与地图 payload 语义契约。
- 按需共享：`dice_check_rules.md`、`inventory_rules.md`、`dossier_rules.md`、`lazy_context_rules.md`、`output_contract_rules.md`。

## 演员层

演员层只写玩家可见剧情 JSON。演员层应只接收正文写作所需的可见上下文。

- `chatgpt_host_prompt.md`：演员输出 JSON 与 block 规则。
- `chatgpt_style_rules.md`：正文与场景表演风格。
- `chatgpt_npc_voice_rules.md`：NPC 对话表演。
- `chatgpt_image_rules.md`：演员侧生图回合边界。
- `chatgpt_map_rules.md`：玩家可见地图叙事边界。
- `character_card_json_rules.md`：需要时的角色卡写回规则。
- 按需共享：`dice_check_rules.md`、`inventory_rules.md`、`dossier_rules.md`、`lazy_context_rules.md`、`output_contract_rules.md`。

## 后台层

后台层维护本地编排、编码、持久化、资产、前端行为、校验和审计。这些规则不是演员层正文指令。

- `codex_system_architecture_rules.md`：本地工程架构。
- `codex_computer_use_prompt.md`：浏览器自动化边界。
- `encoding_rules.md`：UTF-8 与 Prompt 语言策略。
- `campaign_data_lifecycle_rules.md`：跑团数据生命周期。
- `frontend_interaction_rules.md`：前端展示与交互规则。
- `asset_cache_lifecycle_rules.md`：缓存安全规则。
- `canvas_asset_generation_rules.md`：本地 Canvas 资产生成规则。
- `ai_flavor_check_rules.md`：本地输出 QA 与重写触发。

## 热加载板块

热加载是运行时选择与注入层，归后台维护。演员层只能看到精简后的能力信息。

- `prompt_modules.json`：Prompt 模块、层级与触发器的机器注册表。
- 跑团级 `custom_rules.json`：临时规则，可路由到导演、演员或双方。
- Capability plan：本地路由上下文；演员 Prompt 只接收精简可见子集。
- Lazy context rules：按当前回合需求加载 Prompt 与记忆模块。
- Output contract rules：共享结构边界，不是正文内容。
- `prompt_language_sync.json`：由 `sync-prompts --apply` 生成的双语包同步基线。

## 双语包策略

- 英文运行时 Prompt 与 `_CN.md` 中文包必须成对存在。
- 运行 `python -m trpg_orchestrator.cli sync-prompts --apply` 创建缺失对应包并刷新同步基线。
- 运行 `python -m trpg_orchestrator.cli sync-prompts --check` 确认 Prompt 修改完整。
- 同步命令不保证翻译质量；它保证基线建立后不会静默接受单边修改。

## 演员层干净输入策略

- 演员 Prompt 不得包含后台专属地图画法、Canvas、视觉 prompt、缓存、manifest、路由调度、payload 补全、debug、warning 或空字段。
- 演员 Prompt 只保留玩家行动、可见记忆、当前场景压力、NPC 表演方向、禁止边界、选择要求、简化进度和必要写回目标。
- 被删除字段记录在 `actor_prompt_pruned_fields.md`。
