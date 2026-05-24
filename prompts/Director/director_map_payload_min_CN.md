# 导演最小地图 Payload 规则

- 只用于判断当前回合是否可能需要地图 payload 准备。
- 除非本回合 `output_requests.map` 授权，否则不要更新地图。
- 路线和地图判断必须基于可见移动或明确请求。
- `user_requested` 需要玩家明确要求地图或路线。
- `director_triggered` 需要可见地点、路线、危险、边界或通行状态变化。
- payload 细节保持最小；完整地图绘制规则交给更重的地图规则。
- 如果 `map.mode` 是 `update_canvas`，`payloads.map_canvas` 必须包含 `render_token: "map_canvas.v1"` 和真实绘图数据：`ascii` 必须是字符串数组，`points` 必须是数组；可选 `routes`/`hazards` 数组、`legend` 对象、`canvas` 对象。
- 优先使用有来源的 `initial_map_canvas` 和当前可见场景锚点。不要为了让地图更满而发明地理。
- `map_canvas` 由运行时渲染器消费；它不是正文描述，也不能是占位。
