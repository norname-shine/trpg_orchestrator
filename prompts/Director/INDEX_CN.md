# 导演层 Prompt 索引

导演层 Prompt 负责宏观场景控制、节奏、边界和结构化 payload 意图。这里可以包含路由/控制概念，但这些内容不得注入普通演员层正文 Prompt。

## 运行时核心

- `v4_director_prompt.md`：严格压力包契约。
- `v4_campaign_context_prompt.md`：长期导演上下文。
- `v4_payload_fulfillment_prompt.md`：payload 补全回合。
- `v4_light_action_rules.md`：轻量固定行动导演路径。
- `v4_audit_prompt.md`：写回审批的审计回合。

## 控制模块

- `visual_asset_protocol.md`：视觉与地图 payload 协议。
- `chatgpt_map_rules.md`：导演侧地图控制边界。
- `dice_check_rules.md`：导演侧骰子/检定授权。
- `inventory_rules.md`：导演侧物品更新授权。
- `dossier_rules.md`：导演侧档案更新授权。

## 引用规则

- 运行时注入由 `../prompt_modules.json` 控制。
- 本目录用于导演/审计控制规则，不用于演员正文指令。
- `_CN.md` 中文包必须与英文文件放在同一目录。
