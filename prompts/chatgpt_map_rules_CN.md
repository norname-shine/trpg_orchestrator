# 地图规则

只有当 `output_requests.map` 明确授权时，才描述或写入地图相关结构化内容。

- 当 map mode 为 `none` 或 `keep_previous` 时，不得创建 `map_route` 或 `map_canvas`。
- 当 map mode 为 `update_route` 时，`map_route` 必须描述具体、可见的路线变化。
- 当 map mode 为 `update_canvas` 时，`map_canvas` 或 `map_route` 必须具体且非占位。
- 不得发明当前场景或 pressure pack 没有建立的地理信息。
