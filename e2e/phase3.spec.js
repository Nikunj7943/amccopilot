// Playwright smoke test for AMCPilot Phase 3 (Reminders page, Message Template). Needs demo data.
// Run: AMC_TEST_PASSWORD='...' node phase3.spec.js
const { chromium } = require("playwright");
const fs = require("fs"); const path = require("path");
const BASE = "http://localhost:8008";
const PWD = process.env.AMC_TEST_PASSWORD;
if (!PWD) { console.error("Set AMC_TEST_PASSWORD"); process.exit(2); }
const CHROME = `${process.env.HOME}/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell`;
let failed = 0;
const ok = (c, m) => { console.log((c ? "PASS " : "FAIL ") + m); if (!c) failed++; };
(async () => {
  const browser = await chromium.launch({ executablePath: CHROME });
  const ctx = await browser.newContext({ viewport: { width: 1360, height: 850 } });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/login`);
  await page.fill("#login_email", "pw.owner@example.com");
  await page.fill("#login_password", PWD);
  await page.press("#login_password", "Enter");
  await page.waitForURL(/\/(desk|app)/, { timeout: 30000 });

  await page.goto(`${BASE}/app/amcpilot-reminders`); await page.waitForTimeout(3000);
  await page.screenshot({ path: `${__dirname}/shots/13-reminders-page.png` });
  const body = await page.innerText("body");
  ok(body.includes("Due Soon Test"), "renewals section shows the due-soon demo customer");
  ok(/AMC Renewals Due/.test(body), "page has Renewals section");
  ok(/Filters Due/.test(body), "page has Filters Due section");
  ok(await page.locator("a:has-text('Send on WhatsApp')").count() > 0, "WhatsApp send links present");
  const href = await page.locator("a:has-text('Send on WhatsApp')").first().getAttribute("href");
  ok(href.startsWith("https://wa.me/91"), `wa.me link looks right (${href.slice(0,40)}...)`);

  await page.goto(`${BASE}/desk/message-template`); await page.waitForTimeout(2500);
  await page.screenshot({ path: `${__dirname}/shots/14-message-templates.png` });
  ok((await page.innerText("body")).includes("Renewal Reminder"), "default templates visible in list");

  await browser.close();
  console.log(failed ? `\n${failed} CHECK(S) FAILED` : "\nALL CHECKS PASSED");
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error("ERROR", e.message); process.exit(2); });
