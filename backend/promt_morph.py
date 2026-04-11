# -*- coding: utf-8 -*-
"""
promt_morph.py
==============
morph.dll (PROMT Expert NMT v23.2) нинг тўлиқ Python реализацияси.

COM интерфейс: IPromtMorph v1–v13 барча методлари.
Маълумот манбаи: Uzbek.fdi → uzbek_fdi_data.json

Ишлатиш:
    morph = PromtMorph()
    morph.initialize("./resources")
    morph.put_key("китобларимдан")
    print(morph.get_key())          # → 'китоб'
    print(morph.modifs)             # → {'pos': 'noun', 'case': 'abl', 'number': 'pl', ...}
    print(morph.number_of_psp)      # → 1
    forms = morph.psp_forms(0, 0)   # → ['китоб','китобни','китобга',...]
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# ══════════════════════════════════════════════════════════════
# КОНСТАНТАЛАР — PROMT морфология теглари
# ══════════════════════════════════════════════════════════════

class POS:
    """Сўз туркумлари (Part of Speech)"""
    NOUN    = "noun"
    VERB    = "verb"
    ADJ     = "adjective"
    ADV     = "adverb"
    PRON    = "pronoun"
    NUM     = "numeral"
    CONJ    = "conjunction"
    PREP    = "preposition"
    PART    = "particle"
    INTERJ  = "interjection"
    UNKNOWN = "unknown"

class Case:
    """Келишиклар (Cases) — ўзбек тили"""
    NOM  = "nominative"   # Бош: китоб
    GEN  = "genitive"     # Қаратқич: китобнинг
    DAT  = "dative"       # Жўналиш: китобга
    ACC  = "accusative"   # Тушум: китобни
    LOC  = "locative"     # Ўрин-пайт: китобда
    ABL  = "ablative"     # Чиқиш: китобдан

class Number:
    SG = "singular"
    PL = "plural"

class Person:
    P1 = "first"
    P2 = "second"
    P3 = "third"

class Tense:
    PAST    = "past"
    PRESENT = "present"
    FUTURE  = "future"

class Gender:
    MASC = "masculine"
    FEM  = "feminine"
    NEUT = "neuter"
    NONE = "none"


# ══════════════════════════════════════════════════════════════
# ПАРАДИГМА ЖАДВАЛЛАРИ — ўзбек тили
# ══════════════════════════════════════════════════════════════

# От парадигмаси: [келишик][сон] → қўшимча
NOUN_PARADIGM = {
    # Шахс қўшимчасиз
    (Case.NOM, Number.SG): "",
    (Case.NOM, Number.PL): "лар",
    (Case.GEN, Number.SG): "нинг",
    (Case.GEN, Number.PL): "ларнинг",
    (Case.DAT, Number.SG): "га",
    (Case.DAT, Number.PL): "ларга",
    (Case.ACC, Number.SG): "ни",
    (Case.ACC, Number.PL): "ларни",
    (Case.LOC, Number.SG): "да",
    (Case.LOC, Number.PL): "ларда",
    (Case.ABL, Number.SG): "дан",
    (Case.ABL, Number.PL): "лардан",
}

# Эгалик қўшимчалари: [шахс][сон] → қўшимча
POSSESSIVE = {
    (Person.P1, Number.SG): "им",
    (Person.P2, Number.SG): "инг",
    (Person.P3, Number.SG): "и",
    (Person.P1, Number.PL): "имиз",
    (Person.P2, Number.PL): "ингиз",
    (Person.P3, Number.PL): "лари",
}

# Феъл тусланиши: [замон][шахс][сон] → қўшимча
VERB_PARADIGM = {
    # Ҳозирги/Келаси замон
    (Tense.PRESENT, Person.P1, Number.SG): "аман",
    (Tense.PRESENT, Person.P2, Number.SG): "асан",
    (Tense.PRESENT, Person.P3, Number.SG): "ади",
    (Tense.PRESENT, Person.P1, Number.PL): "амиз",
    (Tense.PRESENT, Person.P2, Number.PL): "асиз",
    (Tense.PRESENT, Person.P3, Number.PL): "адилар",
    # Ўтган замон
    (Tense.PAST, Person.P1, Number.SG): "дим",
    (Tense.PAST, Person.P2, Number.SG): "динг",
    (Tense.PAST, Person.P3, Number.SG): "ди",
    (Tense.PAST, Person.P1, Number.PL): "дик",
    (Tense.PAST, Person.P2, Number.PL): "дингиз",
    (Tense.PAST, Person.P3, Number.PL): "дилар",
    # Ҳозирги давом этаётган
    (Tense.PRESENT + "_cont", Person.P1, Number.SG): "япман",
    (Tense.PRESENT + "_cont", Person.P2, Number.SG): "япсан",
    (Tense.PRESENT + "_cont", Person.P3, Number.SG): "япти",
    (Tense.PRESENT + "_cont", Person.P1, Number.PL): "япмиз",
    (Tense.PRESENT + "_cont", Person.P2, Number.PL): "япсиз",
    (Tense.PRESENT + "_cont", Person.P3, Number.PL): "яптилар",
}

# Феъл номи (masdar) шакллари
VERBAL_NOUN = {
    "infinitive":   "моқ",
    "verbal_noun":  "иш",
    "participle":   "ган",
    "converb":      "иб",
    "neg_part":     "маган",
    "neg_conv":     "масдан",
}

# Сифат даражалари
ADJ_DEGREES = {
    "positive":    "",
    "comparative": "роқ",
    "superlative": "энг ",  # олд қўшимча
}

# Суффикс → (грамматик маъно) харитаси — таҳлил учун
SUFFIX_ANALYSIS = {
    # Келишиклар
    "нинг": {"pos": POS.NOUN, "case": Case.GEN, "number": Number.SG},
    "га":   {"pos": POS.NOUN, "case": Case.DAT, "number": Number.SG},
    "ни":   {"pos": POS.NOUN, "case": Case.ACC, "number": Number.SG},
    "да":   {"pos": POS.NOUN, "case": Case.LOC, "number": Number.SG},
    "дан":  {"pos": POS.NOUN, "case": Case.ABL, "number": Number.SG},
    # Кўплик + келишик
    "лар":    {"pos": POS.NOUN, "case": Case.NOM, "number": Number.PL},
    "ларнинг":{"pos": POS.NOUN, "case": Case.GEN, "number": Number.PL},
    "ларга":  {"pos": POS.NOUN, "case": Case.DAT, "number": Number.PL},
    "ларни":  {"pos": POS.NOUN, "case": Case.ACC, "number": Number.PL},
    "ларда":  {"pos": POS.NOUN, "case": Case.LOC, "number": Number.PL},
    "лардан": {"pos": POS.NOUN, "case": Case.ABL, "number": Number.PL},
    # Эгалик + келишик
    "ларим":    {"pos": POS.NOUN, "number": Number.PL, "poss": (Person.P1, Number.SG)},
    "ларинг":   {"pos": POS.NOUN, "number": Number.PL, "poss": (Person.P2, Number.SG)},
    "лари":     {"pos": POS.NOUN, "number": Number.PL, "poss": (Person.P3, Number.SG)},
    "ларимиз":  {"pos": POS.NOUN, "number": Number.PL, "poss": (Person.P1, Number.PL)},
    "ларингиз": {"pos": POS.NOUN, "number": Number.PL, "poss": (Person.P2, Number.PL)},
    "им":    {"pos": POS.NOUN, "number": Number.SG, "poss": (Person.P1, Number.SG)},
    "инг":   {"pos": POS.NOUN, "number": Number.SG, "poss": (Person.P2, Number.SG)},
    "и":     {"pos": POS.NOUN, "number": Number.SG, "poss": (Person.P3, Number.SG)},
    "имиз":  {"pos": POS.NOUN, "number": Number.SG, "poss": (Person.P1, Number.PL)},
    "ингиз": {"pos": POS.NOUN, "number": Number.SG, "poss": (Person.P2, Number.PL)},
    # Феъл ўтган замон
    "дим":    {"pos": POS.VERB, "tense": Tense.PAST, "person": Person.P1, "number": Number.SG},
    "динг":   {"pos": POS.VERB, "tense": Tense.PAST, "person": Person.P2, "number": Number.SG},
    "ди":     {"pos": POS.VERB, "tense": Tense.PAST, "person": Person.P3, "number": Number.SG},
    "дик":    {"pos": POS.VERB, "tense": Tense.PAST, "person": Person.P1, "number": Number.PL},
    "дингиз": {"pos": POS.VERB, "tense": Tense.PAST, "person": Person.P2, "number": Number.PL},
    "дилар":  {"pos": POS.VERB, "tense": Tense.PAST, "person": Person.P3, "number": Number.PL},
    # Феъл ҳозирги замон
    "аман":   {"pos": POS.VERB, "tense": Tense.PRESENT, "person": Person.P1, "number": Number.SG},
    "асан":   {"pos": POS.VERB, "tense": Tense.PRESENT, "person": Person.P2, "number": Number.SG},
    "ади":    {"pos": POS.VERB, "tense": Tense.PRESENT, "person": Person.P3, "number": Number.SG},
    "амиз":   {"pos": POS.VERB, "tense": Tense.PRESENT, "person": Person.P1, "number": Number.PL},
    "асиз":   {"pos": POS.VERB, "tense": Tense.PRESENT, "person": Person.P2, "number": Number.PL},
    "адилар": {"pos": POS.VERB, "tense": Tense.PRESENT, "person": Person.P3, "number": Number.PL},
    # Феъл давом этаётган
    "япман":  {"pos": POS.VERB, "tense": "present_cont", "person": Person.P1, "number": Number.SG},
    "япсан":  {"pos": POS.VERB, "tense": "present_cont", "person": Person.P2, "number": Number.SG},
    "япти":   {"pos": POS.VERB, "tense": "present_cont", "person": Person.P3, "number": Number.SG},
    "япмиз":  {"pos": POS.VERB, "tense": "present_cont", "person": Person.P1, "number": Number.PL},
    "япсиз":  {"pos": POS.VERB, "tense": "present_cont", "person": Person.P2, "number": Number.PL},
    "яптилар":{"pos": POS.VERB, "tense": "present_cont", "person": Person.P3, "number": Number.PL},
    # Феъл номи
    "моқ":    {"pos": POS.VERB, "form": "infinitive"},
    "иш":     {"pos": POS.VERB, "form": "verbal_noun"},
    "ган":    {"pos": POS.VERB, "form": "participle"},
    "иб":     {"pos": POS.VERB, "form": "converb"},
    "маган":  {"pos": POS.VERB, "form": "neg_participle"},
    # Ясама қўшимчалар
    "лик":    {"derivation": "nominalization"},
    "чи":     {"derivation": "agent"},
    "сиз":    {"derivation": "privative"},
    "ли":     {"derivation": "possessive_adj"},
    "ча":     {"derivation": "diminutive_adv"},
    "роқ":    {"derivation": "comparative"},
}

# Суффикслар узундан қисқага тартибда
SUFFIXES_ORDERED = sorted(SUFFIX_ANALYSIS.keys(), key=len, reverse=True)


# ══════════════════════════════════════════════════════════════
# ЛУҒАТ — Uzbek.fdi маълумотлари
# ══════════════════════════════════════════════════════════════

@dataclass
class LexEntry:
    """Луғат ёзуви"""
    word:    str
    pos:     str = POS.UNKNOWN
    gender:  str = Gender.NONE
    fdi_id:  int = 0
    bases:   list = field(default_factory=list)


@dataclass
class PspEntry:
    """Парадигма ёзуви (PSP = Парадигма)"""
    base_idx:  int
    psp_idx:   int
    canon_form: str
    attributes: dict = field(default_factory=dict)
    forms:     list  = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Таҳлил натижаси"""
    word:        str
    canon_form:  str
    pos:         str
    modifs:      dict = field(default_factory=dict)
    attributes:  dict = field(default_factory=dict)
    suffixes:    list = field(default_factory=list)
    root:        str  = ""
    psp_entries: list = field(default_factory=list)
    translations: list = field(default_factory=list)


# ══════════════════════════════════════════════════════════════
# АСОСИЙ СИНФ — IPromtMorph реализацияси
# ══════════════════════════════════════════════════════════════

class PromtMorph:
    """
    morph.dll (PROMT Expert NMT) нинг тўлиқ Python аналоги.

    COM интерфейслари:
      IPromtMorph    v1  — асосий (initialize, put_key, get_key, modifs, psp)
      IPromtMorph    v2  — modifs2, attributes2
      IPromtMorph    v3  — put_key2, put_base2, noun_gender, aux_verb
      IPromtMorph    v4  — ob_* (сўз бирикмалари)
      IPromtMorph    v5  — initialize2
      IPromtMorph    v9  — get_form_in_key, paradigm методлари
      IPromtMorph    v12 — get_relatives_of_base
    """

    def __init__(self):
        self._initialized = False
        self._data_path   = None
        self._roots_cyr   = frozenset()
        self._roots_lat   = frozenset()
        self._word_id     = {}
        self._current_word     = ""
        self._current_analysis: Optional[AnalysisResult] = None
        self._bases       = []
        self._current_base_idx = 0

    # ── Initialize (IPromtMorph::Initialize) ─────────────────
    def initialize(self, data_path: str = ".") -> bool:
        """
        morph.dll::Initialize(pDir)
        Маълумотлар папкасини юклаш.
        """
        path = Path(data_path)
        json_file = path / "uzbek_fdi_data.json"

        if not json_file.exists():
            # Стандарт йўлларни қидириш
            for candidate in [
                Path(__file__).parent / "uzbek_fdi_data.json",
                Path(__file__).parent / "resources" / "uzbek_fdi_data.json",
                Path("uzbek_fdi_data.json"),
            ]:
                if candidate.exists():
                    json_file = candidate
                    break
            else:
                raise FileNotFoundError(
                    f"uzbek_fdi_data.json топилмади: {data_path}\n"
                    "Аввал Uzbek.fdi → JSON конвертациясини бажаринг."
                )

        raw = json.loads(json_file.read_text("utf-8"))
        self._roots_cyr = frozenset(raw["roots_cyrillic"])
        self._roots_lat = frozenset(raw["roots_latin"])
        self._word_id   = raw.get("word_ids", {})
        self._pos_map   = raw.get("pos_map", {})  # Hunspell+FDI merged POS tags
        self._bases     = ["Uzbek"]
        self._data_path = str(json_file.parent)
        self._initialized = True
        return True

    def initialize2(self, translator=None, dictionaries=None) -> bool:
        """IPromtMorph5::Initialize2 — кенгайтирилган инициализация"""
        return self.initialize(self._data_path or ".")

    def initialize3(self, data_path: str = ".") -> bool:
        """IPromtMorph11::Initialize3"""
        return self.initialize(data_path)

    def _check_init(self):
        if not self._initialized:
            raise RuntimeError("Morph not initialized — initialize() ни чақиринг")

    # ── PutKey / GetKey ───────────────────────────────────────
    def put_key(self, word: str) -> None:
        """
        IPromtMorph::PutKey(word)
        Таҳлил учун сўз юклаш.
        """
        self._check_init()
        self._current_word = word.strip()
        self._current_analysis = self._analyze(self._current_word)

    def put_key2(self, word: str, flags: int = 0) -> None:
        """IPromtMorph3::PutKey2 — байроқлар билан"""
        self.put_key(word)

    def get_key(self) -> str:
        """
        IPromtMorph::GetKey()
        Канон (луғавий) шаклни қайтаради.
        Мисол: 'китобларимдан' → 'китоб'
        """
        self._check_init()
        if self._current_analysis:
            return self._current_analysis.canon_form
        return self._current_word

    # ── Modifs / Attributes ───────────────────────────────────
    @property
    def modifs(self) -> dict:
        """
        IPromtMorph::Modifs
        Морфологик белгилар: POS, келишик, сон, замон...
        """
        self._check_init()
        if self._current_analysis:
            return self._current_analysis.modifs
        return {}

    @property
    def modifs2(self) -> dict:
        """IPromtMorph2::Modifs2 — кенгайтирилган белгилар"""
        return {**self.modifs, **self.attributes}

    @property
    def attributes(self) -> dict:
        """IPromtMorph::Attributes — грамматик атрибутлар"""
        self._check_init()
        if self._current_analysis:
            return self._current_analysis.attributes
        return {}

    @property
    def attributes2(self) -> dict:
        """IPromtMorph2::Attributes2"""
        return self.attributes

    # ── Bases ─────────────────────────────────────────────────
    @property
    def number_of_bases(self) -> int:
        """IPromtMorph::NumberOfBases"""
        return len(self._bases)

    def put_base(self, index: int) -> None:
        """IPromtMorph::PutBase(sDIndex)"""
        if 0 <= index < len(self._bases):
            self._current_base_idx = index

    def put_base2(self, index: int, flags: int = 0) -> None:
        """IPromtMorph3::PutBase2"""
        self.put_base(index)

    def base_by_index(self, index: int) -> str:
        """IPromtMorph::BaseByIndex(sBIndex)"""
        if 0 <= index < len(self._bases):
            return self._bases[index]
        raise IndexError(f"Bad index in get_BaseByIndex: {index}")

    # ── PSP (Парадигма) ───────────────────────────────────────
    @property
    def number_of_psp(self) -> int:
        """IPromtMorph::NumberOfPsp"""
        self._check_init()
        if self._current_analysis:
            return len(self._current_analysis.psp_entries)
        return 0

    def psp(self, base_idx: int, psp_idx: int) -> int:
        """IPromtMorph::Psp(sBIndex, sPIndex) — парадигма ID"""
        self._check_init()
        entries = self._current_analysis.psp_entries if self._current_analysis else []
        if psp_idx < len(entries):
            return entries[psp_idx].psp_idx
        raise IndexError(f"Bad sPIndex in get_Psp: {psp_idx}")

    def psp_canon_form(self, base_idx: int, psp_idx: int) -> str:
        """IPromtMorph::PspCanonForm(sBIndex, sPIndex)"""
        self._check_init()
        entries = self._current_analysis.psp_entries if self._current_analysis else []
        if psp_idx < len(entries):
            return entries[psp_idx].canon_form
        raise IndexError(f"Bad sBIndex in get_PspCanonForm: {base_idx}")

    def psp_attr(self, base_idx: int, psp_idx: int) -> dict:
        """IPromtMorph::PspAttr(sBIndex, sPIndex)"""
        self._check_init()
        entries = self._current_analysis.psp_entries if self._current_analysis else []
        if psp_idx < len(entries):
            return entries[psp_idx].attributes
        return {}

    def number_of_psp_forms(self, base_idx: int, psp_idx: int) -> int:
        """IPromtMorph::NumberOfPspForms"""
        entries = self._current_analysis.psp_entries if self._current_analysis else []
        if psp_idx < len(entries):
            return len(entries[psp_idx].forms)
        raise IndexError(f"Bad sBIndex in get_NumberOfPspForms: {base_idx}")

    def psp_form(self, base_idx: int, psp_idx: int, form_idx: int) -> str:
        """
        IPromtMorph::PspForm(sBIndex, sPIndex, sFIndex)
        Барча флексия шаклларини қайтаради.
        """
        entries = self._current_analysis.psp_entries if self._current_analysis else []
        if psp_idx < len(entries):
            forms = entries[psp_idx].forms
            if form_idx < len(forms):
                return forms[form_idx]
            raise IndexError(f"Bad sFIndex in get_PspForm: {form_idx}")
        raise IndexError(f"Bad sBIndex in get_PspForm: {base_idx}")

    def psp_forms(self, base_idx: int, psp_idx: int) -> list:
        """Барча формаларни рўйхат шаклида қайтаради (ёрдамчи метод)"""
        count = self.number_of_psp_forms(base_idx, psp_idx)
        return [self.psp_form(base_idx, psp_idx, i) for i in range(count)]

    def psp_entry(self, base_idx: int, psp_idx: int) -> dict:
        """IPromtMorph::PspEntry — тўлиқ парадигма ёзуви"""
        entries = self._current_analysis.psp_entries if self._current_analysis else []
        if psp_idx < len(entries):
            e = entries[psp_idx]
            return {
                "base_idx":   e.base_idx,
                "psp_idx":    e.psp_idx,
                "canon_form": e.canon_form,
                "attributes": e.attributes,
                "forms":      e.forms,
            }
        raise IndexError(f"Bad index in get_PspEntry: {psp_idx}")

    # ── PSP Offsets ───────────────────────────────────────────
    def number_of_psp_offsets(self, base_idx: int, psp_idx: int) -> int:
        """IPromtMorph::NumberOfPspOffsets"""
        entries = self._current_analysis.psp_entries if self._current_analysis else []
        if psp_idx < len(entries):
            return len(entries[psp_idx].forms)
        raise IndexError(f"Bad sBIndex in get_NumberOfPspOffsets: {base_idx}")

    def psp_offset(self, base_idx: int, psp_idx: int, offset_idx: int) -> int:
        """IPromtMorph::PspOffset — форма офсети"""
        return offset_idx  # Офсет = индекс (содда реализация)

    # ── Translations ──────────────────────────────────────────
    @property
    def number_of_translations(self) -> int:
        """IPromtMorph::NumberOfTranslations"""
        if self._current_analysis:
            return len(self._current_analysis.translations)
        return 0

    def translation(self, base_idx: int, psp_idx: int, trans_idx: int) -> str:
        """IPromtMorph::Translation"""
        if self._current_analysis and trans_idx < len(self._current_analysis.translations):
            return self._current_analysis.translations[trans_idx]
        raise IndexError(f"Bad sTIndex in get_TranslationPsp: {trans_idx}")

    def translation_base(self, base_idx: int, psp_idx: int, trans_idx: int) -> int:
        """IPromtMorph::TranslationBase"""
        return 0

    def translation_canon_form(self, base_idx: int, psp_idx: int, trans_idx: int) -> str:
        """IPromtMorph::TranslationCanonForm"""
        return self.translation(base_idx, psp_idx, trans_idx)

    def number_of_translation_forms(self, base_idx: int, psp_idx: int, trans_idx: int) -> int:
        """IPromtMorph::NumberOfTranslationForms"""
        return 1

    def translation_form(self, base_idx: int, psp_idx: int, trans_idx: int, form_idx: int) -> str:
        """IPromtMorph::TranslationForm"""
        return self.translation_canon_form(base_idx, psp_idx, trans_idx)

    # ── NounGender / AuxVerb (IPromtMorph3) ───────────────────
    @property
    def noun_gender(self) -> str:
        """IPromtMorph3::NounGender — ўзбекда жинс йўқ"""
        return Gender.NONE

    @property
    def aux_verb(self) -> str:
        """IPromtMorph3::AuxVerb — ёрдамчи феъл"""
        if self._current_analysis and self._current_analysis.pos == POS.VERB:
            return "бўл"
        return ""

    # ── ObWord методлари (IPromtMorph4) ──────────────────────
    @property
    def ob_number_of_words(self) -> int:
        """IPromtMorph4::ObNumberOfWords — бирикмадаги сўзлар"""
        return 1 if self._current_word else 0

    def ob_word_by_index(self, index: int) -> str:
        """IPromtMorph4::ObWordByIndex"""
        if index == 0:
            return self._current_word
        raise IndexError(f"Bad index: {index}")

    def ob_word_psp(self, word_idx: int, base_idx: int) -> int:
        """IPromtMorph4::ObWordPsp"""
        return 0

    def ob_word_canon_form(self, word_idx: int) -> str:
        """IPromtMorph4::ObWordCanonForm"""
        return self.get_key()

    def ob_word_number_of_forms(self, word_idx: int) -> int:
        """IPromtMorph4::ObWordNumberOfForms"""
        return self.number_of_psp_forms(0, 0) if self.number_of_psp > 0 else 0

    def ob_word_form(self, word_idx: int, form_idx: int) -> str:
        """IPromtMorph4::ObWordForm"""
        return self.psp_form(0, 0, form_idx)

    def ob_word_psp_attr(self, word_idx: int, base_idx: int, psp_idx: int) -> dict:
        """IPromtMorph4::ObWordPspAttr"""
        return self.psp_attr(base_idx, psp_idx)

    # ── GetFormInKey (IPromtMorph9) ───────────────────────────
    def get_form_in_key(self, lex_idx: int, form_idx: int) -> str:
        """IPromtMorph9::GetFormInKey(iLIndex, iFIndex)"""
        return self.psp_form(0, 0, form_idx)

    def count_words_in_key(self) -> int:
        """IPromtMorph9::CountWordsInKey"""
        return 1 if self._current_word else 0

    def get_word_stem_in_key(self, word_idx: int) -> str:
        """IPromtMorph9::GetWordStemInKey"""
        if self._current_analysis and self._current_analysis.root:
            return self._current_analysis.root
        return self._current_word

    def get_word_psp_in_key(self, word_idx: int) -> int:
        """IPromtMorph9::GetWordPspInKey"""
        return 0

    def get_word_form_in_key(self, word_idx: int, form_idx: int) -> str:
        """IPromtMorph9::GetWordFormInKey"""
        return self.psp_form(0, 0, form_idx)

    def get_forced_input_word_form(self, stem: str, paradigm: int, flags: int = 0) -> str:
        """IPromtMorph9::GetForcedInputWordForm"""
        return stem

    def get_forced_output_word_form(self, stem: str, paradigm: int) -> str:
        """IPromtMorph9::GetForcedOutputWordForm"""
        return stem

    def count_input_l_paradigms(self) -> int:
        """IPromtMorph9::CountInputLParadigms"""
        return self.number_of_psp

    def count_output_l_paradigms(self) -> int:
        """IPromtMorph9::CountOutputLParadigms"""
        return self.number_of_psp

    def count_word_forms_in_l_paradigm(self, lang: int, psp_idx: int) -> int:
        """IPromtMorph9::CountWordFormsInLParadigm"""
        return self.number_of_psp_forms(0, psp_idx)

    # ── GetRelativesOfBase (IPromtMorph12) ────────────────────
    def get_relatives_of_base(self, base: str) -> list:
        """
        IPromtMorph12::GetRelativesOfBase
        Сўзга яқин/ўхшаш сўзларни топиш.
        """
        prefix = base[:3] if len(base) >= 3 else base
        pool = self._roots_cyr if self._is_cyrillic(base) else self._roots_lat
        return sorted(w for w in pool if w.startswith(prefix) and w != base)[:10]

    # ══════════════════════════════════════════════════════════
    # ИЧКИ ТАҲЛИЛ ДВИЖОГИ
    # ══════════════════════════════════════════════════════════

    def _is_cyrillic(self, word: str) -> bool:
        return any('\u0400' <= c <= '\u04FF' or c in 'ўЎғҒқҚҳҲ' for c in word)

    def _in_dict(self, word: str) -> bool:
        return word in self._roots_cyr or word in self._roots_lat

    def _strip_suffixes(self, word: str) -> tuple:
        """Суффикслар занжирини ажратиш — энг тўлиқ таҳлил"""
        if self._in_dict(word):
            return word, [], {}

        # Бир қадамли суффикс ажратиш
        for suf in SUFFIXES_ORDERED:
            if word.endswith(suf) and len(word) - len(suf) >= 2:
                root = word[:-len(suf)]
                if self._in_dict(root):
                    attrs = SUFFIX_ANALYSIS[suf].copy()
                    return root, [suf], attrs

        # Икки қадамли — кўплик + келишик
        for suf1 in ["ларимдан","ларингдан","лардан","ларга","ларда","ларни","ларнинг","ларим","ларинг","лари","ларимиз","ларингиз","лар"]:
            if word.endswith(suf1) and len(word) - len(suf1) >= 2:
                root = word[:-len(suf1)]
                if self._in_dict(root):
                    return root, [suf1], {
                        "pos": POS.NOUN,
                        "number": Number.PL,
                        "suffix": suf1,
                    }

        # Феъл суффикслари
        for suf in ["япман","япсан","япти","япмиз","япсиз","яптилар",
                     "аман","асан","ади","амиз","асиз","адилар",
                     "дим","динг","ди","дик","дингиз","дилар",
                     "моқ","иш","ган","иб","маган"]:
            if word.endswith(suf) and len(word) - len(suf) >= 2:
                root = word[:-len(suf)]
                if self._in_dict(root):
                    return root, [suf], SUFFIX_ANALYSIS.get(suf, {"pos": POS.VERB})

        return word, [], {"pos": POS.UNKNOWN}

    def _determine_pos(self, word: str, attrs: dict) -> str:
        """Сўз туркумини аниқлаш — Hunspell+FDI merged pos_map + suffix analysis."""
        if "pos" in attrs and attrs["pos"] != POS.UNKNOWN:
            return attrs["pos"]
        wl = word.lower()
        pm = self._pos_map if hasattr(self, '_pos_map') and self._pos_map else {}

        # PRIORITY 1: exact match in pos_map
        if pm.get(wl, "") not in ("", "unknown"):
            return pm[wl]

        # PRIORITY 2: try stripping common verb suffixes to find root in pos_map
        verb_sfx = [
            "ди", "дим", "динг", "дик", "дилар",  # past
            "ади", "аман", "асан", "амиз", "адилар",  # present
            "ган", "ган", "яптим", "япти", "япман",  # participle
            "моқда", "моқчи", "аётир", "аётган",
            "илди", "илган", "илади",
            "инди", "инган",
        ]
        for sfx in sorted(verb_sfx, key=len, reverse=True):
            if wl.endswith(sfx) and len(wl) > len(sfx) + 1:
                stem = wl[:-len(sfx)]
                if pm.get(stem, "") == "verb" or stem in self._roots_cyr or stem in self._roots_lat:
                    return POS.VERB

        # PRIORITY 3: try stripping noun suffixes
        noun_sfx = [
            "си", "сини", "сида", "сидан", "сига", "синда",  # possessive
            "лари", "ларни", "ларда", "лардан", "ларга", "ларнинг",
            "ни", "нинг", "да", "дан", "га", "лар",
        ]
        for sfx in sorted(noun_sfx, key=len, reverse=True):
            if wl.endswith(sfx) and len(wl) > len(sfx) + 1:
                stem = wl[:-len(sfx)]
                sp = pm.get(stem, "")
                if sp not in ("", "unknown"):
                    return sp
                if stem in self._roots_cyr or stem in self._roots_lat:
                    return POS.NOUN

        # PRIORITY 4: suffix-based heuristic
        if wl.endswith(("моқ", "лаш", "иш")) and len(wl) > 4:
            return POS.VERB
        if wl.endswith(("лик", "чи", "чилик", "гар", "кор")):
            return POS.NOUN
        if wl.endswith(("ли", "сиз", "ий", "ик")):
            return POS.ADJ

        # PRIORITY 5: dictionary check
        if self._in_dict(word):
            return POS.NOUN
        return POS.UNKNOWN

    def _build_noun_forms(self, root: str) -> list:
        """От парадигмасини тузиш"""
        forms = []
        for (case, number), suffix in NOUN_PARADIGM.items():
            forms.append({
                "form":   root + suffix,
                "case":   case,
                "number": number,
                "suffix": suffix,
            })
        return forms

    def _build_verb_forms(self, root: str) -> list:
        """Феъл тусланиш жадвалини тузиш"""
        forms = []
        for (tense, person, number), suffix in VERB_PARADIGM.items():
            if isinstance(tense, str):
                forms.append({
                    "form":   root + suffix,
                    "tense":  tense,
                    "person": person,
                    "number": number,
                    "suffix": suffix,
                })
        # Феъл номи шакллари
        for form_name, suffix in VERBAL_NOUN.items():
            forms.append({
                "form":      root + suffix,
                "verb_form": form_name,
                "suffix":    suffix,
            })
        return forms

    def _analyze(self, word: str) -> AnalysisResult:
        """Морфологик таҳлил — асосий метод"""
        root, suffixes, attrs = self._strip_suffixes(word)
        pos = self._determine_pos(root if root else word, attrs)

        # Парадигма яратиш
        psp_entries = []
        if pos == POS.NOUN or (pos == POS.UNKNOWN and self._in_dict(root or word)):
            forms_raw = self._build_noun_forms(root or word)
            form_list = [f["form"] for f in forms_raw]
            psp_entries.append(PspEntry(
                base_idx=0,
                psp_idx=0,
                canon_form=root or word,
                attributes={"pos": POS.NOUN},
                forms=form_list,
            ))
        elif pos == POS.VERB:
            forms_raw = self._build_verb_forms(root or word)
            form_list = [f["form"] for f in forms_raw]
            psp_entries.append(PspEntry(
                base_idx=0,
                psp_idx=1,
                canon_form=root or word,
                attributes={"pos": POS.VERB},
                forms=form_list,
            ))

        # Модификаторлар
        modifs = {
            "pos":      pos,
            "root":     root or word,
            "suffixes": suffixes,
            "script":   "cyrillic" if self._is_cyrillic(word) else "latin",
            "in_dict":  self._in_dict(root or word),
        }
        if "case" in attrs:
            modifs["case"] = attrs["case"]
        if "number" in attrs:
            modifs["number"] = attrs["number"]
        if "tense" in attrs:
            modifs["tense"] = attrs["tense"]
        if "person" in attrs:
            modifs["person"] = attrs["person"]
        if "poss" in attrs:
            modifs["possessive"] = attrs["poss"]

        return AnalysisResult(
            word=word,
            canon_form=root or word,
            pos=pos,
            modifs=modifs,
            attributes=attrs,
            suffixes=suffixes,
            root=root or word,
            psp_entries=psp_entries,
        )

    # ══════════════════════════════════════════════════════════
    # ЁРДАМЧИ УСУЛЛАР (IPromtMorph12, IPromtMorphUtility)
    # ══════════════════════════════════════════════════════════

    def search(self, query: str, limit: int = 20) -> list:
        """Луғатдан қидириш"""
        q = query.lower()
        pool = list(self._roots_cyr) + list(self._roots_lat)
        return sorted(w for w in pool if q in w.lower())[:limit]

    def suggest(self, word: str, limit: int = 10) -> list:
        """Ўхшаш сўзлар таклифи"""
        prefix = word[:3] if len(word) >= 3 else word
        pool = self._roots_cyr if self._is_cyrillic(word) else self._roots_lat
        return sorted(w for w in pool if w.startswith(prefix) and w != word)[:limit]

    def analyze_text(self, text: str) -> list:
        """Матндаги барча сўзларни таҳлил қилиш"""
        words = re.findall(r'[а-яёА-ЯЁўЎғҒқҚҳҲa-zA-Z]+', text)
        results = []
        for w in words:
            self.put_key(w)
            results.append({
                "word":       w,
                "canon":      self.get_key(),
                "pos":        self.modifs.get("pos", POS.UNKNOWN),
                "root":       self.modifs.get("root", w),
                "suffixes":   self.modifs.get("suffixes", []),
                "case":       self.modifs.get("case"),
                "number":     self.modifs.get("number"),
                "tense":      self.modifs.get("tense"),
            })
        return results

    def stats(self) -> dict:
        """Луғат статистикаси"""
        return {
            "initialized":    self._initialized,
            "data_path":      self._data_path,
            "total_words":    len(self._roots_cyr) + len(self._roots_lat),
            "cyrillic_words": len(self._roots_cyr),
            "latin_words":    len(self._roots_lat),
            "bases":          self._bases,
            "source":         "Uzbek.fdi → PROMT Expert NMT v23.2",
        }

    def __repr__(self):
        st = "initialized" if self._initialized else "not initialized"
        return f"<PromtMorph [{st}] word='{self._current_word}'>"


# ══════════════════════════════════════════════════════════════
# IPromtMorphUtility
# ══════════════════════════════════════════════════════════════

class PromtMorphUtility:
    """
    morph.dll::PromtMorphUtility (COM класс)
    Сўз бирикмаларини қайта ишлаш.
    """

    def __init__(self, morph: PromtMorph = None):
        self._morph = morph or PromtMorph()

    def process_collocation(self, phrase: str, lang_id: int = 0) -> dict:
        """
        IPromtMorphUtility::ProcessCollocation
        Бирикмани морфологик таҳлил қилиш.
        """
        words = phrase.strip().split()
        results = []
        for w in words:
            self._morph.put_key(w)
            results.append({
                "word":  w,
                "canon": self._morph.get_key(),
                "pos":   self._morph.modifs.get("pos"),
                "modifs": self._morph.modifs,
            })
        return {
            "phrase":  phrase,
            "words":   results,
            "canon_phrase": " ".join(r["canon"] for r in results),
        }


# ══════════════════════════════════════════════════════════════
# ТЕСТ
# ══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("  promt_morph.py — morph.dll Python аналоги")
    print("=" * 60)

    morph = PromtMorph()

    # JSON файл йўлини аргументдан олиш
    data_path = sys.argv[1] if len(sys.argv) > 1 else "."
    morph.initialize(data_path)

    print(f"\nСтатистика: {morph.stats()}")
    print()

    test_words = [
        "китоб", "китоблар", "китобларимдан",
        "мактаб", "мактабда", "мактабдан",
        "давлат", "давлатнинг",
        "ўзбек", "ўзбекча",
        "ишлайди", "ишламади",
        "toshkent", "davlat",
    ]

    print(f"{'Сўз':25s} {'Канон':15s} {'Тур':10s} {'Суффикс':15s} {'Мезон'}")
    print("-" * 80)

    for w in test_words:
        morph.put_key(w)
        canon   = morph.get_key()
        pos     = morph.modifs.get("pos", "?")
        suffs   = ",".join(morph.modifs.get("suffixes", []) or ["-"])
        case    = morph.modifs.get("case", "")
        number  = morph.modifs.get("number", "")
        tense   = morph.modifs.get("tense", "")
        extra   = " | ".join(filter(None, [case, number, tense]))
        print(f"  {w:23s} {canon:15s} {pos:10s} {suffs:15s} {extra}")

    print()
    print("Парадигма (китоб):")
    morph.put_key("китоб")
    for i, form in enumerate(morph.psp_forms(0, 0)):
        print(f"  {i:2d}. {form}")

    print()
    print("Матн таҳлили:")
    results = morph.analyze_text("Тошкентда мактабларимиз кўп")
    for r in results:
        print(f"  {r['word']:20s} → {r['canon']:15s} [{r['pos']}]")

    print()
    util = PromtMorphUtility(morph)
    coll = util.process_collocation("давлат тили")
    print(f"Бирикма: '{coll['phrase']}' → '{coll['canon_phrase']}'")
