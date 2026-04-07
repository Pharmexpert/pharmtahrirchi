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

UZBEK_SUFFIXES_LAT = [
    (s.replace("ғ", "g'").replace("қ", "q").replace("ҳ", "h").replace("ў", "o'").replace("ш", "sh").replace("ч", "ch").replace("ъ", "'"), t)
    for s, t in UZBEK_SUFFIXES_CYR
]


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

        # Step 1: Direct dictionary lookup (whole word)
        if dic and dic.lookup(word_lower):
            # Word itself is in dictionary, no decomposition needed
            return MorphAnalysis(
                word=word, stem=word_lower,
                pos=self._infer_pos_from_word(word_lower, dic),
                morphemes=[Morpheme(surface=word, kind="stem")],
                source="hunspell.direct"
            )

        # Step 2: Heuristic greedy suffix stripping
        analysis = self._heuristic_decompose(word_lower, script, dic)
        if analysis:
            return analysis

        # Step 3: Spylls suggestion fallback
        if dic:
            try:
                suggestions = list(dic.suggest(word_lower))[:1]
                if suggestions:
                    # Word is probably a typo → return "unknown" analysis with suggestion
                    return MorphAnalysis(
                        word=word, stem=suggestions[0],
                        pos="unknown",
                        morphemes=[Morpheme(surface=word, kind="stem", gloss=f"тавсия: {suggestions[0]}")],
                        source="hunspell.suggest"
                    )
            except Exception:
                pass

        return None

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
        """Try to peel off known Uzbek suffixes one by one from the end."""
        suffixes = UZBEK_SUFFIXES_CYR if script == "cyrl" else UZBEK_SUFFIXES_LAT
        original = word

        morphemes: List[Morpheme] = []
        features: Dict = {
            "tense": None, "person": None, "number": None,
            "case": None, "mood": None, "negation": False,
        }

        max_iterations = 6
        for _ in range(max_iterations):
            stripped_something = False
            for suffix, gloss in suffixes:
                if word.endswith(suffix) and len(word) > len(suffix) + 1:
                    potential_stem = word[:-len(suffix)]
                    # Check if the potential stem is in dictionary
                    if dic and dic.lookup(potential_stem):
                        morphemes.insert(0, Morpheme(surface=suffix, kind="suffix", gloss=gloss))
                        self._enrich_features(features, gloss)
                        word = potential_stem
                        stripped_something = True
                        break

                    # Or maybe stem itself needs another round of stripping → continue peeling
                    # Check if stem has any more suffixes to strip
                    if len(potential_stem) >= 3:
                        # Heuristic: if stem looks like plausible Uzbek root (mostly consonants+vowels), accept
                        if self._looks_like_root(potential_stem):
                            morphemes.insert(0, Morpheme(surface=suffix, kind="suffix", gloss=gloss))
                            self._enrich_features(features, gloss)
                            word = potential_stem
                            stripped_something = True
                            break
            if not stripped_something:
                break

        if not morphemes:
            return None  # No decomposition happened

        # Add stem as first morpheme
        morphemes.insert(0, Morpheme(surface=word, kind="stem"))

        pos = self._infer_pos_from_suffixes(morphemes)

        return MorphAnalysis(
            word=original,
            stem=word,
            pos=pos,
            morphemes=morphemes,
            tense=features["tense"],
            person=features["person"],
            number=features["number"],
            case=features["case"],
            mood=features["mood"],
            negation=features["negation"],
            source="heuristic",
        )

    def _looks_like_root(self, s: str) -> bool:
        """Cheap check: does this look like a plausible Uzbek root?"""
        if len(s) < 2 or len(s) > 10:
            return False
        # Must have at least one vowel
        vowels = set("аеёиоуыюяўаеиоуэü")  # cyr + lat loose
        return any(ch in vowels for ch in s.lower())

    def _enrich_features(self, features: Dict, gloss: str):
        """Extract grammar features from suffix gloss."""
        g = gloss.lower()
        if "negation" in g or "negative" in g or "prohibitive" in g:
            features["negation"] = True
        if "past" in g:
            features["tense"] = "past"
        elif "progressive" in g or "present" in g:
            features["tense"] = "progressive" if "progressive" in g else "present"
        elif "future" in g or "habitual" in g:
            features["tense"] = "future" if "future" in g else "habitual"
        if "1sg" in g or "1pl" in g:
            features["person"] = 1
        elif "2sg" in g or "2pl" in g:
            features["person"] = 2
        elif "3sg" in g or "3pl" in g:
            features["person"] = 3
        if "1sg" in g or "2sg" in g or "3sg" in g:
            features["number"] = "singular"
        elif "1pl" in g or "2pl" in g or "3pl" in g or "plural" in g:
            features["number"] = "plural"
        if "question" in g or "interrogative" in g or "dubitative" in g:
            features["mood"] = "interrogative"
        elif "imperative" in g:
            features["mood"] = "imperative"
        elif "optative" in g:
            features["mood"] = "optative"
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
        """Look up Hunspell flags and map to POS."""
        try:
            entries = dic.dic.homonyms(word) if hasattr(dic.dic, "homonyms") else []
            for entry in entries:
                flags = getattr(entry, "flags", set()) or set()
                for f in flags:
                    sem = FLAG_SEMANTICS.get(str(f), {})
                    if "pos" in sem:
                        return sem["pos"]
        except Exception:
            pass
        return "unknown"

    def _infer_pos_from_suffixes(self, morphemes: List[Morpheme]) -> str:
        """Infer POS based on which suffix categories are present."""
        suffixes = [m.gloss for m in morphemes if m.kind == "suffix"]
        text = " ".join(suffixes).lower()
        if any(t in text for t in ["tense", "past", "progressive", "future", "habitual",
                                   "negation", "imperative", "optative", "question",
                                   "sg.", "pl.", "interrogative", "prohibitive"]):
            return "verb"
        if any(t in text for t in ["case", "accusative", "dative", "ablative",
                                   "locative", "genitive", "plural", "possessive"]):
            return "noun"
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
