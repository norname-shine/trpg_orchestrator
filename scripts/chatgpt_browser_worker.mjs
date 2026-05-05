import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { chromium } from "playwright";

const workerDir = process.env.TRPG_CHATGPT_WORKER_DIR || path.join(process.cwd(), ".runtime", "chatgpt_worker");
const tasksDir = path.join(workerDir, "tasks");
const statusPath = path.join(workerDir, "worker_status.json");
const cdpUrl = process.env.TRPG_BROWSER_CDP_URL || "http://127.0.0.1:9222";
const userDataDir = process.env.TRPG_BROWSER_USER_DATA_DIR;
const manualWaitMs = Number(process.env.TRPG_BROWSER_MANUAL_WAIT_MS || 10 * 60 * 1000);

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

const browser = await openBrowser();
const page = await chatgptPage(browser);
console.log(`TRPG browser worker ready: ${workerDir}`);

while (true) {
  const task = nextTask();
  if (!task) {
    await sleep(500);
    continue;
  }
  await handleTask(task).catch((err) => {
    writeTaskStatus(task.id, { state: "failed", error: String(err?.message || err), updated_at: Date.now() });
  });
}

async function handleTask(task) {
  writeTaskStatus(task.id, { state: "running", stage: "actor_waiting", label: "准备 ChatGPT 常驻浏览器", percent: 5, updated_at: Date.now() });
  await waitForHumanReady(page, task.id);
  if (!task.capture_only) {
    writeTaskStatus(task.id, { state: "running", stage: "actor_waiting", label: "打开新聊天", percent: 12, updated_at: Date.now() });
    await openNewChat(page, task.id);
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
    throw new Error("Latest ChatGPT reply is incomplete or missing required markers.");
  }
  fs.writeFileSync(task.output_path, latest.trim() + "\n", "utf8");
  writeTaskStatus(task.id, { state: "complete", stage: "actor_complete", label: "ChatGPT 正文已返回", percent: 70, output_chars: latest.length, updated_at: Date.now() });
}

function nextTask() {
  const files = fs.readdirSync(tasksDir).filter((name) => name.endsWith(".json") && !name.endsWith(".status.json")).sort();
  for (const file of files) {
    const full = path.join(tasksDir, file);
    const task = readJson(full);
    if (!task || task.state !== "pending") continue;
    task.state = "claimed";
    fs.writeFileSync(full, JSON.stringify(task, null, 2), "utf8");
    return task;
  }
  return null;
}

function writeTaskStatus(id, data) {
  const payload = { task_id: id, ...data };
  fs.writeFileSync(path.join(tasksDir, `${id}.status.json`), JSON.stringify(payload, null, 2), "utf8");
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

async function waitForHumanReady(page, taskId) {
  const start = Date.now();
  while (Date.now() - start < manualWaitMs) {
    const bodyText = await page.locator("body").innerText({ timeout: 3000 }).catch(() => "");
    const lower = `${page.url()}\n${bodyText}`.toLowerCase();
    if (await isComposerVisible(page)) return;
    if (needsHumanVerification(lower)) {
      writeTaskStatus(taskId, { state: "running", stage: "waiting_human_verification", needs_human_verification: true, label: "等待人工验证", percent: 20, updated_at: Date.now() });
      await sleep(1500);
      continue;
    }
    if (bodyText.trim().length > 0) return;
    await sleep(1000);
  }
  fail("ChatGPT page is still unavailable. Complete login or verification in the browser.");
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
  const selectors = ['[data-testid="send-button"]', 'button[aria-label="Send prompt"]', 'button[aria-label="Send message"]', 'button[aria-label*="Send"]', 'button[aria-label*="发送"]'];
  for (const selector of selectors) {
    const locator = page.locator(selector).last();
    if (await locator.isVisible({ timeout: 3000 }).catch(() => false)) {
      await locator.click({ timeout: 10_000 });
      return;
    }
  }
  fail("Send button not found.");
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
