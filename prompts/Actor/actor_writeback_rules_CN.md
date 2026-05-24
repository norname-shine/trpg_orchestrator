# 演员层证据写回规则

只写玩家可见的证据候选。`state_writeback` 之后还会被审查；但凡本回合产生以后可能复查的可见事实，演员层必须负责结构化写出。

- `state_writeback` 必须始终包含 `short_term_state`、`long_term_memory`、`new_open_threads`、`closed_threads`、`gallery_assets`、`inventory_items`。
- 没有新开线程时，输出 `new_open_threads: []`。
- 没有关闭线程时，输出 `closed_threads: []`。
- 始终输出 `gallery_assets: []`；演员层正文不持久化资产夹卡片。
- 只有两个必填容器允许为空对象：`short_term_state: {}` 与 `long_term_memory: {}`。
- `long_term_memory` 只能记录本回合正文中已经可见的事实或变化。
- 剧情进度写回只能记录本回合可见进展证据；节点完成或跳转由后续校验决定。
- 不要写空占位对象。
- 不要包含调度字段、本地路由说明、管理诊断、forecast 数据、隐藏成因或未来节点。

## 资料夹边界

演员层只服务于玩家可见正文。演员层不负责下发、复制、改名、分类或持久化资产夹卡片。

- 正常演员输出中，`state_writeback.gallery_assets` 保持 `[]`。
- 地图、CG、Canvas 与资产夹持久化由导演层 / 后端单独处理。
- 不要从正文、选择项、地图文本、物品观察、NPC 对话或导演 payload 摘要中生成资料夹卡片。
- 如果某个可见事实未来需要资产卡，但导演层没有提供 payload，只能写入正文或短期状态证据，不要编造 gallery 行。
- 物品状态、鉴定、损耗、携带关系或库存归属变化只写入 `state_writeback.inventory_items`。

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
    "gallery_assets": [],
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
