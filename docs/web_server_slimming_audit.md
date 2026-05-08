# web_server.py 瘦身验收

## 已实迁移

- `frontend_state`：`frontend_state_response()`、`campaign_state()`、`lightweight_output_shell()`、`build_frontend_state()` 已由 `services/frontend_state.py` 承接，`web_server.py` 只保留兼容调用入口。
- `assets`：`asset_list()`、`asset_lookup()`、`save_asset()`、`delete_asset()`、`rebuild_assets()` 已由 `services/assets.py` 承接，接口路径和返回结构保持不变。
- `writeback_review`：`writeback_review_payload()`、`audit_writeback_payload()`、`apply_writeback_payload()` 已由 `services/writeback_review.py` 承接，继续使用原 outbox 文件名和 V4 audit/writeback 结构。

## 已清理的旧 impl

以下旧实现钩子在 `web_server.py` 中已不存在，service 文件也不再调用它们：

- `_frontend_state_response_impl`
- `_campaign_state_impl`
- `_asset_list_impl`
- `_asset_lookup_impl`
- `_save_asset_impl`
- `_delete_asset_impl`
- `_rebuild_assets_impl`
- `_writeback_review_payload_impl`
- `_audit_writeback_payload_impl`
- `_apply_writeback_payload_impl`

## web_server.py 当前保留职责

必须留在 `web_server.py` 的职责：

- HTTP handler 与路由分发：`TRPGHandler.do_GET()`、`TRPGHandler.do_POST()`、`TRPGHandler._json()`、`TRPGHandler._serve_static()`。
- 请求参数读取与 JSON 返回：`first_query()` 以及各 `/api/...` endpoint 的参数接入。
- 静态文件服务与本地 server 启动：`main()`、静态页面和 campaign asset 文件服务。
- 本地运行状态：`JobState`、全局 `JOB`、运行中 job 的 snapshot 与状态更新。

可以暂时保留的 helper：

- 路径兼容 helper：`safe_segment()`、`campaign_outbox_dir()`、`resolve_outbox_dir()`、`require_outbox_campaign()`、`outbox_campaign_id()`、`sync_global_outbox_to_campaign()`。
- status/output/helper：`status_payload()`、`output_payload()`、`raw_output_payload()`、`frontend_pipeline_status()`、`empty_output_payload()`。
- streaming/job helper：`launch_job()`、`run_command()`、`run_command_streaming()`、`maybe_update_stream_from_line()`、`run_turn_stream_payload()`。
- 多 endpoint 共用的轻量 helper：`campaign_list()`、`select_campaign()`、`safe_outbox_snapshot()`、`read_web_capability_plan()`。

下一轮应迁出的业务组：

- visual contract 与前端视觉注册表业务：`visual_contract_updates_from_pressure()`、`build_visual_registry()`、`frontend_map_panel()`。
- module payload 与 gallery taxonomy 业务：`module_payload_response()`、`frontend_gallery()`、`gallery_taxonomy_for_campaign()`、`normalize_frontend_gallery_kind()`。
- campaign 管理业务：`create_campaign_smart_payload()`、`init_campaign_payload()`、`update_campaign_profile_payload()`、`update_campaign_status_payload()`、`delete_campaign_payload()`。
- prompt inspector 与规则/记忆报告业务：`prompt_inspector_payload()`、`memory_report_payload()`、`campaign_export_payload()`。

## service 仍依赖的 web_server helper

`services/frontend_state.py` 仍通过 `_web_server()` 读取：

- 合理过渡：`JOB`、`campaign_list()`、`streaming_preview_enabled()`、`output_payload()`、`frontend_pipeline_status()`、`empty_output_payload()`。这些仍和 HTTP/server 运行状态或多个 endpoint 的 output 语义绑定。
- 下一轮建议迁出：`frontend_campaign_setup()`、`campaign_chapter()`、`frontend_character_card()`、`frontend_companion_card()`、`frontend_quests()`、`frontend_inventory()`、`gallery_taxonomy_for_campaign()`、`gallery_filters_from_taxonomy()`、`frontend_story_progress_payload()`、`campaign_initialization_frontend_payload()`、`frontend_map_panel()`、`build_visual_registry()`、`resolve_outbox_dir()`。
- 配置/路径兼容：`CAMPAIGNS_DIR`、`safe_segment()`、`normalize_story_config()`、`summarize_model_config()`、`list_payload()`。

`services/assets.py` 仍通过 `_web_server()` 读取：

- 合理过渡：`CAMPAIGNS_DIR`、`safe_segment()`、`MemoryStore`，用于保持现有 campaign asset 路径和默认 campaign 解析兼容。
- 下一轮建议迁出：`migrateAssetKinds()`、`build_actor_identity_context()`、`normalize_frontend_gallery_kind()`、`is_attribute_star_asset()`、`is_valid_cached_map_asset()`。

`services/writeback_review.py` 仍通过 `_web_server()` 读取：

- 合理过渡：`resolve_outbox_dir()`、`require_outbox_campaign()`，用于保持 outbox 兼容路径和 campaign 校验。
- 下一轮建议迁出：`visual_contract_updates_from_pressure()`、`status_payload()`。

## 下一轮建议迁移顺序

1. 迁移 gallery taxonomy / frontend visual registry：这是 `frontend_state` 和 `assets` 共同依赖 `web_server.py` 的主要原因。
2. 迁移 module payload 业务：把 `module_payload_response()` 和各模块 payload helper 拆到独立 service，降低 `/api/module/*` 后续膨胀风险。
3. 迁移 campaign profile/status 管理业务：把 create/update/delete payload 逻辑从 HTTP 层剥离，保留路由和 job 调度入口。

## 不做的事

- 本次不迁移 capability。
- 本次不改 `app.js`。
- 本次不改 Prompt。
- 本次不重构 `JobState`。
- 本次不改 API 路径。
- 本次不改前端调用协议。
