# 资产输出规则

普通可视资产候选只允许包含这些字段：

- `kind`
- `id`
- `title`
- `detail`
- `gallery_category`
- `asset_use`
- `actor_role`
- `certainty`
- `display_zone`
- `cache_policy`
- `asset_subtype`
- `asset_tags`
- `asset_tags` 只能是字符串数组，例如 `"asset_tags": ["线索", "地图关联"]`。不得输出带 `id`、`label`、`icon` 或说明文字的对象标签。
- `character_targets`
- `map_canvas`
- `map_route`

不得输出 `asset_kind`、`source_type`、`path`、`url`、manifest key、运行时缓存 key 或文件系统路径。后台只从 `asset_use` 派生 `asset_kind`，并只在资产登记完成时写入 `source_type`。

`gallery_category` 只控制前端筛选入口。它必须是核心分类 `prop`、`item`、`character`、`map`、`cg`，或团内已登记的自定义资料夹分类。不得输出 `gallery_category=scene`。

`asset_use` 控制后台处理方式。普通资产只能使用 `portrait`、`item`、`prop` 或 `map`。场景、地点、区域、路线、地图类视觉资料统一使用 `gallery_category=map` 与 `asset_use=map`。

`actor_role` 只控制剧情身份。不得用它决定前端筛选分类。

CG 不属于普通 asset_normalizer 负载。CG 请求走 image generation request / image_job 链路，图片成功生成后再登记为 `gallery_category=cg`、`asset_use=cg`、`asset_kind=cg_image`。

普通资产缺少任一必填字段时，后台返回 `asset_contract_error`。不得通过改分类、降级到 review、脑补 actor role 或静默丢弃来绕过错误。

Actor 文本层不得新增资产定义。Actor 图像层可以承接生图指令，但普通资产候选属于导演/后台意图和后台登记链路。
