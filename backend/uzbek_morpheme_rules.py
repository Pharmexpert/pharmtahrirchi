"""
Uzbek morpheme order rules and validation engine.

Based on canonical Uzbek grammar (turkologiya literature):
  STEM + VOICE + NEGATION + ASPECT + TENSE + AGREEMENT + QUESTION/PARTICLE

This module:
  1. Defines morpheme categories with priority order (slot system)
  2. Validates a sequence of morphemes against canonical order
  3. Provides "tightness" score for ranking decompositions
  4. Persists rules in DB for editability

References:
  - Sjoberg, A. F. (1993). Uzbek Structural Grammar
  - Bodrogligeti, A. J. E. (2003). An Academic Reference Grammar of Modern Literary Uzbek
  - O'zbek tili grammatikasi (Toshkent, 1975-1976)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple


# ═══════════════════════════════════════════════════
# Morpheme slot system (canonical Uzbek order)
# ═══════════════════════════════════════════════════
#
# A higher slot number = farther from the stem (more "outer" suffix).
# A lower slot number = closer to the stem (more "inner" suffix).
#
# For VERBS:
#   0: stem
#   1: voice (causative -tir/-dir, passive -il/-in, reflexive -in, reciprocal -ish)
#   2: negation (-ma)
#   3: aspect / converb (-ib, -gan, -moqda, -yotgan, -y)
#   4: tense / mood (-di, -gan, -yapti, -ar, -ajak)
#   5: agreement (-m, -ng, -k, -ngiz, -lar, -man, -san, -miz, -siz)
#   6: question / particle (-mi, -kan, -ku, -da)
#
# For NOUNS:
#   0: stem
#   1: derivational (-chi, -dor, -lik, -li, -siz, -cha)
#   2: plural (-lar)
#   3: possessive (-im, -ing, -i, -imiz, -ingiz, -lari)
#   4: case (-ni, -ga, -da, -dan, -ning)
#   5: question / particle (-mi, -kan, -ku)

# Map gloss substring → (slot, slot_name, applicable_pos)
SLOT_MAP: Dict[str, Tuple[int, str, str]] = {
    # Verb slots
    "voice": (1, "voice", "verb"),
    "causative": (1, "voice", "verb"),
    "passive": (1, "voice", "verb"),
    "reflexive": (1, "voice", "verb"),
    "reciprocal": (1, "voice", "verb"),
    "negation": (2, "negation", "verb"),
    "negative": (2, "negation", "verb"),
    "prohibitive": (2, "negation", "verb"),
    "converb": (3, "aspect", "verb"),
    "progressive": (3, "aspect", "verb"),
    "habitual": (3, "aspect", "verb"),
    "future": (4, "tense", "verb"),
    "past": (4, "tense", "verb"),
    "present": (4, "tense", "verb"),
    "imperative": (4, "mood", "verb"),
    "optative": (4, "mood", "verb"),
    "conditional": (4, "mood", "verb"),
    # Agreement is encoded in compound suffixes (e.g. "1sg.past")
    # but for sole agreement markers:
    "1sg": (5, "agreement", "verb"),
    "2sg": (5, "agreement", "verb"),
    "3sg": (5, "agreement", "verb"),
    "1pl": (5, "agreement", "verb"),
    "2pl": (5, "agreement", "verb"),
    "3pl": (5, "agreement", "verb"),
    # Question
    "question": (6, "question", "any"),
    "interrogative": (6, "question", "any"),
    "dubitative": (6, "question", "any"),

    # Noun slots
    "derivational": (1, "derivation", "noun"),
    "plural": (2, "number", "noun"),
    "possessive": (3, "possessive", "noun"),
    "accusative": (4, "case", "noun"),
    "dative": (4, "case", "noun"),
    "ablative": (4, "case", "noun"),
    "locative": (4, "case", "noun"),
    "genitive": (4, "case", "noun"),
}


@dataclass
class ValidationResult:
    valid: bool
    score: float                  # 0.0 (bad) — 1.0 (perfect)
    issues: List[str]             # human-readable problems
    morpheme_slots: List[int]     # detected slot for each morpheme


def get_slots_for_gloss(gloss: str) -> List[Tuple[int, str]]:
    """Return all (slot, slot_name) tuples that apply to a given gloss."""
    g = gloss.lower()
    matches = []
    for keyword, (slot, name, _pos) in SLOT_MAP.items():
        if keyword in g:
            matches.append((slot, name))
    return matches


def validate_morpheme_order(morphemes: List[Dict], pos_hint: str = "verb") -> ValidationResult:
    """
    Validate that suffixes appear in canonical Uzbek slot order
    (closest to stem first, then progressively outer).

    morphemes: list of {kind, surface, gloss}
    pos_hint: 'verb' or 'noun' (affects which slot system to use)

    Returns:
      - valid: True if order is OK
      - score: 1.0 - (out_of_order_count / total_suffixes)
      - issues: list of order violations
      - morpheme_slots: slot index for each morpheme (None if no slot)
    """
    issues: List[str] = []
    slots: List[int] = []
    last_slot = -1  # closer-to-stem suffixes have lower slots, must be increasing

    suffixes = [m for m in morphemes if m.get("kind") == "suffix"]
    if not suffixes:
        return ValidationResult(valid=True, score=1.0, issues=[], morpheme_slots=[0] * len(morphemes))

    out_of_order = 0
    for m in suffixes:
        gloss = m.get("gloss", "") or ""
        candidates = get_slots_for_gloss(gloss)
        if not candidates:
            slots.append(-1)
            continue
        # Pick the slot most consistent with monotone increase
        chosen = min(candidates, key=lambda c: abs(c[0] - last_slot - 1))
        slot_num, slot_name = chosen
        if slot_num < last_slot:
            issues.append(
                f"Морфема '{m.get('surface', '')}' ({slot_name}, slot={slot_num}) "
                f"олдинги слот {last_slot}'дан кичик — нотўғри тартиб"
            )
            out_of_order += 1
        slots.append(slot_num)
        last_slot = max(last_slot, slot_num)

    score = max(0.0, 1.0 - (out_of_order / max(1, len(suffixes))))
    valid = out_of_order == 0

    # Pre-pad with 0 for stem(s)
    full_slots = [0] * (len(morphemes) - len(slots)) + slots

    return ValidationResult(
        valid=valid,
        score=score,
        issues=issues,
        morpheme_slots=full_slots,
    )


# ═══════════════════════════════════════════════════
# Canonical Uzbek morphology rules (for DB seeding)
# ═══════════════════════════════════════════════════
#
# These are the rules that define WHAT can appear in each slot.
# They will be loaded into the morphology_rules table on first run.

CANONICAL_RULES = [
    # ───── Voice (slot 1) ─────
    {"slot": 1, "category": "voice", "form": "tir", "lat_form": "tir", "function": "causative",
     "example": "ишлат → ишлат+тир", "lang": "uz"},
    {"slot": 1, "category": "voice", "form": "дир", "lat_form": "dir", "function": "causative",
     "example": "келдир → кел+дир", "lang": "uz"},
    {"slot": 1, "category": "voice", "form": "ил", "lat_form": "il", "function": "passive",
     "example": "ёзилди → ёз+ил+ди", "lang": "uz"},
    {"slot": 1, "category": "voice", "form": "ин", "lat_form": "in", "function": "reflexive",
     "example": "ювин → юв+ин", "lang": "uz"},
    {"slot": 1, "category": "voice", "form": "иш", "lat_form": "ish", "function": "reciprocal",
     "example": "ёзиш → ёз+иш", "lang": "uz"},

    # ───── Negation (slot 2) ─────
    {"slot": 2, "category": "negation", "form": "ма", "lat_form": "ma", "function": "verb negation",
     "example": "ишламади → ишла+ма+ди", "lang": "uz"},

    # ───── Aspect / Converb (slot 3) ─────
    {"slot": 3, "category": "aspect", "form": "моқда", "lat_form": "moqda", "function": "progressive",
     "example": "ишламоқда → ишла+моқда", "lang": "uz"},
    {"slot": 3, "category": "aspect", "form": "ётган", "lat_form": "yotgan", "function": "progressive participle",
     "example": "ишлаётган → ишла+ётган", "lang": "uz"},
    {"slot": 3, "category": "aspect", "form": "ган", "lat_form": "gan", "function": "perfect participle",
     "example": "ишлаган → ишла+ган", "lang": "uz"},
    {"slot": 3, "category": "aspect", "form": "иб", "lat_form": "ib", "function": "converb",
     "example": "ёзиб → ёз+иб", "lang": "uz"},
    {"slot": 3, "category": "aspect", "form": "ади", "lat_form": "adi", "function": "habitual",
     "example": "ишлайди → ишла+й+ди", "lang": "uz"},

    # ───── Tense / Mood (slot 4) ─────
    {"slot": 4, "category": "tense", "form": "ди", "lat_form": "di", "function": "definite past",
     "example": "ишлади → ишла+ди", "lang": "uz"},
    {"slot": 4, "category": "tense", "form": "ган", "lat_form": "gan", "function": "indefinite past",
     "example": "ишлаган → ишла+ган", "lang": "uz"},
    {"slot": 4, "category": "tense", "form": "ажак", "lat_form": "ajak", "function": "future",
     "example": "ишлажак → ишла+ажак", "lang": "uz"},
    {"slot": 4, "category": "tense", "form": "ар", "lat_form": "ar", "function": "indefinite future",
     "example": "ёзар → ёз+ар", "lang": "uz"},
    {"slot": 4, "category": "mood", "form": "син", "lat_form": "sin", "function": "imperative 3sg",
     "example": "ишласин → ишла+син", "lang": "uz"},
    {"slot": 4, "category": "mood", "form": "са", "lat_form": "sa", "function": "conditional",
     "example": "ишласа → ишла+са", "lang": "uz"},

    # ───── Agreement (slot 5) — verb ─────
    {"slot": 5, "category": "agreement", "form": "ман", "lat_form": "man", "function": "1sg",
     "example": "ишлайман → ишла+й+ман", "lang": "uz"},
    {"slot": 5, "category": "agreement", "form": "сан", "lat_form": "san", "function": "2sg",
     "example": "ишлайсан → ишла+й+сан", "lang": "uz"},
    {"slot": 5, "category": "agreement", "form": "миз", "lat_form": "miz", "function": "1pl",
     "example": "ишлаймиз → ишла+й+миз", "lang": "uz"},
    {"slot": 5, "category": "agreement", "form": "сиз", "lat_form": "siz", "function": "2pl",
     "example": "ишлайсиз → ишла+й+сиз", "lang": "uz"},
    {"slot": 5, "category": "agreement", "form": "м", "lat_form": "m", "function": "1sg.short",
     "example": "ишладим → ишла+ди+м", "lang": "uz"},
    {"slot": 5, "category": "agreement", "form": "нг", "lat_form": "ng", "function": "2sg.short",
     "example": "ишладинг → ишла+ди+нг", "lang": "uz"},
    {"slot": 5, "category": "agreement", "form": "к", "lat_form": "k", "function": "1pl.short",
     "example": "ишладик → ишла+ди+к", "lang": "uz"},
    {"slot": 5, "category": "agreement", "form": "нгиз", "lat_form": "ngiz", "function": "2pl.short",
     "example": "ишладингиз → ишла+ди+нгиз", "lang": "uz"},
    {"slot": 5, "category": "agreement", "form": "лар", "lat_form": "lar", "function": "3pl",
     "example": "ишладилар → ишла+ди+лар", "lang": "uz"},

    # ───── Noun derivation (slot 1) ─────
    {"slot": 1, "category": "derivation", "form": "чи", "lat_form": "chi", "function": "agent noun",
     "example": "ишчи → иш+чи", "lang": "uz", "pos": "noun"},
    {"slot": 1, "category": "derivation", "form": "лик", "lat_form": "lik", "function": "abstract noun",
     "example": "ишлилик → иш+ли+лик", "lang": "uz", "pos": "noun"},
    {"slot": 1, "category": "derivation", "form": "ли", "lat_form": "li", "function": "having",
     "example": "ишли → иш+ли", "lang": "uz", "pos": "noun"},
    {"slot": 1, "category": "derivation", "form": "сиз", "lat_form": "siz", "function": "without",
     "example": "ишсиз → иш+сиз", "lang": "uz", "pos": "noun"},
    {"slot": 1, "category": "derivation", "form": "ча", "lat_form": "cha", "function": "diminutive",
     "example": "китобча → китоб+ча", "lang": "uz", "pos": "noun"},

    # ───── Plural (slot 2 — noun) ─────
    {"slot": 2, "category": "plural", "form": "лар", "lat_form": "lar", "function": "plural",
     "example": "китоблар → китоб+лар", "lang": "uz", "pos": "noun"},

    # ───── Possessive (slot 3 — noun) ─────
    {"slot": 3, "category": "possessive", "form": "им", "lat_form": "im", "function": "1sg.poss",
     "example": "китобим → китоб+им", "lang": "uz", "pos": "noun"},
    {"slot": 3, "category": "possessive", "form": "инг", "lat_form": "ing", "function": "2sg.poss",
     "example": "китобинг → китоб+инг", "lang": "uz", "pos": "noun"},
    {"slot": 3, "category": "possessive", "form": "и", "lat_form": "i", "function": "3sg.poss",
     "example": "китоби → китоб+и", "lang": "uz", "pos": "noun"},
    {"slot": 3, "category": "possessive", "form": "имиз", "lat_form": "imiz", "function": "1pl.poss",
     "example": "китобимиз → китоб+имиз", "lang": "uz", "pos": "noun"},
    {"slot": 3, "category": "possessive", "form": "ингиз", "lat_form": "ingiz", "function": "2pl.poss",
     "example": "китобингиз → китоб+ингиз", "lang": "uz", "pos": "noun"},
    {"slot": 3, "category": "possessive", "form": "лари", "lat_form": "lari", "function": "3pl.poss",
     "example": "китоблари → китоб+лари", "lang": "uz", "pos": "noun"},

    # ───── Case (slot 4 — noun) ─────
    {"slot": 4, "category": "case", "form": "ни", "lat_form": "ni", "function": "accusative",
     "example": "китобни → китоб+ни", "lang": "uz", "pos": "noun"},
    {"slot": 4, "category": "case", "form": "га", "lat_form": "ga", "function": "dative",
     "example": "китобга → китоб+га", "lang": "uz", "pos": "noun"},
    {"slot": 4, "category": "case", "form": "да", "lat_form": "da", "function": "locative",
     "example": "китобда → китоб+да", "lang": "uz", "pos": "noun"},
    {"slot": 4, "category": "case", "form": "дан", "lat_form": "dan", "function": "ablative",
     "example": "китобдан → китоб+дан", "lang": "uz", "pos": "noun"},
    {"slot": 4, "category": "case", "form": "нинг", "lat_form": "ning", "function": "genitive",
     "example": "китобнинг → китоб+нинг", "lang": "uz", "pos": "noun"},

    # ───── Question particles (slot 6) ─────
    {"slot": 6, "category": "particle", "form": "ми", "lat_form": "mi", "function": "question",
     "example": "ишлайсанми → ишла+й+сан+ми", "lang": "uz"},
    {"slot": 6, "category": "particle", "form": "микан", "lat_form": "mikan", "function": "dubitative",
     "example": "ишлармикан → ишла+р+микан", "lang": "uz"},
    {"slot": 6, "category": "particle", "form": "ку", "lat_form": "ku", "function": "emphatic",
     "example": "ишлайсан-ку → ишла+й+сан+ку", "lang": "uz"},
]


def get_canonical_rules() -> List[Dict]:
    """Return the canonical rules list for DB seeding."""
    return CANONICAL_RULES


def find_violation_explanation(slot_seen: int, last_slot: int) -> str:
    """Generate human-readable explanation for a slot order violation."""
    SLOT_NAMES = {
        0: "ўзак (стем)",
        1: "ясовчи / нисбат",
        2: "инкор",
        3: "аспект / сифатдош",
        4: "замон / mayl",
        5: "шахс / сон",
        6: "сўроқ / юклама",
    }
    seen_name = SLOT_NAMES.get(slot_seen, f"slot {slot_seen}")
    last_name = SLOT_NAMES.get(last_slot, f"slot {last_slot}")
    return (
        f"'{seen_name}' категориясидаги қўшимча '{last_name}'дан кейин кела олмайди. "
        f"Тўғри тартиб: {' → '.join(SLOT_NAMES[i] for i in sorted(SLOT_NAMES.keys()))}"
    )
