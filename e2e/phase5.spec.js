// Playwright smoke test for AMCPilot Phase 5 (guest QR page /ro/<token>, RO Unit QR button). Needs demo data.
// Run: AMC_TEST_PASSWORD='...' node phase5.spec.js
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

  // ---------- Guest, no login at all, fresh context ----------
  const guestCtx = await browser.newContext({ viewport: { width: 390, height: 844 } }); // phone-sized
  const guestPage = await guestCtx.newPage();
  const token = await (async () => {
    // fetch token via a quick authenticated call in a throwaway context isn't guest-safe,
    // so read it directly from a side-channel file written by console earlier is messy;
    // instead query via the (already logged-in) owner context below AFTER this block.
    return null;
  })();
  await guestCtx.close();

  // Get token as the owner first, then re-test the page as a pure guest.
  const ownerCtx = await browser.newContext({ viewport: { width: 1360, height: 850 } });
  const ownerPage = await ownerCtx.newPage();
  await ownerPage.goto(`${BASE}/login`);
  await ownerPage.fill("#login_email", "pw.owner@example.com");
  await ownerPage.fill("#login_password", PWD);
  await ownerPage.press("#login_password", "Enter");
  await ownerPage.waitForURL(/\/(desk|app)/, { timeout: 30000 });

  const realToken = await ownerPage.evaluate(async () => {
    const custs = await frappe.db.get_list("AMC Customer", { filters: { customer_name: "Ramesh Patel" }, fields: ["name"], limit: 1 });
    const units = await frappe.db.get_list("RO Unit", { filters: { customer: custs[0].name }, fields: ["name", "qr_token"], limit: 1 });
    return units[0].qr_token;
  });
  ok(!!realToken, "fetched a real qr_token as owner");

  // RO Unit form shows "Show QR / Customer Link" and renders an image
  const unitName = await ownerPage.evaluate(async (t) => {
    const r = await frappe.db.get_list("RO Unit", { filters: { qr_token: t }, fields: ["name"] });
    return r[0].name;
  }, realToken);
  await ownerPage.goto(`${BASE}/desk/ro-unit/${unitName}`); await ownerPage.waitForTimeout(3000);
  await ownerPage.locator("button:has-text('Show QR')").click();
  await ownerPage.waitForTimeout(1500);
  await ownerPage.screenshot({ path: `${__dirname}/shots/18-ro-unit-qr-dialog.png` });
  ok(await ownerPage.locator(".modal img").count() > 0, "QR dialog shows an image");
  ok((await ownerPage.innerText(".modal")).includes(`/ro/${realToken}`), "QR dialog shows the customer link URL");
  await ownerCtx.close();

  // ---------- True guest: brand-new context, no cookies, no login ----------
  const guest2 = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const gp = await guest2.newPage();
  await gp.goto(`${BASE}/ro/${realToken}`);
  await gp.waitForTimeout(1500);
  await gp.screenshot({ path: `${__dirname}/shots/19-guest-qr-page.png` });
  const gbody = await gp.innerText("body");
  ok(gbody.includes("Ramesh Patel"), "guest page shows the customer name");
  ok(gbody.includes("Aqua 7L"), "guest page shows the model");
  ok(gbody.includes("Request a Service Visit"), "guest page shows the request button");
  ok(!gbody.includes("9825011001"), "guest page does not leak the customer's mobile number");

  await gp.locator("#request-btn").click();
  await gp.waitForTimeout(2000);
  await gp.screenshot({ path: `${__dirname}/shots/20-guest-after-request.png` });
  const afterBody = await gp.innerText("body");
  ok(/Request sent|already requested/i.test(afterBody), "clicking Request shows a confirmation");

  // bad token -> redirected home, not a crash
  const resp = await gp.goto(`${BASE}/ro/totally-invalid-token-xyz`);
  ok(resp.status() < 500, `bad token does not 500 (got ${resp.status()})`);

  await guest2.close();
  await browser.close();
  console.log(failed ? `\n${failed} CHECK(S) FAILED` : "\nALL CHECKS PASSED");
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error("ERROR", e.message); process.exit(2); });
