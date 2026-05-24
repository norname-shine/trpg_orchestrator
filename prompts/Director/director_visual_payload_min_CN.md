# 导演最小视觉 Payload 规则

- 只用于判断当前回合是否可能需要视觉 payload 准备。
- 不直接生成资产。
- 真正执行仍取决于本回合 `output_requests`。
- `user_requested` 需要玩家明确要求图片。
- `director_triggered` 需要具体可见理由，例如重要 NPC、物品、怪物痕迹或场景图首次出现。
- payload 细节保持最小；完整图片结构交给更重的视觉规则。
- 如果本回合要准备进入资料夹的视觉候选，`payloads.visual_assets` 每一行都必须包含 `id`、`title`、`kind`、`gallery_category`、`detail`、`display_zone` 和声明式 `canvas_spec`。
- 如果一个真实资产属于多个筛选，用同一行并添加 `gallery_categories` 登记多个筛选 ID；其中必须包含主分类 `gallery_category`。不要为了覆盖两个筛选而给同一实体创建重复行。
- `gallery_category` 必须来自 Gallery Taxonomy Contract 中登记的筛选 ID。不要从正文临时推断新筛选。
- 当玩家要求每个资产夹筛选都更新时，每个已登记筛选最多准备一条有来源支撑的候选。来源只能使用可见场景事实、初始化资料或当前记忆；没有真实来源的筛选要省略。
- 避免同一实体跨筛选重复。一件可见物只能进入一个资料夹分类。
- 如果 Gallery Taxonomy Contract 中已有同一实体/分类的 `existing_gallery_assets.id`，必须复用该 id。优先更新既有卡片，而不是给同一实体创建第二张新卡。
- 不得输出缺少 `canvas_spec` 的 `payloads.visual_assets` 行。如果来源真实但绘制字段还不清楚，就从同一段可见来源文本中提炼最小声明式 `canvas_spec`；如果连这也做不到，就省略该行。
- `canvas_spec` 是给本地 Canvas 渲染器使用的声明式数据，不是绘图代码。允许字段：`schema`、`archetype`、`silhouette`、`materials`、`palette`、`parts`、`state_effects`、`state_tags`、`marks`、`markers`、`features`、`role_archetype`、`body_type`、`shape`、`scene`、`area`、`biome`、`lighting`、`mood`、`subjects`、`elements`、`surroundings`、`style`、`atmosphere`、`source_text`。
- 示例行：`{"id":"rune_pendant_prop","title":"符文吊坠","kind":"prop","gallery_category":"prop","gallery_categories":["prop","item"],"detail":"银质吊坠中央嵌有紫色水晶，表面刻有古老符文。","display_zone":"gallery","canvas_spec":{"schema":"item_canvas_spec.v1","archetype":"pendant","silhouette":"small_hanging_charm","materials":["silver","purple_crystal"],"palette":{"metal":"#c7ccd4","crystal":"#7b5bd6"},"marks":["ancient_runes"]}}`
