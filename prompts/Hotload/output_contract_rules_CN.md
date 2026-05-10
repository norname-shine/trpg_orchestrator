# 输出契约规则

pressure pack 使用 `output_requests` 作为重 payload 的授权来源，但资料夹和物品栏业务写入不再走旧 payload 协议。

- `output_requests` 是轻量控制声明。
- `payloads` 是重结构化输出。
- 如果 `output_requests.<module>.mode` 为 `none`，该 module 的 payload 不得出现。
- 如果 `output_requests.<module>.mode` 为 `keep_previous`，不应生成新的 payload。
- 禁止空占位 payload。
- Payload 必须有具体触发原因。
- `output_requests.gallery`、`output_requests.inventory`、`payloads.gallery_updates`、`payloads.inventory_updates` 已移除。
- 资料夹业务变化只能写入 `state_writeback.gallery_assets`。
- 物品栏业务变化只能写入 `state_writeback.inventory_items`。
- `visual_assets` 只服务媒体生成。它可以请求图片或 Canvas 工作，但不等于资料夹入库。
- 已有资料夹资产必须使用稳定 `asset.id`；已有物品必须使用稳定 `item_id`。
- 后台不会按标题、类型或描述相似度合并资料夹资产或物品。
- 剩余 optional modules 的 `state_writeback.optional_writebacks` 必须遵守 `output_requests`。
- 故事进度写回是轻量内容，可在 `story_progress` mode 为 `update` 时出现。
- 故事进度百分比只由后台计算。
- AI 不得输出 overall_progress、chapter_progress、node_progress、percent 或 percentage。
- 所有 UI 标签、chip、badge 类字段只能是 `string[]`。示例：`"conditions": ["失忆"]`、`"badges": ["主角", "医疗相关"]`、`"asset_tags": ["线索"]`；不得输出带 `id`、`label`、`icon` 或说明元数据的对象标签。
