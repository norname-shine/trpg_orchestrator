# Canvas 资产生成规则

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
