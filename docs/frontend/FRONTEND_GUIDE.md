\# Frontend Architecture \& API Flow Guide



\## Tech Stack Overview

\- \*\*Framework:\*\* React 18 + Vite 6

\- \*\*Styling:\*\* Plain CSS (`src/styles.css`) for lightweight, predictable layout control

\- \*\*Icons \& Localization:\*\* `lucide-react` and `react-i18next` supporting 4 languages (`en`, `hi`, `ur`, `doi`)





\## Key Files \& Responsibilities



1\. \*\*`src/App.jsx`:\*\* Manages core application screens, patient chat state, voice recording modal, review-and-send confirmation screen, and role routing.



2\. \*\*`src/services/` (`api.js`, `auth.js`, `intake.js`, `kiosk.js`):\*\* Centralises all `fetch` calls to the FastAPI backend with `Authorization: Bearer <token>` headers. No mock data is used.



3\. \*\*`src/i18n/languages.js`:\*\* Single source of truth for supported languages (`en`, `hi`, `ur`, `doi`), display labels, and the RTL flag (`dir="rtl"` for Urdu).



4\. \*\*`src/pages/staff/IntakeInsights.jsx`:\*\* Renders the staff review panel showing immutable original patient words, labelled machine translation, extracted symptoms, and field-level evidence labels (`Exact match`, `Possible match`, `Added or corrected by staff`, `Not found`).







\## End-to-End Request Trace (Patient Chat Message)



1\. Patient types a message in `src/App.jsx` and clicks \*\*Send\*\*, invoking `sendMessage()` in `src/services/intake.js`.



2\. `api.js` sends `POST /api/conversations/{id}/messages` with JSON body `{ content, language, input\_mode }` and the session Bearer token.



3\. Backend validates input via Pydantic, runs translation/extraction/dialogue rules, and returns `MessageExchange`.



4\. React renders the message bubbles and preliminary department card using standard JSX escaping (no `dangerouslySetInnerHTML`, preventing XSS).

