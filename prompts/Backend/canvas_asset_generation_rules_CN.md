# Canvas 资产生成规则

## 同步补充：玩家与伙伴头像

- 玩家头像规格必须高于普通 NPC，并作为主角色稳定识别标识。
- 伙伴 / 副玩家头像必须与 NPC 头像分开缓存，不得进入 NPC 栏或资料夹。
- 伙伴绘制前必须先从当前团记忆、伙伴原始设定、性格、物种 / 形态、装备与世界风格解析开放式 `visual_profile`。
- `companion_type_raw` 是开放字符串，必须保留原文；它不是白名单，不是资料夹分类，也不能把未知伙伴降级成 NPC。
- `companion_type_preset` 只用于常见提示的视觉增强，例如 palico、servant、familiar、construct、vehicle；未命中 preset 时必须生成 custom 伙伴 profile，不得复用玩家或 NPC 模板。
- 伙伴 Canvas metadata 必须包含 `runtime_role: companion`、`gallery_category: hidden`、`visible_in_gallery: false`、`not_in_gallery_filters: true`、`render_tier: companion`、`companion_type_raw`、`companion_type_preset` 和 `visual_profile`。
- 如果 `visual_profile.certainty` 不是 `confirmed`，头像只是 UI 标识，不得把未确认外观写成长期事实。

## 同步补充：gallery_taxonomy 准入

- Canvas 资产是否进入资料夹，必须先通过当前团 `gallery_taxonomy` 白名单。
- `gallery_taxonomy.core_categories` 是系统稳定分类，固定为 `prop`、`item`、`character`、`map`、`cg`。
- `gallery_taxonomy.campaign_categories` 是导演初始化下发的当前团扩展分类，数量限制为 0-3 个。
- `all` 只是前端聚合筛选，不是资料夹分类 ID。
- `companion` 不是资料夹分类。当前玩家与当前绑定伙伴 / 副玩家默认 `gallery_category: hidden`。
- 未在 taxonomy 中注册的分类不得只因为 PNG 存在就自动创建筛选或资料卡。

本规则说明本地前端如何生成视觉资产。它是 Codex 与 Web 控制台的运行时规则，不是要求 ChatGPT 直接生成图片的规则。

## 总边界

- Canvas 资产由本地前端生成。
- 除非用户明确要求生图，ChatGPT 不应生成图片提示词。
- 视觉资产来自已确认的本地记忆、当前场景状态、V4 压力包和当前团可见记录。
- 不得发明未确认的角色外观、怪物全貌、地图地点、路线终点、装备归属或物品事实。
- 如果来源不确定，资产应标记为线索、痕迹、未知生态或当前场景占位。

## 缓存规则

- 所有生成资产必须通过 `/api/asset` 缓存。
- 生成图像只保存为 PNG data URL。
- 缓存 key 必须基于 campaign id、资产类型、对象 id 和 generator version。
- 绘制规则变化并需要替换旧图时，递增 `ASSET_GENERATOR_VERSION`。
- 普通轮询时，如果 campaign id、object id 和 generator version 没变化，不要重复重绘或覆盖同一张可见地图。
- 缓存路径：
  - 地图：`campaigns/<campaign_id>/assets/maps/`
  - 头像：`campaigns/<campaign_id>/assets/portraits/`
  - 物品和生态线索：`campaigns/<campaign_id>/assets/items/`

## 区域地图规则

- 左侧区域地图必须显示为缓存 PNG 图片。
- 前端可以使用隐藏 Canvas 作为 PNG 生成来源，但可见元素必须是图片。
- 区域地图使用 16:9 比例。
- 不向用户暴露手动重绘或刷新地图按钮。
- 地图应按当前 campaign / location / generator version 生成一次，然后从缓存加载。
- 地图标签在小窗口里必须可读，源 PNG 的文字应比普通 UI 字更大。
- 路线节点和标签必须留在图像边界内。
- 优先绘制可读路线图，而不是完全写实地形图。
- 优先使用已确认场景和地点数据。如果缺少路线数据，只能推断通用锚点，例如起点、当前场景、远端压力点。
- 如果场景包含痕迹、泥、药瓶、车损、迁徙、怪物迹象或生态压力，应画成线索标记，不要画成已确认怪物事实。

## 资料夹地图缩略图

- 资料夹地图缩略图可以复用同一地图生成器，但标签要更紧凑。
- 缩略图文字要可读，不能溢出卡片。
- 缩略图也必须缓存为 PNG。

## NPC 头像规则

- NPC 头像必须本地生成并缓存。
- NPC 头像使用稳定姓名或 id 作为 seed。
- NPC 资料夹必须排除主玩家和伙伴 / 副玩家。主玩家只使用 `portrait` 资产，伙伴使用 `companion` 或 `companion_portrait` 资产。
- 伙伴 / 副玩家绘制由 `archetype`、`species` 或 `kind` 决定，例如怪猎团 `palico`，Fate 团 `servant`，默认使用通用 companion。
- NPC 头像必须有明显差异，至少变化发型、头饰、胡须或嘴型、衣服颜色、强调色、背景色中的几项。
- 不要只用同一张脸改颜色。
- 未确认外观不能被固定成正史，头像只是界面标识，除非记忆明确确认外观。
- 玩家和 NPC 消息块应复用稳定 `avatar_key`，保持头像一致。

## 正式生图头像覆盖规则

- Canvas 首次头像只是默认占位和兜底，不是永久形象来源。
- 当正式生图成品包含已存在的玩家、NPC、伙伴、从者、怪物或关键角色时，优先从成品图中自动识别并截取对应角色头像。
- 截取结果必须按资产类型写入各自缓存：主玩家写入 `portrait`，伙伴/从者写入 `companion` 或 `companion_portrait`，NPC 写入 `npc_portrait`，怪物写入怪物头像或资料夹怪物资产。
- 多角色同框时，必须尝试分别匹配每个可识别角色，不能只把整张大图当作唯一资料夹图。
- 成功截取并匹配的角色头像应覆盖旧 Canvas 头像；未能可靠识别的角色继续保留原头像，不做错误覆盖。
- 覆盖头像时同步更新该角色专属配置里的视觉基准：脸型、五官风格、发型、服饰调性、主色、画风气质、明显识别物和禁止漂移点。
- 后续为该角色生成新头像、立绘、半身像或全身像时，必须读取该视觉基准，保持同一套长相和风味。
- 本规则对所有团通用，不得按 Fate、怪猎、COC、DND、废土或原创团写死分支；只能通过角色类型、资产类型和 actor_id / avatar_key 匹配。

## 玩家与伙伴头像

- 玩家头像规格应高于普通 NPC，能作为主角色识别。
- 伙伴头像与 NPC 头像分开缓存，不能进入 NPC 栏。
- 怪猎团伙伴是艾露猫时，必须画出猫耳、内耳、猫鼻、胡须、护目镜或小披肩等可识别元素。
- Fate 团伙伴 / 副玩家可能是从者，应使用 servant 视觉强调，而不是艾露猫规则。

## 物品语义与绘制

- 新物品第一次进入前台可见列表时，必须先做语义分析，再选择 Canvas 绘制分支。
- 语义分析先识别物理对象，再识别状态。比如“手机彻底无信号”应识别为手机设备处于无信号状态，不是通用文档，也不是名为“无信号”的物品。
- 同一物品的不同状态不生成不同卡片。更新详情和 metadata 即可，例如井匣升温、发光的井匣仍是井匣。
- 怪猎团“骨斩斧”应识别为 `switch_axe`。
- 怪猎团“旧泥甲碎片”应识别为 `mud_armor_fragment`。
- Fate 团“井匣”应识别为 `sealed_relic_box`。
- 每个物品尽量生成独立 PNG 资产，这不是高成本行为。

## Manifest 元数据

- manifest 应保留 key、kind、path、seed、asset_seed、generator_version 和 metadata。
- metadata 应记录 title、detail、type、source、object_id、visual_prompt 和 certainty。
- 删除或重建缓存只影响 PNG 和 manifest，不得修改记忆、日志、prompt 或状态写回。

## map_canvas 场景地图 Canvas 算法

- 有 `map_canvas` 时，地图生成器必须走语义地图算法；没有 `map_canvas` 时才使用 `map_route` fallback。
- 不要逐字符硬画 ASCII，不要把点阵网格、战棋坐标、图例、罗盘、说明栏、标题区画进地图 PNG。
- 生成顺序固定为：背景 -> 主地图面板 -> 房间结构/墙体/地面 -> 家具 -> 特殊区域 -> 路线/阻断 -> 点位 icon -> 标签框。
- 点阵只用于推导空间结构：房间、隔墙、通路、连续液体区域、危险区、资源点、未知点、人物点。
- 连续 `~` 必须合并为整片异常液体区域；不要逐格画波浪。
- `#` 画为厚墙体和结构边界；`.` 画为可通行地面；`+` 画为统一交互 icon；`!` 画为统一危险 icon；`?` 画为统一未知 icon。
- icon 与文字必须分离，使用 `[icon] [圆角标签框]` 的统一结构；标签不能压在图标上，不能遮挡主体结构。
- 标签框颜色按语义区分：普通物件浅米白，黑水浅蓝白，危险浅粉白，未知浅紫白，人物浅白并轻微呼应主色。
- 地图风格随团类型切换：Fate/现代都市、COC、DND、废土、怪物猎人等只改变色板和气质，不改变核心结构协议。
- 地图应像“视觉小说 / 场景记录 / 档案式地图界面”，不是恐怖战术图、写实照片、插画海报或纯字符图复刻。
- 所有生成结果必须通过 `/api/asset` 写入当前团 `assets/maps/`，manifest metadata 应保留原始 `map_canvas`，用于判断是否需要重画。


## 统一头像命名与 VCG 锁定

- 头像资产按角色只保留一套引用。NPC 资料夹卡片复用 `npc_portrait`，不再生成 `gallery_npc`。
- 文件名沿用传统头像主体结构，只在后缀追加版本标识：常规数字版本使用 `_v1`、`_v2`、...、`_v16`；正式 CG 反哺版本使用 `_VCG`。
- 示例：`npc_portrait_<asset_seed>_<actor_name>_v16.png` 与 `npc_portrait_<asset_seed>_<actor_name>_VCG.png`。
- manifest key 也遵守同一版本规则：常规版本为 `:v16`，正式 CG 反哺为 `:VCG`。
- 如果某角色已经存在 `VCG` 头像资产，自动 Canvas 头像迭代必须停止；最近的数字版本只保留为稳定保底资产。
- 正式 CG 反哺可以更新或替换 `VCG` 资产，但普通刷新不得用新的随机 Canvas 头像覆盖它。
- 本规则对主角、NPC、伙伴、从者、怪物和关键角色通用，适配所有团类型。

## 资料夹固定分类准入

- Canvas 资产是否进入资料夹，必须先通过当前团开局固定的分类 ID 白名单。
- 基础固定分类恒为 `prop`、`item`、`character`、`map`、`cg`；导演初始化只可追加 0-3 个自定义资料夹。
- NPC、怪物、BOSS、敌对首领、御主、从者、关键角色统一进入 `character`；线索/文献类物件进入 `item` 或 `prop`。
- CG 与地图/场景分离：CG 缓存在 `cg` 分类，地图和地点缩略图缓存在 `scene` 分类。
- 未定义 kind、临时视觉记录、后台系统说明、不能对应稳定实体的普通视觉资产，不得仅因为生成了 PNG 就新建资料夹卡片。
- 同一角色、物品或场景已有卡片时，新的 Canvas PNG 只能更新原卡缩略图、状态或详情，不新建重复卡。
