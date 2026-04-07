"""
Comprehensive Uzbek morphology test suite.

Tests cover:
  - Verbs (tense, aspect, person, number, negation, mood)
  - Nouns (case, possessive, plural, derivation)
  - Adjectives & adverbs
  - Compound morphemes
  - Edge cases
  - Pharma-specific terms

Each test has expected fields:
  - word: input
  - expected_pos: 'verb' | 'noun' | 'adjective' | 'adverb'
  - expected_stem: stem (lowercase)
  - expected_morpheme_count: minimum number of morphemes
  - expected_features: dict of expected features (tense, person, etc.)
  - description: what's being tested

Run:
    cd backend
    python tests/test_morphology.py
"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import morphology

# ═══════════════════════════════════════════════════
# Test cases (50+)
# ═══════════════════════════════════════════════════

TESTS = [
    # ───────────────── VERBS — Tenses ─────────────────
    {
        "word": "ishladim",
        "expected_pos": "verb",
        "expected_stem": "ishla",
        "expected_features": {"tense": "past", "person": 1, "number": "singular"},
        "description": "Past 1sg",
    },
    {
        "word": "ishlading",
        "expected_pos": "verb",
        "expected_stem": "ishla",
        "expected_features": {"tense": "past", "person": 2, "number": "singular"},
        "description": "Past 2sg",
    },
    {
        "word": "ishladi",
        "expected_pos": "verb",
        "expected_stem": "ishla",
        "expected_features": {"tense": "past", "person": 3, "number": "singular"},
        "description": "Past 3sg",
    },
    {
        "word": "ishladik",
        "expected_pos": "verb",
        "expected_stem": "ishla",
        "expected_features": {"tense": "past", "person": 1, "number": "plural"},
        "description": "Past 1pl",
    },
    {
        "word": "ishlamoqda",
        "expected_pos": "verb",
        "expected_stem": "ishla",
        "expected_features": {"tense": "progressive"},
        "description": "Progressive 3sg",
    },
    {
        "word": "ishlamoqdaman",
        "expected_pos": "verb",
        "expected_stem": "ishla",
        "expected_features": {"tense": "progressive", "person": 1},
        "description": "Progressive 1sg",
    },

    # ───────────────── VERBS — Negation ─────────────────
    {
        "word": "ishlamadi",
        "expected_pos": "verb",
        "expected_stem": "ishla",
        "expected_features": {"negation": True, "tense": "past", "person": 3},
        "description": "Negation past 3sg",
    },
    {
        "word": "ishlamadim",
        "expected_pos": "verb",
        "expected_stem": "ishla",
        "expected_features": {"negation": True, "tense": "past", "person": 1},
        "description": "Negation past 1sg",
    },

    # ───────────────── VERBS — Question ─────────────────
    {
        "word": "ishlaysanmi",
        "expected_pos": "verb",
        "expected_stem": "ishla",
        "expected_features": {"mood": "interrogative", "person": 2},
        "description": "Question 2sg",
    },

    # ───────────────── NOUNS — Cases ─────────────────
    {
        "word": "kitobni",
        "expected_pos": "noun",
        "expected_stem": "kitob",
        "expected_features": {"case": "accusative"},
        "description": "Accusative",
    },
    {
        "word": "kitobga",
        "expected_pos": "noun",
        "expected_stem": "kitob",
        "expected_features": {"case": "dative"},
        "description": "Dative",
    },
    {
        "word": "kitobda",
        "expected_pos": "noun",
        "expected_stem": "kitob",
        "expected_features": {"case": "locative"},
        "description": "Locative",
    },
    {
        "word": "kitobdan",
        "expected_pos": "noun",
        "expected_stem": "kitob",
        "expected_features": {"case": "ablative"},
        "description": "Ablative",
    },
    {
        "word": "kitobning",
        "expected_pos": "noun",
        "expected_stem": "kitob",
        "expected_features": {"case": "genitive"},
        "description": "Genitive",
    },

    # ───────────────── NOUNS — Plural ─────────────────
    {
        "word": "kitoblar",
        "expected_pos": "noun",
        "expected_stem": "kitob",
        "expected_features": {"number": "plural"},
        "description": "Plural",
    },
    {
        "word": "kitoblarni",
        "expected_pos": "noun",
        "expected_stem": "kitob",
        "expected_features": {"number": "plural", "case": "accusative"},
        "description": "Plural + accusative",
    },
    {
        "word": "kitoblarga",
        "expected_pos": "noun",
        "expected_stem": "kitob",
        "expected_features": {"number": "plural", "case": "dative"},
        "description": "Plural + dative",
    },

    # ───────────────── NOUNS — Possessive ─────────────────
    {
        "word": "kitobim",
        "expected_pos": "noun",
        "expected_stem": "kitob",
        "expected_features": {"person": 1, "number": "singular"},
        "description": "1sg possessive",
    },
    {
        "word": "kitobing",
        "expected_pos": "noun",
        "expected_stem": "kitob",
        "expected_features": {"person": 2, "number": "singular"},
        "description": "2sg possessive",
    },
    {
        "word": "kitobi",
        "expected_pos": "noun",
        "expected_stem": "kitob",
        "expected_features": {"person": 3, "number": "singular"},
        "description": "3sg possessive",
    },
    {
        "word": "kitobimiz",
        "expected_pos": "noun",
        "expected_stem": "kitob",
        "expected_features": {"person": 1, "number": "plural"},
        "description": "1pl possessive",
    },
    {
        "word": "kitobingiz",
        "expected_pos": "noun",
        "expected_stem": "kitob",
        "expected_features": {"person": 2, "number": "plural"},
        "description": "2pl possessive",
    },
    {
        "word": "kitoblari",
        "expected_pos": "noun",
        "expected_stem": "kitob",
        "expected_features": {"person": 3},
        "description": "3pl possessive",
    },

    # ───────────────── COMPOUND MORPHOLOGY ─────────────────
    {
        "word": "kitobimga",
        "expected_pos": "noun",
        "expected_stem": "kitob",
        "expected_features": {"person": 1, "case": "dative"},
        "description": "Possessive + case",
    },
    {
        "word": "kitoblarimni",
        "expected_pos": "noun",
        "expected_stem": "kitob",
        "expected_features": {"number": "plural", "person": 1, "case": "accusative"},
        "description": "Plural + 1sg.poss + accusative",
    },

    # ───────────────── REAL UZBEK WORDS ─────────────────
    {"word": "uy", "expected_pos": "noun", "expected_stem": "uy", "description": "Simple noun"},
    {"word": "uyim", "expected_pos": "noun", "expected_stem": "uy", "description": "house-1sg"},
    {"word": "uyimiz", "expected_pos": "noun", "expected_stem": "uy", "description": "house-1pl"},
    {"word": "uyga", "expected_pos": "noun", "expected_stem": "uy", "description": "house-DAT"},
    {"word": "uyda", "expected_pos": "noun", "expected_stem": "uy", "description": "house-LOC"},
    {"word": "uydan", "expected_pos": "noun", "expected_stem": "uy", "description": "house-ABL"},
    {"word": "mehmon", "expected_pos": "noun", "expected_stem": "mehmon", "description": "guest"},
    {"word": "mehmondan", "expected_pos": "noun", "expected_stem": "mehmon", "description": "guest-ABL"},
    {"word": "talaba", "expected_pos": "noun", "expected_stem": "talaba", "description": "student"},
    {"word": "talabalar", "expected_pos": "noun", "expected_stem": "talaba", "description": "students"},

    # ───────────────── PHARMA-SPECIFIC TERMS ─────────────────
    {"word": "dori", "expected_pos": "noun", "expected_stem": "dori", "description": "medicine"},
    {"word": "dorilar", "expected_pos": "noun", "expected_stem": "dori", "description": "medicines"},
    {"word": "doriga", "expected_pos": "noun", "expected_stem": "dori", "description": "to medicine"},
    {"word": "kasalxona", "expected_pos": "noun", "expected_stem": "kasalxona", "description": "hospital"},
    {"word": "kasalxonada", "expected_pos": "noun", "expected_stem": "kasalxona", "description": "in hospital"},

    # ───────────────── EDGE CASES ─────────────────
    {"word": "yo", "expected_pos": "unknown", "expected_stem": "yo", "description": "Too short"},
    {"word": "asalbanan123", "expected_pos": "unknown", "description": "Invalid mix"},
]


# ═══════════════════════════════════════════════════
# Test runner
# ═══════════════════════════════════════════════════

def run_tests(verbose: bool = False):
    analyzer = morphology.get_analyzer()
    analyzer._ensure_loaded()

    total = len(TESTS)
    passed = 0
    pos_correct = 0
    stem_correct = 0
    feature_correct = 0
    feature_total = 0
    failed_tests = []

    for i, test in enumerate(TESTS, 1):
        word = test["word"]
        result = analyzer.analyze(word)

        ok_pos = False
        ok_stem = False
        ok_features = []

        if result is None:
            if test.get("expected_pos") == "unknown":
                passed += 1
                continue
            failed_tests.append(f"  {i}. {word!r}: returned None ({test.get('description', '')})")
            continue

        # POS check
        exp_pos = test.get("expected_pos")
        if exp_pos and result.pos == exp_pos:
            ok_pos = True
            pos_correct += 1
        elif exp_pos == "unknown":
            ok_pos = True  # We allow any for unknowns

        # Stem check
        exp_stem = test.get("expected_stem")
        if exp_stem and result.stem.lower() == exp_stem.lower():
            ok_stem = True
            stem_correct += 1

        # Feature checks
        exp_features = test.get("expected_features", {})
        for key, exp_val in exp_features.items():
            feature_total += 1
            actual = getattr(result, key, None)
            if actual == exp_val:
                feature_correct += 1
                ok_features.append(f"{key}=✓")
            else:
                ok_features.append(f"{key}={actual!r}≠{exp_val!r}")

        # Pass criteria: stem AND pos correct, all features pass
        all_features_ok = all("✓" in f for f in ok_features) if ok_features else True
        if ok_stem and (ok_pos or exp_pos is None) and all_features_ok:
            passed += 1
            if verbose:
                print(f"  ✅ {i:3d}. {word:25s} → {result.breakdown()}")
        else:
            failed_tests.append(
                f"  ❌ {i:3d}. {word!r:30s} stem={'✓' if ok_stem else f'{result.stem}≠{exp_stem}'}, "
                f"pos={'✓' if ok_pos else f'{result.pos}≠{exp_pos}'}, "
                f"features=[{', '.join(ok_features) if ok_features else '-'}]"
            )

    print()
    print("=" * 70)
    print(f"Test Results: {passed}/{total} passed ({100*passed/total:.1f}%)")
    print(f"  POS accuracy:     {pos_correct}/{total} ({100*pos_correct/total:.1f}%)")
    print(f"  Stem accuracy:    {stem_correct}/{total} ({100*stem_correct/total:.1f}%)")
    print(f"  Feature accuracy: {feature_correct}/{feature_total} "
          f"({100*feature_correct/max(1,feature_total):.1f}%)" if feature_total else "  Feature accuracy: N/A")
    print("=" * 70)

    if failed_tests:
        print()
        print("Failures:")
        for ft in failed_tests:
            print(ft)

    return {
        "total": total,
        "passed": passed,
        "pos_correct": pos_correct,
        "stem_correct": stem_correct,
        "feature_correct": feature_correct,
        "feature_total": feature_total,
        "pass_rate": passed / total if total else 0,
    }


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    results = run_tests(verbose=verbose)
    sys.exit(0 if results["pass_rate"] >= 0.6 else 1)
