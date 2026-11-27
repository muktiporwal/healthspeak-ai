# Model Test Report — HealthSpeakAI

**Status:** Draft / test execution pending repository access  
**Test date:** Not run in this environment  
**Purpose:** Record opt-in real-model test outcomes and basic model limitations.

## Test commands

Run from the `backend` directory in PowerShell:

```powershell
$env:HEALTHSPEAK_AI_TESTS="1"
pytest -q tests/test_speech.py -k real
pytest -q tests/test_dogri.py -k real
```

Record the wall-clock time for each command (for example, use `Measure-Command { pytest ... }`) and include the pass/fail/skip result. Do not claim results until tests are executed.

## Results log

| Test suite | Command | Duration | Result | Notes |
|---|---|---:|---|---|
| Speech / Whisper | `pytest -q tests/test_speech.py -k real` | Not run | Pending | Requires opt-in flag and model/runtime setup |
| Dogri / IndicTrans2 | `pytest -q tests/test_dogri.py -k real` | Not run | Pending | Requires opt-in flag and model/runtime setup |

## Model limitations and practical considerations

### Whisper speech recognition
- Whisper is a multilingual speech-recognition model, but language coverage and quality are not uniform.
- It does **not provide Dogri as a supported language**, so Dogri audio may be misrecognized, mapped to a nearby language, or produce unreliable text.
- Recognition can degrade with background noise, overlapping speakers, low-volume recordings, accents, fast speech, uncommon medical words, and code-switching.
- Transcription is not clinical validation: a correct-looking transcript can still omit or alter a symptom, medication, negation, or duration. Important details should be confirmed with the user.

### IndicTrans2 translation
- IndicTrans2 supports a range of Indian-language translation directions, but performance depends on the language pair, dialect, spelling variation, domain, and training coverage.
- Informal speech, regional vocabulary, mixed Hindi/Urdu/English, transliteration, and medical expressions may be translated inconsistently.
- A translated symptom statement can lose negation, severity, duration, or who the symptom belongs to. The translated output should not be treated as a verified medical statement without checking the source and context.

## Interpretation and caveats

- Test-suite success means the tested examples passed; it does not establish real-world clinical accuracy or safety.
- Report model versions, hardware/runtime, network or download conditions, and test data when available.
- Preserve failed cases. If a known failure is deliberately excluded from a test gate, mark it `xfail` with a concise, evidence-based reason; do not delete it or label it expected-failure merely to inflate the pass rate.
- The synthetic extraction evaluation is a small targeted set, not a representative patient dataset. It is useful as a transparent baseline and regression check.
