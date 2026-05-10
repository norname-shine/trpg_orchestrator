# 演员层证据写回规则

只写玩家可见的证据候选。`state_writeback` 之后还会被审查；但凡本回合产生以后可能复查的可见事实，演员层必须负责结构化写出。

- `state_writeback` 必须始终包含 `short_term_state`、`long_term_memory`、`new_open_threads`、`closed_threads`。
- 没有新开线程时，输出 `new_open_threads: []`。
- 没有关闭线程时，输出 `closed_threads: []`。
- 只有两个必填容器允许为空对象：`short_term_state: {}` 与 `long_term_memory: {}`。
- `long_term_memory` 只能记录本回合正文中已经可见的事实或变化。
- 剧情进度写回只能记录本回合可见进展证据；节点完成或跳转由后续校验决定。
- 不要写空占位对象。
- 不要包含调度字段、本地路由说明、管理诊断、forecast 数据、隐藏成因或未来节点。

## 全局资料夹写回

当本回合产生或更新玩家已知、可展示、可复查的资料时，使用 `state_writeback.gallery_assets`。包括但不限于：线索、地图笔记、地点记录、角色记录、物品记录、文档、符号记录、怪物/敌人观察、环境异常。

- 每个 `gallery_assets` 条目必须包含非空字符串 `id`、`type`、`title`。
- 推荐字段：`category`、`display_zone`、`detail`、`source`、`payload`。
- 更新已有资料时，必须使用稳定 `asset.id` 并返回完整 asset。运行时按 id 整条替换，不做浅合并，也不按标题猜。
- 不得使用已移除的资料夹传输字段、已移除的资料夹请求模块、dossier 更新传输或纯正文 dossier 文本作为资料夹事实源。
- `visual_assets` 只代表媒体、生图或 Canvas 请求，不等于资料夹入库。

## 全局物品写回

当本回合产生物品新增、物品状态变化、物品派生时，使用 `state_writeback.inventory_items`。

- 每个 `inventory_items` 条目必须包含非空字符串 `item_id`、`title`。
- 派生物品必须包含 `source_item_id`。
- 更新已有物品时使用稳定 `item_id`。运行时不会按标题或描述相似度合并。
- 不得使用已移除的物品传输字段或已移除的物品请求模块。

必需结构示例：

```json
{
  "state_writeback": {
    "short_term_state": {},
    "long_term_memory": {},
    "new_open_threads": [],
    "closed_threads": [],
    "gallery_assets": [
      {
        "id": "stable_visible_fact_id",
        "type": "clue",
        "title": "可见线索标题",
        "detail": "玩家本回合观察、阅读或确认到的内容。"
      }
    ],
    "inventory_items": [
      {
        "item_id": "stable_item_id",
        "title": "物品标题",
        "state": {
          "status": "已观察到的状态"
        }
      }
    ]
  }
}
```

TODO：记忆语义类型属于后续 memory-semantics 分支，不在本 prompt-dispatch 分支实现。
