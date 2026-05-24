# TRPG Orchestrator

本项目是一个本地文字 TRPG 双模型自动化系统骨架。

核心分工：

- DeepSeek V4：长期记忆导演，生成现场压力包，审核状态回写。
- ChatGPT 网页客户端：正文主持，只负责沉浸式正文、选择点和状态回写。
- 本地 Codex/CLI：读取本地 JSON 记忆、调用 V4、生成 ChatGPT 输入、驱动网页、质检、备份、写回和记录日志。

项目不使用 OpenAI API。ChatGPT 正文输出通过已登录的 ChatGPT 网页固定对话完成。

## 功能

- 多跑团管理和 active campaign 切换
- 本地 JSON 长期记忆
- V4 严格 JSON 压力包
- ChatGPT 网页 Playwright 自动化
- AI 味机械检查和重写流程
- V4 状态回写审核
- 记忆备份与完整日志
- 本地 Web 控制台
- 浅色跑团控制台前端，支持行动输入、输出查看、跑团选择、导出

## 安全边界

公开仓库不会包含：

- `.env`
- DeepSeek API key
- ChatGPT 浏览器登录 profile
- `node_modules/`
- `outbox/`
- 真实跑团数据、日志和备份

只保留 `campaigns/example_campaign` 作为公开模板。

## 初始化

```powershell
cd H:\COdex\trpg_orchestrator
python -m pip install -e .
npm install
copy .env.example .env
copy campaigns\campaign_registry.example.json campaigns\campaign_registry.json
```

编辑 `.env`：

```text
DEEPSEEK_API_KEY=你的 DeepSeek key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
TRPG_CHATGPT_AUTOMATION=playwright
TRPG_BROWSER_USER_DATA_DIR=H:\COdex\trpg_orchestrator\.browser-profile
TRPG_BROWSER_CHANNEL=chrome
```

如果想改用 browser-harness 的截图/坐标点击链路，可把自动化模式改成：

```text
TRPG_CHATGPT_AUTOMATION=browser_harness
TRPG_BROWSER_USER_DATA_DIR=H:\COdex\trpg_orchestrator\.browser-profile
```

## CLI 用法

```powershell
$env:PYTHONPATH='H:\COdex\trpg_orchestrator\src'
$env:PYTHONIOENCODING='utf-8'
python -m trpg_orchestrator.cli status
python -m trpg_orchestrator.cli validate-memory
python -m trpg_orchestrator.cli prepare --action "玩家行动"
python -m trpg_orchestrator.cli send
python -m trpg_orchestrator.cli ingest
python -m trpg_orchestrator.cli run-turn --action "玩家行动" --auto-rewrite --rewrite-attempts 2
```

## Web 控制台

双击：

```text
启动TRPG控制台.bat
```

或手动启动：

```powershell
$env:PYTHONPATH='H:\COdex\trpg_orchestrator\src'
python -m trpg_orchestrator.web_server
```

打开：

```text
http://127.0.0.1:8787/
```

## 浏览器自动化限制

系统只会操作已登录的 ChatGPT Project 固定对话，并且只做：

- 粘贴
- 发送
- 等待回复
- 复制最新回复

如果遇到登录、验证码、支付、订阅、账号设置、安全验证或隐私设置，应停止并由用户处理。

## 验证

```powershell
python -m compileall .\src
python -m trpg_orchestrator.cli validate-memory
node --check .\web\app.js
```
