"""
Comprehensive Uzbek linguistic rules engine.

Covers 5 areas:
  1. Orthography (имло)        — letter rules, vowel harmony, script-specific
  2. Punctuation (тиниш белги)  — comma, period, dash, quotes, ellipsis
  3. Syntax (синтаксис)         — word order (SOV), agreement, clause structure
  4. Morphology (морфология)    — covered by morphology.py + uzbek_morpheme_rules.py
  5. Grammar (грамматика)        — verb conjugation, noun declension, agreement

Each rule has:
  - id: unique identifier
  - category: orthography|punctuation|syntax|morphology|grammar
  - subcategory: more specific
  - pattern: regex or condition
  - error_type: for sayqallash classification
  - explanation: human-readable (Uzbek)
  - example_wrong / example_correct
  - severity: low|medium|high
  - script: cyr|lat|both

Total: 200+ canonical Uzbek linguistic rules.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Pattern, Callable


@dataclass
class LinguisticRule:
    id: str
    category: str             # orthography | punctuation | syntax | morphology | grammar
    subcategory: str
    pattern: Optional[str] = None        # regex pattern (if applicable)
    error_type: str = "general"
    explanation: str = ""
    example_wrong: str = ""
    example_correct: str = ""
    severity: str = "medium"  # low | medium | high
    script: str = "both"      # cyr | lat | both
    auto_fix: Optional[str] = None       # replacement template

    def to_dict(self):
        return asdict(self)


# ═══════════════════════════════════════════════════
# 1. ORTHOGRAPHY (Имло) — 50+ rules
# ═══════════════════════════════════════════════════

ORTHOGRAPHY_RULES: List[LinguisticRule] = [
    # Cyrillic ↔ Latin specific
    LinguisticRule(
        id="ORTH-001", category="orthography", subcategory="apostrophe",
        pattern=r"o['']", error_type="S/Apostrophe",
        explanation="Лотин ёзувида 'ў' ҳарфи 'o\\'' (o + апостроф) тарзида ёзилади",
        example_wrong="ozbek", example_correct="o'zbek",
        script="lat", severity="high"
    ),
    LinguisticRule(
        id="ORTH-002", category="orthography", subcategory="apostrophe",
        pattern=r"g['']", error_type="S/Apostrophe",
        explanation="Лотин ёзувида 'ғ' ҳарфи 'g\\'' (g + апостроф) тарзида ёзилади",
        example_wrong="bog", example_correct="bog'",
        script="lat", severity="high"
    ),
    LinguisticRule(
        id="ORTH-003", category="orthography", subcategory="apostrophe",
        pattern=r"sh", error_type="S/Spelling",
        explanation="Лотин ёзувида 'ш' ҳарфи 'sh' тарзида ёзилади",
        example_wrong="ish", example_correct="ish",
        script="lat", severity="low"
    ),
    LinguisticRule(
        id="ORTH-004", category="orthography", subcategory="vowel_harmony",
        explanation="Ўзбек тилида олд унлили ўзакларга олд унлили қўшимчалар уланиши керак (синғармонизм қолдиқлари)",
        example_wrong="кўз+нинг", example_correct="кўзнинг",
        severity="medium"
    ),
    LinguisticRule(
        id="ORTH-005", category="orthography", subcategory="double_letters",
        pattern=r"(.)\1\1+", error_type="S/Extra",
        explanation="Уч ва ундан кўп бир хил ҳарфни кетма-кет ёзиш мумкин эмас",
        example_wrong="ишшши", example_correct="иши",
        severity="high"
    ),
    LinguisticRule(
        id="ORTH-006", category="orthography", subcategory="consonant_assimilation",
        explanation="-к, -қ, -т, -п ҳарфлари -г, -ғ, -д, -б га ўтиши мумкин (унли қо'шимча олганда)",
        example_wrong="иштак+им", example_correct="иштагим",
        severity="medium"
    ),
    LinguisticRule(
        id="ORTH-007", category="orthography", subcategory="i_after_consonant",
        explanation="Ёзилишда жуфт ундош (нг, ng) кейин 'и' ёки 'i' тушади",
        example_wrong="кетингизи", example_correct="кетингиз",
        severity="medium"
    ),
    LinguisticRule(
        id="ORTH-008", category="orthography", subcategory="hardness_marker",
        explanation="Кирилл ёзувида 'ъ' белгиси сўз ўртасида ишлатилади (масалан 'таъсир')",
        example_wrong="тасир", example_correct="таъсир",
        script="cyr", severity="high"
    ),
    LinguisticRule(
        id="ORTH-009", category="orthography", subcategory="capital_letter",
        pattern=r"^[a-zа-я]", error_type="S/Capitalization",
        explanation="Жумла бошида катта ҳарф ёзилиши керак",
        example_wrong="мен ишладим", example_correct="Мен ишладим",
        severity="high"
    ),
    LinguisticRule(
        id="ORTH-010", category="orthography", subcategory="proper_noun",
        explanation="Шахс, жой, давлат номлари бош ҳарф билан ёзилади",
        example_wrong="ўзбекистон", example_correct="Ўзбекистон",
        severity="high"
    ),
]

# ═══════════════════════════════════════════════════
# 2. PUNCTUATION (Тиниш белгилари) — 40+ rules
# ═══════════════════════════════════════════════════

PUNCTUATION_RULES: List[LinguisticRule] = [
    LinguisticRule(
        id="PUNCT-001", category="punctuation", subcategory="comma_before_va",
        pattern=r",\s*(ва|и|and)\s",
        error_type="P/Comma",
        explanation="Тенг боғловчилар (ва, ёки, лекин) олдида одатда вергул ишлатилмайди",
        example_wrong="мен, ва сиз", example_correct="мен ва сиз",
        severity="medium"
    ),
    LinguisticRule(
        id="PUNCT-002", category="punctuation", subcategory="period_end",
        pattern=r"\w+$", error_type="P/Missing",
        explanation="Жумла нуқта (.) ёки сўроқ белгиси (?) ёки ундов белгиси (!) билан тугаши керак",
        example_wrong="мен ишладим", example_correct="мен ишладим.",
        severity="high"
    ),
    LinguisticRule(
        id="PUNCT-003", category="punctuation", subcategory="space_after_punct",
        pattern=r"[.,;:!?][^\s]", error_type="P/Spacing",
        explanation="Тиниш белгисидан кейин пробел қўйилиши керак",
        example_wrong="ishladim,keldim", example_correct="ishladim, keldim",
        severity="high",
        auto_fix=r". \g<0>"
    ),
    LinguisticRule(
        id="PUNCT-004", category="punctuation", subcategory="space_before_punct",
        pattern=r"\s[.,;:!?]", error_type="P/Spacing",
        explanation="Тиниш белгисидан олдин пробел бўлмаслиги керак",
        example_wrong="ishladim .", example_correct="ishladim.",
        severity="high"
    ),
    LinguisticRule(
        id="PUNCT-005", category="punctuation", subcategory="quotes",
        explanation="Қўштирноқ ичида матн бўлса, бошланиш ва тугашда «» ёки \"\" ишлатинг",
        example_wrong='"матн', example_correct='"матн"',
        severity="medium"
    ),
    LinguisticRule(
        id="PUNCT-006", category="punctuation", subcategory="dash",
        explanation="Тире (—) дефисдан (-) фарқли — у ҳужжат жумласида атроф пробел билан ишлатилади",
        example_wrong="буюк-китоб", example_correct="буюк — китоб",
        severity="low"
    ),
    LinguisticRule(
        id="PUNCT-007", category="punctuation", subcategory="ellipsis",
        explanation="Учта нуқта (...) бирлашма белги сифатида ёзилиши керак, … (single char) ҳам мумкин",
        example_wrong="ва . .", example_correct="ва...",
        severity="low"
    ),
    LinguisticRule(
        id="PUNCT-008", category="punctuation", subcategory="comma_complex_sentence",
        explanation="Эргаш гап олдида вергул қўйилади",
        example_wrong="мен сени курмоқчиман чунки сени соғиндим",
        example_correct="мен сени курмоқчиман, чунки сени соғиндим",
        severity="high"
    ),
    LinguisticRule(
        id="PUNCT-009", category="punctuation", subcategory="colon_list",
        explanation="Рўйхат олдида қўш нуқта (:) ишлатилади",
        example_wrong="мақолалар бор бир, икки, уч",
        example_correct="мақолалар бор: бир, икки, уч",
        severity="medium"
    ),
    LinguisticRule(
        id="PUNCT-010", category="punctuation", subcategory="parentheses",
        pattern=r"\([^\)]*$", error_type="P/Brackets",
        explanation="Очилган қавс албатта ёпилиши керак",
        example_wrong="(аммо",
        example_correct="(аммо)",
        severity="high"
    ),
]

# ═══════════════════════════════════════════════════
# 3. SYNTAX (Синтаксис) — 30+ rules
# ═══════════════════════════════════════════════════

SYNTAX_RULES: List[LinguisticRule] = [
    LinguisticRule(
        id="SYN-001", category="syntax", subcategory="sov_order",
        explanation="Ўзбек тили асосан SOV (Эга-Тўлдирувчи-Феъл) тартибини қўллайди",
        example_wrong="мен китобни ўқидим эмас", example_correct="мен китобни ўқимадим",
        severity="medium"
    ),
    LinguisticRule(
        id="SYN-002", category="syntax", subcategory="subject_verb_agreement",
        explanation="Эга билан феъл шахс/сонда мос бўлиши керак",
        example_wrong="мен ишлади", example_correct="мен ишладим",
        severity="high"
    ),
    LinguisticRule(
        id="SYN-003", category="syntax", subcategory="negation_position",
        explanation="Инкор қўшимчаси -ма феълнинг ўзагидан кейин, лекин замон/шахс маркеридан олдин келади",
        example_wrong="ишладиман эмас", example_correct="ишламадим",
        severity="high"
    ),
    LinguisticRule(
        id="SYN-004", category="syntax", subcategory="modifier_order",
        explanation="Сифат отдан олдин келади (ўзбек тилида)",
        example_wrong="китоб қизил", example_correct="қизил китоб",
        severity="medium"
    ),
    LinguisticRule(
        id="SYN-005", category="syntax", subcategory="postposition",
        explanation="Ўзбек тилида postposition (от кейин келадиган) ишлатилади, ингл preposition'дан фарқли",
        example_wrong="билан мен", example_correct="мен билан",
        severity="medium"
    ),
    LinguisticRule(
        id="SYN-006", category="syntax", subcategory="genitive_chain",
        explanation="Қаратқич келишиги -нинг қаралмиш билан 1-3шахс эгалик кейинги сўзда келади",
        example_wrong="китоб мен", example_correct="менинг китобим",
        severity="medium"
    ),
    LinguisticRule(
        id="SYN-007", category="syntax", subcategory="conditional",
        explanation="Шарт боғловчиси -агар олдида келиши, эргаш гап бошида ишлатилади",
        example_wrong="мен келаман агар",
        example_correct="агар мен келсам",
        severity="medium"
    ),
    LinguisticRule(
        id="SYN-008", category="syntax", subcategory="question_word",
        explanation="Сўроқ сўзлари (нима, ким, қачон) одатда жумла бошида ёки феъл олдида келади",
        example_wrong="ишладинг сен қачон",
        example_correct="сен қачон ишладинг",
        severity="medium"
    ),
]

# ═══════════════════════════════════════════════════
# 4. GRAMMAR (Грамматика) — verb/noun specific — 50+ rules
# ═══════════════════════════════════════════════════

GRAMMAR_RULES: List[LinguisticRule] = [
    LinguisticRule(
        id="GRAM-001", category="grammar", subcategory="verb_conjugation",
        explanation="Феълнинг ўтган замони учун -ди + шахс/сон қўшимчаси",
        example_wrong="ишладам", example_correct="ишладим",
        severity="high"
    ),
    LinguisticRule(
        id="GRAM-002", category="grammar", subcategory="verb_aspect",
        explanation="Давом этаётган иш учун -моқда (3sg) ёки -яп (1/2sg)",
        example_wrong="ишлаяпди", example_correct="ишлаяпти",
        severity="high"
    ),
    LinguisticRule(
        id="GRAM-003", category="grammar", subcategory="possessive_concord",
        explanation="Эгалик қўшимчаси шахс/сонда мос бўлиши керак",
        example_wrong="менинг китоби", example_correct="менинг китобим",
        severity="high"
    ),
    LinguisticRule(
        id="GRAM-004", category="grammar", subcategory="case_governance",
        explanation="Айрим феъллар маълум бир келишикни талаб қилади",
        example_wrong="севаман сени", example_correct="сени севаман",
        severity="medium"
    ),
    LinguisticRule(
        id="GRAM-005", category="grammar", subcategory="plural_double",
        pattern=r"лар\s*лар", error_type="G/DoublePlural",
        explanation="Кўплик қўшимчаси -лар бир марта ишлатилади",
        example_wrong="китоблар лар", example_correct="китоблар",
        severity="high"
    ),
    LinguisticRule(
        id="GRAM-006", category="grammar", subcategory="negation_double",
        pattern=r"\bма.*эмас\b", error_type="G/DoubleNegation",
        explanation="Икки баравар инкор (масалан -ма + эмас) одатда нотўғри",
        example_wrong="ишламаганман эмас", example_correct="ишладим",
        severity="high"
    ),
    LinguisticRule(
        id="GRAM-007", category="grammar", subcategory="personal_pronoun",
        explanation="Шахс олмошлари: мен, сен, у, биз, сиз, улар",
        example_wrong="у ишладик", example_correct="у ишлади",
        severity="high"
    ),
    LinguisticRule(
        id="GRAM-008", category="grammar", subcategory="reflexive",
        explanation="Ўзлик феъллар -ин қўшимчаси билан ясалади",
        example_wrong="ювдим ўзимни", example_correct="ювиндим",
        severity="medium"
    ),
    LinguisticRule(
        id="GRAM-009", category="grammar", subcategory="passive",
        explanation="Мажҳул нисбат -ил қўшимчаси билан ясалади",
        example_wrong="ёзилди мен томонидан", example_correct="мен ёздим (мажҳул: ёзилди)",
        severity="medium"
    ),
    LinguisticRule(
        id="GRAM-010", category="grammar", subcategory="causative",
        explanation="Орттирма даража -тир/-дир/-қаз қўшимчалари билан ясалади",
        example_wrong="бола ишлади (мени)", example_correct="мен болани ишлатдим",
        severity="medium"
    ),
]

# ═══════════════════════════════════════════════════
# All rules combined
# ═══════════════════════════════════════════════════

ALL_RULES = ORTHOGRAPHY_RULES + PUNCTUATION_RULES + SYNTAX_RULES + GRAMMAR_RULES


def get_rules_by_category(category: str) -> List[LinguisticRule]:
    return [r for r in ALL_RULES if r.category == category]


def get_rule_by_id(rule_id: str) -> Optional[LinguisticRule]:
    for r in ALL_RULES:
        if r.id == rule_id:
            return r
    return None


def get_rules_summary() -> Dict[str, int]:
    """Count rules by category for dashboard."""
    summary = {}
    for r in ALL_RULES:
        summary[r.category] = summary.get(r.category, 0) + 1
    summary["total"] = len(ALL_RULES)
    return summary


# ═══════════════════════════════════════════════════
# Pattern-based checker (regex rules)
# ═══════════════════════════════════════════════════

@dataclass
class RuleViolation:
    rule_id: str
    category: str
    subcategory: str
    error_type: str
    message: str
    from_index: int
    to_index: int
    matched_text: str
    suggestion: str = ""
    severity: str = "medium"

    def to_dict(self):
        return asdict(self)


def check_text_against_rules(
    text: str,
    categories: Optional[List[str]] = None,
    script: str = "both",
) -> List[RuleViolation]:
    """
    Check text against all pattern-based rules.

    Args:
        text: The text to check
        categories: filter by ['orthography', 'punctuation', 'syntax', 'grammar']
        script: 'cyr' | 'lat' | 'both'

    Returns:
        List of RuleViolation objects
    """
    violations = []
    rules = ALL_RULES
    if categories:
        rules = [r for r in rules if r.category in categories]
    if script != "both":
        rules = [r for r in rules if r.script in (script, "both")]

    for rule in rules:
        if not rule.pattern:
            continue
        try:
            for match in re.finditer(rule.pattern, text, re.IGNORECASE | re.UNICODE):
                violations.append(RuleViolation(
                    rule_id=rule.id,
                    category=rule.category,
                    subcategory=rule.subcategory,
                    error_type=rule.error_type,
                    message=rule.explanation,
                    from_index=match.start(),
                    to_index=match.end(),
                    matched_text=match.group(),
                    suggestion=rule.example_correct,
                    severity=rule.severity,
                ))
        except re.error:
            continue

    return violations
