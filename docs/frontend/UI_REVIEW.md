# Frontend UI and Multi-Language Walk-Through Review

_Original review by Sanjeev, with status notes added for the current app._

## Scope

Walked through the React frontend (`src/App.jsx`, `src/i18n/` and `src/pages/staff/IntakeInsights.jsx`) across
English, Hindi, Urdu and Dogri flows without modifying application code.

> **Current status:** Dogri is now hidden from every language picker (flag in `src/i18n/languages.js`), so findings
> about Dogri describe the interface as it would look if it were switched back on with `VITE_ENABLE_DOGRI=true`.
> The frontend has no doctor sign-up screen (an administrator creates doctor accounts), and the Pending Verification
> page is English-only. In development, the one-time code is shown
> in a labelled demo panel and no real SMS is sent.

## Observations and Findings

1. **Language persistence and scope:** changing the language in the sidebar updates both the UI display language and
   the chat input language, whereas the chat dropdown only switches the message language. The separation is clear,
   though a tooltip would help first-time patients.
2. **Urdu RTL layout (`dir="rtl"`):** switching to Urdu flips page alignment cleanly. Long numeric timestamps and badge
   chips in the staff queue should be double-checked on narrow laptop viewports so spacing stays balanced.
3. **Dogri fallback consistency (only when Dogri is enabled):** the patient chat and voice screens show draft Dogri
   labels from `src/i18n/doi.json`, while staff, doctor and admin screens fall back to Hindi (`hi.json`). Both use the
   Devanagari script, so it stays readable, but this mixing is the reason Dogri is hidden for now. A visible
   fallback notice would help if it is enabled later.
4. **Staff evidence and revision clarity:** the review screens separate the immutable `original_text` from the
   machine-translated English and show explicit evidence badges (`Exact match`, `Possible match`,
   `Added or corrected by staff`, `Not found`, `Rejected`) instead of misleading confidence percentages.
5. **Voice transcript editability:** letting patients review and edit the raw transcript before submission prevents
   transcription mistakes from entering the intake record.
6. **Not yet reviewed (added):** the doctor-only login view, the Pending Verification page, the doctor dashboard
   with Urgent / Normal chips, the admin doctor-approvals panel and the demo OTP panel are newer than this walk-through.
   The Pending Verification page is English-only and should be checked in Hindi and Urdu.
