import { chromium } from "playwright";
const userDataDir = process.env.TRPG_BROWSER_USER_DATA_DIR;
const browserChannel = process.env.TRPG_BROWSER_CHANNEL || "chrome";
const context = await chromium.launchPersistentContext(userDataDir, { channel: browserChannel, headless: false, viewport: { width: 1440, height: 1000 } });
try {
  const page = context.pages()[0] || await context.newPage();
  await page.goto("https://chatgpt.com", { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.waitForLoadState("networkidle", { timeout: 30000 }).catch(() => {});
  const project = page.getByText("TRPG 自动主持", { exact: true }).first();
  if (await project.isVisible({ timeout: 5000 }).catch(() => false)) {
    await project.click({ force: true });
    await page.waitForTimeout(1800);
  }
  const text = await page.locator("body").innerText({ timeout: 10000 }).catch(() => "");
  const lines = text.split(/\n+/).map(s => s.trim()).filter(Boolean);
  for (const line of lines.slice(0, 220)) console.log(line);
} finally {
  await context.close();
}
