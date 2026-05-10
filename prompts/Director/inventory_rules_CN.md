# 物品栏规则

物品栏业务变化只能写入 `state_writeback.inventory_items`。

- 没有场景证据时，不得发明物品获得、丢失或装备变化。
- 装备变化必须基于事实；证据不确定时，应保持可逆表述。
- 被检查但尚未确认的物品，不得当作完全鉴定完成的物品。
- 不得输出 `output_requests.inventory`、`payloads.inventory_updates` 或物品栏相关 `optional_writebacks`。
- 新物品记录必须来自 `state_writeback.inventory_items`；不要从纯正文、资源文本、伤势文本或背景物件描述中创建正式物品。
- 已有物品必须使用稳定 `item_id`；后台不会按标题、类型或描述相似度猜测同一物品。
- 每个物品更新必须是完整 inventory item payload，至少包含 `item_id` 和 `title`。
