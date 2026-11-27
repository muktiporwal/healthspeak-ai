\# Frontend UI \& Multi-Language Walk-Through Review



\## Scope

Walked through the React frontend (`src/App.jsx`, `src/i18n/`, and `src/pages/staff/IntakeInsights.jsx`) across English, Hindi, Urdu, and Dogri flows without modifying application code.





\## Observations \& Findings



1\. \*\*Language Persistence \& Scope:\*\* Changing language in the sidebar updates both UI display language and chat input language, whereas the chat dropdown only switches message language—clear separation, though adding a tooltip would help first-time patients.



2\. \*\*Urdu RTL Layout (`dir="rtl"`):\*\* Switching to Urdu flips page alignment cleanly; long numeric timestamps and badge chips inside the staff queue should be double-checked on narrow laptop viewports so spacing stays balanced.



3\. \*\*Dogri Fallback Consistency:\*\* Patient chat and voice screens display draft Dogri labels (`src/i18n/doi.json`), while staff/doctor/admin screens fall back to Hindi (`hi.json`). Because both use Devanagari script, the transition is readable, though a subtle language-fallback notice on admin/staff views would improve clarity.



4\. \*\*Staff Evidence \& Revision Clarity:\*\* `IntakeInsights.jsx` clearly separates immutable `original\_text` from machine-translated English and displays explicit evidence badges (`Exact match`, `Possible match`, `Added or corrected by staff`, `Not found`) instead of misleading confidence percentages.



5\. \*\*Voice Transcript Editability:\*\* Allowing patients to review and edit the raw transcript before submission prevents transcription mistakes from entering the intake record.

