# Frontend Architecture and API Flow Guide

_Original guide by Sanjeev; updated for the current app (doctor verification, role-based dashboards, Dogri hidden)._

## Tech Stack Overview

- **Framework:** React 18 + Vite 6
- **Styling:** plain CSS (`src/styles.css`) for lightweight, predictable layout control
- **Icons and localization:** `lucide-react` and `react-i18next`. Three display languages are offered: English (`en`),
  Hindi (`hi`) and Urdu (`ur`, right-to-left). Dogri (`doi`) is implemented but **hidden** from every picker until the
  interface is fully translated and reviewed (see `src/i18n/languages.js`).

## Key Files and Responsibilities

1. **`src/App.jsx`:** the core screens (login, signup, patient chat, voice, review-and-send), shared state, and role
   routing. `homeFor(user)` decides where a person lands from the account the **server** returns (role and, for
   doctors, `verification_status`); the role buttons on the login screen are only a hint.
2. **`src/services/`:** every `fetch` to the FastAPI backend goes through `api.js` with an
   `Authorization: Bearer <token>` header. `auth.js`, `intake.js`, `kiosk.js`, `visits.js`, `admin.js` and
   `doctors.js` hold the per-area calls. No mock data is used.
3. **`src/i18n/languages.js`:** the single list of languages (code, name, label, RTL flag, and whether it is shown in
   pickers). `src/i18n/index.js` loads `en.json`, `hi.json`, `ur.json` and `doi.json`. A saved language that is hidden
   (for example a Dogri account) is displayed in English, labelled English.
4. **`src/pages/staff/IntakeInsights.jsx`:** priority chip and panel (Urgent / Normal), the symptom review list, the
   per-field evidence labels (`Exact match`, `Possible match`, `Added or corrected by staff`, `Not found`, `Rejected`) and
   the patient's earlier visits. The immutable original words and the labelled machine translation are shown in the
   `IntakeReview` screen in `src/App.jsx`.
5. **Doctor pages:** `src/pages/doctor/PendingVerification.jsx` (shown to a doctor account that is not yet approved),
   `src/pages/doctor/DoctorHome.jsx` (dashboard) and `DoctorIntakeDetails.jsx` (read-only intake for assigned
   patients). The admin approves in `src/pages/admin/DoctorApprovals.jsx`. **The frontend has no doctor sign-up
   screen:** doctor accounts are created by an administrator. Choosing "Doctor" on the login screen shows a
   doctor-only login (no Patient option, no sign-up link).

## Authentication, token and roles

- The login token is kept in `sessionStorage` under `healthspeak.token`, so it is forgotten when the tab closes.
- A doctor account that is **Pending Verification** is refused by every doctor endpoint (403) until an administrator
  approves, so the pending page shows no patient data. This is enforced by the backend, not the page.
- The backend still exposes a public `POST /api/doctors/register` endpoint (it always creates a pending account);
  the frontend no longer calls it.
- The Pending Verification page is currently English-only.

## OTP (development demo mode)

`src/components/DevSmsNotice.jsx` shows the one-time code in a "DEMO MODE" notification panel. It appears only when the
API returns `dev_code`, which the backend does only in development with the console SMS provider. **No real SMS is
sent**, and the panel never appears in production.

## End-to-End Request Trace (Patient Chat Message)

1. The patient types a message in `src/App.jsx` and clicks **Send**, calling `sendMessage()` in `src/services/intake.js`.
2. `api.js` sends `POST /api/conversations/{id}/messages` with JSON `{ content, language, input_mode }` (plus
   `transcription_id` for a voice message) and the session Bearer token.
3. The backend validates the input with Pydantic, runs the input guard, translation, extraction and dialogue rules,
   and returns a `MessageExchange`.
4. React renders the message bubbles and the preliminary department card using normal JSX escaping (the code never
   uses `dangerouslySetInnerHTML`, which prevents XSS).
