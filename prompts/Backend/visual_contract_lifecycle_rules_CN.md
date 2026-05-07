# 视觉契约生命周期规则

`visual_contracts.json` 是绑定单个跑团的视觉解释层。

- 它不替代源记忆；源事实通过 `binding.memory_refs` 引用。
- 每个稳定 `entity_key` 保存一份契约；归并导演候选项，不整体覆盖文件。
- 字段保持可扩展。类型专属细节放入嵌套对象，例如 `visual_identity.physical`、`visual_identity.actor`、`visual_identity.spatial` 或 `render_intent.details`。
- 资产缓存记录应保存 `visual_contract_key` 和 `visual_contract_hash`。
- 当契约 hash 仍匹配时沿用缓存；只有契约或渲染器版本变化时才重建。
- 拒绝空契约、占位契约、仅调试契约或未绑定团记忆的契约。
- 本地 Canvas 和图像演员层应从同一份已保存契约派生输入。
