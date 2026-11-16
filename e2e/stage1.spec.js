// Playwright smoke test for Stage 1 (rule gaps: G1 parts rule, G2 AMC Plan/billing, G3 auto-schedule). Needs demo data.
// Run: AMC_TEST_PASSWORD='...' node stage1.spec.js
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

  // AMC Plan list
  await page.goto(`${BASE}/desk/amc-plan`); await page.waitForTimeout(2500);
  await page.screenshot({ path: `${__dirname}/shots/24-amc-plan-list.png` });
  ok((await page.innerText("body")).includes("Comprehensive"), "AMC Plan list shows seeded plans");

  // Priya's draft contract (has plan set) -> Activate -> visits generated
  const draft = await page.evaluate(async () => {
    const r = await frappe.db.get_list("AMC Contract", { filters: { status: "Draft" }, fields: ["name"], limit: 1 });
    return r[0] && r[0].name;
  });
  await page.goto(`${BASE}/desk/amc-contract/${draft}`); await page.waitForTimeout(2500);
  await page.screenshot({ path: `${__dirname}/shots/25-contract-with-plan.png` });
  ok((await page.innerText("body")).includes("Standard AMC"), "contract shows its Plan");
  await page.locator("button:has-text('Activate')").click();
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${__dirname}/shots/26-contract-activated.png` });
  const visitCount = await page.evaluate(async (c) => {
    const r = await frappe.db.get_list("Service Visit", { filters: { contract: c }, fields: ["name"] });
    return r.length;
  }, draft);
  ok(visitCount > 0, `Activate generated ${visitCount} scheduled visit(s)`);

  // Service Visit: try to complete with no parts -> blocked message
  const visit = await page.evaluate(async (c) => {
    const r = await frappe.db.get_list("Service Visit", { filters: { contract: c }, fields: ["name"], limit: 1 });
    return r[0] && r[0].name;
  }, draft);
  await page.goto(`${BASE}/desk/service-visit/${visit}`); await page.waitForTimeout(2500);
  await page.locator("select[data-fieldname='status'], input[data-fieldname='status']").first().selectOption({ label: "Completed" }).catch(()=>{});
  await page.evaluate(() => { cur_frm.set_value("status", "Completed"); });
  await page.waitForTimeout(500);
  await page.locator(".primary-action:has-text('Save'), button:has-text('Save')").first().click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${__dirname}/shots/27-visit-blocked-no-parts.png` });
  const blockedBody = await page.innerText("body");
  ok(/Parts Used|No Parts Used/i.test(blockedBody), "blocked-completion message visible");

  // tick No Parts Used and save -> should succeed
  await page.evaluate(() => { cur_frm.set_value("no_parts_used", 1); });
  await page.waitForTimeout(300);
  await page.keyboard.press("Control+s");
  await page.waitForTimeout(2000);
  await page.screenshot({ path: `${__dirname}/shots/28-visit-completed-with-flag.png` });
  const status = await page.evaluate(() => cur_frm.doc.status);
  ok(status === "Completed", `visit completed after ticking No Parts Used (status=${status})`);

  // Parts Due report loads
  await page.goto(`${BASE}/desk/query-report/Parts Due`); await page.waitForTimeout(3000);
  await page.screenshot({ path: `${__dirname}/shots/29-parts-due-report.png` });
  ok((await page.innerText("body")).includes("Parts Due") || (await page.innerText("body")).includes("Service Part"), "Parts Due report page loads");

  await browser.close();
  console.log(failed ? `\n${failed} CHECK(S) FAILED` : "\nALL CHECKS PASSED");
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error("ERROR", e.message); process.exit(2); });
