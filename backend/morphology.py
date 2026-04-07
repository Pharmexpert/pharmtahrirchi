"""
Uzbek morphological analyzer.

Decomposes words into: stem + affixes with linguistic metadata
using Hunspell dictionary + spylls affix rules + custom Uzbek grammar rules.

Used by:
  - Grammar checker (phase 4)
  - Sayqallash pipeline (level 0)
  - Dictionary word enrichment
  - User-facing morphology explanation UI

Example:
    analyzer = get_analyzer()
    result = analyzer.analyze("ишламоқдамасанми")
    # → MorphAnalysis(
    #     word="ишламоқдамасанми",
    #     stem="ишла",
    #     pos="verb",
    #     affixes=[
    #       (suffix, "моқда", "progressive tense"),
    #       (suffix, "мас", "negative"),
    #       (suffix, "санми", "2sg question"),
    #     ],
    #     tense="progressive",
    #     negation=True,
    #     person=2,
    #     number="singular",
    #     mood="interrogative",
    #   )
"""

from __future__ import annotations

import os
import re
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Tuple, Dict

logger = logging.getLogger("morphology")

# ═══════════════════════════════════════════════════
# Affix flag → semantic category mapping
# Based on hunspell_data.py FLAG_DESCRIPTIONS
# ═══════════════════════════════════════════════════

FLAG_SEMANTICS = {
    # Part of speech
    "F": {"pos": "verb", "desc": "феъл шакллари"},
    "X": {"pos": "verb", "desc": "феъл тусланиши", "tense_marker": True},
    "Q": {"pos": "verb", "desc": "1-шахс феъл", "person": 1},
    "A": {"pos": "adjective", "desc": "сифат/ўхшатиш"},
    "Z": {"pos": "adverb", "desc": "зарф"},
    "N": {"pos": "noun", "desc": "жой/йўналиш"},

    # Possessive
    "B": {"category": "possessive", "person": 1, "desc": "1-шахс эгалик (унлисиз)"},
    "C": {"category": "possessive", "person": 1, "desc": "1-шахс эгалик (унли кейин)"},
    "D": {"category": "possessive", "person": 2, "desc": "2-шахс эгалик"},
    "q": {"category": "possessive", "desc": "эгалик кичик ҳарф"},
    "M": {"category": "possessive", "desc": "эгалик + сифат"},

    # Number & case
    "S": {"category": "number", "number": "plural", "desc": "кўплик"},
    "V": {"category": "case", "desc": "келишик (дан, да, ни, га)"},
    "H": {"category": "case", "desc": "ҳол қўшимчалари"},

    # Interrogative/particle
    "I": {"category": "particle", "desc": "юклама (ки, ми, чи, ку)"},
    "K": {"category": "interrogative", "desc": "сўроқ (микан)"},
    "L": {"category": "interrogative", "person": 2, "desc": "2-шахс сўроқ (мисан, мисиз)"},

    # Morphology others
    "E": {"category": "alternation", "desc": "ундош алмашуви (-к → +г)"},
    "G": {"category": "grammatical", "desc": "грамматик категория"},
    "J": {"category": "auxiliary", "desc": "феъл (эканлик)"},
    "P": {"category": "prefix", "desc": "префикс"},
    "R": {"category": "marker", "desc": "қўшимча белги"},
    "T": {"category": "transformation", "desc": "тус ўзгариши"},
    "U": {"category": "harmony", "desc": "уйғунлик"},
    "W": {"category": "ordinal", "desc": "тартиб"},
    "Y": {"category": "auxiliary", "desc": "йордамчи"},
    "-": {"category": "special", "desc": "махсус белги (тире)"},
}

# Common Uzbek suffix patterns (used for heuristic segmentation)
# Ordered longest-first for greedy matching
UZBEK_SUFFIXES_CYR = [
    # Verb tense & aspect
    ("моқдаман", "1sg.progressive"),
    ("моқдасан", "2sg.progressive"),
    ("моқдамиз", "1pl.progressive"),
    ("моқдасиз", "2pl.progressive"),
    ("моқдалар", "3pl.progressive"),
    ("моқда", "3sg.progressive"),
    # Past tense
    ("гандик", "1pl.past.perfect"),
    ("гансиз", "2pl.past.perfect"),
    ("ганман", "1sg.past.perfect"),
    ("гансан", "2sg.past.perfect"),
    ("ганлар", "3pl.past.perfect"),
    ("ган", "3sg.past.perfect"),
    ("дилар", "3pl.past"),
    ("дингиз", "2pl.past"),
    ("димиз", "1pl.past"),
    ("динг", "2sg.past"),
    ("дим", "1sg.past"),
    ("дик", "1pl.past"),
    ("ди", "3sg.past"),
    # Future / habitual
    ("адиганмиз", "1pl.habitual"),
    ("адиганман", "1sg.habitual"),
    ("адиган", "habitual"),
    ("ажагимиз", "1pl.future"),
    ("ажагим", "1sg.future"),
    ("ажак", "future"),
    # Imperative / optative
    ("син", "3sg.imperative"),
    ("синлар", "3pl.imperative"),
    ("айлик", "1pl.optative"),
    ("ай", "1sg.optative"),
    # Negation
    ("масангиз", "2pl.negation.conditional"),
    ("масанг", "2sg.negation.conditional"),
    ("маслик", "negation.nominal"),
    ("магин", "2sg.prohibitive"),
    ("май", "negation.converb"),
    ("мас", "negation"),
    ("ма", "negation"),
    # Question
    ("санми", "2sg.question"),
    ("сизми", "2pl.question"),
    ("миканми", "dubitative.question"),
    ("микан", "dubitative"),
    ("ми", "question"),
    # Case
    ("ларни", "plural.accusative"),
    ("ларга", "plural.dative"),
    ("лардан", "plural.ablative"),
    ("ларда", "plural.locative"),
    ("лар", "plural"),
    ("нинг", "genitive"),
    ("ни", "accusative"),
    ("дан", "ablative"),
    ("да", "locative"),
    ("га", "dative"),
    ("ка", "dative"),
    ("қа", "dative"),
    # Possessive
    ("имиз", "1pl.possessive"),
    ("ингиз", "2pl.possessive"),
    ("лари", "3pl.possessive"),
    ("им", "1sg.possessive"),
    ("инг", "2sg.possessive"),
    ("си", "3sg.possessive"),
    ("и", "3sg.possessive"),
]

# Sort cyrillic suffixes longest-first for greedy matching
UZBEK_SUFFIXES_CYR.sort(key=lambda x: -len(x[0]))

# Full Cyrillic → Latin transliteration map for Uzbek
_CYR_TO_LAT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "j", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "x", "ц": "ts", "ш": "sh", "ы": "i", "э": "e", "ю": "yu",
    "я": "ya", "ғ": "g'", "қ": "q", "ҳ": "h", "ў": "o'", "ъ": "'", "ь": "",
    "ч": "ch", "ў": "o'",
}


def _cyr_to_lat(s: str) -> str:
    out = []
    for ch in s:
        out.append(_CYR_TO_LAT.get(ch, ch))
    return "".join(out)


# Build Latin suffix list by full transliteration of cyrillic ones,
# plus add common Latin-specific forms
UZBEK_SUFFIXES_LAT = [
    (_cyr_to_lat(s), t) for s, t in UZBEK_SUFFIXES_CYR
]

# Manually verified additions for Latin (in case transliteration produces ambiguities)
_LAT_ADDITIONS = [
    ("moqdaman", "1sg.progressive"),
    ("moqdasan", "2sg.progressive"),
    ("moqdamiz", "1pl.progressive"),
    ("moqdasiz", "2pl.progressive"),
    ("moqdalar", "3pl.progressive"),
    ("moqda", "3sg.progressive"),
    ("ganman", "1sg.past.perfect"),
    ("gansan", "2sg.past.perfect"),
    ("gan", "3sg.past.perfect"),
    ("dim", "1sg.past"),
    ("ding", "2sg.past"),
    ("di", "3sg.past"),
    ("masangiz", "2pl.negation.conditional"),
    ("masang", "2sg.negation.conditional"),
    ("magin", "2sg.prohibitive"),
    ("may", "negation.converb"),
    ("mas", "negation"),
    ("ma", "negation"),
    ("sanmi", "2sg.question"),
    ("sizmi", "2pl.question"),
    ("mikan", "dubitative"),
    ("mi", "question"),
    ("larni", "plural.accusative"),
    ("larga", "plural.dative"),
    ("lardan", "plural.ablative"),
    ("larda", "plural.locative"),
    ("lar", "plural"),
    ("ning", "genitive"),
    ("ni", "accusative"),
    ("dan", "ablative"),
    ("da", "locative"),
    ("ga", "dative"),
    ("imiz", "1pl.possessive"),
    ("ingiz", "2pl.possessive"),
    ("im", "1sg.possessive"),
    ("ing", "2sg.possessive"),
    ("si", "3sg.possessive"),
]
# Merge additions in front (longest-first preserved due to suffix matching loop)
_seen = set()
_merged = []
for entry in _LAT_ADDITIONS + UZBEK_SUFFIXES_LAT:
    if entry[0] and entry[0] not in _seen:
        _seen.add(entry[0])
        _merged.append(entry)
# Sort by length desc so greedy matching works
_merged.sort(key=lambda x: -len(x[0]))
UZBEK_SUFFIXES_LAT = _merged


@dataclass
class Morpheme:
    surface: str              # actual text
    kind: str                 # "stem", "suffix", "prefix"
    gloss: str = ""           # grammatical gloss
    category: str = ""        # pos, tense, person, case, ...

    def to_dict(self):
        return asdict(self)


@dataclass
class MorphAnalysis:
    word: str
    stem: str
    pos: str = "unknown"                 # verb/noun/adjective/adverb/unknown
    morphemes: List[Morpheme] = field(default_factory=list)

    # Rich features (when determinable)
    tense: Optional[str] = None          # past/present/future/progressive
    person: Optional[int] = None         # 1/2/3
    number: Optional[str] = None         # singular/plural
    case: Optional[str] = None           # nominative/accusative/...
    mood: Optional[str] = None           # indicative/imperative/interrogative
    negation: bool = False
    source: str = "hunspell"             # hunspell/heuristic/combined

    # Phase 2.5: Validation
    valid_order: bool = True             # passes Uzbek slot order
    order_score: float = 1.0             # 0..1 (1 = perfect)
    order_issues: List[str] = field(default_factory=list)

    def breakdown(self) -> str:
        """Human-readable: 'ишла + моқда (progressive) + мас (negation) + санми (2sg.question)'"""
        parts = []
        for m in self.morphemes:
            if m.gloss:
                parts.append(f"{m.surface} ({m.gloss})")
            else:
                parts.append(m.surface)
        return " + ".join(parts) if parts else self.word

    def to_dict(self):
        return {
            "word": self.word,
            "stem": self.stem,
            "pos": self.pos,
            "morphemes": [m.to_dict() for m in self.morphemes],
            "tense": self.tense,
            "person": self.person,
            "number": self.number,
            "case": self.case,
            "mood": self.mood,
            "negation": self.negation,
            "breakdown": self.breakdown(),
            "source": self.source,
            "valid_order": self.valid_order,
            "order_score": self.order_score,
            "order_issues": self.order_issues,
        }


class UzbekMorphologyAnalyzer:
    """Hybrid morphology analyzer for Uzbek: Hunspell dictionary + heuristic suffix stripping."""

    def __init__(self):
        self._hunspell = None
        self._hunspell_lat = None
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded:
            return
        try:
            from spylls.hunspell import Dictionary
            HUNSPELL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hunspell")

            cyr_base = os.path.join(HUNSPELL_DIR, "uz_UZ_Cyrl")
            lat_base = os.path.join(HUNSPELL_DIR, "uz_UZ")

            if os.path.exists(cyr_base + ".dic"):
                self._hunspell = Dictionary.from_files(cyr_base)
                logger.info("[Morph] Cyrillic Hunspell loaded")
            if os.path.exists(lat_base + ".dic"):
                self._hunspell_lat = Dictionary.from_files(lat_base)
                logger.info("[Morph] Latin Hunspell loaded")
        except Exception as e:
            logger.error(f"[Morph] Failed to load Hunspell: {e}")
        finally:
            self._loaded = True

    def _detect_script(self, word: str) -> str:
        """Return 'cyrl' or 'lat'."""
        cyr = sum(1 for ch in word if "\u0400" <= ch <= "\u04FF")
        return "cyrl" if cyr > len(word) / 3 else "lat"

    def _get_dict(self, script: str):
        return self._hunspell if script == "cyrl" else self._hunspell_lat

    # ───────────────────────────────────────────────
    # Public API
    # ───────────────────────────────────────────────

    def analyze(self, word: str) -> Optional[MorphAnalysis]:
        """Analyze single word. Returns None if cannot decompose."""
        self._ensure_loaded()
        word = word.strip()
        if not word or len(word) < 2:
            return None

        script = self._detect_script(word)
        dic = self._get_dict(script)
        word_lower = word.lower()

        result: Optional[MorphAnalysis] = None

        # Step 1: Direct dictionary lookup (whole word)
        if dic and dic.lookup(word_lower):
            heuristic = self._heuristic_decompose(word_lower, script, dic)
            if heuristic and len(heuristic.morphemes) > 1:
                heuristic.source = "hunspell.direct+heuristic"
                if heuristic.pos == "unknown":
                    heuristic.pos = self._infer_pos_from_word(word_lower, dic)
                result = heuristic
            else:
                result = MorphAnalysis(
                    word=word, stem=word_lower,
                    pos=self._infer_pos_from_word(word_lower, dic),
                    morphemes=[Morpheme(surface=word, kind="stem")],
                    source="hunspell.direct"
                )

        # Step 2: Heuristic decomposition
        if result is None:
            analysis = self._heuristic_decompose(word_lower, script, dic)
            if analysis:
                result = analysis

        # Step 3: Spylls suggestion fallback
        if result is None and dic:
            try:
                suggestions = list(dic.suggest(word_lower))[:1]
                if suggestions:
                    result = MorphAnalysis(
                        word=word, stem=suggestions[0],
                        pos="unknown",
                        morphemes=[Morpheme(surface=word, kind="stem", gloss=f"тавсия: {suggestions[0]}")],
                        source="hunspell.suggest"
                    )
            except Exception:
                pass

        if result is None:
            return None

        # Phase 2.5: Validate morpheme order against canonical Uzbek slots
        try:
            from uzbek_morpheme_rules import validate_morpheme_order
            validation = validate_morpheme_order(
                [m.to_dict() for m in result.morphemes],
                pos_hint=result.pos or "verb",
            )
            result.valid_order = validation.valid
            result.order_score = validation.score
            result.order_issues = validation.issues
        except Exception as e:
            logger.debug(f"Morpheme order validation skipped: {e}")

        return result

    def is_valid_form(self, word: str) -> bool:
        """Quick yes/no: is this word morphologically well-formed?"""
        return self.analyze(word) is not None

    def analyze_text(self, text: str) -> List[MorphAnalysis]:
        """Analyze every word in a text. Returns list of analyses (None skipped)."""
        results = []
        for word in re.findall(r"\w+", text, re.UNICODE):
            if len(word) < 2:
                continue
            a = self.analyze(word)
            if a:
                results.append(a)
        return results

    # ───────────────────────────────────────────────
    # Heuristic decomposition
    # ───────────────────────────────────────────────

    def _heuristic_decompose(self, word: str, script: str, dic) -> Optional[MorphAnalysis]:
        """
        Beam-search based decomposition that explores multiple suffix candidates
        and ranks them by Uzbek slot order validity.

        Strategy:
          1. Generate up to TOP_K candidate decompositions
          2. Score each by stem-in-dict bonus + slot order monotonicity
          3. Return the highest-scoring valid candidate
        """
        suffixes = UZBEK_SUFFIXES_CYR if script == "cyrl" else UZBEK_SUFFIXES_LAT

        candidates = self._beam_decompose(word, suffixes, dic, beam_width=4, max_depth=6)
        if not candidates:
            return None

        # Score each candidate
        best = None
        best_score = -1.0
        for cand in candidates:
            score = self._score_candidate(cand, dic)
            if score > best_score:
                best_score = score
                best = cand

        if best is None:
            return None

        morpheme_list = best["morphemes"]
        stem = best["stem"]
        features = best["features"]

        if len(morpheme_list) <= 1:
            return None  # No real decomposition

        pos = self._infer_pos_from_suffixes(morpheme_list)

        return MorphAnalysis(
            word=word,
            stem=stem,
            pos=pos,
            morphemes=morpheme_list,
            tense=features["tense"],
            person=features["person"],
            number=features["number"],
            case=features["case"],
            mood=features["mood"],
            negation=features["negation"],
            source="heuristic",
        )

    def _beam_decompose(self, word: str, suffixes, dic, beam_width: int = 4, max_depth: int = 6) -> List[Dict]:
        """
        Beam search: at each peeling step, keep top N candidates that have
        the highest "is_in_dict OR looks_like_root" plausibility.

        Returns a list of candidate dicts:
          { stem, morphemes, features, depth }
        """
        # Each beam state: (current_word, morpheme_chain, features, log_score)
        initial_features = {
            "tense": None, "person": None, "number": None,
            "case": None, "mood": None, "negation": False,
        }
        # Initial beam = just the word as candidate stem
        beam = [{
            "stem": word,
            "morphemes": [Morpheme(surface=word, kind="stem")],
            "features": dict(initial_features),
            "score": 0.0,
        }]
        # Final candidates
        final_candidates = []

        for depth in range(max_depth):
            new_beam = []
            for state in beam:
                w = state["stem"]
                if dic and dic.lookup(w):
                    # This is a valid terminal
                    final_candidates.append(state)

                # Try peeling each suffix
                for suffix, gloss in suffixes:
                    if w.endswith(suffix) and len(w) > len(suffix) + 1:
                        potential_stem = w[:-len(suffix)]
                        in_dict = bool(dic and dic.lookup(potential_stem))
                        looks_root = self._looks_like_root(potential_stem)
                        # Minimum stem length: 2 for dict-recognized stems,
                        # 3 for heuristic-only roots (avoid stripping into nonsense)
                        if in_dict:
                            if len(potential_stem) < 2:
                                continue
                        else:
                            if len(potential_stem) < 3:
                                continue
                            if not looks_root:
                                continue

                        # Phonological constraint: don't strip vowel-only single-letter
                        # suffix "и"/"i" if the original word is itself a recognized
                        # noun ending in consonant+vowel (e.g. "dori" = drug, not "dor"+"i")
                        if suffix in ("i", "и") and dic and dic.lookup(w):
                            # Original word is a valid Hunspell entry → don't peel "i"
                            continue
                        new_state = {
                            "stem": potential_stem,
                            "morphemes": [Morpheme(surface=potential_stem, kind="stem")] +
                                         [Morpheme(surface=suffix, kind="suffix", gloss=gloss)] +
                                         [m for m in state["morphemes"] if m.kind == "suffix"],
                            "features": self._merge_features(state["features"], gloss),
                            "score": state["score"] + (2.0 if in_dict else 0.5),
                        }
                        new_beam.append(new_state)

            if not new_beam:
                break
            # Keep top beam_width by score
            new_beam.sort(key=lambda s: -s["score"])
            beam = new_beam[:beam_width]

        # Add final beam states as candidates if they're valid
        for state in beam:
            if dic and dic.lookup(state["stem"]):
                final_candidates.append(state)
            elif self._looks_like_root(state["stem"]):
                final_candidates.append(state)

        return final_candidates

    def _merge_features(self, base: Dict, gloss: str) -> Dict:
        """Like _enrich_features but creates a new dict."""
        new_features = dict(base)
        self._enrich_features(new_features, gloss)
        return new_features

    def _score_candidate(self, candidate: Dict, dic) -> float:
        """
        Score a candidate decomposition.

        Components:
          + 5.0 if stem is in dictionary
          + 1.0 per morpheme that has a recognized slot
          + 3.0 if morpheme order is valid (monotone increasing slots)
          - 2.0 per slot order violation
          + 0.5 * number of morphemes (prefer richer parses, but not too many)
        """
        from uzbek_morpheme_rules import validate_morpheme_order

        score = 0.0

        if dic and dic.lookup(candidate["stem"]):
            score += 5.0

        morphemes_dict = [m.to_dict() for m in candidate["morphemes"]]
        validation = validate_morpheme_order(morphemes_dict)

        if validation.valid:
            score += 3.0
        score -= 2.0 * len(validation.issues)

        # Prefer fewer morphemes (Occam's razor) — but not too few
        n_suffixes = sum(1 for m in candidate["morphemes"] if m.kind == "suffix")
        score += min(n_suffixes, 4) * 0.3

        # Bonus for recognized slots
        for slot in validation.morpheme_slots:
            if slot >= 0:
                score += 0.5

        return score

    def _looks_like_root(self, s: str) -> bool:
        """Cheap check: does this look like a plausible Uzbek root or partial stem?

        Allow up to 20 chars because intermediate stems during recursive
        suffix peeling can be longer than final roots.
        """
        if len(s) < 2 or len(s) > 20:
            return False
        # Must have at least one vowel (cyrillic OR latin)
        # Cyrillic vowels: а е ё и о у ы ю я ў э
        # Latin vowels: a e i o u (and o' for ў)
        vowels = set("аеёиоуыюяўэaeiou")
        return any(ch in vowels for ch in s.lower())

    def _enrich_features(self, features: Dict, gloss: str):
        """Extract grammar features from suffix gloss.

        IMPORTANT: Suffixes are peeled from end → start, so the FIRST call
        corresponds to the OUTERMOST suffix. Outermost suffix wins for
        person/number/mood/case (use first-write-wins semantics).
        Negation and tense accumulate (last write wins, since they may be
        nested in deeper morphemes).
        """
        g = gloss.lower()

        # Negation accumulates (any negation marker → negation True)
        if "negation" in g or "negative" in g or "prohibitive" in g:
            features["negation"] = True

        # Tense: last write wins (deeper = closer to root = main verb tense)
        if "past" in g:
            features["tense"] = "past"
        elif "progressive" in g or "present" in g:
            features["tense"] = "progressive" if "progressive" in g else "present"
        elif "future" in g or "habitual" in g:
            features["tense"] = "future" if "future" in g else "habitual"

        # Person/number: FIRST WRITE WINS (outermost suffix = surface agreement)
        if features.get("person") is None:
            if "1sg" in g or "1pl" in g:
                features["person"] = 1
            elif "2sg" in g or "2pl" in g:
                features["person"] = 2
            elif "3sg" in g or "3pl" in g:
                features["person"] = 3
        if features.get("number") is None:
            if "1sg" in g or "2sg" in g or "3sg" in g:
                features["number"] = "singular"
            elif "1pl" in g or "2pl" in g or "3pl" in g or "plural" in g:
                features["number"] = "plural"

        # Mood: first write wins (outermost suffix marks utterance type)
        if features.get("mood") is None:
            if "question" in g or "interrogative" in g or "dubitative" in g:
                features["mood"] = "interrogative"
            elif "imperative" in g:
                features["mood"] = "imperative"
            elif "optative" in g:
                features["mood"] = "optative"

        # Case: first write wins
        if features.get("case") is None:
            if "accusative" in g:
                features["case"] = "accusative"
            elif "dative" in g:
                features["case"] = "dative"
            elif "ablative" in g:
                features["case"] = "ablative"
            elif "locative" in g:
                features["case"] = "locative"
            elif "genitive" in g:
                features["case"] = "genitive"

    def _infer_pos_from_word(self, word: str, dic) -> str:
        """
        Look up Hunspell flags and map to POS by counting noun vs verb signals.

        Uzbek Hunspell dict assigns multiple flags per word; many nouns have
        possessive/case/plural markers (B, M, S, V) AND a separate entry with
        verb conjugation flags (X) because the same root can serve both roles
        in agglutinative language. We weight noun signals stronger than verb
        because most "uy", "mehmon", "kitob" type words are primarily nouns.
        """
        # Strong noun signals: possessive/plural/case markers
        NOUN_FLAGS = {"S", "V", "B", "C", "D", "M", "N"}
        # Strong verb signals: tense/conjugation
        VERB_FLAGS = {"F", "X"}

        try:
            entries = list(dic.dic.homonyms(word)) if hasattr(dic.dic, "homonyms") else []
            noun_count = 0
            verb_count = 0
            for entry in entries:
                flags = getattr(entry, "flags", set()) or set()
                fs = {str(f) for f in flags}
                noun_count += len(fs & NOUN_FLAGS)
                verb_count += len(fs & VERB_FLAGS)

            # 3+ noun flags is decisive → noun
            if noun_count >= 3:
                return "noun"
            # Pure verb (no noun flags at all)
            if verb_count > 0 and noun_count == 0:
                return "verb"
            # Mixed but verb stronger
            if verb_count > noun_count:
                return "verb"
            # Default: noun (most accepted Uzbek words are nouns)
            if noun_count > 0:
                return "noun"
            return "noun"
        except Exception:
            pass
        return "unknown"

    def _infer_pos_from_suffixes(self, morphemes: List[Morpheme]) -> str:
        """Infer POS based on which suffix categories are present.

        Noun markers (case/possessive/plural) are checked FIRST so that
        e.g. 'kitobimiz' (1pl.possessive) → noun, not verb.
        """
        suffixes = [m.gloss for m in morphemes if m.kind == "suffix"]
        text = " ".join(suffixes).lower()

        # NOUN markers — definite case markers
        noun_markers = ["accusative", "dative", "ablative", "locative", "genitive",
                        "plural", "possessive", "case"]
        if any(t in text for t in noun_markers):
            return "noun"

        # VERB markers — tense / mood / negation
        verb_markers = ["tense", "past", "progressive", "future", "habitual",
                        "present", "negation", "imperative", "optative", "question",
                        "interrogative", "prohibitive", "converb", "dubitative"]
        if any(t in text for t in verb_markers):
            return "verb"

        return "unknown"


# ═══════════════════════════════════════════════════
# Singleton accessor
# ═══════════════════════════════════════════════════

_analyzer: Optional[UzbekMorphologyAnalyzer] = None


def get_analyzer() -> UzbekMorphologyAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = UzbekMorphologyAnalyzer()
    return _analyzer
