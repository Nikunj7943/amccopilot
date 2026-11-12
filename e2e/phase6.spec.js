// Playwright smoke test for AMCPilot Phase 6 (dashboard: number cards + charts). Needs demo data.
// Run: AMC_TEST_PASSWORD='...' node phase6.spec.js
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
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/login`);
  await page.fill("#login_email", "pw.owner@example.com");
  await page.fill("#login_password", PWD);
  await page.press("#login_password", "Enter");
  await page.waitForURL(/\/(desk|app)/, { timeout: 30000 });

  await page.goto(`${BASE}/desk/amcpilot`); await page.waitForTimeout(4000);
  await page.waitForSelector("text=Filters Overdue", { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(3000);
  await page.screenshot({ path: `${__dirname}/shots/21-dashboard.png`, fullPage: true });
  const body = await page.innerText("body");
  ok(body.includes("Active Contracts"), "shows Active Contracts stat card");
  ok(body.includes("Filters Overdue"), "shows Filters Overdue stat card");
  ok(body.includes("Contracts by Status"), "shows Contracts by Status chart title");
  ok(body.includes("Payments Collected"), "shows Payments Collected chart title");
  ok(await page.locator(".widget-head:has-text('Active Contracts'), .widget-head:has-text('Customers'), .widget-head:has-text('RO Units Active'), .widget-head:has-text('Payments Pending'), .widget-head:has-text('Visits Scheduled'), .widget-head:has-text('Filters Overdue')").count() >= 6, "all 6 number card widgets rendered");
  ok(await page.locator("svg").count() > 0, "at least one SVG chart rendered");

  await browser.close();
  console.log(failed ? `\n${failed} CHECK(S) FAILED` : "\nALL CHECKS PASSED");
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error("ERROR", e.message); process.exit(2); });
