# Glossary Suggestions — Symptom Extraction (Review Draft)

**Purpose:** Candidate Hindi, Urdu, and Dogri phrases for symptom matching and negation handling. These are suggestions only; a fluent speaker and clinical reviewer should approve them before any lexicon or rules are updated. `dialogue_text.py` is intentionally not modified.

## Hindi candidates

| Concept | Candidate phrase | Example sentence |
|---|---|---|
| Fever | बुखार / तेज़ बुखार | मुझे दो दिन से बुखार है। |
| Headache | सिर दर्द / सिर में दर्द | मेरे सिर में दर्द हो रहा है। |
| Cough | खाँसी | मुझे खाँसी नहीं है। |
| Sore throat | गले में दर्द | गले में दर्द और खराश है। |
| Stomach pain | पेट दर्द / पेट में दर्द | कल से पेट में दर्द है। |
| Vomiting | उल्टी | मुझे उल्टी नहीं हुई। |
| Dizziness | चक्कर | मेरी माँ को चक्कर आ रहे हैं। |
| Breathlessness | साँस फूलना / साँस लेने में दिक्कत | आराम करते हुए भी साँस लेने में दिक्कत है। |
| Rash | दाने / त्वचा पर चकत्ते | हाथ पर लाल दाने हैं। |
| Negation | नहीं / बिल्कुल नहीं / न | मुझे बुखार नहीं है। |

## Urdu candidates

| Concept | Candidate phrase | Example sentence |
|---|---|---|
| Fever | بخار | مجھے بخار ہے۔ |
| Headache | سر درد | میرے سر میں درد ہے۔ |
| Cough | کھانسی | مجھے کھانسی نہیں ہے۔ |
| Sore throat | گلے میں درد | میرے گلے میں درد ہے۔ |
| Stomach pain | پیٹ میں درد | کل سے پیٹ میں درد ہے۔ |
| Vomiting | قے / الٹی | مجھے قے نہیں ہوئی۔ |
| Dizziness | چکر آنا | میری والدہ کو چکر آ رہے ہیں۔ |
| Breathlessness | سانس لینے میں دشواری | مجھے سانس لینے میں دشواری ہو رہی ہے۔ |
| Negation | نہیں / نہ / مت (context-sensitive) | مجھے بخار نہیں ہے۔ |

## Dogri candidates

Dogri spelling and everyday usage vary by speaker and script. These should be checked by a fluent Dogri speaker; the phrases below are tentative and may be more Hindi-influenced than locally natural.

| Concept | Tentative phrase | Example sentence |
|---|---|---|
| Fever | बुखार (tentative/common borrowing) | मिगी बुखार ऐ। |
| Headache | सिर दर्द (tentative) | मिगी सिर दर्द ऐ। |
| Cough | खांसी (tentative/common borrowing) | मिगी खांसी नेईं ऐ। |
| Stomach pain | पेट दर्द (tentative) | मिगी पेट दर्द ऐ। |
| Vomiting | उल्टी (tentative/common borrowing) | मिगी उल्टी नेईं आई। |
| Dizziness | चक्कर (tentative) | मेरी माता गी चक्कर औंदे न। |
| Negation | नेईं / न (tentative; context and dialect dependent) | मिगी बुखार नेईं ऐ। |

## Additional negation / scope examples to review

| Candidate pattern | Example | Review question |
|---|---|---|
| Symptom negation | “No fever, but a cough.” | Is only fever negated? |
| Multiple negations | “No fever and no cough.” | Are both symptoms excluded? |
| Other-person scope | “My mother has a cough; I do not.” | Is the symptom attributed to the right person? |
| Temporal scope | “I had fever yesterday, but not today.” | Does the extractor preserve past vs current? |
| Uncertainty | “I might have a fever.” | Is uncertain symptom mention handled distinctly? |
| Contrast | “Not a headache—it's tooth pain.” | Is the corrected symptom extracted, not the negated one? |

## Approval notes

- Confirm spelling, script, naturalness, dialect, and transliteration variants.
- Confirm that the examples are unambiguous and that negation scope is correct.
- Add only approved terms to the existing lexicon in a separate, reviewed change.
