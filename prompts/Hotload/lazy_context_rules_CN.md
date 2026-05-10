# 懒加载上下文规则

本项目使用 capability-based prompt 和 memory loading。

- 模型只能使用本轮提供的上下文。
- 缺失模块不代表允许编造隐藏事实。
- 地图、媒体用 `visual_assets`、档案 patch、角色卡、骰子请求和 Canvas jobs 等重 payload，只能在 `output_requests` 授权时出现。
- 资料夹和物品栏业务变化不得使用 `output_requests` 或 `payloads`；只能写入 `state_writeback.gallery_assets` 与 `state_writeback.inventory_items`。
- 如果 capability 未加载，不要伪造它的详细 payload。
- ChatGPT 只能通过 `capability_escalation_request` 请求未来回合升级 capability。
- 任何模型不得在同一回合触发递归加载。
- V4 可以通过 `output_requests` 请求 capability，但本地后端决定本轮是否可用。
- ChatGPT 不得覆盖 V4 的 `output_requests`。
- ChatGPT 不得输出未授权的 `optional_writebacks`。
- 后台可以在 capability 缺失时 fallback、defer 或 warning。
