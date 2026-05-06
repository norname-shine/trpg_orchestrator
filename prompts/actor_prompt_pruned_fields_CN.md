# 演员层 Prompt 被裁字段归档

本文档记录从演员层 Prompt 中主动移除的字段。演员层只负责剧情正文和结构化写回；后台与导演层调度细节不进入演员 Prompt。

## capability_plan

- `prompt_modules`：本地模块选择调试信息。归后台；只适合管理调试页恢复查看。
- `memory_refs`：本地记忆选择调试信息。归后台；只适合管理调试页恢复查看。
- `warnings`：Prompt / 模块加载诊断。归后台；对正文写作无用。
- `loaded_capabilities`：原始路由能力列表。演员层改收精简后的可见能力子集。
- `missing_capabilities`：payload 缺口诊断。归后台 / 导演层。
- `output_requests`：导演到后台的触发路由。演员层只接收结果层面的正文 / 写回要求。

## pressure_pack

- `output_requests`：故事进度、地图、视觉资产、资料库、物品、档案等后台更新触发器。演员层只接收必要叙事与写回目标。
- `payloads`：结构化后台 payload 容器。演员层只接收筛选后的可见摘要。
- `map_canvas`：Canvas 绘制坐标、点、路线、危险和渲染提示。归后台地图渲染器。
- `map_route`：后台 / 玩家地图拓扑。必要时演员层只接收简短地点 / 路线摘要。
- `story_topology`：后台故事图支持。演员层只接收当前 progress control。
- `visual_assets`：图像与资料库生成请求。归后台 / 导演资产流水线。
- `image_prompt`、`positive_prompt`、`negative_prompt`、`canvas_spec`、`quality`、`style_preset`：生图提示字段。演员正文不应消耗上下文处理渲染指令。
- `trigger_image_generation`：后台生图回合触发器。演员层不调度生图。
- `public_think`：玩家等待时的 UI 进度文案，不是剧情正文素材。
- `protocol_warnings`、`warnings`、`debug`、`audit`、`diagnostics`：校验与调试材料。归后台 / 审计。
- 空字符串、空数组、空对象和 null：无演员层业务含义，递归移除。

## memory

- `hidden_truth`、`hidden_motive`、`future_nodes`、`forbidden_reveals`、`director_notes` 等隐藏或未来规划字段：归导演 / 审计。
- cache、manifest、asset metadata、本地文件路径：后台资产生命周期数据，不是正文指令。
- 重复字符串和重复 JSON 片段：去重以节省上下文，同时保留一份语义副本。

## payloads

- `canvas_style`、`icon_rules`、`coordinates`、`points`、`edges`、`routes`、`legend`、`ascii`：本地可视化细节。
- `source_object_id`、`asset_key`、`cached_url`、`created_at`、`generator_version`：本地资产身份 / 缓存字段。
- 后台请求容器下的 `mode`、`trigger`、`reason`：路由元数据。演员层接收可见效果，不接收调度元数据。
