// End to end (synthetic data only): Dogri is hidden from the language pickers, the development OTP is shown as a
// labelled demo notification, a self-registered doctor is Pending until an administrator approves, and every role
// lands on its own dashboard (decided by the server's account data).
import { launch } from "./cdp.mjs";

const [, , BROWSER, SEED_PW] = process.argv;
const APP = process.env.E2E_APP || "http://127.0.0.1:5173/";
const API = process.env.E2E_API || "http://127.0.0.1:8000/api";
const results = [];
const check = (name, ok, extra = "") => { results.push({ name, ok }); console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? "  — " + String(extra).slice(0, 200) : ""}`); };
const page = await launch({ browser: BROWSER });
const t = (js) => page.eval(`window.__t.${js}`);
const post = (path, body, token) => page.eval(`fetch('${API}${path}', {method:'POST', headers:{'Content-Type':'application/json'${token ? `, 'Authorization':'Bearer ${token}'` : ""}}, body: JSON.stringify(${JSON.stringify(body)})}).then(async r => ({status:r.status, body: await r.json().catch(() => ({}))}))`);
const stamp = Date.now().toString().slice(-7);
const DOC_EMAIL = `e2e.doctor${stamp}@example.com`;
const DOC_PW = `E2E-Doctor-${stamp}`;
const login = async (id, pw) => {
  await page.goto(APP);
  await page.waitFor("window.__t.has('Your Language') || document.querySelector('.auth-form') || document.querySelector('.staff-layout')", 20000);
  await page.eval("sessionStorage.clear()");
  await page.goto(APP);
  await page.waitFor("window.__t.has('Log in') || window.__t.has('Login')", 20000);
  await t("btn('Log in')").catch(() => {});
};

try {
  await page.goto(APP);
  await page.waitFor("document.body.innerText.length > 50", 20000);

  // ---- Dogri is not offered anywhere ----
  const optionsOf = "[...document.querySelectorAll('select option')].map(o => o.value + '|' + o.innerText)";
  const opts = await page.eval(optionsOf);
  check("language pickers do not offer Dogri", !opts.some((o) => /doi|Dogri|डोगरी/.test(o)), opts.join(", "));
  check("English, Hindi and Urdu are still offered", ["en|", "hi|", "ur|"].every((p) => opts.some((o) => o.startsWith(p))), opts.join(", "));

  // ---- doctor registration (API) then UI behaviour ----
  const reg = await post("/doctors/register", {
    full_name: `Dr E2E ${stamp}`, email: DOC_EMAIL, phone: "93" + stamp.padStart(8, "0"), password: DOC_PW,
    qualification: "MBBS", specialization: "General Medicine", registration_number: `E2E/${stamp}`,
    registration_authority: "Synthetic Council", hospital_name: "Synthetic Hospital", years_experience: 4,
  });
  check("doctor registration is accepted as pending", reg.status === 201 && reg.body.user.verification_status === "pending", JSON.stringify(reg.body).slice(0, 120));
  const pendingToken = reg.body.access_token;
  const blocked = await page.eval(`fetch('${API}/queue', {headers:{Authorization:'Bearer ${pendingToken}'}}).then(r => r.status)`);
  check("a pending doctor's token is refused by doctor endpoints (403)", blocked === 403, blocked);

  await page.eval(`sessionStorage.setItem('healthspeak.token', ${JSON.stringify(pendingToken)})`);
  await page.goto(APP);
  await page.waitFor("document.querySelector('[data-testid=pending-verification]')", 20000);
  check("a pending doctor lands on the Pending Verification page", true);
  const text = await page.eval("document.body.innerText");
  check("the pending page shows no patient queue or intake data", !/Patients assigned to me|SYMPTOMS|Token/i.test(text));

  // ---- administrator approves ----
  const adm = await post("/auth/login", { identifier: "admin@example.com", password: SEED_PW });
  const apps = await page.eval(`fetch('${API}/admin/doctors?status=pending', {headers:{Authorization:'Bearer ${adm.body.access_token}'}}).then(r => r.json())`);
  const mine = apps.items.find((a) => a.user.email === DOC_EMAIL);
  check("the administrator sees the application", Boolean(mine));
  const ap = await post(`/admin/doctors/${mine.user.id}/approve`, { note: "e2e check" }, adm.body.access_token);
  check("the administrator approves it", ap.status === 200 && ap.body.profile.verification_status === "approved");
  await t("btn('Check again')");
  await page.waitFor("window.__t.has('DOCTOR DASHBOARD') || document.querySelector('.staff-layout')", 20000);
  check("after approval the doctor reaches the Doctor Dashboard", await page.eval("document.body.innerText.includes('DOCTOR DASHBOARD')"));
  check("the doctor dashboard is not the patient dashboard", !(await page.eval("document.body.innerText.includes('Start Text Chat')")));

  // ---- other roles ----
  for (const [email, expect, label] of [["patient@example.com", "Start Text Chat", "patient"], ["staff@example.com", "STAFF", "staff"], ["admin@example.com", "DOCTOR VERIFICATION", "admin"]]) {
    const r = await post("/auth/login", { identifier: email, password: SEED_PW });
    await page.eval(`sessionStorage.setItem('healthspeak.token', ${JSON.stringify(r.body.access_token)})`);
    await page.goto(APP);
    await page.waitFor(`document.body.innerText.includes(${JSON.stringify(expect)})`, 20000)
      .then(() => check(`${label} lands on its own dashboard`, true))
      .catch(() => check(`${label} lands on its own dashboard`, false, "missing " + expect));
  }

  // ---- demo OTP notification (forgot password, development mode) ----
  await page.eval("sessionStorage.clear()");
  await page.goto(APP);
  await page.waitFor("document.body.innerText.length > 50", 20000);
  const sms = await page.eval(`fetch('${API}/auth/password-reset/request', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({identifier:'+919000000001'})}).then(r => r.json())`);
  check("the API returns the demo code only in development mode", Boolean(sms.dev_code) && /Development mode/.test(sms.dev_notice || ""), JSON.stringify(sms).slice(0, 100));
} catch (e) {
  check("suite ran to the end", false, e.message);
} finally {
  const failed = results.filter((r) => !r.ok).length;
  console.log(`\n${results.length - failed} passed, ${failed} failed`);
  await page.close();
  process.exit(failed ? 1 : 0);
}
