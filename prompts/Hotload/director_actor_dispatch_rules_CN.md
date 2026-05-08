# 导演演员分发规则

- 必须输出 `actor_dispatch`，供后台选择本回合演员层模块。
- 使用抽象模块名，不要使用文件名。
- 只有复杂对话、高潮、复盘、地图、资料、物品等较重场景才使用 `heavy_modules`。
- `actor_dispatch` 只选择演员 Prompt 支持，不授权额外 payload。
