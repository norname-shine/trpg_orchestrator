# 导演最小地图 Payload 规则

- 只用于判断当前回合是否可能需要地图 payload 准备。
- 除非本回合 `output_requests.map` 授权，否则不要更新地图。
- 路线和地图判断必须基于可见移动或明确请求。
- `user_requested` 需要玩家明确要求地图或路线。
- `director_triggered` 需要可见地点、路线、危险、边界或通行状态变化。
- payload 细节保持最小；完整地图绘制规则交给更重的地图规则。
