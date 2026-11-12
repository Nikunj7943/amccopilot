// Playwright smoke test for AMCPilot. Dev site only.
// One-time setup:  cd apps/amc_pilot/e2e && npm init -y && npm i playwright   (and a Chromium, e.g. npx playwright install chromium)
// Run:  AMC_TEST_PASSWORD='<password of pw.owner@example.com and pw.tech@example.com>' node amc.spec.js
// Needs: bench server on :8008 and demo data (bench --site amcpilot.localhost execute amc_pilot.amcpilot.dev.seed.run)
const { chromium } = require("playwright");
const fs = require("fs");
const path = require("path");
const BASE = process.env.BASE || "http://localhost:8008";
const PWD = process.env.AMC_TEST_PASSWORD;
if (!PWD) { console.error("Set AMC_TEST_PASSWORD"); process.exit(2); }
const SHOTS = path.join(__dirname, "shots");
fs.mkdirSync(SHOTS, { recursive: true });
const CHROME = process.env.CHROME ||
  `${process.env.HOME}/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell`;

let failed = 0;
const ok = (c, m) => { console.log((c ? "PASS " : "FAIL ") + m); if (!c) failed++; };

async function login(browser, user) {
  const ctx = await browser.newContext({ viewport: { width: 1360, height: 850 } });
  const page = await ctx.newPage();
  await page.goto(`${BASE}/login`);
  await page.fill("#login_email", user);
  await page.fill("#login_password", PWD);
  await page.press("#login_password", "Enter");
  await page.waitForURL(/\/(desk|app)/, { timeout: 30000 });
  return { ctx, page };
}

(async () => {
  const browser = await chromium.launch({ executablePath: CHROME });

  // ---------- AMC Owner ----------
  const { ctx, page } = await login(browser, "pw.owner@example.com");
  await page.goto(`${BASE}/desk`); await page.waitForTimeout(3000);
  await page.screenshot({ path: `${SHOTS}/01-desk-home.png` });
  ok((await page.content()).includes("AMCPilot"), "apps screen / desk shows AMCPilot");

  await page.goto(`${BASE}/desk/amcpilot`); await page.waitForTimeout(3000);
  await page.screenshot({ path: `${SHOTS}/02-workspace.png` });
  const body = await page.innerText("body");
  for (const t of ["AMC Customer", "RO Unit", "RO Model", "Service Part", "AMC Technician", "AMC Settings"])
    ok(body.includes(t), `workspace/sidebar shows "${t}"`);

  await page.goto(`${BASE}/desk/ro-unit`); await page.waitForTimeout(3000);
  await page.screenshot({ path: `${SHOTS}/03-ro-unit-list.png` });
  ok((await page.innerText("body")).includes("Ramesh Patel"), "RO Unit list shows demo data");

  // open the unit that has an install date and check filters + button
  const unitName = await page.evaluate(async () => {
    const r = await frappe.db.get_list("RO Unit", { filters: { customer_name: "Ramesh Patel" }, fields: ["name"], limit: 1 });
    return r[0] && r[0].name;
  });
  ok(!!unitName, "found demo RO Unit " + unitName);
  await page.goto(`${BASE}/desk/ro-unit/${unitName}`); await page.waitForTimeout(3500);
  await page.screenshot({ path: `${SHOTS}/04-ro-unit-form.png` });
  ok(await page.locator("button:has-text('Reload filters from model')").count() > 0, "Reload filters button visible for owner");
  const rows = await page.evaluate(() => cur_frm.doc.unit_filters.length);
  ok(rows === 3, `unit has 3 auto-filled filter rows (got ${rows})`);
  const due = await page.evaluate(() => cur_frm.doc.unit_filters.every(r => r.next_due_on));
  ok(due, "every filter row has next_due_on");
  await page.evaluate(() => cur_frm.page.btn_secondary && 0);
  await page.locator("button:has-text('Reload filters from model')").first().click();
  await page.waitForTimeout(2000);
  ok((await page.evaluate(() => cur_frm.doc.unit_filters.length)) === 3, "Reload with nothing missing changes nothing");

  // customer: mobile normalisation + rejection
  const mobile = "9" + String(Date.now()).slice(-9);
  const result = await page.evaluate(async (m) => {
    const out = {};
    try { await frappe.xcall("frappe.client.insert", { doc: { doctype: "AMC Customer", customer_name: "PW Bad", mobile_no: "12345" } }); out.bad = "saved"; }
    catch (e) { out.bad = "rejected"; }
    const d = await frappe.xcall("frappe.client.insert", { doc: { doctype: "AMC Customer", customer_name: "PW Temp", mobile_no: "+91 " + m.slice(0, 5) + "-" + m.slice(5) } });
    out.stored = d.mobile_no; out.name = d.name;
    await frappe.xcall("frappe.client.delete", { doctype: "AMC Customer", name: d.name });
    return out;
  }, mobile);
  ok(result.bad === "rejected", "invalid mobile rejected");
  ok(result.stored === mobile, `+91 number stored as 10 digits (${result.stored})`);

  // New customer form through the UI
  await page.goto(`${BASE}/desk/amc-customer/new`); await page.waitForTimeout(3000);
  await page.screenshot({ path: `${SHOTS}/05-customer-new.png` });
  await ctx.close();

  // ---------- AMC Technician ----------
  const t = await login(browser, "pw.tech@example.com");
  await t.page.goto(`${BASE}/desk/amc-customer`); await t.page.waitForTimeout(3000);
  await t.page.screenshot({ path: `${SHOTS}/06-technician-customer-list.png` });
  ok((await t.page.innerText("body")).includes("Ramesh Patel"), "technician can read customers");
  ok(await t.page.locator("button.primary-action:has-text('Add')").count() === 0, "technician has no Add button");
  const canCreate = await t.page.evaluate(() => frappe.model.can_create("AMC Customer"));
  const canWrite = await t.page.evaluate(() => frappe.model.can_write("AMC Customer"));
  ok(!canCreate && !canWrite, "technician cannot create/write (client perms)");
  await t.page.goto(`${BASE}/desk/ro-unit/${unitName}`); await t.page.waitForTimeout(3500);
  await t.page.screenshot({ path: `${SHOTS}/07-technician-unit-form.png` });
  ok(await t.page.locator("button:has-text('Reload filters from model')").count() === 0, "no Reload button for technician");
  await t.ctx.close();

  await browser.close();
  console.log(failed ? `\n${failed} CHECK(S) FAILED` : "\nALL CHECKS PASSED");
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error("ERROR", e.message); process.exit(2); });
