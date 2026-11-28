# UI Translation and Localization Review Sheet

_Original sheet by Sanjeev; strings re-copied from `src/i18n/*.json` and status updated so a reviewer sees exactly what the app shows._

## Overview

- **Languages offered in the pickers:** English (`en`), Hindi (`hi`) and Urdu (`ur`, right-to-left).
- **Dogri (`doi`, Devanagari) is currently HIDDEN from every language picker.** It is kept in the code and the database,
  and `src/i18n/doi.json` holds draft translations, but the interface is not fully translated, so it is not offered
  until the dashboards and other major screens are translated and reviewed. To show it for testing, build or run
  with `VITE_ENABLE_DOGRI=true` (see `src/i18n/languages.js`).
- **Dogri coverage:** `doi.json` has 244 keys; English has 356. Every key missing in Dogri falls back to Hindi and then to
  English, which is why Dogri would show Hindi on many screens today.
- **Right-to-left:** selecting Urdu sets `html dir="rtl"` across screens.
- **The Pending Verification page is currently English-only** (they use English default text;
  other languages show the same English). Staff, doctor and admin screens are only partly translated.
- **Emergency guidance in the chat** (call 112) is not a UI string: it comes from the backend dialogue templates in
  `backend/app/ai/dialogue_text.py`, in the language the patient is chatting in. Those need the same review.
- **All non-English wording is an initial draft** and needs review by fluent native speakers and, for medical
  sentences, a clinician, before real use.

## Strings to review

Copied from the JSON files, so the text and key below are exactly what the app uses.

| Screen / context | Key | English (`en`) | Hindi draft (`hi`) | Urdu draft (`ur`) | Dogri draft (`doi`) | Review status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Speak button (home dashboard) | `dash.tapToSpeak` | Tap to Speak | बोलने के लिए दबाएँ | بولنے کے لیے دبائیں | बोलने आस्तै दबाओ | Needs fluent review |
| Review step button | `chat.reviewSend` | Review and send | समीक्षा करें और भेजें | جائزہ لیں اور بھیجیں | समीक्षा करो ते भेजो | Needs fluent review |
| AI disclaimer (short, on every suggestion) | `chat.suggestNote` | Not a diagnosis. Medical staff will review and confirm. | यह निदान नहीं है। चिकित्सा कर्मचारी समीक्षा करके पुष्टि करेंगे। | یہ تشخیص نہیں ہے۔ طبی عملہ جائزہ لے کر تصدیق کرے گا۔ | एह् बमारी दी पन्छान नेईं ऐ। मेडिकल स्टाफ समीक्षा करियै पुष्टि करग। | Needs fluent review |
| AI disclaimer (footer) | `common.noDiagnosis` | HealthSpeak AI does not diagnose or prescribe. | HealthSpeak AI बीमारी का निदान नहीं करता और न ही दवा लिखता है। | HealthSpeak AI بیماری کی تشخیص نہیں کرتا اور نہ ہی دوا تجویز کرتا ہے۔ | HealthSpeak AI बमारी दी पन्छान नेईं करदा ते न दवाई लिखदा ऐ। | Needs fluent review |
| Voice: limited speech recognition warning | `voice.limited` | Speech recognition for this language is limited. The text below may have mistakes or missing words. Please read it carefully and correct it before sending. | इस भाषा के लिए आवाज़ पहचानने की क्षमता सीमित है। नीचे लिखे शब्दों में गलतियाँ या छूटे हुए शब्द हो सकते हैं। कृपया भेजने से पहले ध्यान से पढ़ें और सुधारें। | اس زبان کے لیے آواز کی شناخت محدود ہے۔ نیچے لکھے الفاظ میں غلطیاں یا چھوٹے ہوئے الفاظ ہو سکتے ہیں۔ براہ کرم بھیجنے سے پہلے غور سے پڑھیں اور درست کریں۔ | इस भाशा आस्तै आवाज़ पन्छानने दी क्षमता सीमित ऐ। थल्ले लिखे दे शब्दें च गलतियां जां छुट्टे दे शब्द होई सकदे न। मेहरबानी करियै भेजने थमां पैह्लें ध्यान कन्नै पढ़ो ते ठीक करो। | Needs fluent review |
| Voice: suggested Dogri spelling notice | `voice.suggestedNote` | Suggested Dogri spelling: some Hindi words in the text of the recording were respelled the Dogri way. This is a suggestion, not a verified transcript. Please read it and correct anything wrong before continuing. | सुझाई गई डोगरी वर्तनी: रिकॉर्डिंग के लिखे शब्दों में कुछ हिंदी शब्द डोगरी तरीके से बदले गए हैं। यह केवल एक सुझाव है, जाँचा हुआ लिखित रूप नहीं। आगे बढ़ने से पहले इसे पढ़ें और गलतियाँ सुधारें। | تجویز کردہ ڈوگری ہجے: ریکارڈنگ کے لکھے ہوئے الفاظ میں کچھ ہندی الفاظ ڈوگری انداز میں بدلے گئے ہیں۔ یہ صرف ایک تجویز ہے، تصدیق شدہ متن نہیں۔ آگے بڑھنے سے پہلے اسے پڑھیں اور غلطیاں درست کریں۔ | सुझाई गेदी डोगरी वर्तनी: रिकॉर्डिंग दे लिखे दे शब्दें च किश हिंदी शब्द डोगरी तरीके कन्नै बदले गेदे न। एह् सिर्फ इक सुझाव ऐ, जाचेआ दा लिखत नेईं। अग्गें बधने थमां पैह्लें इसगी पढ़ो ते गलतियां ठीक करो। | Needs fluent review |
| Demo OTP panel: message | `forgot.devMessage` | Your HealthSpeak verification code is | आपका HealthSpeak सत्यापन कोड है | آپ کا HealthSpeak تصدیقی کوڈ ہے | (missing, falls back) | Needs fluent review |
| Demo OTP panel: no real SMS | `forgot.devNoSms` | No real SMS was sent. In this demo the code is shown on screen. In production it would arrive by text message, and this panel would not appear. | कोई असली SMS नहीं भेजा गया। इस डेमो में कोड स्क्रीन पर दिखाया गया है। असली उपयोग में यह टेक्स्ट संदेश से आएगा और यह पैनल नहीं दिखेगा। | کوئی اصل SMS نہیں بھیجا گیا۔ اس ڈیمو میں کوڈ اسکرین پر دکھایا گیا ہے۔ اصل استعمال میں یہ ٹیکسٹ میسج سے آئے گا اور یہ پینل نظر نہیں آئے گا۔ | (missing, falls back) | Needs fluent review |
| Login: welcome heading | `auth.welcomeBack` | Welcome Back 👋 | फिर से स्वागत है 👋 | دوبارہ خوش آمدید 👋 | फिरी सुआगत ऐ 👋 | Needs fluent review |
| Login button | `common.login` | Log in | लॉग इन | لاگ ان | लाग इन | Needs fluent review |
