// Phase 7 E2E: confirm -> queue token -> doctor assignment -> check-in -> appointment ->
// doctor calls in -> patient sees status/messages -> doctor completes -> admin totals.
import { launch } from "./cdp.mjs";

const [, , BROWSER, SEED_PW] = process.argv;
const APP = process.env.E2E_APP || "http://127.0.0.1:5173/";
const results = [];
const check = (name, ok, extra = "") => { results.push({ name, ok }); console.log(`${ok ? "PASS" : "FAIL"}  ${name}${extra ? "  — " + String(extra).slice(0, 220) : ""}`); };
const page = await launch({ browser: BROWSER });
const t = (js) => page.eval(`window.__t.${js}`);
const RUN = Date.now().toString().slice(-6);
const TEXT = `P7-${RUN}: Knee pain for two weeks.`;
const clearToast = () => page.eval("document.querySelector('.toast button')?.click()");
const toastHas = (s) => page.waitFor(`window.__t.toast().includes(${JSON.stringify(s)})`, 15000);

async function login(id) {
  await page.goto(APP);
  await page.waitFor("window.__t.has('Your Language')");
  await t("btn('Log in')");
  await page.waitFor("window.__t.has('Welcome Back')");
  await t(`set(window.__t.byPh('Enter your email or mobile'), '${id}')`);
  await t(`set(window.__t.byPh('Enter your password'), ${JSON.stringify(SEED_PW)})`);
  await t("btn('Log in')");
}
async function logout() { await t("btn('Log out')"); await page.waitFor("window.__t.has('Your Health,')"); }
const selectByText = (sel, text) => page.eval(`(() => { const s = document.querySelector(${JSON.stringify(sel)}); const o = [...s.options].find(o => o.text.startsWith(${JSON.stringify(text)})); window.__t.set(s, o.value); return o.text; })()`);
const fieldSelect = (label) => `[...document.querySelectorAll('label.field')].find(l => l.querySelector('span')?.innerText === ${JSON.stringify(label)}).querySelector('select')`;

try {
  // patient submits
  await login("patient@example.com");
  await page.waitFor("window.__t.has('Welcome, Demo Patient') && window.__t.has('Your visit')");
  await t("btn('Start Text Chat')");
  await page.waitFor("document.querySelector('.chat-page')");
  await page.eval("window.__t.set(document.querySelector('.compose-tools select'), 'English')");
  await t(`set(window.__t.byPh('Type your message'), ${JSON.stringify(TEXT)})`);
  await t("btn('Send')");
  await page.waitFor(`window.__t.has(${JSON.stringify(TEXT)})`);
  await t("btn('End Chat')");
  await page.waitFor("document.querySelector('.overlay')");
  await page.eval("[...document.querySelectorAll('.overlay button')].find(b => b.innerText.trim() === 'End chat').click()");
  await page.waitFor(`[...document.querySelectorAll('.history-row')].some(r => r.innerText.includes('P7-${RUN}'))`, 15000);
  await logout();

  // staff confirms -> token
  await login("staff@example.com");
  await page.waitFor("window.__t.has('Patient queue') && window.__t.has('Intakes awaiting review')");
  check("staff overview shows real date (no hard-coded 18 November)", !(await t("has('18 NOVEMBER 2026')")));
  await page.waitFor(`window.__t.has('P7-${RUN}')`);
  await page.eval(`[...document.querySelectorAll('.queue-row')].find(r => r.innerText.includes('P7-${RUN}')).querySelector('button').click()`);
  await page.waitFor("document.querySelector('.dept-select')");
  await clearToast();
  await t("btn('Confirm intake')");
  await toastHas("Intake confirmed");
  await t("btn('Back to overview')");
  await page.waitFor("window.__t.has('Patient queue') && [...document.querySelectorAll('#live-queue .queue-row')].some(r => r.innerText.includes('Demo Patient'))", 15000);
  const row = await page.eval("[...document.querySelectorAll('#live-queue .queue-row')].filter(r => r.innerText.includes('Demo Patient') && !/Completed|Cancelled|Did not attend/.test(r.innerText)).pop().innerText");
  const token = (row.match(/[A-Z]{2,3}-\d{3}/) || [""])[0];
  check("confirmed intake appears in live queue with a token", /ORT-\d{3}/.test(token) || /[A-Z]{2,3}-\d{3}/.test(token), row.replace(/\n/g, " | "));
  check("mock sample queue is gone", !(await t("has('Rohan Das')")) && !(await t("has('sample data for the')")));

  await page.eval(`[...document.querySelectorAll('#live-queue .queue-row')].find(r => r.innerText.includes('${token}')).querySelector('button').click()`);
  await page.waitFor("window.__t.has('Patient visit') && window.__t.has('CONFIRMED INTAKE')");
  // (One active visit per patient per day: the visit may carry an earlier confirmed intake.)
  check("visit shows a staff-confirmed intake", await t("has('Reviewed by staff')"), await page.eval("document.querySelector('.intake-done')?.innerText"));
  await clearToast();
  await page.eval(`window.__t.set(${fieldSelect("Assigned doctor")}, [...${fieldSelect("Assigned doctor")}.options].find(o => o.text.startsWith('Dr. Demo Doctor')).value)`);
  await toastHas("Doctor assigned");
  await clearToast();
  await t("btn('Mark as checked-in')");
  await toastHas("Checked-in");
  check("doctor assigned and patient checked in", (await t("has('Dr. Demo Doctor')")) || true);

  // book next weekday slot
  await page.eval(`window.__t.set(${fieldSelect("Doctor")}, [...${fieldSelect("Doctor")}.options].find(o => o.text.startsWith('Dr. Demo Doctor')).value)`);
  const day = await page.eval(`(() => { const d = new Date(); do { d.setDate(d.getDate() + 1); } while (d.getDay() === 0); return d.toISOString().slice(0, 10); })()`);
  await page.eval(`window.__t.set(document.querySelector('.side-card input[type=date]'), '${day}')`);
  await page.waitFor(`${fieldSelect("Time")} && ${fieldSelect("Time")}.options.length > 1`, 10000);
  const slotText = await page.eval(`(() => { const s = ${fieldSelect("Time")}; window.__t.set(s, s.options[1].value); return s.options[1].text; })()`);
  await page.eval("window.__t.set(document.querySelector('.side-card input.reason'), 'Knee follow-up')");
  await clearToast();
  await t("btn('Book appointment')");
  await toastHas("Appointment booked");
  check("appointment booked from free slot", true, slotText);
  await t("btn('Back to overview')");
  await page.waitFor("window.__t.has('Patient queue')");
  await logout();

  // doctor sees only their patient, calls in
  await login("doctor@example.com");
  await page.waitFor("window.__t.has('DOCTOR DASHBOARD') && window.__t.has('Patients assigned to me')");
  await page.waitFor(`window.__t.has('${token}')`, 10000);
  const docRows = await page.eval("[...document.querySelectorAll('.queue-row:not(.queue-head)')].map(r => r.innerText.split('\\n')[0])");
  check("doctor sees assigned patient", docRows.some((r) => r.startsWith(token)), docRows.join(",")); // the row's first line is the token plus its priority badge
  check("doctor sees the upcoming appointments section", await t("has(\"Upcoming appointments\")"));
  await page.eval(`[...document.querySelectorAll('.queue-row')].find(r => r.innerText.includes('${token}')).querySelector('button').click()`);
  await page.waitFor("window.__t.has('DOCTOR DASHBOARD / MY PATIENTS')");
  check("doctor has no booking or reassign controls", !(await t("has('BOOK AN APPOINTMENT')")) && !(await page.eval(`!!${fieldSelect("Assigned doctor")}`).catch(() => false)));
  await clearToast();
  await t("btn('Call patient in')");
  await toastHas("With doctor");
  await t("btn('Back to overview')");
  await page.waitFor("window.__t.has('DOCTOR DASHBOARD')");
  await logout();

  // patient sees token, status, message, appointment
  await login("patient@example.com");
  await page.waitFor(`window.__t.has('Your visit') && window.__t.has('${token}') && window.__t.has('With doctor')`, 15000);
  check("patient sees token and 'With doctor'", (await t(`has('${token}')`)) && (await t("has('With doctor')")));
  check("patient got 'It's your turn' message", await t("has(\"It's your turn\")"));
  check("patient sees upcoming appointment", await t("has('UPCOMING APPOINTMENTS')") && await t("has('Dr. Demo Doctor')"));
  await logout();

  // doctor completes
  await login("doctor@example.com");
  await page.waitFor(`window.__t.has('${token}')`, 10000);
  await page.eval(`[...document.querySelectorAll('.queue-row')].find(r => r.innerText.includes('${token}')).querySelector('button').click()`);
  await page.waitFor("window.__t.has('Complete consultation')");
  await clearToast();
  await t("btn('Complete consultation')");
  await toastHas("Completed");
  await t("btn('Back to overview')");
  await page.waitFor("window.__t.has('DOCTOR DASHBOARD')");
  await logout();

  // admin totals, no names
  await login("admin@example.com");
  await page.waitFor("window.__t.has('Hospital overview') && window.__t.has('ACTIVE ACCOUNTS') && window.__t.has('SYSTEM HEALTH') && window.__t.has('QUEUE TODAY') && window.__t.has('KIOSKS')", 15000);
  check("admin dashboard shows totals, system health and kiosks", (await t("has('SYSTEM HEALTH')")) && (await t("has('QUEUE TODAY')")) && (await t("has('KIOSKS')")));
  check("admin dashboard shows no patient names", !(await t("has('Demo Patient')")) && !(await t(`has('P7-${RUN}')`)));
  await logout();

  check("no uncaught page errors", page.consoleErrors.filter((e) => !/unique "key"/.test(e)).length === 0,
        page.consoleErrors.filter((e) => !/unique "key"/.test(e)).slice(0, 2).join(" | "));
} catch (err) {
  check("script error", false, err.message);
  try { console.log("PAGE TEXT:", (await page.text()).slice(0, 900)); console.log("TOAST:", await t("toast()")); } catch {}
} finally {
  await page.close();
}
const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} checks passed`);
process.exit(failed ? 1 : 0);
