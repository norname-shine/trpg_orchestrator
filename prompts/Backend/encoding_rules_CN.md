# Encoding Rules

本仓库在 Windows 环境运行，历史 Python 文件可能是 GBK，前端、Prompt、JSON、Markdown、outbox 和 campaign 数据必须按 UTF-8 管理。编码规则是系统稳定性规则，不是风格建议。

## 一、核心原则

- 玩家正文、ChatGPT 输入、ChatGPT 回复、状态写回、JSON 记忆、前端展示文本不得出现乱码。
- 运行时数据一律按 UTF-8 写入。
- 读取旧文件时可以自动识别 UTF-8 / UTF-8-BOM / GBK，但解析前必须检查 mojibake。
- 不允许用 `errors = "replace"` / `errors = 'replace'` 等替换解码方式静默吞掉乱码后继续解析、写回或展示。
- 一旦运行时文本仍像乱码，必须报错阻断，让开发者修复源文件或编码边界。

## 二、读取规则

- 普通文本读取优先使用 `read_text_auto(path)`。
- 运行时关键文本读取必须使用 `read_runtime_text(path)`，包括：
  - `chatgpt_input.md`
  - `chatgpt_raw_output.md`
  - `chatgpt_clean_output.md`
  - `last_player_action.txt`
  - outbox 快照
  - 后台解析入口
  - 导出文本内容
- JSON 读取必须使用 `read_json(path)`，由共享 helper 统一走自动识别。
- 禁止新增带替换解码的直接 `Path.read_text` 调用。
- 禁止在解析 ChatGPT 输出、状态写回、正文块、前端状态时使用宽松替换模式。

## 三、写入规则

- 新生成的 Prompt、JSON、Markdown、HTML、CSS、JS、outbox 文本都必须 UTF-8。
- 普通文本写入使用 `write_text_utf8(path, text)`。
- JSON 写入使用 `write_json(path, data)`，必须 `ensure_ascii=False`。
- 写入前应检查文本是否已经是 mojibake；如果是，停止写入。
- 不要把终端 mojibake 复制回文件。
- 不要因为 PowerShell 显示乱码就改动文件内容；先确认文件真实编码。

## 四、后台解析规则

- ChatGPT 原文进入解析前必须走 `read_runtime_text`。
- `parse_chatgpt_output` 只处理已确认非乱码的 Unicode 字符串。
- 后台 API 返回 JSON 时必须 `ensure_ascii=False` 并声明 `charset=utf-8`。
- 如果 outbox 与当前 campaign 不一致或编码异常，前端应显示阻断提示，不写入长期记忆。

## 五、前端规则

- Web server 必须以 UTF-8 发送 HTML、CSS、JS、JSON、Markdown。
- HTML 页面必须保留 `<meta charset="utf-8">`。
- 前端只能展示后端返回的已解码 Unicode 文本，不做 GBK/UTF-8 猜测。
- 如果浏览器显示乱码，修复源文件编码或后台响应编码，不要在前端硬替换字符。

## 六、历史 GBK Python 文件

- 旧 Python 文件可暂时保留 GBK 编码。
- 修改 GBK Python 文件时，不要随手加入大量中文字符串。
- 如果需要系统性修复编码，单独做一次“文件编码规范化”任务，统一转 UTF-8，并跑完整验证。

## 七、验证

- 编码相关改动后至少运行：
  - `python -m py_compile trpg_orchestrator/src/trpg_orchestrator/encoding_utils.py trpg_orchestrator/src/trpg_orchestrator/cli.py trpg_orchestrator/src/trpg_orchestrator/web_server.py`
  - `node --check trpg_orchestrator/web/app.js`
- 至少检查一个 campaign-scoped outbox 文件和全局 outbox 镜像文件，确认中文不是 mojibake。
