# 懒加载上下文规则

本项目使用基于 capability 的 prompt 与记忆加载。

- 模型只能使用本轮已提供的上下文。
- 缺少模块不是发明隐藏事实的许可。
- 地图、视觉资产、资料夹更新、物品栏 patch、档案 patch、角色卡、骰子请求、Canvas jobs 等重 payload，只能在 `output_requests` 授权时出现。
- 如果某个 capability 没有加载，不得伪造它的详细 payload。
- ChatGPT 只能通过 `capability_escalation_request` 为未来轮次请求能力升级。
- 任何模型都不得在同一轮内部触发递归加载。
- V4 可以通过 `output_requests` 请求 capability，但本地后端决定本轮是否可用。
- ChatGPT 不得覆盖 V4 的 `output_requests`。
- ChatGPT 不得输出未授权的 `optional_writebacks`。
- 当请求的 capability 缺失时，后端可以 fallback、defer 或警告。
