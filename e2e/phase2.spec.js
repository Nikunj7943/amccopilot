// Playwright smoke test for AMCPilot Phase 2 (AMC Contract, Service Visit). Needs demo data.
// Run: AMC_TEST_PASSWORD='...' node phase2.spec.js
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

  await page.goto(`${BASE}/desk/amcpilot`); await page.waitForTimeout(3000);
  await page.screenshot({ path: `${__dirname}/shots/08-workspace-p2.png` });
  const body = await page.innerText("body");
  ok(body.includes("AMC Contract"), "workspace shows AMC Contract");
  ok(body.includes("Service Visit"), "workspace shows Service Visit");

  await page.goto(`${BASE}/desk/amc-contract`); await page.waitForTimeout(3000);
  await page.screenshot({ path: `${__dirname}/shots/09-contract-list.png` });
  ok((await page.innerText("body")).includes("Ramesh"), "contract list shows demo contract");

  const contractName = await page.evaluate(async () => {
    const r = await frappe.db.get_list("AMC Contract", { filters: { status: "Draft" }, fields: ["name"], limit: 1 });
    return r[0] && r[0].name;
  });
  await page.goto(`${BASE}/desk/amc-contract/${contractName}`); await page.waitForTimeout(3000);
  await page.screenshot({ path: `${__dirname}/shots/10-contract-draft.png` });
  ok(await page.locator("button:has-text('Activate')").count() > 0, "Activate button shown for Draft contract");
  await page.locator("button:has-text('Activate')").click();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${__dirname}/shots/11-contract-active.png` });
  const status = await page.evaluate(() => cur_frm.doc.status);
  ok(status === "Active", `contract activated (status=${status})`);
  ok(await page.locator("button:has-text('Cancel Contract')").count() > 0, "Cancel Contract button shown for Active");

  // completed visit shows filter row updated + contract visits_used
  const visitName = await page.evaluate(async () => {
    const r = await frappe.db.get_list("Service Visit", { filters: { status: "Completed" }, fields: ["name"], limit: 1 });
    return r[0] && r[0].name;
  });
  await page.goto(`${BASE}/desk/service-visit/${visitName}`); await page.waitForTimeout(3000);
  await page.screenshot({ path: `${__dirname}/shots/12-visit-completed.png` });
  const covered = await page.evaluate(() => cur_frm.doc.covered_by_contract);
  ok(covered === 1, "completed demo visit is covered_by_contract");

  await browser.close();
  console.log(failed ? `\n${failed} CHECK(S) FAILED` : "\nALL CHECKS PASSED");
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error("ERROR", e.message); process.exit(2); });
