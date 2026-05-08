# Phase 1 Structural Cleanup Audit

## 1. 本轮目标

本轮目标是稳定执行链，降低 `web_server.py`、`web/app.js`、writeback、capability 和 prompt module 边界的结构风险。

这不是新增功能阶段；本轮验收只确认既有流程兼容、关键闸门有效、状态分区清晰、写回可信度和 prompt 职责边界仍受测试保护。

## 2. 已完成项

- run-turn 分段：`run_turn_pipeline()` 仍按 `prepare -> send -> ingest -> rewrite -> image` 顺序执行，并在任一阶段失败时停止后续阶段。
- browser_evidence 闸门：send/capture 写入 `browser_evidence.json`；ingest 前检查 evidence，缺失、`ok=false`、campaign mismatch、mode 非安全、markers 失败、output hash mismatch 都会阻断 ingest。
- web_server 三块 service 实迁移：`frontend_state`、`assets`、`writeback_review` 已由 `services/` 承接，`web_server.py` 保留同名兼容包装。
- app.js state 分区收敛：`state.campaign`、`state.story`、`state.assets`、`state.gallery`、`state.map`、`state.character`、`state.writeback`、`state.job`、`state.ui` 已作为主访问口径，legacy proxy 仍保留。
- capability 事件型触发：在原关键词触发之外，新增 `detect_capability_events()`，覆盖位置变化、物品获得/丢失/检查、线索观察、NPC 在场、状态变化、检定、生图请求和生图否定。
- prompt module 职责边界：`prompts/prompt_modules.json` 要求每个 module 带 `responsibility`、`allowed_outputs`、`must_not`，并由 registry 校验 director/actor/audit 越权输出。
- writeback 可信度和粒度：`memory_type`、`certainty`、`source`、`ttl` 已被标准化；只有 `confirmed_fact + confirmed` 进入长期事实，线索、NPC 说法和短期场景分别落到更安全的位置。

## 3. 兼容性确认

- CLI 参数：`prepare`、`send`、`capture`、`ingest`、`send-image`、`run-turn` 仍保留原参数；`run-turn` 仍接收 `--action`、`--campaign-id`、`--offline-pressure-pack`、`--skip-v4-audit`、`--auto-rewrite`、`--rewrite-attempts`。
- outbox 文件：`last_player_action.txt`、`capability_plan.json`、`pressure_pack.json`、`chatgpt_input.md`、`chatgpt_raw_output.md`、`chatgpt_blocks.json`、`state_writeback.json`、`v4_audit_result.json`、`browser_evidence.json` 等路径和文件名保持不变。
- API 路径：`/api/frontend-state`、`/api/assets`、`/api/asset`、`/api/writeback-review`、`/api/audit-writeback`、`/api/apply-writeback` 仍由原 endpoint 读取参数并返回 JSON。
- API 响应：service 迁移后保持原 payload 形状；writeback review 缺少 outbox 文件时仍返回兼容状态而不是让前端崩溃。
- prompt module 选择：`select_prompt_modules()` 仍兼容 capability plan 和 pressure pack 的 output_requests 触发。
- writeback 旧格式：旧字符串和旧 dict writeback 会被 `normalize_writeback_entry()` 包装为安全默认值。
- 前端读取方式：`LEGACY_STATE_FIELDS` 和 `partitionLegacyState()` 仍保留，旧入口不会立即崩溃；新代码使用分区字段。

## 4. 测试覆盖

- `tests/test_run_turn_pipeline.py`：run-turn 阶段顺序、失败短路、CLI 参数传递。
- `tests/test_browser_evidence.py`：browser evidence 缺失、`ok=false`、campaign mismatch、output hash mismatch、markers 通过路径。
- `tests/test_services_layer.py`：`frontend_state`、`assets`、`writeback_review` service 独立运行和 `web_server.py` 兼容包装。
- `tests/test_frontend_app_state_partition.py`：`web/app.js` 语法检查、分区字段、legacy proxy、campaign scoped reset 和 UI 偏好保留。
- `tests/test_capability_events.py`：关键词兼容、事件型触发、`image_negated` 覆盖关键词/事件/frontend flags、低置信 warning。
- `tests/test_prompt_module_registry.py`：prompt module 必填字段、director/actor/audit 越权输出校验、触发兼容。
- `tests/test_writeback.py`：可信写回、旧格式兼容、长期事实门槛、线索/NPC 说法隔离、短期场景写入、重复 hash 防重。
- `tests/test_schema_validator.py`：writeback 和 pressure pack schema 兼容约束。
- `tests/test_output_parser.py`：ChatGPT 输出解析基本兼容性。

## 5. 仍存在的风险

- services 仍有部分 helper 依赖 `web_server.py`，例如 outbox 路径、status payload、gallery taxonomy、visual registry、map panel 等。
- `web/app.js` 的 legacy state proxy 仍保留，说明前端仍处于兼容过渡期。
- `capability_events` 仍是规则型检测，不是语义模型；它降低关键词漏触发，但不能完全理解复杂语境。
- `web_server.py` 仍有 gallery、module payload、campaign/profile、prompt inspector、memory report/export 等业务可后续拆分。
- prompt registry 校验仍偏静态配置校验，不能证明 prompt 正文实际行为永远遵守职责边界。
- 前端尚未做真实浏览器交互自动化回归；目前主要依靠源码结构测试和 `node --check`。

## 6. 下一阶段建议

1. 先观察一轮真实使用，不继续大拆，重点记录 run-turn、writeback、frontend state、capability 误触发/漏触发问题。
2. 后续优先迁移 gallery taxonomy / visual registry 或 module payload，二选一，不要并行拆太多方向。
3. 再考虑删除 `app.js` legacy proxy，但必须在源码检查和真实前端回归都确认无旧引用后做。
