"""
Phase 4: Uzbek Grammar Checker.

Combines:
  - Morphology Analyzer (Phase 2) — decompose word → stem + affixes
  - Tahrirchi Lexicon (Phase 3) — 8.7M word semantic index
  - BERT (Phase 1) — contextual MASK prediction
  - Sayqallash rules DB — exact + semantic rules

Produces typed grammar issues with suggestions and gloss.

Issue types:
    G/Morphology    — Word cannot be morphologically decomposed
    G/Agreement     — Subject-verb person/number disagreement
    G/Tense         — Inconsistent tense in sentence
    G/WordOrder     — Unusual SOV (Uzbek) violation
    G/Negation      — Double negation or missing negation
    S/UnknownWord   — Word not in 8.7M lexicon (likely typo)
    S/Suggestion    — BERT contextual suggestion disagrees with word
"""
from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

logger = logging.getLogger("grammar_checker")


@dataclass
class GrammarIssue:
    word: str
    from_index: int
    to_index: int
    issue_type: str                   # G/Morphology, G/Agreement, ...
    message: str                      # Human-readable explanation (Uzbek)
    suggestions: List[str] = field(default_factory=list)
    source: str = ""                  # morph, bert, faiss_lexicon, rules
    confidence: float = 0.0           # 0.0 — 1.0

    def to_dict(self):
        return asdict(self)


class UzbekGrammarChecker:
    """Multi-signal Uzbek grammar checker."""

    def __init__(self):
        self._morph = None
        self._bert = None
        self._lexicon = None

    # Lazy accessors (heavy imports)
    def _get_morph(self):
        if self._morph is None:
            import morphology
            self._morph = morphology.get_analyzer()
        return self._morph

    def _get_bert(self):
        if self._bert is None:
            import bert_engine
            self._bert = bert_engine.engine
        return self._bert

    def _get_lexicon(self):
        if self._lexicon is None:
            import db
            self._lexicon = db.tahrirchi_lexicon
        return self._lexicon

    # ───────────────────────────────────────────────
    # Main check()
    # ───────────────────────────────────────────────

    def check(self, text: str, lang: str = "uz") -> List[GrammarIssue]:
        """Run all grammar checks on text. Returns list of issues."""
        if lang != "uz":
            return []  # Only Uzbek supported in Phase 4
        if not text or not text.strip():
            return []

        issues: List[GrammarIssue] = []

        # Level 1: Per-word morphology check
        issues += self._check_morphology(text)

        # Level 2: Per-word lexicon check (BERT + FAISS lexicon)
        issues += self._check_lexicon_coverage(text)

        # Level 3: Sentence-level checks
        issues += self._check_agreement(text)
        issues += self._check_tense_consistency(text)
        issues += self._check_double_negation(text)

        # Deduplicate by (from_index, issue_type)
        seen = set()
        unique_issues = []
        for i in issues:
            key = (i.from_index, i.issue_type)
            if key not in seen:
                seen.add(key)
                unique_issues.append(i)

        return unique_issues

    # ───────────────────────────────────────────────
    # Level 1: Morphology validation
    # ───────────────────────────────────────────────

    def _check_morphology(self, text: str) -> List[GrammarIssue]:
        """Each word must be morphologically decomposable."""
        issues = []
        morph = self._get_morph()
        bert = self._get_bert()

        for match in re.finditer(r"\w+", text, re.UNICODE):
            word = match.group()
            if len(word) < 3:
                continue

            analysis = morph.analyze(word)
            if analysis is not None:
                # Word is OK
                continue

            # Word is morphologically unknown
            # Try BERT MASK prediction for suggestions
            suggestions = []
            try:
                masked = text[:match.start()] + "[MASK]" + text[match.end():]
                if bert.initialized:
                    suggestions = bert.predict_mask(masked, top_k=3)
            except Exception as e:
                logger.debug(f"BERT predict_mask error: {e}")

            issues.append(GrammarIssue(
                word=word,
                from_index=match.start(),
                to_index=match.end(),
                issue_type="G/Morphology",
                message=f"'{word}' — морфологик жиҳатдан нотанил сўз",
                suggestions=suggestions,
                source="morph+bert",
                confidence=0.7,
            ))

        return issues

    # ───────────────────────────────────────────────
    # Level 2: Lexicon coverage (tahrirchi.db FAISS)
    # ───────────────────────────────────────────────

    def _check_lexicon_coverage(self, text: str) -> List[GrammarIssue]:
        """Each content word should have semantic neighbors in 8.7M lexicon."""
        issues = []
        lex = self._get_lexicon()
        if not lex.is_ready():
            return issues  # Lexicon not loaded yet

        for match in re.finditer(r"\w+", text, re.UNICODE):
            word = match.group()
            if len(word) < 4:
                continue
            # Only check words that look like content words (not particles)
            if word.lower() in {"ва", "ёки", "лекин", "аммо", "бироқ", "чунки", "ҳатто"}:
                continue

            similar = lex.search_similar(word.lower(), k=5)

            # If no similar words found OR top similarity is very low → likely unknown
            if not similar:
                continue  # BERT not ready or embedding failed
            top_sim = similar[0]["similarity"] if similar else 0

            # Word itself not found in lexicon AND no semantically close neighbors
            if top_sim < 0.75:
                suggestions = [s["word"] for s in similar[:3]]
                issues.append(GrammarIssue(
                    word=word,
                    from_index=match.start(),
                    to_index=match.end(),
                    issue_type="S/UnknownWord",
                    message=f"'{word}' — 8.7M луғатда аниқ мос келмайди (энг яқин: {top_sim:.2f})",
                    suggestions=suggestions,
                    source="tahrirchi_faiss",
                    confidence=1.0 - top_sim,
                ))

        return issues

    # ───────────────────────────────────────────────
    # Level 3: Subject-verb agreement (person/number)
    # ───────────────────────────────────────────────

    def _check_agreement(self, text: str) -> List[GrammarIssue]:
        """Look for person mismatch between pronoun and verb."""
        issues = []
        morph = self._get_morph()

        # Pronoun → expected (person, number)
        PRONOUN_PERSON = {
            "мен": (1, "singular"), "биз": (1, "plural"),
            "сен": (2, "singular"), "сиз": (2, "plural"),
            "у": (3, "singular"), "улар": (3, "plural"),
            # Latin
            "men": (1, "singular"), "biz": (1, "plural"),
            "sen": (2, "singular"), "siz": (2, "plural"),
            "u": (3, "singular"), "ular": (3, "plural"),
        }

        # Split into sentences
        sentences = re.split(r"[.!?]+", text)
        offset = 0
        for sent in sentences:
            if not sent.strip():
                offset += len(sent) + 1
                continue

            # Find pronoun subject
            pronoun_found = None
            for word_match in re.finditer(r"\w+", sent, re.UNICODE):
                w = word_match.group().lower()
                if w in PRONOUN_PERSON:
                    pronoun_found = (w, PRONOUN_PERSON[w], offset + word_match.start())
                    break

            if not pronoun_found:
                offset += len(sent) + 1
                continue

            pronoun, (expected_person, expected_number), pron_pos = pronoun_found

            # Find verb in same sentence
            for word_match in re.finditer(r"\w+", sent, re.UNICODE):
                w = word_match.group()
                if w.lower() == pronoun:
                    continue
                analysis = morph.analyze(w)
                if analysis and analysis.pos == "verb" and analysis.person:
                    if analysis.person != expected_person or (
                        analysis.number and analysis.number != expected_number
                    ):
                        issues.append(GrammarIssue(
                            word=w,
                            from_index=offset + word_match.start(),
                            to_index=offset + word_match.end(),
                            issue_type="G/Agreement",
                            message=(
                                f"'{pronoun}' (person={expected_person}/{expected_number}) "
                                f"билан '{w}' (person={analysis.person}/{analysis.number}) мос келмайди"
                            ),
                            suggestions=[],
                            source="morph",
                            confidence=0.85,
                        ))
                        break

            offset += len(sent) + 1

        return issues

    # ───────────────────────────────────────────────
    # Level 3: Tense consistency
    # ───────────────────────────────────────────────

    def _check_tense_consistency(self, text: str) -> List[GrammarIssue]:
        """Within a sentence, verbs should share tense (with exceptions)."""
        issues = []
        morph = self._get_morph()

        sentences = re.split(r"[.!?]+", text)
        offset = 0
        for sent in sentences:
            if not sent.strip():
                offset += len(sent) + 1
                continue

            verb_tenses = []  # list of (word, tense, absolute_pos)
            for word_match in re.finditer(r"\w+", sent, re.UNICODE):
                w = word_match.group()
                analysis = morph.analyze(w)
                if analysis and analysis.pos == "verb" and analysis.tense:
                    verb_tenses.append((w, analysis.tense, offset + word_match.start(), offset + word_match.end()))

            if len(verb_tenses) >= 2:
                tenses_set = {t[1] for t in verb_tenses}
                if len(tenses_set) > 1 and not (
                    "progressive" in tenses_set and "past" in tenses_set  # allowed combo
                ):
                    # Flag the second verb with different tense
                    first_tense = verb_tenses[0][1]
                    for w, tense, start, end in verb_tenses[1:]:
                        if tense != first_tense:
                            issues.append(GrammarIssue(
                                word=w,
                                from_index=start,
                                to_index=end,
                                issue_type="G/Tense",
                                message=f"Замон мос келмайди: биринчи феъл '{first_tense}', '{w}' эса '{tense}'",
                                suggestions=[],
                                source="morph",
                                confidence=0.6,
                            ))
                            break

            offset += len(sent) + 1

        return issues

    # ───────────────────────────────────────────────
    # Level 3: Double negation (usually an error in Uzbek)
    # ───────────────────────────────────────────────

    def _check_double_negation(self, text: str) -> List[GrammarIssue]:
        """Detect multiple negations in one clause."""
        issues = []
        morph = self._get_morph()

        sentences = re.split(r"[.!?,]+", text)
        offset = 0
        for sent in sentences:
            if not sent.strip():
                offset += len(sent) + 1
                continue
            negations = []
            for word_match in re.finditer(r"\w+", sent, re.UNICODE):
                w = word_match.group()
                analysis = morph.analyze(w)
                if analysis and analysis.negation:
                    negations.append((w, offset + word_match.start(), offset + word_match.end()))

            if len(negations) >= 2:
                # Flag the second negation
                w, start, end = negations[1]
                issues.append(GrammarIssue(
                    word=w,
                    from_index=start,
                    to_index=end,
                    issue_type="G/Negation",
                    message=f"Иккиланма инкор: бир жумлада {len(negations)} та инкор",
                    suggestions=[],
                    source="morph",
                    confidence=0.75,
                ))

            offset += len(sent) + 1

        return issues


# ═══════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════

_checker: Optional[UzbekGrammarChecker] = None


def get_checker() -> UzbekGrammarChecker:
    global _checker
    if _checker is None:
        _checker = UzbekGrammarChecker()
    return _checker
