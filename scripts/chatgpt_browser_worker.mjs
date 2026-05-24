import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { chromium } from "playwright";

const workerDir = process.env.TRPG_CHATGPT_WORKER_DIR || path.join(process.cwd(), ".runtime", "chatgpt_worker");
const tasksDir = path.join(workerDir, "tasks");
const statusPath = path.join(workerDir, "worker_status.json");
const cdpUrl = process.env.TRPG_BROWSER_CDP_URL || "http://127.0.0.1:9222";
const userDataDir = process.env.TRPG_BROWSER_USER_DATA_DIR;
const manualWaitMs = Number(process.env.TRPG_BROWSER_MANUAL_WAIT_MS || 10 * 60 * 1000);
const quickPageReadyMs = Number(process.env.TRPG_BROWSER_QUICK_PAGE_READY_MS || 15_000);
const staleTaskMs = Number(process.env.TRPG_BROWSER_STALE_TASK_MS || 2 * 60 * 1000);

const M = {
  body: "\u3010\u6b63\u6587\u3011",
  choices: "\u3010\u9009\u62e9\u70b9\u3011",
  summary: "\u3010\u56de\u5408\u6458\u8981\u3011",
  writebackBegin: "\u3010\u72b6\u6001\u56de\u5199_BEGIN\u3011",
  writebackEnd: "\u3010\u72b6\u6001\u56de\u5199_END\u3011",
};

if (!userDataDir) fail("TRPG_BROWSER_USER_DATA_DIR is required for browser worker.");

fs.mkdirSync(tasksDir, { recursive: true });
writeWorkerStatus({ running: true, started_at: new Date().toISOString(), cdp_url: cdpUrl });
setInterval(() => writeWorkerStatus({ running: true, heartbeat_at: new Date().toISOString(), cdp_url: cdpUrl }), 15_000);

let browser = await openBrowser();
let page = await chatgptPage(browser);
console.log(`TRPG browser worker ready: ${workerDir}`);

while (true) {
  const task = nextTask();
  if (!task) {
    await sleep(500);
    continue;
  }
  await handleTask(task).catch((err) => {
    writeTaskEvidence(task, { ok: false, markers_ok: false, blocked_reason: blockedReasonFromTaskOutput(task) || "browser_automation_error", error: String(err?.message || err) });
    if (isRecoverableBrowserError(err) && !task.recovered_once) {
      writeTaskStatus(task.id, { state: "running", stage: "browser_restarting", label: "Browser closed or disconnected; restarting", percent: 10, updated_at: Date.now() });
      return restartBrowserSession()
        .then(() => handleTask({ ...task, recovered_once: true }))
        .catch((retryErr) => writeTaskStatus(task.id, { state: "failed", error: String(retryErr?.message || retryErr), updated_at: Date.now() }));
    }
    writeTaskStatus(task.id, { state: "failed", error: String(err?.message || err), updated_at: Date.now() });
  });
}

async function handleTask(task) {
  page = await readyChatGPTPage(task.id);
  writeTaskStatus(task.id, { state: "running", stage: "actor_waiting", label: "准备 ChatGPT 常驻浏览器", percent: 5, updated_at: Date.now() });
  page = await ensureTaskPageReady(page, task.id);
  if (!task.capture_only) {
    writeTaskStatus(task.id, { state: "running", stage: "actor_waiting", label: "打开新聊天", percent: 12, updated_at: Date.now() });
    await openTaskConversation(page, task);
    writeTaskStatus(task.id, { state: "running", stage: "actor_waiting", label: "粘贴演员层输入", percent: 18, updated_at: Date.now() });
    const inputText = fs.readFileSync(task.input_path, "utf8");
    await fillComposer(page, inputText);
    await clickSend(page);
  }
  writeTaskStatus(task.id, { state: "running", stage: "actor_waiting", label: "等待 ChatGPT 返回", percent: 35, updated_at: Date.now() });
  const latest = task.mode === "image"
    ? await waitForImageCompletion(page, task.id, imageArtifactPath(task.output_path))
    : await waitForAssistantCompletion(page, task.id);

  if (task.mode !== "image" && !isCompleteReply(latest)) {
    fs.writeFileSync(task.output_path, latest.trim() + "\n", "utf8");
    writeTaskEvidence(task, { ok: false, markers_ok: false, blocked_reason: blockedReasonFromTaskOutput(task) || "missing_markers", error: "Latest ChatGPT reply is incomplete or missing required markers." });
    throw new Error("Latest ChatGPT reply is incomplete or missing required markers.");
  }
  fs.writeFileSync(task.output_path, latest.trim() + "\n", "utf8");
  writeTaskEvidence(task, { ok: true, markers_ok: true });
  writeTaskStatus(task.id, { state: "complete", stage: "actor_complete", label: "ChatGPT 正文已返回", percent: 70, output_chars: latest.length, updated_at: Date.now() });
}

function nextTask() {
  const files = fs.readdirSync(tasksDir).filter((name) => name.endsWith(".json") && !name.endsWith(".status.json")).sort();
  for (const file of files) {
    const full = path.join(tasksDir, file);
    const task = readJson(full);
    if (!task) continue;
    if (task.state !== "pending") {
      if (task.state !== "claimed" || !isStaleClaimedTask(task.id)) continue;
      writeTaskStatus(task.id, { state: "running", stage: "task_requeued", label: "Recovering stale claimed ChatGPT task", percent: 4, updated_at: Date.now() });
    }
    task.state = "claimed";
    fs.writeFileSync(full, JSON.stringify(task, null, 2), "utf8");
    return task;
  }
  return null;
}

function isStaleClaimedTask(id) {
  const status = readJson(path.join(tasksDir, `${id}.status.json`));
  const updatedAt = Number(status?.updated_at || 0);
  const state = String(status?.state || "");
  if (state === "complete" || state === "failed") return false;
  return !updatedAt || Date.now() - updatedAt > staleTaskMs;
}

function writeTaskStatus(id, data) {
  const payload = { task_id: id, ...data };
  fs.writeFileSync(path.join(tasksDir, `${id}.status.json`), JSON.stringify(payload, null, 2), "utf8");
}

function writeTaskEvidence(task, data) {
  const evidencePath = task.evidence_path || path.join(path.dirname(task.output_path), "browser_evidence.json");
  const payload = {
    ok: Boolean(data.ok),
    mode: task.capture_only ? "capture_only" : String(task.mode || "text"),
    campaign_id: String(task.campaign_id || ""),
    input_hash: task.capture_only ? "" : sha256File(task.input_path),
    output_hash: sha256File(task.output_path),
    markers_ok: Boolean(data.markers_ok),
    blocked_reason: String(data.blocked_reason || ""),
    error: String(data.error || ""),
  };
  fs.writeFileSync(evidencePath, JSON.stringify(payload, null, 2) + "\n", "utf8");
}

function sha256File(file) {
  if (!file || !fs.existsSync(file)) return "";
  return createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

function blockedReasonFromTaskOutput(task) {
  if (!task?.output_path || !fs.existsSync(task.output_path)) return "";
  const text = fs.readFileSync(task.output_path, "utf8").toLowerCase();
  const terms = ["log in", "sign in", "captcha", "verification", "verify your identity", "payment", "billing", "subscription", "security", "登录", "验证码", "安全验证", "支付", "订阅"];
  const found = terms.find((term) => text.includes(term.toLowerCase()));
  if (found) return `blocked browser state detected: ${found}`;
  if (!text.trim()) return "empty_output";
  return "";
}

function writeWorkerStatus(data) {
  fs.mkdirSync(workerDir, { recursive: true });
  fs.writeFileSync(statusPath, JSON.stringify({ pid: process.pid, ...data, updated_at: Date.now() }, null, 2), "utf8");
}

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return null;
  }
}

async function openBrowser() {
  try {
    return await chromium.connectOverCDP(cdpUrl);
  } catch {
    const chromePath = findChromeExecutable();
    if (!chromePath) fail("Chrome executable not found. Set TRPG_BROWSER_EXECUTABLE_PATH.");
    spawn(chromePath, [
      `--remote-debugging-port=${getRemoteDebuggingPort(cdpUrl)}`,
      `--user-data-dir=${userDataDir}`,
      "--no-first-run",
      "--no-default-browser-check",
      "--disable-popup-blocking",
      "https://chatgpt.com/",
    ], { detached: true, stdio: "ignore", windowsHide: false }).unref();
    await waitForCDP(cdpUrl, 60_000);
    return await chromium.connectOverCDP(cdpUrl);
  }
}

async function readyChatGPTPage(taskId = "") {
  writeTaskStatus(taskId, { state: "running", stage: "browser_checking", label: "Checking ChatGPT browser", percent: 6, updated_at: Date.now() });
  if (!browser || (typeof browser.isConnected === "function" && !browser.isConnected())) {
    browser = await openBrowser();
  }
  if (!page || page.isClosed()) {
    page = await chatgptPage(browser);
  }
  return page;
}

async function ensureTaskPageReady(currentPage, taskId) {
  try {
    await withTimeout(waitForHumanReady(currentPage, taskId, quickPageReadyMs), quickPageReadyMs + 5_000, "ChatGPT existing page readiness timed out.");
    return currentPage;
  } catch (err) {
    writeTaskStatus(taskId, { state: "running", stage: "browser_new_page", label: "现有 ChatGPT 页不可用，打开新窗口", percent: 8, warning: String(err?.message || err), updated_at: Date.now() });
    const context = browser.contexts()[0];
    if (!context) fail("Browser context not found.");
    const fresh = await context.newPage();
    await fresh.goto("https://chatgpt.com/", { waitUntil: "domcontentloaded", timeout: 60_000 });
    await waitForHumanReady(fresh, taskId, manualWaitMs);
    return fresh;
  }
}

async function restartBrowserSession() {
  try {
    if (typeof browser?.close === "function") await browser.close().catch(() => {});
  } catch {}
  browser = await openBrowser();
  page = await chatgptPage(browser);
}

function isRecoverableBrowserError(err) {
  const text = String(err?.message || err || "").toLowerCase();
  return [
    "browser has been closed",
    "page has been closed",
    "target page",
    "browser closed",
    "browser disconnected",
    "connect econnrefused",
    "cdp",
  ].some((term) => text.includes(term));
}

async function openTaskConversation(page, task) {
  const projectName = String(task.project_name || "").trim();
  const conversationName = String(task.conversation_name || "").trim();
  const autoCreate = task.auto_create !== false;
  if (projectName) {
    writeTaskStatus(task.id, { state: "running", stage: "project_opening", label: "Opening ChatGPT project", percent: 12, updated_at: Date.now() });
    const opened = await openProject(page, projectName, task.id, autoCreate);
    if (!opened) {
      writeTaskStatus(task.id, { state: "running", stage: "project_unavailable", label: `Project unavailable, using normal ChatGPT chat: ${projectName}`, percent: 14, updated_at: Date.now() });
    }
  }
  if (conversationName) {
    writeTaskStatus(task.id, { state: "running", stage: "conversation_opening", label: "Opening campaign conversation", percent: 15, updated_at: Date.now() });
    await openConversation(page, conversationName, task.id, autoCreate);
  } else {
    await openNewChat(page, task.id);
  }
}

async function chatgptPage(browser) {
  const context = browser.contexts()[0];
  if (!context) fail("Browser context not found.");
  let page = context.pages().find((candidate) => !candidate.isClosed() && candidate.url().includes("chatgpt.com"));
  if (!page) page = await context.newPage();
  if (!page.url().includes("chatgpt.com")) {
    await page.goto("https://chatgpt.com/", { waitUntil: "domcontentloaded", timeout: 60_000 });
  }
  return page;
}

async function waitForHumanReady(page, taskId, maxWaitMs = manualWaitMs) {
  let start = Date.now();
  let lastStatusAt = 0;
  while (Date.now() - start < maxWaitMs) {
    if (Date.now() - lastStatusAt > 5_000) {
      writeTaskStatus(taskId, { state: "running", stage: "actor_waiting", label: "等待 ChatGPT 页面可操作", percent: 6, updated_at: Date.now() });
      lastStatusAt = Date.now();
    }
    const bodyText = await page.locator("body").innerText({ timeout: 3000 }).catch(() => "");
    const lower = `${page.url()}\n${bodyText}`.toLowerCase();
    if (await isComposerVisible(page)) return;
    if (needsHumanVerification(lower)) {
      writeTaskStatus(taskId, { state: "running", stage: "waiting_human_verification", needs_human_verification: true, label: "等待人工验证", percent: 20, updated_at: Date.now() });
      start = Date.now();
      await sleep(1500);
      continue;
    }
    if (bodyText.trim().length > 0) return;
    await sleep(1000);
  }
  fail("ChatGPT page is still unavailable. Complete login or verification in the browser.");
}

function withTimeout(promise, ms, message) {
  return Promise.race([
    promise,
    new Promise((_, reject) => setTimeout(() => reject(new Error(message)), ms)),
  ]);
}

async function openProject(page, name, taskId, allowCreate = false) {
  await ensureSidebarOpen(page);
  if (await clickFirstVisible(projectLinkCandidates(page, name), 1800)) {
    await page.waitForTimeout(1200);
    return true;
  }
  await openProjectsSection(page);
  if (await clickFirstVisible(projectLinkCandidates(page, name), 2500)) {
    await page.waitForTimeout(1200);
    return true;
  }
  if (allowCreate) {
    writeTaskStatus(taskId, { state: "running", stage: "project_creating", label: "Creating ChatGPT project", percent: 13, updated_at: Date.now() });
    return await createProject(page, name, taskId);
  }
  return false;
}

async function openConversation(page, name, taskId, allowCreate = false) {
  await ensureSidebarOpen(page);
  const candidates = [
    page.getByText(name, { exact: true }).first(),
    findByTextLoose(page, name),
  ];
  for (const candidate of candidates) {
    if (await candidate.isVisible({ timeout: 2200 }).catch(() => false)) {
      await candidate.click({ force: true });
      await page.waitForTimeout(1200);
      await waitForComposerReady(page, taskId);
      return;
    }
  }
  if (allowCreate) {
    writeTaskStatus(taskId, { state: "running", stage: "conversation_creating", label: "Creating campaign conversation", percent: 16, updated_at: Date.now() });
    await openNewChat(page, taskId);
    return;
  }
  fail(`Conversation not found: ${name}`);
}

async function createProject(page, name, taskId = "") {
  await ensureSidebarOpen(page);
  await openProjectsSection(page);
  const buttons = projectCreateButtonCandidates(page);
  for (const candidate of buttons) {
    const first = candidate.first();
    if (await first.isVisible({ timeout: 1500 }).catch(() => false)) {
      await first.click({ force: true });
      await page.waitForTimeout(800);
      await fillProjectName(page, name);
      await submitProjectCreateDialog(page);
      await waitForProjectAvailable(page, name, taskId);
      return true;
    }
  }
  return false;
}

async function openProjectsSection(page) {
  const candidates = [
    page.getByRole("button", { name: /Projects|项目|專案/i }),
    page.getByRole("link", { name: /Projects|项目|專案/i }),
    page.locator("a, button, [role='button'], [role='link']").filter({ hasText: /Projects|项目|專案/i }),
    page.locator('[aria-label*="Projects" i], [aria-label*="项目"], [aria-label*="專案"]'),
  ];
  for (const candidate of candidates) {
    const first = candidate.first();
    if (await first.isVisible({ timeout: 800 }).catch(() => false)) {
      await first.click({ force: true }).catch(() => {});
      await page.waitForTimeout(500);
      return;
    }
  }
}

function projectLinkCandidates(page, name) {
  const escaped = escapeRegExp(name);
  return [
    page.locator('a[href*="/project"]').filter({ hasText: name }).first(),
    page.locator('a, [role="link"], [role="button"], button').filter({ hasText: new RegExp(escaped, "i") }).first(),
    page.locator(`[aria-label*="${cssAttrEscape(name)}"]`).first(),
    page.getByText(name, { exact: true }).first(),
    page.getByRole("link", { name }).first(),
    page.getByRole("button", { name }).first(),
    findByTextLoose(page, name),
  ];
}

function projectCreateButtonCandidates(page) {
  return [
    page.getByRole("button", { name: /New project|Create project|创建项目|新建项目|新增项目|新增專案|建立專案/i }),
    page.getByRole("link", { name: /New project|Create project|创建项目|新建项目|新增项目|新增專案|建立專案/i }),
    page.getByText("New project", { exact: true }),
    page.getByText("Create project", { exact: true }),
    page.getByText("创建项目", { exact: true }),
    page.getByText("新建项目", { exact: true }),
    page.locator("button, a, [role='button'], [role='link']").filter({ hasText: /New project|Create project|创建项目|新建项目|新增项目|新增專案|建立專案/i }),
    page.locator('[data-testid*="project" i]').filter({ hasText: /New|Create|创建|新建|新增|建立/i }),
    page.locator('[aria-label*="New project" i], [aria-label*="Create project" i], [aria-label*="创建项目"], [aria-label*="新建项目"], [aria-label*="新增项目"], [aria-label*="新增專案"], [aria-label*="建立專案"]'),
  ];
}

async function fillProjectName(page, name) {
  const inputs = [
    page.locator('input[name="name"]'),
    page.locator('input[placeholder*="project" i]'),
    page.locator('input[placeholder*="项目"]'),
    page.locator('input[placeholder*="專案"]'),
    page.locator('[role="dialog"] input').first(),
    page.locator("input").last(),
  ];
  for (const input of inputs) {
    if (await input.isVisible({ timeout: 1500 }).catch(() => false)) {
      await input.fill(name);
      return;
    }
  }
  fail(`Project creation dialog opened but project name input was not found: ${name}`);
}

async function submitProjectCreateDialog(page) {
  const createButtons = [
    page.getByRole("button", { name: /Create|Done|Save|创建|建立|完成|保存|儲存/i }).last(),
    page.locator('[role="dialog"] button').filter({ hasText: /Create|Done|Save|创建|建立|完成|保存|儲存/i }).last(),
    page.locator("button").filter({ hasText: /Create|Done|Save|创建|建立|完成|保存|儲存/i }).last(),
  ];
  for (const createButton of createButtons) {
    if (await createButton.isVisible({ timeout: 1500 }).catch(() => false)) {
      await createButton.click({ force: true });
      await page.waitForTimeout(1800);
      return;
    }
  }
  fail("Project creation dialog submit button was not found.");
}

async function waitForProjectAvailable(page, name, taskId = "") {
  for (let i = 0; i < 20; i += 1) {
    await ensureSidebarOpen(page);
    await openProjectsSection(page);
    for (const candidate of projectLinkCandidates(page, name)) {
      if (await candidate.isVisible({ timeout: 800 }).catch(() => false)) {
        await candidate.click({ force: true }).catch(() => {});
        await page.waitForTimeout(1000);
        return;
      }
    }
    writeTaskStatus(taskId, { state: "running", stage: "project_creating", label: "Waiting for created ChatGPT project", percent: 14, updated_at: Date.now() });
    await page.waitForTimeout(1000);
  }
  fail(`Project was submitted for creation but could not be opened: ${name}`);
}

function findByTextLoose(page, text) {
  const escaped = escapeRegExp(text);
  return page.locator(`text=/${escaped}/i`).first();
}

async function clickFirstVisible(candidates, timeout = 1500) {
  for (const candidate of candidates) {
    const first = candidate.first();
    if (await first.isVisible({ timeout }).catch(() => false)) {
      await first.click({ force: true });
      return true;
    }
  }
  return false;
}

function escapeRegExp(text) {
  return String(text || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function cssAttrEscape(text) {
  return String(text || "").replace(/\\/g, "\\\\").replace(/"/g, '\\"');
}

async function openNewChat(page, taskId) {
  await ensureSidebarOpen(page);
  const candidates = [
    page.getByText("New chat", { exact: true }),
    page.getByText("新聊天", { exact: true }),
    page.locator('a[href="/"]').filter({ hasText: /New chat|新聊天/i }),
    page.locator('button[aria-label*="New chat"]'),
    page.locator('button[aria-label*="新聊天"]'),
    page.locator("button").filter({ hasText: /New chat|新聊天/i }),
  ];
  for (const candidate of candidates) {
    const first = candidate.first();
    if (await first.isVisible({ timeout: 1200 }).catch(() => false)) {
      await first.click({ force: true });
      await page.waitForTimeout(800);
      await waitForComposerReady(page, taskId);
      return;
    }
  }
  await page.goto("https://chatgpt.com/", { waitUntil: "domcontentloaded", timeout: 60_000 });
  await waitForComposerReady(page, taskId);
}

async function waitForComposerReady(page, taskId) {
  for (let i = 0; i < 60; i += 1) {
    await waitForHumanReady(page, taskId);
    if (await isComposerVisible(page)) return;
    await sleep(500);
  }
  fail("New chat composer not found.");
}

async function ensureSidebarOpen(page) {
  const candidates = [
    page.locator('button[aria-label*="Open sidebar"]'),
    page.locator('button[aria-label*="Show sidebar"]'),
    page.locator('button[aria-label*="sidebar"]'),
    page.locator('button[aria-label*="打开边栏"]'),
    page.locator('button[aria-label*="显示边栏"]'),
  ];
  for (const candidate of candidates) {
    const first = candidate.first();
    if (await first.isVisible({ timeout: 500 }).catch(() => false)) {
      await first.click({ force: true }).catch(() => {});
      await page.waitForTimeout(500);
      return;
    }
  }
}

async function fillComposer(page, text) {
  const selectors = ['[data-testid="prompt-textarea"]', "textarea", '[contenteditable="true"]', ".ProseMirror"];
  for (const selector of selectors) {
    const locator = page.locator(selector).last();
    if (await locator.isVisible({ timeout: 3000 }).catch(() => false)) {
      await locator.click();
      await page.keyboard.press(process.platform === "darwin" ? "Meta+A" : "Control+A");
      await page.keyboard.insertText(text);
      return;
    }
  }
  fail("Composer input not found.");
}

async function clickSend(page) {
  const selectors = [
    '[data-testid="composer-submit-button"]',
    '[data-testid="send-button"]',
    '[data-testid*="send" i]',
    'button[aria-label="Send"]',
    'button[aria-label="Send prompt"]',
    'button[aria-label="Send message"]',
    'button[aria-label*="Send"]',
    'button[aria-label*="Submit"]',
    'button[aria-label*="发送"]',
    'button[aria-label*="提交"]',
  ];
  for (const selector of selectors) {
    const locator = page.locator(selector).last();
    if (await locator.isVisible({ timeout: 2500 }).catch(() => false)) {
      await locator.click({ timeout: 10_000 });
      if (await waitForSendStarted(page)) return;
    }
  }
  await page.keyboard.press("Enter");
  if (await waitForSendStarted(page)) return;
  await page.keyboard.press(process.platform === "darwin" ? "Meta+Enter" : "Control+Enter");
  if (await waitForSendStarted(page)) return;
  await page.waitForTimeout(1200);
  const stopVisible = await page.locator('[data-testid="stop-button"], button[aria-label*="Stop"], button[aria-label*="停止"]').first().isVisible({ timeout: 800 }).catch(() => false);
  const assistantStarted = Boolean((await latestAssistantText(page).catch(() => "")).trim());
  if (stopVisible || assistantStarted) return;
  const bodyText = await page.locator("body").innerText({ timeout: 3000 }).catch(() => "");
  fail(`Send button not found. page=${page.url()} preview=${bodyText.slice(0, 500)}`);
}

async function waitForSendStarted(page) {
  for (let i = 0; i < 10; i += 1) {
    const stopVisible = await page.locator('[data-testid="stop-button"], button[aria-label*="Stop"], button[aria-label*="停止"]').first().isVisible({ timeout: 300 }).catch(() => false);
    if (stopVisible) return true;
    const assistantStarted = Boolean((await latestAssistantText(page).catch(() => "")).trim());
    if (assistantStarted) return true;
    const composerText = await composerTextValue(page);
    if (composerText !== null && composerText.trim() === "") return true;
    await sleep(300);
  }
  return false;
}

async function composerTextValue(page) {
  const selectors = ['[data-testid="prompt-textarea"]', "textarea", '[contenteditable="true"]', ".ProseMirror"];
  for (const selector of selectors) {
    const locator = page.locator(selector).last();
    if (!(await locator.isVisible({ timeout: 300 }).catch(() => false))) continue;
    if (selector === "textarea") {
      return await locator.inputValue({ timeout: 500 }).catch(() => "");
    }
    return await locator.innerText({ timeout: 500 }).catch(() => "");
  }
  return null;
}

async function waitForAssistantCompletion(page, taskId) {
  let stableCount = 0;
  let lastText = "";
  for (let i = 0; i < 240; i += 1) {
    await waitForHumanReady(page, taskId);
    const text = await latestAssistantText(page);
    const stopVisible = await page.locator('[data-testid="stop-button"], button[aria-label*="Stop"], button[aria-label*="停止"]').first().isVisible({ timeout: 500 }).catch(() => false);
    if (text && text === lastText && !stopVisible) stableCount += 1;
    else {
      stableCount = 0;
      lastText = text;
      writeTaskStatus(taskId, { state: "running", stage: "actor_waiting", label: "演员层正在生成正文", percent: 45, updated_at: Date.now() });
    }
    if (stableCount >= 5 && text) return text;
    await sleep(1000);
  }
  return lastText;
}

async function waitForImageCompletion(page, taskId, artifactPath) {
  let stableCount = 0;
  let lastSnapshot = "";
  for (let i = 0; i < 360; i += 1) {
    await waitForHumanReady(page, taskId);
    const snapshot = await latestAssistantSnapshot(page, artifactPath);
    const stopVisible = await page.locator('[data-testid="stop-button"], button[aria-label*="Stop"], button[aria-label*="停止"]').first().isVisible({ timeout: 500 }).catch(() => false);
    if (snapshot && snapshot === lastSnapshot && !stopVisible) stableCount += 1;
    else {
      stableCount = 0;
      lastSnapshot = snapshot;
    }
    if (stableCount >= 8 && snapshot) return snapshot;
    await sleep(1000);
  }
  return lastSnapshot || "IMAGE_GENERATION_SNAPSHOT_EMPTY";
}

async function latestAssistantText(page) {
  const locators = page.locator('[data-message-author-role="assistant"]');
  const count = await locators.count().catch(() => 0);
  for (let i = count - 1; i >= 0; i -= 1) {
    const text = await locators.nth(i).innerText({ timeout: 1000 }).catch(() => "");
    if (text.includes(M.body) || text.includes(M.writebackBegin) || text.includes(M.choices) || looksLikeStructuredJson(text)) return text;
  }
  return "";
}

async function latestAssistantSnapshot(page, artifactPath) {
  const locators = page.locator('[data-message-author-role="assistant"]');
  const count = await locators.count().catch(() => 0);
  if (!count) return "";
  const latest = locators.nth(count - 1);
  const text = await latest.innerText({ timeout: 1000 }).catch(() => "");
  const images = latest.locator("img");
  const imageCount = await images.count().catch(() => 0);
  let artifact = "";
  if (imageCount > 0 && artifactPath) {
    await images.nth(imageCount - 1).screenshot({ path: artifactPath }).then(() => { artifact = artifactPath; }).catch(() => {});
  }
  return JSON.stringify({ mode: "image", captured_at: new Date().toISOString(), text, image_count: imageCount, image_artifact: artifact }, null, 2);
}

function isCompleteReply(text) {
  if (looksLikeStructuredJson(text)) return true;
  return Object.values(M).every((marker) => text.includes(marker));
}

function looksLikeStructuredJson(text) {
  const payload = extractJsonPayload(text);
  if (!payload) return false;
  try {
    const data = JSON.parse(payload);
    return Array.isArray(data.blocks) && data.blocks.length > 0 && (isPlainObject(data.state_writeback) || isPlainObject(data.writeback) || isPlainObject(data.memory_patch));
  } catch {
    return false;
  }
}

function extractJsonPayload(text) {
  const trimmed = String(text || "").trim();
  const fenced = trimmed.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);
  const candidate = fenced ? fenced[1].trim() : trimmed;
  if (candidate.startsWith("{") && candidate.endsWith("}")) return candidate;
  const first = candidate.indexOf("{");
  const last = candidate.lastIndexOf("}");
  return first >= 0 && last > first ? candidate.slice(first, last + 1) : "";
}

async function isComposerVisible(page) {
  return page.locator('[data-testid="prompt-textarea"], textarea, [contenteditable="true"], .ProseMirror').last().isVisible({ timeout: 500 }).catch(() => false);
}

function needsHumanVerification(text) {
  return ["captcha", "verify your identity", "verification", "just a moment", "checking", "log in", "sign in", "请稍候", "验证", "登录"].some((term) => text.includes(term.toLowerCase()));
}

function imageArtifactPath(outputPath) {
  const parsed = path.parse(outputPath);
  return path.join(parsed.dir, `${parsed.name}.png`);
}

function findChromeExecutable() {
  const explicit = process.env.TRPG_BROWSER_EXECUTABLE_PATH;
  if (explicit && fs.existsSync(explicit)) return explicit;
  return [
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    path.join(process.env.LOCALAPPDATA || "", "Google\\Chrome\\Application\\chrome.exe"),
  ].find((candidate) => fs.existsSync(candidate)) || "";
}

function getRemoteDebuggingPort(url) {
  try { return new URL(url).port || "9222"; } catch { return "9222"; }
}

async function waitForCDP(url, timeoutMs) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`${url}/json/version`);
      if (res.ok) return;
    } catch {}
    await sleep(1000);
  }
  fail(`Chrome started but CDP was not ready: ${url}`);
}

function isPlainObject(value) {
  return value && typeof value === "object" && !Array.isArray(value);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function fail(message) {
  throw new Error(message);
}
