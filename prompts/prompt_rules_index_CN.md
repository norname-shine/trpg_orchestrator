# Prompt 规则总索引

这是 Prompt 包的主索引。运行时 Prompt 文件按层级组织；机器路由仍由 `prompt_modules.json` 控制。

## 目录结构

- `ReferenceSpec/`：Prompt 文件引用与更新规范。
- `Director/`：导演层规则，负责 pressure pack、宏观节奏、payload 意图、视觉契约候选和控制决策。
- `Actor/`：演员层规则，负责正文、对话、可见检定、图像回合提示和证据候选。
- `Backend/`：本地工程、前端、编码、持久化、缓存和 QA 规则。
- `Hotload/`：懒加载、输出契约、裁剪归档和运行时注入支持。

## 运行时引用

- `prompt_modules.json`：热加载注册表，`path` 相对 `prompts/`。
- `prompt_language_sync.json`：由 `sync-prompts --apply` 生成的双语同步基线。
- `prompt_rules_index.json`：本索引的机器可读镜像。
- `ReferenceSpec/reference_protocol.md`：Prompt 引用与更新规则。

## 导演层

导演层决定压力、节奏、边界、payload 请求、状态提示和视觉契约候选。见 `Director/INDEX.md`。

- 核心 Prompt：`Director/v4_director_prompt.md`。
- 上下文与补全：`Director/v4_campaign_context_prompt.md`、`Director/v4_payload_fulfillment_prompt.md`、`Director/v4_light_action_rules.md`。
- 审计 Prompt：`Director/v4_audit_prompt.md`。
- 控制模块：`Director/dice_check_rules.md`、`Director/inventory_rules.md`、`Director/dossier_rules.md`、`Director/chatgpt_map_rules.md`、`Director/visual_asset_protocol.md`、`Director/visual_contract_director_rules.md`。

## 演员层

演员层写玩家可见的剧情 JSON，并处理独立的图像演员提示。见 `Actor/INDEX.md`。

- 核心 Prompt：`Actor/chatgpt_host_prompt.md`。
- 常驻支持：`Actor/actor_context_rules.md`、`Actor/actor_writeback_rules.md`。
- 演员专用懒加载模块：`Actor/actor_dice_check_rules.md`、`Actor/actor_inventory_rules.md`、`Actor/actor_dossier_rules.md`、`Actor/actor_map_rules.md`、`Actor/actor_character_evidence_rules.md`。
- 图像回合：`Actor/chatgpt_image_rules.md`。正文 Prompt 不接收原始视觉 payload；图像 Prompt 接收经过净化且可见的场景/视觉契约派生输入。

## 后台层

后台层维护本地编排、编码、持久化、资产、前端行为、校验和审计链路。见 `Backend/INDEX.md`。

- 架构与模型边界：`Backend/codex_system_architecture_rules.md`、`Backend/model_layer_contract_rules.md`。
- 运行时安全与体验：`Backend/encoding_rules.md`、`Backend/frontend_interaction_rules.md`、`Backend/campaign_data_lifecycle_rules.md`。
- 资产与 QA：`Backend/asset_cache_lifecycle_rules.md`、`Backend/visual_contract_lifecycle_rules.md`、`PromptModules/asset_output_rules.md`、`Backend/canvas_asset_generation_rules.md`、`Backend/gallery_asset_rules.md`、`Backend/ai_flavor_check_rules.md`。

## Hotload 层

Hotload 是运行时选择和注入层。见 `Hotload/INDEX.md`。

- 导演/审计控制模块：`Hotload/lazy_context_rules.md`、`Hotload/output_contract_rules.md`。
- 演员裁剪归档：`Hotload/actor_prompt_pruned_fields.md`。
- 演员 Prompt 只接收紧凑的可见能力摘要、当前剧情位置、场景简报和允许的证据/检定范围。

## 双语包策略

- 英文运行时 Prompt 和 `_CN.md` 中文包必须在同一目录成对维护。
- Prompt 移动或编辑后运行 `python -m trpg_orchestrator.cli sync-prompts --apply` 刷新同步基线。
- 修改完成前运行 `python -m trpg_orchestrator.cli sync-prompts --check`。
- 同步命令保证成对覆盖和单边修改检测，不保证翻译质量。
