// The ONE place that lists the languages the app supports. Add a language here (and in the backend
// enums + a migration) instead of scattering names and codes through the screens.
//
//  code    - API / database value. Dogri uses its ISO 639-3 code "doi" (there is no ISO 639-1 code).
//  name    - English name; also the value kept in the speaking-language state of the chat screens.
//  label   - how the language is written in its own script, shown in the display-language picker.
//  rtl     - right-to-left script.
//  typedIn - script a patient should type in (used for the "you are typing in English letters" hint).
//  hintKey - translation key of that hint.
const ALL_LANGUAGES = [
  { code: "en", name: "English", label: "English", rtl: false },
  { code: "hi", name: "Hindi", label: "हिन्दी", rtl: false, typedIn: "Devanagari", hintKey: "chat.scriptHintHi" },
  { code: "ur", name: "Urdu", label: "اردو", rtl: true, typedIn: "Urdu", hintKey: "chat.scriptHintUr" },
  {
    code: "doi",
    name: "Dogri",
    label: "Dogri — डोगरी",
    rtl: false,
    typedIn: "Devanagari",
    hintKey: "chat.scriptHintDoi",
    // The assistant's own bubbles (greeting, "reading your message", department card) are shown in the
    // language the patient chose to chat in, even if the rest of the screen is in another language.
    assistantFollowsSpeaking: true,
    // Dogri is HIDDEN from every language picker until the dashboard and the other major screens are genuinely
    // translated and reviewed (about a third of the screens still fall back to Hindi, which would be shown under
    // a "Dogri" label). The backend, database values and translations are all kept. To show it again for
    // testing build/run with VITE_ENABLE_DOGRI=true; to enable it for good, set `enabled: true` here.
    enabled: import.meta.env.VITE_ENABLE_DOGRI === "true",
  },
];

// Languages a person can PICK (display language, speaking language). Hidden ones stay known for lookups,
// so a stored Dogri conversation is still labelled correctly for staff.
export const LANGUAGES = ALL_LANGUAGES.filter((l) => l.enabled !== false);

// i18n `lng` option for assistant-authored text, or undefined to keep the screen's display language.
export const assistantLng = (code) => (LANGUAGE_BY_CODE[code] && LANGUAGE_BY_CODE[code].assistantFollowsSpeaking ? code : undefined);

export const LANGUAGE_CODE_LIST = LANGUAGES.map((l) => l.code);
export const LANGUAGE_BY_CODE = Object.fromEntries(ALL_LANGUAGES.map((l) => [l.code, l]));
// Used by the screens that store the speaking language by its English name: { English: "en", ... }
export const LANGUAGE_CODES = Object.fromEntries(LANGUAGES.map((l) => [l.name, l.code]));
export const NAME_BY_CODE = Object.fromEntries(ALL_LANGUAGES.map((l) => [l.code, l.name]));
export const isSupportedLanguage = (code) => LANGUAGE_CODE_LIST.includes(code);
export const isRtl = (code) => Boolean(LANGUAGE_BY_CODE[code] && LANGUAGE_BY_CODE[code].rtl);

// A saved language that is currently hidden (e.g. an account whose display language was Dogri) is shown in
// English, and the screen says English: never another language under the wrong label.
export const displayLanguageFor = (code) => (LANGUAGE_CODE_LIST.includes(code) ? code : "en");
// Speaking-language name (as kept by the chat screens) that follows a saved display language.
export const speakingNameFor = (code) => NAME_BY_CODE[displayLanguageFor(code)] || "English";
