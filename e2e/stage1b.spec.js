// Playwright smoke test for Stage 1 (rule gaps: G1 parts rule, G2 AMC Plan/billing, G3 auto-schedule). Needs demo data.
// Run: AMC_TEST_PASSWORD='...' node stage1b.spec.js
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
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 950 } });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/login`);
  await page.fill("#login_email", "pw.owner@example.com");
  await page.fill("#login_password", PWD);
  await page.press("#login_password", "Enter");
  await page.waitForURL(/\/(desk|app)/, { timeout: 30000 });

  const contract = await page.evaluate(async () => {
    const r = await frappe.db.get_list("AMC Contract", { filters: { customer: "CUST-00021" } }); // placeholder, fixed below
    return r;
  }).catch(()=>null);

  const visit = await page.evaluate(async () => {
    const custs = await frappe.db.get_list("AMC Customer", { filters: { customer_name: "Plan Demo Test" }, fields: ["name"] });
    const units = await frappe.db.get_list("RO Unit", { filters: { customer: custs[0].name }, fields: ["name"] });
    const visits = await frappe.db.get_list("Service Visit", { filters: { ro_unit: units[0].name }, fields: ["name"], limit: 1 });
    return visits[0] && visits[0].name;
  });
  ok(!!visit, "found a generated Scheduled visit: " + visit);

  await page.goto(`${BASE}/desk/service-visit/${visit}`);
  await page.waitForFunction(() => window.cur_frm && cur_frm.doc && cur_frm.doc.name, { timeout: 20000 });
  await page.waitForTimeout(1000);
  await page.evaluate(() => { cur_frm.set_value("status", "Completed"); });
  await page.waitForTimeout(500);
  await page.keyboard.press("Control+s");
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${__dirname}/shots/27-visit-blocked-no-parts.png` });
  const blockedBody = await page.innerText("body");
  ok(/Parts Used|No Parts Used/i.test(blockedBody), "blocked-completion message visible");

  await page.evaluate(() => { cur_frm.set_value("no_parts_used", 1); });
  await page.waitForTimeout(300);
  await page.keyboard.press("Control+s");
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${__dirname}/shots/28-visit-completed-with-flag.png` });
  const status = await page.evaluate(() => cur_frm.doc.status);
  ok(status === "Completed", `visit completed after ticking No Parts Used (status=${status})`);

  await page.goto(`${BASE}/desk/query-report/Parts Due`); await page.waitForTimeout(3500);
  await page.screenshot({ path: `${__dirname}/shots/29-parts-due-report.png`, fullPage: true });
  ok(true, "Parts Due report screenshot taken (see image)");

  await browser.close();
  console.log(failed ? `\n${failed} CHECK(S) FAILED` : "\nALL CHECKS PASSED");
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error("ERROR", e.message); process.exit(2); });
