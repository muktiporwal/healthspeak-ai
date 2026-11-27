"""Small synthetic regression/evaluation set for the existing rules-v2 pipeline.
Run from backend: pytest -q -s tests/test_extraction_eval.py
No production extractor, lexicon, or routing rules are modified.
"""
import json
from pathlib import Path

from sqlalchemy import select

from app.ai.department_classification import suggest
from app.ai.text_processing import extract
from app.services.department_service import active_rules, default_department

DATA_PATH = Path(__file__).parent / "data" / "synthetic_symptom_cases.json"
CASES = json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _normalise(values):
    return {str(v).strip().lower() for v in (values or [])}


def test_synthetic_cases_and_print_accuracy(db, departments):
    """Evaluate extraction + default configured department rules against synthetic labels."""
    rules = active_rules(db)
    default = default_department(db)
    fallback = (str(default.id), default.code, default.name) if default else None
    symptom_correct = department_correct = attention_correct = combined_correct = 0
    failures = []

    for case in CASES:
        extraction = extract(case["text"])
        predicted_symptoms = _normalise(m.term for m in extraction.reported)
        suggestion = suggest(case["text"], rules, fallback)
        predicted_department = (suggestion.department_code or "").strip().lower()
        expected_symptoms = _normalise(case["expected_symptoms"])
        expected_department = case["expected_department"].strip().lower()
        symptom_ok = predicted_symptoms == expected_symptoms
        department_ok = predicted_department == expected_department
        attention_ok = bool(suggestion.attention) == bool(case.get("expected_attention", False))
        combined_ok = symptom_ok and department_ok and attention_ok
        symptom_correct += symptom_ok
        department_correct += department_ok
        attention_correct += attention_ok
        combined_correct += combined_ok
        if not combined_ok:
            failures.append({
                "id": case["id"], "text": case["text"],
                "expected_symptoms": sorted(expected_symptoms),
                "predicted_symptoms": sorted(predicted_symptoms),
                "expected_department": expected_department,
                "predicted_department": predicted_department,
                "expected_attention": bool(case.get("expected_attention", False)),
                "predicted_attention": bool(suggestion.attention),
                "notes": case.get("notes", ""),
            })

    total = len(CASES)
    print(f"Cases evaluated: {total}/{total}")
    print(f"Symptom exact-match accuracy: {symptom_correct/total:.1%} ({symptom_correct}/{total})")
    print(f"Department-code accuracy: {department_correct/total:.1%} ({department_correct}/{total})")
    print(f"Attention-flag accuracy: {attention_correct/total:.1%} ({attention_correct}/{total})")
    print(f"Combined exact-match accuracy: {combined_correct/total:.1%} ({combined_correct}/{total})")
    if failures:
        print("Mismatches (retain for review; labels are synthetic):")
        for failure in failures:
            print(" -", failure)
    # The evaluation prints the metric summary and preserves mismatches for review.
    # It is a report-style regression check, not a production-quality gate.
    assert total == len(CASES)
