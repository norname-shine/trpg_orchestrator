import fs from "node:fs";
import { chromium } from "playwright";

const args = parseArgs(process.argv.slice(2));
const inputPath = requiredArg(args, "input");
const outputPath = requiredArg(args, "output");
const projectName = requiredArg(args, "project");
const conversationName = requiredArg(args, "conversation");
const captureOnly = args["capture-only"] === "true";
const userDataDir = process.env.TRPG_BROWSER_USER_DATA_DIR;
const browserChannel = process.env.TRPG_BROWSER_CHANNEL || "chrome";
const cdpUrl = process.env.TRPG_BROWSER_CDP_URL || "http://127.0.0.1:9222";
const M = {
  body: "\u3010\u6b63\u6587\u3011",
  choices: "\u3010\u9009\u62e9\u70b9\u3011",
  summary: "\u3010\u56de\u5408\u6458\u8981\u3011",
  writebackBegin: "\u3010\u72b6\u6001\u56de\u5199_BEGIN\u3011",
  writebackEnd: "\u3010\u72b6\u6001\u56de\u5199_END\u3011",
};

if (!userDataDir) fail("TRPG_BROWSER_USER_DATA_DIR is required for Playwright automation.");

const inputText = captureOnly ? "" : fs.readFileSync(inputPath, "utf8");
let shouldCloseBrowser = false;
const browser = await openBrowser();
try {
  const page = await chatgptPage(browser);
  await safetyCheck(page);
  await openProject(page, projectName);
  await openConversation(page, conversationName);
  await safetyCheck(page);
  if (captureOnly) {
    const latest = await latestAssistantText(page);
    if (!isCompleteReply(latest)) fail("Latest assistant reply is missing required markers.");
    fs.writeFileSync(outputPath, latest.trim() + "\n", "utf8");
    console.log(`Captured latest assistant reply: ${latest.length} chars`);
  } else {
  await fillComposer(page, inputText);
  await clickSend(page);
  let latest = await waitForAssistantCompletion(page);

  if (!isCompleteReply(latest)) {
    const continued = await clickContinueOnce(page);
    if (continued) latest = await waitForAssistantCompletion(page);
  }

  if (!isCompleteReply(latest) && hasContentButMissingWriteback(latest)) {
    await requestWritebackOnly(page);
    const补 = await waitForAssistantCompletion(page);
    latest = mergeWriteback(latest, 补);
  }

  if (!isCompleteReply(latest)) {
    fs.writeFileSync(outputPath, latest.trim() + "\n", "utf8");
    fail("Latest ChatGPT reply is incomplete or missing required markers after recovery attempt.");
  }

  fs.writeFileSync(outputPath, latest.trim() + "\n", "utf8");
  console.log(`Captured complete assistant reply: ${latest.length} chars`);
  }
} finally {
  if (shouldCloseBrowser) await browser.close();
}

async function openBrowser() {
  try {
    return await chromium.connectOverCDP(cdpUrl);
  } catch {
    const context = await chromium.launchPersistentContext(userDataDir, {
      channel: browserChannel,
      headless: false,
      viewport: { width: 1440, height: 1000 },
    });
    shouldCloseBrowser = true;
    return { contexts: () => [context], close: () => context.close() };
  }
}

async function chatgptPage(browser) {
  const context = browser.contexts()[0];
  const page = context.pages().find((p) => p.url().includes("chatgpt.com")) || await context.newPage();
  if (!page.url().includes("chatgpt.com")) {
    await page.goto("https://chatgpt.com", { waitUntil: "domcontentloaded", timeout: 60000 });
  }
  await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
  return page;
}

async function openProject(page, name) {
  if (await page.getByText(name, { exact: true }).first().isVisible({ timeout: 3000 }).catch(() => false)) {
    await page.getByText(name, { exact: true }).first().click({ force: true });
    await page.waitForTimeout(1000);
    return;
  }
  fail(`Project not found: ${name}`);
}

async function openConversation(page, name) {
  if (await page.getByText(name, { exact: true }).first().isVisible({ timeout: 3000 }).catch(() => false)) {
    await page.getByText(name, { exact: true }).first().click({ force: true });
    await page.waitForTimeout(1200);
    return;
  }
  fail(`Fixed conversation not found: ${name}`);
}

async function safetyCheck(page) {
  const text = (await page.locator("body").innerText({ timeout: 10000 }).catch(() => "")).toLowerCase();
  const blocked = [
    "log in", "sign in", "captcha", "verification", "verify your identity",
    "payment", "billing", "subscription", "account settings", "privacy settings", "security settings",
    "\u8d26\u53f7\u8bbe\u7f6e", "\u5b89\u5168\u9a8c\u8bc1", "\u9a8c\u8bc1\u7801", "\u652f\u4ed8", "\u8ba2\u9605", "\u9690\u79c1\u8bbe\u7f6e",
  ];
  const found = blocked.find((term) => text.includes(term.toLowerCase()));
  if (found) fail(`Blocked browser state detected: ${found}`);
}

async function fillComposer(page, text) {
  const selectors = ['[data-testid="prompt-textarea"]', 'textarea', '[contenteditable="true"]', '.ProseMirror'];
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
      await locator.click({ timeout: 10000 });
      return;
    }
  }
  fail("Send button not found.");
}

async function waitForAssistantCompletion(page) {
  let stableCount = 0;
  let lastText = "";
  for (let i = 0; i < 240; i += 1) {
    await safetyCheck(page);
    const text = await latestAssistantText(page);
    const stopVisible = await page.locator('[data-testid="stop-button"], button[aria-label*="Stop"], button[aria-label*="停止"]').first().isVisible({ timeout: 500 }).catch(() => false);
    if (text && text === lastText && !stopVisible) stableCount += 1;
    else { stableCount = 0; lastText = text; }
    if (stableCount >= 5 && text) return text;
    await page.waitForTimeout(1000);
  }
  return lastText;
}

async function latestAssistantText(page) {
  const locators = page.locator('[data-message-author-role="assistant"]');
  const count = await locators.count().catch(() => 0);
  for (let i = count - 1; i >= 0; i -= 1) {
    const text = await locators.nth(i).innerText({ timeout: 1000 }).catch(() => "");
    if (text.includes(M.body) || text.includes(M.writebackBegin) || text.includes(M.choices)) return text;
  }
  return "";
}

async function clickContinueOnce(page) {
  const candidates = [
    page.getByText("Continue generating", { exact: true }),
    page.getByText("\u7ee7\u7eed\u751f\u6210", { exact: true }),
    page.locator('button[aria-label*="Continue"]'),
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
  const prompt = "只补全上一条回复缺失的状态回写 JSON，不要重写正文。必须从【状态回写_BEGIN】开始，到【状态回写_END】结束。";
  await fillComposer(page, prompt);
  await clickSend(page);
}

function mergeWriteback(original, supplement) {
  if (original.includes(M.writebackBegin) && !original.includes(M.writebackEnd) && supplement.includes(M.writebackBegin)) {
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
  return Object.values(M).every((marker) => text.includes(marker));
}

function parseArgs(argv) {
  const result = {};
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i]?.replace(/^--/, "");
    const value = argv[i + 1];
    if (key) result[key] = value;
  }
  return result;
}

function requiredArg(args, key) {
  if (!args[key]) fail(`missing --${key}`);
  return args[key];
}

function fail(message) {
  console.error(message);
  process.exit(1);
}
