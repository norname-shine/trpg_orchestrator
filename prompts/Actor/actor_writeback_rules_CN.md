# 演员层证据写回规则

只有当场景简报列出对应证据区域，并且玩家可见正文中有明确证据时，才写入证据候选。演员层不做最终持久化、物品、档案、角色卡、骰子、地图、视觉或剧情节点裁决。

- 剧情进度写回只记录本回合正文中已经可见发生的进展证据；节点完成或跳转由后续校验决定。
- 物品、角色卡、档案条目都是证据候选，不是最终接受的更新。
- 骰子/检定处理在被允许时可以请求或报告玩家可见的 `system_check`，但不得编造随机结果，也不得自行持久化长期后果。
- 演员层输出不得创建地图、视觉、图库、Canvas 或渲染器数据。
- 不得包含调度字段、本地路由说明、管理诊断或空占位对象。

每个长期写回条目和 optional_writebacks 条目都应包含：

```json
{
  "memory_type": "confirmed_fact | observed_clue | npc_claim | short_term_scene | progress_update",
  "certainty": "confirmed | likely | uncertain",
  "source": "actor",
  "ttl": "scene | session | permanent",
  "value": ""
}
```

类型必须保守使用：

- `confirmed_fact`：已由玩家可见正文或已批准跑团记忆确认的事实。
- `observed_clue`：玩家观察到的线索；线索不等于隐藏真相。
- `npc_claim`：NPC 的说法或认知；只代表该 NPC 所知，不代表世界真相。
- `short_term_scene`：当前场景临时状态、气氛、位置压力或临场描写。
- `progress_update`：主线、节点或 beat 的可见进度证据。

不确定时使用 `observed_clue`、`npc_claim` 或 `short_term_scene`，不要使用 `confirmed_fact`。
