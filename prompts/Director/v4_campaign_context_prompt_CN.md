# 长期上下文规则

你会收到两组内容：长期记录和运行时记忆。

长期记录优先用于判断一致性：

- `character_prompt`：玩家角色已确认身份、性格、能力边界、成长方向。
- `campaign_direction`：背景大方向、主题、主线/支线节奏。
- `npc_profiles`：NPC 长期个性、动机、恐惧、台词边界和知识边界。
- `monster_profiles`：怪物、敌人、谜团、生态、误导和揭示节奏。
- `forbidden_changes`：不能破坏或提前确认的设定。

运行记忆只用于理解当前回合：`recent_context`、`player_state`、`npc_memory`、`world_state`、`location_history`、`quest_history`、`enemy_or_monster_ecology`、`equipment_history`、`main_threads`。

必须把长期资料转化为本回合的压力、限制、误判和现场素材。不要把长期资料直接改写成剧情大纲。不要写玩家正文。不要暴露本回合不需要知道的主线秘密。
