# 导演前瞻规则

- `orchestration_forecast` 是 backend-only 字段。
- 它只影响下一回合热加载。
- 不得泄露给演员层。
- 它不授权资产生成、地图更新或 payload 执行。
- 必须包含过期时间窗口。
