# Codex 本地系统架构规则

本文件是 Codex 修改本仓库代码前必须先遵守的本地规则。它约束的是跑团控制台的工程实现方式，不是单一团的剧情规则。

## 一、总原则

- 写任何代码时，不只解决眼前 bug，要先站在整个跑团系统、多团类型通用的角度构思方案。
- 代码必须可复用、可扩展、可复现。
- 跑团控制台必须兼容多种团类型：COC、DnD、Fate、怪物团、原创团，以及后续新增模组。
- 写代码前先定义通用协议、通用数据结构、通用渲染路径，再添加团类型适配。
- 所有组件、数值、UI、逻辑都不能只为某一个团写死。
- 如果某个实现看起来只适用于一个团，必须把它降级为配置、适配器、注册项或 fallback，而不是写进核心逻辑。

## 一点五、模型职责分层

- DeepSeek V4、ChatGPT、Codex 必须按独立后台职责拆分，规则按角色分层注入，不混逻辑。
- 固定跑团链路是：玩家输入 -> DeepSeek V4 导演层 -> ChatGPT 演员层 -> 后台收口 -> 前台刷新。
- DeepSeek V4 固定担任导演层，只负责宏观剧情方向、现场压力包、生图触发判定、地图更新判定、NPC 整体方向和知识边界。
- ChatGPT 固定担任演员层，只承接 V4 压力包，负责玩家可读正文、具体对白、场景细节和结构化状态写回。
- Codex 固定担任本地工程层，只负责代码、规则、接口、解析、资产生成、缓存、质检、写回和持久化。
- Codex 不参与真实跑团的导演/演员剧情链路，不替 V4 决定剧情大方向，不替 ChatGPT 写最终正文。
- V4 输出不得直接推给普通玩家前台；必须由后台转发给 ChatGPT 演员层细化后，再由后台统一解析和刷新前台。
- 生图、地图更新、剧情主线决策由 V4 判定；本地系统只执行结构化结果，ChatGPT 只负责正文落地。
- 三层规则必须分文件维护，可单独迭代和替换模型。通用契约见 `prompts/model_layer_contract_rules.md`。

## 二、统一数据协议优先

- 前端应优先消费 `/api/frontend-state` 返回的 `frontend_state`。
- 不允许新增模块继续从多个旧接口散读数据，除非是迁移期临时兼容。
- 新增前台模块必须先声明它消费的字段结构，再写 UI。
- 多团并行时，ChatGPT 输入输出、解析结果和写回审核必须优先落到 `campaigns/<campaign_id>/outbox/`，全局 `outbox/` 只能作为手动操作镜像。
- 文本读写必须遵守 `prompts/encoding_rules.md`。运行时正文、ChatGPT 输出、JSON 记忆和前端响应不得使用 `errors="replace"` 静默吞乱码。
- 后端负责把不同来源的数据归一化：
  - campaign memory
  - campaign_profile
  - V4 pressure_pack
  - ChatGPT blocks
  - state_writeback
  - asset manifest
- 前端负责展示统一结构，不负责猜测长期记忆事实。

## 三、多团类型适配

- 团类型差异必须通过配置、profile、schema、adapter 或 registry 表达。
- 不要在核心 UI 中写死 `怪猎`、`Fate`、`COC`、`DnD` 的固定字段。
- 允许使用团类型 adapter，但 adapter 必须具备默认 fallback。
- 资料夹分类、角色卡字段、检定展示、物品分类、地图标记、伙伴类型都必须可切换。
- 示例：
  - 怪物团资料夹可包含：怪物、NPC、场景、物品。
  - Fate 团资料夹可包含：从者、御主、NPC、场景、物品。
  - COC 团资料夹可包含：线索、NPC、地点、文献、异常。
  - DnD 团资料夹可包含：角色、怪物、地点、装备、任务。
- 以上只是默认配置，不是核心写死规则。

## 四、角色状态 / 叙事卡

- 角色卡必须支持两种模式：
  - strict_stats：严格对齐跑团数值。
  - narrative_status：模糊叙事状态。
- 前端不能写死生命、专注、体力、力量、敏捷等字段名。
- 三维状态、六维属性、标签、进度条都必须来自统一结构或 fallback 配置。
- 玩家头像、伙伴头像、NPC 头像必须区分资产类型：
  - 主玩家：`portrait`
  - 伙伴 / 副玩家：`companion` 或 `companion_portrait`
  - NPC：`npc_portrait` 或资料夹内 `gallery_npc`
- NPC 栏不得重复生成主玩家或伙伴头像。
- 伙伴类型不能写死为艾露猫；怪猎团可以是 palico，Fate 团可以是 servant，原创团可有 familiar、drone、spirit 等。

## 五、资产生成与隔离

- 每个跑团必须有稳定 `campaign_id` 和 `asset_seed`。
- 所有本地视觉资产 key 和文件名必须包含或派生自当前团的 `campaign_id / asset_seed`。
- 禁止跨团复用同名角色、同名物品、同名地图资产。
- Canvas 只用于隐藏生成 PNG；前台展示必须使用缓存 PNG。
- 资产保存位置：
  - `campaigns/<campaign_id>/assets/maps/`
  - `campaigns/<campaign_id>/assets/portraits/`
  - `campaigns/<campaign_id>/assets/items/`
- asset manifest 必须记录：
  - key
  - kind
  - path
  - seed
  - asset_seed
  - generator_version
  - metadata
- 修改绘制规则后必须递增 `ASSET_GENERATOR_VERSION` 或改变 key 规则。

## 六、物品语义分析

- 任何新物品、新线索、新文献、新素材、新装备第一次进入前台可视列表时，必须先做语义分析。
- 语义分析输出至少包含：
  - type
  - category
  - role
  - material
  - silhouette
  - source_text
- 前端绘制时必须根据 `visual_prompt.type` 或等价语义字段选择绘制器。
- 不得把所有物品都画成通用杂物图标。
- 每个物品应尽量生成独立 PNG 资产；这不是高成本行为。
- 示例：
  - 怪猎团「骨斩斧」应识别为 `switch_axe`。
  - 怪猎团「旧泥甲碎片」应识别为 `mud_armor_fragment`。
  - Fate 团「井匣」应识别为 `sealed_relic_box`。
  - COC 团「潮湿照片」应识别为 `document` 或 `photo_clue`。
  - DnD 团「符文短剑」应识别为 `weapon` 或更具体的 `rune_blade`。
- 新增物品类型时优先注册分析规则和绘制器，不要在多处散落 if/else。

## 七、地图与 visual_assets

- 地图数据优先使用导演层结构化输出：
  - `map_route.nodes`
  - `map_route.edges`
  - `map_route.markers`
  - `visual_assets`
- 如果没有新地图数据，前端展示上一张已缓存地图。
- 地图节点、路线、阻断、线索、危险、资源必须有可区分样式。
- V4 只提供视觉提示，不生成图片。
- 本地前端负责 Canvas 绘制、缓存 PNG、前台展示。

## 八、正文记录与后台内容

- 玩家前台保留日志、摘要、沉浸、剧情、执行日志等玩家需要的栏目。
- 导演层、写回审核、调试信息应进入管理页，不向普通玩家默认展示。
- ChatGPT blocks 是正文展示的主要来源，但必须按 campaign_id / outbox 隔离。
- 如果全局 outbox 与当前团不一致，不能污染当前团前台。
- 每次跑团回合都必须在本地保留记录：原始输入、压力包、ChatGPT 原文、解析块、写回、审核结果和最终更新。
- NPC、伙伴/副玩家、物品、线索、地图、地点、任务都必须进入本地档案或占位档案，不允许只存在于当前页面 DOM。
- 详细生命周期规则见 `prompts/campaign_data_lifecycle_rules.md`。

## 九、UI 实现原则

- 组件尺寸、字段名称、按钮组、筛选项不能为单一团写死。
- 如果一个 UI 模块依赖团类型差异，必须从 frontend_state 或配置读取。
- 常驻底部动作按钮可以有默认项，但要允许后续由团类型或导演层覆盖。
- 页面可视窗口不应因单个模块扩展被破坏，应通过面板比例、滚动、折叠状态处理。

## 十、修改前检查清单

Codex 在修改代码前应快速检查：

- 这次改动是否只服务一个团？如果是，能否变成配置或 adapter？
- 是否新增了写死字段名、写死筛选项、写死物品类型、写死伙伴类型？
- 是否继续遵守 `frontend_state` 统一协议？
- 是否按 `campaign_id / asset_seed` 隔离资产和缓存？
- 是否避免主玩家 / 伙伴 / NPC 资产串用？
- 是否需要更新本地规则文档？
- 是否需要递增 `ASSET_GENERATOR_VERSION`？
- 是否需要验证至少两个不同团类型的返回结构？

## 十一、验证要求

- 前端 JS 改动后运行：
  - `node --check trpg_orchestrator/web/app.js`
- 后端 Python 改动后运行：
  - `python -m py_compile trpg_orchestrator/src/trpg_orchestrator/web_server.py`
- 涉及多团数据时，遍历检查本地数据。
- 涉及资产时，检查 manifest 中的 `asset_seed`、key、path、metadata 是否一致。
