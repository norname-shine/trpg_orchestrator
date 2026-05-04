# 输出契约规则

pressure pack 以 `output_requests` 作为重 payload 的唯一授权来源。

- `output_requests` 是轻量控制声明。
- `payloads` 是重结构化输出。
- 如果 `output_requests.<module>.mode` 为 `none`，该 module 的 payload 不得出现。
- 如果 `output_requests.<module>.mode` 为 `keep_previous`，不应生成新的 payload。
- 禁止空占位 payload。
- payload 必须有具体触发原因。
- ChatGPT 的 `state_writeback.optional_writebacks` 必须遵守 `output_requests`。
- story progress writeback 是轻量内容，可在 `story_progress` mode 为 `update` 时出现。
- 剧情进度百分比只由后端计算。
- AI 不得输出 `overall_progress`、`chapter_progress`、`node_progress`、`percent` 或 `percentage`。
