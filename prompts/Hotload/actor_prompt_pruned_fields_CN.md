# 演员层 Prompt 被裁字段归档

本文档记录从演员层 Prompt 中主动移除的字段。演员层只负责玩家可见正文和结构化写回；后台与导演层调度细节不进入演员层 Prompt。

## 分层策略

- 演员层使用专用的上下文、写回、地图、物品、档案、骰子规则。
- 演员层只提供证据候选，不判断最终持久化或 UI/控制更新。
- 导演层或后台规则仍可包含调度、payload、路由、校验和运行时细节，但这些规则不注入演员层。
- 演员层 Prompt 标题使用“可用剧情工具”“当前剧情位置”“本回合场景简报”等可表演概念。
- `director layer`、`backend`、`V4`、原始 `Capability Plan`、原始 `Scene Control Pack` 不进入演员层输入。

## capability_plan

- `prompt_modules`：本地模块选择调试信息。归后台；只适合管理调试页查看。
- `memory_refs`：本地记忆选择调试信息。归后台；只适合管理调试页查看。
- `warnings`：Prompt 或模块加载诊断。归后台；对正文写作无用。
- `loaded_capabilities`：原始路由能力列表。演员层只接收精简后的可见能力子集。
- `missing_capabilities`：payload 缺口诊断。归后台或导演层。
- `output_requests`：导演到后台的触发路由。演员层只接收结果层面的正文和写回要求。
- `output_contract`、`frontend_refresh`、审计或控制警告：运行时编排和界面刷新细节。演员层不接收直接调度契约。

## pressure_pack

- `output_requests`：故事进度、地图、视觉资产、资料库、物品、档案等后台更新触发器。演员层只接收必要叙事与写回目标。
- `payloads`：结构化后台 payload 容器。演员层只接收筛选后的可见摘要。
- `human_readable_note`：兼容或调试备注，不是演员层指令。
- `progress_control`：原始导演授权对象。演员层只接收清理后的当前剧情位置。
- `map_canvas`：Canvas 绘制坐标、点、路线、危险和渲染提示。归后台地图渲染器。
- `map_route`：后台或玩家地图拓扑。必要时演员层只接收简短地点或路线摘要。
- `story_topology`：后台故事图支持。演员层只接收当前剧情位置。
- `visual_assets`：从演员层正文/故事回合中移除。独立的演员层生图回合可以接收 1 条已清理的生图指令，包含提示词字段和可见场景上下文。
- `image_prompt`、`positive_prompt`、`negative_prompt`、`canvas_spec`、`quality`、`style_preset`：生图提示字段。演员正文不消耗上下文处理渲染指令。
- `trigger_image_generation`：运行时生图回合触发器。演员层正文输出不调度生图；演员层生图回合只消费已经准备好的生图指令。
- `public_think`：玩家等待时的 UI 进度文案，不是剧情正文素材。
- `protocol_warnings`、`warnings`、`debug`、`audit`、`diagnostics`：校验与调试材料。归后台或审计。
- 空字符串、空数组、空对象和 null：无演员层业务含义，递归移除。

## memory

- `hidden_truth`、`hidden_motive`、`future_nodes`、`forbidden_reveals`、`director_notes` 等隐藏或未来规划字段：归导演或审计。
- cache、manifest、asset metadata、本地文件路径：后台资产生命周期数据，不是正文指令。
- 重复字符串和重复 JSON 片段：去重以节省上下文，同时保留一份语义副本。

## payloads

- `canvas_style`、`icon_rules`、`coordinates`、`points`、`edges`、`routes`、`legend`、`ascii`：本地可视化细节。
- `source_object_id`、`asset_key`、`cached_url`、`created_at`、`generator_version`：本地资产身份或缓存字段。
- 后台请求容器下的 `mode`、`trigger`、`reason`：路由元数据。演员层接收可见效果，不接收调度元数据。

## 演员层场景简报

- 原始场景控制 JSON 不展示给演员层。
- 空占位在注入 Prompt 前递归移除。
- 地图渲染、视觉资产、图库、Canvas jobs 等非正文模块不会成为演员层写回目标。
- 可允许的演员层区域会转换成普通标签，例如剧情进展证据、物品证据、角色状态证据、档案证据、骰子/检定处理。

## 演员层无裁决权清单

- 物品：演员层不判断正式获得、失去、消耗、损坏、装备状态或长期物品记录。
- 档案：演员层不判断线索、NPC、地点、文档、阵营或谜团事实是否正式入档。
- 角色卡：演员层不判断数值/属性变化、成长、永久状态、同伴卡变化、缓存覆盖或头像 metadata。
- 骰子/检定：当团规则和场景简报允许时，演员层可以请求或报告玩家可见的 `system_check`，但不得发明机制、编造随机结果或自行持久化长期后果。
- 地图/视觉/图库/Canvas：演员层不创建渲染器或资产 payload。
- 生图：演员层生图回合是有效链路，必须接收清理后的提示词字段，但不得接收原始路由元数据，也不得继续剧情或写回状态。
- 剧情进度：演员层只记录可见证据；节点完成、分支、跳过、合并或失败由后续校验决定。
