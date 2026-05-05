# Expected Shape: Director Turn

- Output is strict JSON only.
- `public_think` is safe and does not reveal secrets.
- `progress_control.current_node_id` remains `c1_n1_opening`.
- `progress_control.legal_next_nodes` only contains authorized next nodes.
- Inventory update may include:
  - `家传短剑` as `short_sword`
  - `油灯` as `oil_lantern`
  - `三角吊坠` as `pendant`
- `暂无伤势或装备损坏` must not become an item.
- No empty `map_canvas`, placeholder visual asset, or default map payload.
