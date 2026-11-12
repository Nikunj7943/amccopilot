// Playwright smoke test for AMCPilot Phase 4 (AMC Payment, UPI fallback, Razorpay settings). Needs demo data.
// Run: AMC_TEST_PASSWORD='...' node phase4.spec.js
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

  await page.goto(`${BASE}/desk/amc-payment`); await page.waitForTimeout(3000);
  await page.screenshot({ path: `${__dirname}/shots/15-payment-list.png` });
  ok((await page.innerText("body")).includes("Paid"), "payment list shows the Paid demo payment");

  // AMC Settings shows Razorpay fields (empty = manual fallback mode)
  await page.goto(`${BASE}/desk/amc-settings`); await page.waitForTimeout(2500);
  let settingsBody = await page.innerText("body");
  ok(settingsBody.includes("Online Payment"), "AMC Settings shows Online Payment section");
  await page.locator("text=Online Payment (optional)").click();
  await page.waitForTimeout(500);
  settingsBody = await page.innerText("body");
  ok(settingsBody.includes("Razorpay Key ID"), "Razorpay Key ID field visible once section expanded");
  await page.screenshot({ path: `${__dirname}/shots/16-settings-razorpay.png` });

  // Create a fresh Draft contract via API, collect payment -> UPI fallback (no keys set)
  const result = await page.evaluate(async () => {
    const custs = await frappe.db.get_list("AMC Customer", { fields: ["name"], limit: 1 });
    const units = await frappe.db.get_list("RO Unit", { filters: { customer: custs[0].name }, fields: ["name"], limit: 1 });
    const contract = await frappe.xcall("frappe.client.insert", {
      doc: { doctype: "AMC Contract", customer: custs[0].name, ro_unit: units[0].name, start_date: frappe.datetime.get_today(), duration_months: 12, amount: 1999, visits_included: 2 },
    });
    const paymentName = await frappe.xcall("amc_pilot.amcpilot.services.payments.create_payment", { contract: contract.name });
    const options = await frappe.xcall("amc_pilot.amcpilot.services.payments.get_payment_options", { payment: paymentName });
    return { paymentName, options };
  });
  ok(result.options.method === "upi", `no Razorpay keys -> UPI fallback (got ${result.options.method})`);
  ok(result.options.upi_link && result.options.upi_link.startsWith("upi://pay"), "UPI link generated");

  await page.goto(`${BASE}/desk/amc-payment/${result.paymentName}`); await page.waitForTimeout(2500);
  await page.screenshot({ path: `${__dirname}/shots/17-payment-pending-form.png` });
  ok(await page.locator("button:has-text('Mark Paid Manually')").count() > 0, "Mark Paid Manually button visible");

  await browser.close();
  console.log(failed ? `\n${failed} CHECK(S) FAILED` : "\nALL CHECKS PASSED");
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error("ERROR", e.message); process.exit(2); });
