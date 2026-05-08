# 导演最小视觉 Payload 规则

- 只用于判断当前回合是否可能需要视觉 payload 准备。
- 不直接生成资产。
- 真正执行仍取决于本回合 `output_requests`。
- `user_requested` 需要玩家明确要求图片。
- `director_triggered` 需要具体可见理由，例如重要 NPC、物品、怪物痕迹或场景图首次出现。
- payload 细节保持最小；完整图片结构交给更重的视觉规则。
