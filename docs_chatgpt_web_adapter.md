# ChatGPT Web Adapter Design

目标：通过用户已经登录的 ChatGPT 网页客户端完成正文生成，不使用 OpenAI API。

允许动作：

1. 打开或切换到 ChatGPT 页面。
2. 确认页面不是登录、验证码、支付、订阅、账号设置、安全验证、隐私设置。
3. 定位 campaign_profile 中绑定的 Project。
4. 定位绑定的固定对话。
5. 粘贴 `outbox/chatgpt_input.md`。
6. 发送。
7. 等待回复完成。
8. 如果出现回复中断，最多点击一次继续生成。
9. 复制最新一条回复，保存到 `outbox/chatgpt_raw_output.md`。

必须停止的情况：

- 未配置 project_name 或 conversation_name。
- 找不到目标 Project。
- 找不到目标固定对话。
- 页面要求登录、验证码、安全验证、支付、订阅或账号设置。
- 无法判断回复是否完成。
- 继续生成一次后仍不完整。
- 复制结果缺少必要格式标记。

当前实现：

- 默认 `TRPG_CHATGPT_AUTOMATION=manual`：`send` 只检查绑定并提示手动粘贴。
- 可选 `TRPG_CHATGPT_AUTOMATION=playwright`：调用 `scripts/chatgpt_web_send.mjs`。
- Playwright 模式必须设置 `TRPG_BROWSER_USER_DATA_DIR`，使用独立持久化浏览器 profile。
- 所有浏览器可见文本先过 `browser_safety_stop_reason`。
- 最新回复保存后立即交给 `parse_chatgpt_output` 做格式校验。

## 迁移原则

- 保留 `chatgpt_input.md`、`chatgpt_raw_output.md`、`browser_evidence.json`、解析、质检、V4 audit、writeback 路径。
- 只替换浏览器执行器，不改变下游 ingest 合同。
- 所有端口 JSON 和落盘文件使用 UTF-8；发现旧 GBK/CP936 文档时先转换，不传播乱码。

PowerShell 示例：

```powershell
$env:TRPG_CHATGPT_AUTOMATION="playwright"
$env:TRPG_BROWSER_USER_DATA_DIR="H:\COdex\trpg_orchestrator\.browser-profile"
python -m trpg_orchestrator.cli send
```
