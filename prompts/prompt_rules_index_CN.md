# Prompt 规则索引

这是 Prompt 包主索引。运行时 Prompt 文件按层级归档；机器路由仍由 `prompt_modules.json` 维护。

## 目录结构

- `ReferenceSpec/`：Prompt 文件的引用位置、引用方式和维护规范。
- `Director/`：导演层规则，负责压力包、宏观节奏、payload 意图和控制决策。
- `Actor/`：演员层规则，负责正文、对白、可见检定、生图回合 Prompt 和证据候选。
- `Backend/`：本地工程、前端、编码、持久化、缓存和 QA 规则。
- `Hotload/`：懒加载、输出契约、裁剪归档和运行时注入配套。

## 运行时引用

- `prompt_modules.json`：热加载注册表。模块 `path` 相对 `prompts/`。
- `prompt_language_sync.json`：由 `sync-prompts --apply` 生成的双语同步基线。
- `prompt_rules_index.json`：本文档的机器可读镜像。
- `ReferenceSpec/reference_protocol.md`：Prompt 引用与更新规范。

## 导演层

导演层负责压力、节奏、边界、payload 请求和状态提示。详见 `Director/INDEX.md`。

- 核心 Prompt：`Director/v4_director_prompt.md`。
- 上下文与分支回合：`Director/v4_campaign_context_prompt.md`、`Director/v4_payload_fulfillment_prompt.md`、`Director/v4_light_action_rules.md`。
- 审计 Prompt：`Director/v4_audit_prompt.md`。
- 控制模块：`Director/dice_check_rules.md`、`Director/inventory_rules.md`、`Director/dossier_rules.md`、`Director/chatgpt_map_rules.md`、`Director/visual_asset_protocol.md`。

## 演员层

演员层负责玩家可见剧情 JSON 和独立演员层生图 Prompt。详见 `Actor/INDEX.md`。

- 核心 Prompt：`Actor/chatgpt_host_prompt.md`。
- 常驻支持：`Actor/actor_context_rules.md`、`Actor/actor_writeback_rules.md`。
- 演员层懒加载模块：`Actor/actor_dice_check_rules.md`、`Actor/actor_inventory_rules.md`、`Actor/actor_dossier_rules.md`、`Actor/actor_map_rules.md`、`Actor/actor_character_evidence_rules.md`。
- 演员层生图回合：`Actor/chatgpt_image_rules.md`；正文/故事 Prompt 不接收视觉 payload，生图 Prompt 接收清理后的生图指令和可见场景上下文。

## 后台层

后台层维护本地编排、编码、持久化、资产、前端行为、校验和审计。详见 `Backend/INDEX.md`。

- 架构与模型边界：`Backend/codex_system_architecture_rules.md`、`Backend/model_layer_contract_rules.md`。
- 运行时安全与体验：`Backend/encoding_rules.md`、`Backend/frontend_interaction_rules.md`、`Backend/campaign_data_lifecycle_rules.md`。
- 资产与 QA：`Backend/asset_cache_lifecycle_rules.md`、`Backend/canvas_asset_generation_rules.md`、`Backend/gallery_asset_rules.md`、`Backend/ai_flavor_check_rules.md`。

## 热更新层

热更新层是运行时选择与注入层。详见 `Hotload/INDEX.md`。

- 导演/审计控制模块：`Hotload/lazy_context_rules.md`、`Hotload/output_contract_rules.md`。
- 演员层裁剪归档：`Hotload/actor_prompt_pruned_fields.md`。
- 演员层 Prompt 只接收精简可见能力、当前剧情位置、场景简报，以及允许的证据/检定区域。

## 双语包策略

- 英文运行时 Prompt 与 `_CN.md` 中文包必须位于同一目录并成对存在。
- Prompt 移动或修改后，运行 `python -m trpg_orchestrator.cli sync-prompts --apply` 刷新同步基线。
- 完成前运行 `python -m trpg_orchestrator.cli sync-prompts --check`。
- 同步命令保证成对覆盖和单边修改检测，不保证翻译质量。
