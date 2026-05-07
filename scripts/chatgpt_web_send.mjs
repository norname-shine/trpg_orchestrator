import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { chromium } from "playwright";

const args = parseArgs(process.argv.slice(2));

const inputPath = requiredArg(args, "input");
const outputPath = requiredArg(args, "output");
const projectName = requiredArg(args, "project");
const conversationName = requiredArg(args, "conversation");
const mode = args.mode || "text";
const evidencePath = args.evidence || path.join(path.dirname(outputPath), "browser_evidence.json");

const captureOnly = args["capture-only"] === "true";
const createIfMissing =
  args["create-if-missing"] === "true" ||
  process.env.TRPG_CHATGPT_CREATE_IF_MISSING === "1";

const userDataDir = process.env.TRPG_BROWSER_USER_DATA_DIR;
const cdpUrl = process.env.TRPG_BROWSER_CDP_URL || "http://127.0.0.1:9222";
const keepBrowserOpen = process.env.TRPG_BROWSER_KEEP_OPEN !== "0";
const manualWaitMs = Number(process.env.TRPG_BROWSER_MANUAL_WAIT_MS || 10 * 60 * 1000);
const streamVisibleReply = process.env.TRPG_STREAM_VISIBLE_REPLY === "1";
const directNewChat = process.env.TRPG_CHATGPT_DIRECT_NEW_CHAT !== "0";
const inputHash = captureOnly ? "" : sha256File(inputPath);

const M = {
  body: "\u3010\u6b63\u6587\u3011",
  choices: "\u3010\u9009\u62e9\u70b9\u3011",
  summary: "\u3010\u56de\u5408\u6458\u8981\u3011",
  writebackBegin: "\u3010\u72b6\u6001\u56de\u5199_BEGIN\u3011",
  writebackEnd: "\u3010\u72b6\u6001\u56de\u5199_END\u3011",
};

if (!userDataDir) {
  fail("TRPG_BROWSER_USER_DATA_DIR is required for Playwright automation.");
}

const inputText = captureOnly ? "" : fs.readFileSync(inputPath, "utf8");

const browser = await openBrowser();

try {
  const page = await chatgptPage(browser);

  await safetyCheck(page);
  if (directNewChat && !captureOnly) {
    await openNewChat(page);
  } else {
    await openProject(page, projectName);
    await openConversation(page, conversationName, createIfMissing);
  }
  await safetyCheck(page);

  if (captureOnly) {
    const latest = await latestAssistantText(page);

    if (!isCompleteReply(latest)) {
      fail("Latest assistant reply is missing required markers or JSON fields.");
    }

    fs.writeFileSync(outputPath, latest.trim() + "\n", "utf8");
    writeEvidence({ ok: true, markers_ok: true });
    console.log(`Captured latest assistant reply: ${latest.length} chars`);
  } else {
    await fillComposer(page, inputText);
    await clickSend(page);

    let latest = mode === "image" ? await waitForImageCompletion(page, imageArtifactPath(outputPath)) : await waitForAssistantCompletion(page);

    if (mode === "image") {
      fs.writeFileSync(outputPath, latest.trim() + "\n", "utf8");
      writeEvidence({ ok: true, markers_ok: true });
      console.log(`Captured image assistant snapshot: ${latest.length} chars`);
      process.exitCode = 0;
    } else {

      if (!isCompleteReply(latest)) {
        const continued = await clickContinueOnce(page);
        if (continued) {
          latest = await waitForAssistantCompletion(page);
        }
      }

      if (!isCompleteReply(latest) && hasContentButMissingWriteback(latest)) {
        await requestWritebackOnly(page);
        const supplement = await waitForAssistantCompletion(page);
        latest = mergeWriteback(latest, supplement);
      }

      if (!isCompleteReply(latest)) {
        fs.writeFileSync(outputPath, latest.trim() + "\n", "utf8");
        writeEvidence({ ok: false, markers_ok: false, blocked_reason: "missing_markers", error: "Latest ChatGPT reply is incomplete or missing required markers after recovery attempt." });
        fail("Latest ChatGPT reply is incomplete or missing required markers after recovery attempt.");
      }

      fs.writeFileSync(outputPath, latest.trim() + "\n", "utf8");
      writeEvidence({ ok: true, markers_ok: true });
      console.log(`Captured complete assistant reply: ${latest.length} chars`);
    }
  }
} finally {
  if (keepBrowserOpen) {
    if (typeof browser.disconnect === "function") {
      await browser.disconnect().catch(() => {});
    }
    console.log("Browser is left open. Please close it manually when you are done.");
  } else {
    await browser.close().catch(() => {});
  }
}

async function openBrowser() {
  try {
    console.log(`Trying to connect browser CDP: ${cdpUrl}`);
    return await chromium.connectOverCDP(cdpUrl);
  } catch {
    console.log("No existing CDP browser found. Launching Chrome for manual login / verification.");
  }

  const chromePath = findChromeExecutable();

  if (!chromePath) {
    fail(
      "Chrome executable not found. Please set TRPG_BROWSER_EXECUTABLE_PATH in .env, " +
        "for example: TRPG_BROWSER_EXECUTABLE_PATH=C:\\\\Program Files\\\\Google\\\\Chrome\\\\Application\\\\chrome.exe"
    );
  }

  const remotePort = getRemoteDebuggingPort(cdpUrl);

  const chromeArgs = [
    `--remote-debugging-port=${remotePort}`,
    `--user-data-dir=${userDataDir}`,
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-popup-blocking",
    "https://chatgpt.com/",
  ];

  console.log(`Launching Chrome: ${chromePath}`);
  console.log(`User data dir: ${userDataDir}`);
  console.log(`Remote debugging port: ${remotePort}`);

  spawn(chromePath, chromeArgs, {
    detached: true,
    stdio: "ignore",
    windowsHide: false,
  }).unref();

  await waitForCDP(cdpUrl, 60_000);

  return await chromium.connectOverCDP(cdpUrl);
}

function getRemoteDebuggingPort(url) {
  try {
    return new URL(url).port || "9222";
  } catch {
    return "9222";
  }
}

function findChromeExecutable() {
  const explicit = process.env.TRPG_BROWSER_EXECUTABLE_PATH;
  if (explicit && fs.existsSync(explicit)) {
    return explicit;
  }

  const candidates = [
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
    path.join(process.env.LOCALAPPDATA || "", "Google\\Chrome\\Application\\chrome.exe"),
  ];

  return candidates.find((candidate) => fs.existsSync(candidate)) || "";
}

async function waitForCDP(url, timeoutMs) {
  const start = Date.now();

  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`${url}/json/version`);
      if (res.ok) {
        return;
      }
    } catch {}

    await sleep(1000);
  }

  fail(`Chrome started but CDP was not ready: ${url}`);
}

async function chatgptPage(browser) {
  const context = browser.contexts()[0];

  if (!context) {
    fail("Browser context not found.");
  }

  let page = await getOrCreateChatGPTPage(context);

  console.log(
    "Waiting for ChatGPT page. If login or human verification appears, complete it manually in the opened browser."
  );

  const start = Date.now();
  let lastUrl = "";
  let lastTitle = "";
  let lastPreview = "";

  while (Date.now() - start < manualWaitMs) {
    if (page.isClosed()) {
      console.log("ChatGPT page was closed. Opening a new ChatGPT page.");
      page = await getOrCreateChatGPTPage(context, true);
    }

    await sleep(1000);

    lastUrl = page.url();
    lastTitle = await page.title().catch(() => "");

    const bodyText = await page.locator("body").innerText({ timeout: 3000 }).catch(() => "");
    lastPreview = bodyText.slice(0, 300);

    const composerVisible = await isComposerVisible(page);
    const projectVisible = await findByTextLoose(page, projectName)
      .isVisible({ timeout: 500 })
      .catch(() => false);

    console.log(
      `ChatGPT check: title=${lastTitle}, url=${lastUrl}, body=${bodyText.trim().length} chars, composer=${composerVisible}, project=${projectVisible}`
    );

    if (composerVisible || projectVisible) {
      return page;
    }

    const waitingText = `${lastTitle}\n${bodyText}`.toLowerCase();

    if (
      waitingText.includes("请稍候") ||
      waitingText.includes("just a moment") ||
      waitingText.includes("please wait") ||
      waitingText.includes("checking") ||
      waitingText.includes("verify") ||
      waitingText.includes("verification") ||
      waitingText.includes("验证") ||
      waitingText.includes("真人") ||
      waitingText.includes("log in") ||
      waitingText.includes("sign in") ||
      waitingText.includes("登录")
    ) {
      continue;
    }

    if (bodyText.trim().length > 0) {
      return page;
    }
  }

  fail(
    "ChatGPT page is still on login / human verification / loading screen. " +
      "Please complete it manually in the opened browser and run the command again. " +
      `url=${lastUrl}, title=${lastTitle}, preview=${lastPreview}`
  );
}

async function getOrCreateChatGPTPage(context, forceNew = false) {
  let page = null;

  if (!forceNew) {
    page = context.pages().find((candidate) => {
      return !candidate.isClosed() && candidate.url().includes("chatgpt.com");
    });
  }

  if (!page) {
    page = await context.newPage();
  }

  if (!page.url().includes("chatgpt.com")) {
    await page.goto("https://chatgpt.com/", {
      waitUntil: "domcontentloaded",
      timeout: 60_000,
    });
  }

  return page;
}

async function openProject(page, name) {
  await ensureSidebarOpen(page);

  const candidates = [
    page.getByText(name, { exact: true }).first(),
    findByTextLoose(page, name),
  ];

  for (const candidate of candidates) {
    if (await candidate.isVisible({ timeout: 3000 }).catch(() => false)) {
      await candidate.click({ force: true });
      await page.waitForTimeout(1200);
      return;
    }
  }

  const bodyText = await page.locator("body").innerText({ timeout: 5000 }).catch(() => "");
  fail(`Project not found: ${name}. Visible page text preview: ${bodyText.slice(0, 500)}`);
}

async function openConversation(page, name, allowCreate = false) {
  await ensureSidebarOpen(page);

  const candidates = [
    page.getByText(name, { exact: true }).first(),
    findByTextLoose(page, name),
  ];

  for (const candidate of candidates) {
    if (await candidate.isVisible({ timeout: 3000 }).catch(() => false)) {
      await candidate.click({ force: true });
      await page.waitForTimeout(1200);
      return;
    }
  }

  if (allowCreate) {
    await openNewChatInCurrentProject(page);
    return;
  }

  const bodyText = await page.locator("body").innerText({ timeout: 5000 }).catch(() => "");
  fail(`Fixed conversation not found: ${name}. Visible page text preview: ${bodyText.slice(0, 500)}`);
}

async function ensureSidebarOpen(page) {
  const candidates = [
    page.locator('button[aria-label*="Open sidebar"]'),
    page.locator('button[aria-label*="打开边栏"]'),
    page.locator('button[aria-label*="Show sidebar"]'),
    page.locator('button[aria-label*="显示边栏"]'),
    page.locator('button[aria-label*="sidebar"]'),
    page.locator('button[aria-label*="边栏"]'),
  ];

  for (const candidate of candidates) {
    const first = candidate.first();

    if (await first.isVisible({ timeout: 800 }).catch(() => false)) {
      await first.click({ force: true }).catch(() => {});
      await page.waitForTimeout(800);
      return;
    }
  }
}

async function openNewChat(page) {
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

    if (await first.isVisible({ timeout: 2000 }).catch(() => false)) {
      await first.click({ force: true });
      await page.waitForTimeout(1200);
      await waitForComposerReady(page);
      return;
    }
  }

  await page.goto("https://chatgpt.com/", {
    waitUntil: "domcontentloaded",
    timeout: 60_000,
  });
  await waitForComposerReady(page);
}

async function waitForComposerReady(page) {
  const start = Date.now();
  while (Date.now() - start < 30_000) {
    await safetyCheck(page);
    if (await isComposerVisible(page)) return;
    await page.waitForTimeout(500);
  }
  fail("New chat composer not found.");
}

async function openNewChatInCurrentProject(page) {
  const candidates = [
    page.getByText("新聊天", { exact: true }),
    page.getByText("New chat", { exact: true }),
    page.locator('a[href="/"]').filter({ hasText: /新聊天|New chat/i }),
    page.locator("button").filter({ hasText: /新聊天|New chat/i }),
  ];

  for (const candidate of candidates) {
    const first = candidate.first();

    if (await first.isVisible({ timeout: 2000 }).catch(() => false)) {
      await first.click({ force: true });
      await page.waitForTimeout(1200);
      return;
    }
  }

  fail("Fixed conversation not found and new chat button not found in current project.");
}

async function safetyCheck(page) {
  const url = page.url().toLowerCase();

  const blockedUrlHints = [
    "/auth",
    "/login",
    "/settings",
    "/account",
    "/billing",
    "/pricing",
    "/plans",
    "/purchase",
  ];

  if (blockedUrlHints.some((hint) => url.includes(hint))) {
    fail(`Blocked browser state detected by url: ${url}`);
  }

  const bodyText = (await page.locator("body").innerText({ timeout: 10_000 }).catch(() => "")).toLowerCase();

  const hardBlockedText = [
    "captcha",
    "verify your identity",
    "账号设置",
    "安全验证",
    "验证码",
    "隐私设置",
  ];

  const hardFound = hardBlockedText.find((term) => bodyText.includes(term.toLowerCase()));

  if (hardFound) {
    fail(`Blocked browser state detected: ${hardFound}`);
  }

  const modalText = await page
    .locator('[role="dialog"], [aria-modal="true"], main')
    .innerText({ timeout: 2000 })
    .catch(() => "");

  const modalLower = modalText.toLowerCase();
  const paywallTerms = [
    "payment",
    "billing",
    "subscription",
    "upgrade to",
    "choose a plan",
    "支付",
    "订阅",
    "升级",
    "选择套餐",
  ];

  const paywallFound = paywallTerms.find((term) => modalLower.includes(term.toLowerCase()));
  const composerVisible = await isComposerVisible(page);

  if (paywallFound && !composerVisible) {
    fail(`Blocked browser state detected: ${paywallFound}`);
  }
}

async function fillComposer(page, text) {
  const selectors = [
    '[data-testid="prompt-textarea"]',
    "textarea",
    '[contenteditable="true"]',
    ".ProseMirror",
  ];

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
    '[data-testid="send-button"]',
    'button[aria-label="Send prompt"]',
    'button[aria-label="Send message"]',
    'button[aria-label*="Send"]',
    'button[aria-label*="发送"]',
  ];

  for (const selector of selectors) {
    const locator = page.locator(selector).last();

    if (await locator.isVisible({ timeout: 3000 }).catch(() => false)) {
      await locator.click({ timeout: 10_000 });
      return;
    }
  }

  fail("Send button not found.");
}

async function waitForAssistantCompletion(page) {
  let stableCount = 0;
  let lastText = "";
  let lastStreamedText = "";

  for (let i = 0; i < 240; i += 1) {
    await safetyCheck(page);

    const text = await latestAssistantText(page);
    if (streamVisibleReply && text && text !== lastStreamedText) {
      emitVisibleReplySnapshot(text);
      lastStreamedText = text;
    }
    const stopVisible = await page
      .locator('[data-testid="stop-button"], button[aria-label*="Stop"], button[aria-label*="停止"]')
      .first()
      .isVisible({ timeout: 500 })
      .catch(() => false);

    if (text && text === lastText && !stopVisible) {
      stableCount += 1;
    } else {
      stableCount = 0;
      lastText = text;
    }

    if (stableCount >= 5 && text) {
      return text;
    }

    await sleep(1000);
  }

  return lastText;
}

function emitVisibleReplySnapshot(text) {
  const body = Buffer.from(publicStreamPreview(text), "utf8").toString("base64");
  console.log(`TRPG_STREAM_SNAPSHOT ${body}`);
}

function publicStreamPreview(text) {
  let value = String(text || "");
  const writebackIndex = value.indexOf(M.writebackBegin);
  if (writebackIndex >= 0) value = value.slice(0, writebackIndex).trimEnd();
  return value;
}

async function waitForImageCompletion(page, artifactPath) {
  let stableCount = 0;
  let lastSnapshot = "";

  for (let i = 0; i < 360; i += 1) {
    await safetyCheck(page);

    const snapshot = await latestAssistantSnapshot(page, artifactPath);
    const stopVisible = await page
      .locator('[data-testid="stop-button"], button[aria-label*="Stop"], button[aria-label*="停止"]')
      .first()
      .isVisible({ timeout: 500 })
      .catch(() => false);

    if (snapshot && snapshot === lastSnapshot && !stopVisible) {
      stableCount += 1;
    } else {
      stableCount = 0;
      lastSnapshot = snapshot;
    }

    if (stableCount >= 8 && snapshot) {
      return snapshot;
    }

    await sleep(1000);
  }

  return lastSnapshot || "IMAGE_GENERATION_SNAPSHOT_EMPTY";
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
    await images.nth(imageCount - 1).screenshot({ path: artifactPath }).then(() => {
      artifact = artifactPath;
    }).catch(() => {});
  }
  const links = await latest
    .locator("a")
    .evaluateAll((items) => items.map((item) => item.href).filter(Boolean).slice(0, 10))
    .catch(() => []);
  return JSON.stringify(
    {
      mode: "image",
      captured_at: new Date().toISOString(),
      text,
      image_count: imageCount,
      image_artifact: artifact,
      links,
    },
    null,
    2
  );
}

function imageArtifactPath(outputPath) {
  const parsed = path.parse(outputPath);
  return path.join(parsed.dir, `${parsed.name}.png`);
}

async function latestAssistantText(page) {
  const locators = page.locator('[data-message-author-role="assistant"]');
  const count = await locators.count().catch(() => 0);

  for (let i = count - 1; i >= 0; i -= 1) {
    const text = await locators.nth(i).innerText({ timeout: 1000 }).catch(() => "");

    if (
      text.includes(M.body) ||
      text.includes(M.writebackBegin) ||
      text.includes(M.choices) ||
      looksLikeStructuredJson(text)
    ) {
      return text;
    }
  }

  return "";
}

async function clickContinueOnce(page) {
  const candidates = [
    page.getByText("Continue generating", { exact: true }),
    page.getByText("\u7ee7\u7eed\u751f\u6210", { exact: true }),
    page.locator('button[aria-label*="Continue"]'),
    page.locator('button[aria-label*="\u7ee7\u7eed"]'),
  ];

  for (const candidate of candidates) {
    const first = candidate.first();

    if (await first.isVisible({ timeout: 2000 }).catch(() => false)) {
      await first.click();
      return true;
    }
  }

  return false;
}

async function requestWritebackOnly(page) {
  const prompt =
    "只补全上一条回复缺失的状态回写 JSON，不要重写正文。必须从【状态回写_BEGIN】开始，到【状态回写_END】结束。";

  await fillComposer(page, prompt);
  await clickSend(page);
}

function mergeWriteback(original, supplement) {
  if (
    original.includes(M.writebackBegin) &&
    !original.includes(M.writebackEnd) &&
    supplement.includes(M.writebackBegin)
  ) {
    return original.split(M.writebackBegin, 1)[0].trim() + "\n" + supplement.trim();
  }

  if (!original.includes(M.writebackBegin) && supplement.includes(M.writebackBegin)) {
    return original.trim() + "\n\n" + supplement.trim();
  }

  return supplement.includes(M.writebackEnd) ? supplement : original;
}

function hasContentButMissingWriteback(text) {
  return text.includes(M.body) && text.includes(M.choices) && text.includes(M.summary) && !text.includes(M.writebackEnd);
}

function isCompleteReply(text) {
  if (looksLikeStructuredJson(text)) {
    return true;
  }

  return Object.values(M).every((marker) => text.includes(marker));
}

function looksLikeStructuredJson(text) {
  const payload = extractJsonPayload(text);

  if (!payload) {
    return false;
  }

  try {
    const data = JSON.parse(payload);

    return (
      Array.isArray(data.blocks) &&
      data.blocks.length > 0 &&
      (isPlainObject(data.state_writeback) || isPlainObject(data.writeback) || isPlainObject(data.memory_patch))
    );
  } catch {
    return false;
  }
}

function extractJsonPayload(text) {
  const trimmed = (text || "").trim();

  if (!trimmed) {
    return "";
  }

  const fenced = trimmed.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);
  const candidate = fenced ? fenced[1].trim() : trimmed;

  if (candidate.startsWith("{") && candidate.endsWith("}")) {
    return candidate;
  }

  const first = candidate.indexOf("{");
  const last = candidate.lastIndexOf("}");

  return first >= 0 && last > first ? candidate.slice(first, last + 1) : "";
}

function isPlainObject(value) {
  return value && typeof value === "object" && !Array.isArray(value);
}

async function isComposerVisible(page) {
  return page
    .locator('[data-testid="prompt-textarea"], textarea, [contenteditable="true"], .ProseMirror')
    .last()
    .isVisible({ timeout: 500 })
    .catch(() => false);
}

function findByTextLoose(page, text) {
  return page.locator("a, button, [role='button'], [role='link'], [aria-label]").filter({ hasText: text }).first();
}

function parseArgs(argv) {
  const result = {};

  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i]?.replace(/^--/, "");
    const value = argv[i + 1];

    if (key) {
      result[key] = value;
    }
  }

  return result;
}

function sha256File(file) {
  if (!fs.existsSync(file)) return "";
  return createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

function blockedReasonFromOutput() {
  if (!fs.existsSync(outputPath)) return "browser_automation_error";
  const text = fs.readFileSync(outputPath, "utf8").toLowerCase();
  const terms = [
    "log in",
    "sign in",
    "captcha",
    "verification",
    "verify your identity",
    "payment",
    "billing",
    "subscription",
    "security",
    "登录",
    "验证码",
    "安全验证",
    "支付",
    "订阅",
  ];
  const found = terms.find((term) => text.includes(term.toLowerCase()));
  if (found) return `blocked browser state detected: ${found}`;
  if (!text.trim()) return "empty_output";
  return "";
}

function writeEvidence({ ok, markers_ok, blocked_reason = "", error = "" }) {
  const reason = blocked_reason || (!ok ? blockedReasonFromOutput() : "");
  const payload = {
    ok: Boolean(ok),
    mode: captureOnly ? "capture_only" : mode,
    campaign_id: "",
    input_hash: inputHash,
    output_hash: sha256File(outputPath),
    markers_ok: Boolean(markers_ok),
    blocked_reason: reason,
    error,
  };
  fs.writeFileSync(evidencePath, JSON.stringify(payload, null, 2) + "\n", "utf8");
}

function requiredArg(parsedArgs, key) {
  if (!parsedArgs[key]) {
    fail(`missing --${key}`);
  }

  return parsedArgs[key];
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function fail(message) {
  writeEvidence({ ok: false, markers_ok: false, blocked_reason: blockedReasonFromOutput(), error: String(message || "") });
  console.error(message);
  process.exit(1);
}
