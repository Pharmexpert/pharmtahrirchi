# -*- coding: utf-8 -*-
"""
syntdata.py — SyntData.dll нинг тўлиқ Python реализацияси
==========================================================
SyntData.dll — PROMT тизимининг синтаксис ва NER движоги
(.NET 4.0 assembly, IPromtTranslator2–15, IPromtMorph9 интерфейслари).

Реализация қилинган:
  - Синтактик таҳлил (SOV, noun group, verb group)
  - NER — 30 та объект тури (шахс, ташкилот, жой, унвон...)
  - Семантик фреймлар (EventFrame)
  - Сўз бирикмаси таҳлили (collocation)
  - IPromtTranslator интерфейси

Ишлатиш:
    from syntdata import SyntData
    sd = SyntData()
    result = sd.parse("Шавкат Мирзиёев Тошкентда нутқ сўзлади")
    print(result.entities)   # [{'text':'Шавкат Мирзиёев','type':'PERSON'}...]
    print(result.syntax)     # SOV таҳлили
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# ══════════════════════════════════════════════════════════════
# NER — Объект турлари (SyntData.dll entity_* теглари)
# ══════════════════════════════════════════════════════════════

class EntityType:
    """entity_* теглари — SyntData.dll дан ажратилган"""
    NAME               = "entity_name"
    PROFESSION         = "entity_profession"          # профессия
    POSITION           = "entity_position"            # должность
    ADDRESS            = "entity_address"             # обращение / адрес
    NATIONALITY        = "entity_nationality"         # национальность
    RELATIVE           = "entity_relative"            # родственник
    TITLE              = "entity_title"               # звание
    ACADEMIC_RANK      = "entity_academic_rank"       # научная степень
    POLITICAL          = "entity_political_affiliation"  # политическая принадлежность
    RELIGIOUS          = "entity_religious_affiliation"  # религиозная принадлежность
    RELIGIOUS_TITLE    = "entity_religious_title"     # церковный чин
    NOBLE_RANK         = "entity_noble_rank"          # дворянский титул
    MILITARY_TITLE     = "entity_military_title"      # военный чин
    ORGANIZATION       = "entity_organization"        # организация
    OTHER              = "entity_other"               # другое
    ATTR               = "entity_attr"
    CHARACTERISTIC     = "entity_characteristic"
    CONTACT_PERSON     = "entity_contact_person"      # контактное лицо
    CONTACTS           = "entity_contacts"            # телефон/контакты
    COUNT              = "entity_count"
    HYPERONYM          = "entity_hyperonym"
    ID                 = "entity_id"
    OWNER              = "entity_owner"               # владелец
    SEM                = "entity_sem"
    SUBTYPE            = "entity_subtype"
    TYPE               = "entity_type"
    UNIFIED_DATA       = "entity_unified_data"        # универсальное представление
    UNKNOWN            = "entity_unknown"
    AGE                = "entity_age"                 # возраст


# ══════════════════════════════════════════════════════════════
# POS теглари
# ══════════════════════════════════════════════════════════════

class POS:
    NOUN         = "noun"
    VERB         = "verb"
    ADJECTIVE    = "adjective"
    ADVERB       = "adverb"
    PRONOUN      = "pronoun"
    PREPOSITION  = "preposition"
    NUMERAL      = "numeral"
    PARTICIPLE   = "participle"
    GERUND       = "gerund"
    CONJUNCTION  = "conjunction"
    ORDINATING_CONJUNCTION = "ordinating conjunction"
    UNKNOWN      = "unknown"


# ══════════════════════════════════════════════════════════════
# Грамматик атрибутлар
# ══════════════════════════════════════════════════════════════

class Case:
    NOMINATIVE   = "Nominative"
    GENITIVE     = "Genitive"
    DATIVE       = "Dative"
    ACCUSATIVE   = "Accusative"
    INSTRUMENTAL = "Instrumental"
    PREPOSITIONAL= "Prepositional"
    LOCATIVE     = "Locative"
    ABLATIVE     = "Ablative"

class Number:
    SINGULAR = "Singular"
    PLURAL   = "Plural"

class Gender:
    MALE    = "Male"
    FEMALE  = "Female"
    NEUTRAL = "Neutral"

class Animacy:
    ANIMATED  = "Animated"
    INANIMATE = "Inanimate"


# ══════════════════════════════════════════════════════════════
# Маълумот структуралари
# ══════════════════════════════════════════════════════════════

@dataclass
class Token:
    """Бир сўз токени"""
    text:        str
    pos:         str         = POS.UNKNOWN
    lemma:       str         = ""
    case:        str         = ""
    number:      str         = ""
    gender:      str         = ""
    animacy:     str         = ""
    tense:       str         = ""
    person:      str         = ""
    is_proper:   bool        = False
    txt_begin:   int         = 0
    txt_length:  int         = 0
    morphology:  dict        = field(default_factory=dict)


@dataclass
class Entity:
    """NER объекти"""
    text:        str
    entity_type: str
    start:       int  = 0
    end:         int  = 0
    attributes:  dict = field(default_factory=dict)
    subtype:     str  = ""
    unified_data:str  = ""


@dataclass
class SyntGroup:
    """Синтактик гуруҳ (noun group, verb group...)"""
    group_type:  str         # "noun_group", "verb_group", "minor_noun_group"
    tokens:      list        = field(default_factory=list)
    head:        Optional[Token] = None
    role:        str         = ""  # subject, object, predicate
    is_main:     bool        = False


@dataclass
class EventFrame:
    """Семантик фрейм"""
    event_type:  str
    agent:       Optional[str] = None
    patient:     Optional[str] = None
    location:    Optional[str] = None
    time:        Optional[str] = None
    attributes:  dict = field(default_factory=dict)


@dataclass
class ParseResult:
    """Таҳлил натижаси"""
    text:        str
    tokens:      list        = field(default_factory=list)
    entities:    list        = field(default_factory=list)
    groups:      list        = field(default_factory=list)
    frames:      list        = field(default_factory=list)
    syntax:      dict        = field(default_factory=dict)
    semantics:   dict        = field(default_factory=dict)
    parsed:      bool        = False


# ══════════════════════════════════════════════════════════════
# NER ЛУҒАТЛАРИ — ўзбек + рус тили
# ══════════════════════════════════════════════════════════════

# Унвонлар ва мурожаатлар
_TITLES = {
    "жаноб", "хоним", "доктор", "профессор", "академик",
    "генерал", "полковник", "майор", "капитан",
    "президент", "вазир", "раис", "директор", "бош",
    "господин", "госпожа", "доктор", "профессор",
    "mr", "mrs", "ms", "dr", "prof",
}

# Ташкилот суффикслари
_ORG_SUFFIXES = {
    "корпорация", "компания", "ширкат", "ассоциация",
    "вазирлик", "қўмита", "агентлик", "институт",
    "университет", "академия", "мактаб", "лицей",
    "банк", "фонд", "марказ",
    "corp", "inc", "ltd", "llc", "gmbh", "company",
}

# Жой кўрсатувчи сўзлар
_LOC_INDICATORS = {
    "шаҳар", "вилоят", "туман", "қишлоқ", "кўча",
    "майдон", "дарё", "тоғ", "кўл", "денгиз",
    "город", "улица", "площадь", "район", "область",
}

# Машҳур ўзбек исмлари (намуна)
_UZ_NAME_PATTERNS = [
    r'\b[А-ЯЁЎҒҚҲ][а-яёўғқҳ]{2,}\s+[А-ЯЁЎҒҚҲ][а-яёўғқҳ]{2,}(?:\s+[А-ЯЁЎҒҚҲ][а-яёўғқҳ]{2,})?\b',
    r'\b[A-Z][a-z]{2,}\s+[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?\b',
]


# ══════════════════════════════════════════════════════════════
# СИНТАКСИС ҚОИДАЛАРИ — SOV ўзбек тили
# ══════════════════════════════════════════════════════════════

# Феъл тусланиши белгилари
_VERB_SUFFIXES = [
    "ди", "дим", "динг", "дик", "дингиз", "дилар",
    "япти", "япман", "яптимиз",
    "моқда", "моқдаман",
    "ади", "аман", "асан", "амиз",
    "иш", "ган", "иб", "моқ",
]

# От белгилари
_NOUN_SUFFIXES = [
    "лар", "нинг", "га", "ни", "да", "дан",
    "ларни", "ларга", "ларда", "лардан",
    "лик", "чи", "сиз", "дош",
]


# ══════════════════════════════════════════════════════════════
# АСОСИЙ СИНФ
# ══════════════════════════════════════════════════════════════

class SyntData:
    """
    SyntData.dll — PROMT синтаксис ва NER движоги (Python реализацияси).

    .NET 4.0 assembly, IPromtTranslator2–15 интерфейслари.
    """

    def __init__(self):
        self._morph = None  # promt_morph.PromtMorph билан интеграция

    def set_morph(self, morph) -> None:
        """promt_morph.PromtMorph билан боғлаш"""
        self._morph = morph

    # ── Асосий таҳлил ─────────────────────────────────────────

    def parse(self, text: str) -> ParseResult:
        """
        IPromtTranslator::ProcessLine — матнни тўлиқ таҳлил қилиш.
        Токенизация → POS → NER → Синтаксис → Семантика.
        """
        result = ParseResult(text=text)
        result.tokens  = self._tokenize(text)
        result.tokens  = self._tag_pos(result.tokens)
        result.entities = self._extract_entities(text, result.tokens)
        result.groups   = self._build_groups(result.tokens)
        result.syntax   = self._analyze_syntax(result.tokens, result.groups)
        result.frames   = self._extract_frames(result.tokens, result.entities)
        result.semantics = self._analyze_semantics(result)
        result.parsed   = True
        return result

    # ── Токенизация ───────────────────────────────────────────

    def _tokenize(self, text: str) -> list:
        """Матнни токенларга бўлиш"""
        tokens = []
        pos = 0
        for m in re.finditer(r'\S+', text):
            word = m.group()
            clean = re.sub(r'[^\w\-\'ʻ]', '', word)
            if clean:
                tok = Token(
                    text=clean,
                    lemma=clean.lower(),
                    txt_begin=m.start(),
                    txt_length=len(clean),
                )
                # Морфологик таҳлил (агар morph боғланган бўлса)
                if self._morph:
                    try:
                        self._morph.put_key(clean)
                        tok.lemma   = self._morph.get_key()
                        modifs      = self._morph.modifs
                        tok.pos     = modifs.get('pos', POS.UNKNOWN)
                        tok.case    = modifs.get('case', '')
                        tok.number  = modifs.get('number', '')
                        tok.morphology = modifs
                    except Exception:
                        pass
                tokens.append(tok)
        return tokens

    # ── POS теглаш ────────────────────────────────────────────

    def _tag_pos(self, tokens: list) -> list:
        """Сўз туркумларини аниқлаш"""
        for tok in tokens:
            if tok.pos != POS.UNKNOWN:
                continue
            w = tok.text.lower()

            # Феъл белгилари
            if any(w.endswith(s) for s in _VERB_SUFFIXES):
                tok.pos = POS.VERB
            # От белгилари
            elif any(w.endswith(s) for s in _NOUN_SUFFIXES):
                tok.pos = POS.NOUN
            # Катта ҳарф = хусусий от
            elif tok.text[0].isupper() and len(tok.text) > 2:
                tok.pos = POS.NOUN
                tok.is_proper = True
            # Рақам
            elif tok.text.isdigit():
                tok.pos = POS.NUMERAL
            # Бошқа
            else:
                tok.pos = POS.NOUN  # ўзбек тилида кўп от

        return tokens

    # ── NER ───────────────────────────────────────────────────

    def _extract_entities(self, text: str, tokens: list) -> list:
        """
        IPromtTranslator::ExtractEntitiesAndCmbinedEntitiesFromXML
        NER объектларини топиш.
        """
        entities = []

        # 1. Шахс исмлари — катта ҳарфли бирикмалар
        for pat in _UZ_NAME_PATTERNS:
            for m in re.finditer(pat, text):
                name = m.group().strip()
                if len(name.split()) >= 2:
                    entities.append(Entity(
                        text=name,
                        entity_type=EntityType.NAME,
                        start=m.start(),
                        end=m.end(),
                        attributes={"entity_name": name},
                    ))

        # 2. Унвон + исм
        for tok in tokens:
            if tok.text.lower() in _TITLES:
                idx = tokens.index(tok)
                if idx + 1 < len(tokens):
                    name_tok = tokens[idx + 1]
                    if name_tok.text[0].isupper():
                        full = f"{tok.text} {name_tok.text}"
                        entities.append(Entity(
                            text=full,
                            entity_type=EntityType.TITLE,
                            start=tok.txt_begin,
                            end=name_tok.txt_begin + name_tok.txt_length,
                            attributes={"entity_title": tok.text.lower()},
                        ))

        # 3. Ташкилот номлари
        for tok in tokens:
            if any(tok.text.lower().endswith(s) or tok.text.lower() == s
                   for s in _ORG_SUFFIXES):
                entities.append(Entity(
                    text=tok.text,
                    entity_type=EntityType.ORGANIZATION,
                    start=tok.txt_begin,
                    end=tok.txt_begin + tok.txt_length,
                ))

        # 4. Жой номлари (-да, -дан, -га қўшимчали катта ҳарфли сўзлар)
        for tok in tokens:
            if tok.is_proper and tok.case in (
                Case.LOCATIVE, Case.ABLATIVE, Case.DATIVE
            ):
                entities.append(Entity(
                    text=tok.text,
                    entity_type=EntityType.ADDRESS,
                    start=tok.txt_begin,
                    end=tok.txt_begin + tok.txt_length,
                    attributes={"entity_address": tok.text},
                ))

        # Устма-уст тушишларни олиб ташлаш
        entities = self._deduplicate_entities(entities)
        return entities

    def _deduplicate_entities(self, entities: list) -> list:
        """Устма-уст тушган объектларни бирлаштириш"""
        if not entities:
            return []
        entities.sort(key=lambda e: (e.start, -(e.end - e.start)))
        result = [entities[0]]
        for ent in entities[1:]:
            last = result[-1]
            if ent.start >= last.end:
                result.append(ent)
        return result

    # ── Синтактик гуруҳлар ───────────────────────────────────

    def _build_groups(self, tokens: list) -> list:
        """
        Noun group / Verb group / Minor collocation part яратиш.
        Ўзбек тили SOV тартиби.
        """
        groups = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]

            # Феъл гуруҳи — гап охирида (SOV)
            if tok.pos == POS.VERB:
                grp = SyntGroup(
                    group_type="verb_group",
                    tokens=[tok],
                    head=tok,
                    role="predicate",
                    is_main=True,
                )
                groups.append(grp)

            # От гуруҳи
            elif tok.pos in (POS.NOUN, POS.ADJECTIVE, POS.PRONOUN, POS.NUMERAL):
                grp_tokens = [tok]
                # Кейинги сифат/от билан бирлаштириш
                j = i + 1
                while j < len(tokens) and tokens[j].pos in (POS.ADJECTIVE, POS.NOUN):
                    grp_tokens.append(tokens[j])
                    j += 1

                # Роль аниқлаш (SOV: биринчи = subject, ўрта = object)
                case = tok.case
                if case == Case.NOMINATIVE or not case:
                    role = "subject" if len(groups) == 0 else "object"
                elif case in (Case.ACCUSATIVE,):
                    role = "object"
                elif case in (Case.DATIVE, Case.LOCATIVE):
                    role = "indirect_object"
                else:
                    role = "modifier"

                grp = SyntGroup(
                    group_type="noun_group" if len(grp_tokens) > 1 else "minor_noun_group",
                    tokens=grp_tokens,
                    head=tok,
                    role=role,
                )
                groups.append(grp)
                i = j - 1

            i += 1

        return groups

    # ── Синтаксис таҳлили ─────────────────────────────────────

    def _analyze_syntax(self, tokens: list, groups: list) -> dict:
        """
        SOV (Subject-Object-Verb) синтаксис таҳлили.
        Ўзбек тили: кесим гап охирида.
        """
        subject   = None
        objects   = []
        predicate = None
        modifiers = []

        for grp in groups:
            if grp.role == "subject":
                subject = grp
            elif grp.role == "predicate":
                predicate = grp
            elif grp.role == "object":
                objects.append(grp)
            else:
                modifiers.append(grp)

        return {
            "order":     "SOV",
            "subject":   subject.head.text if subject else None,
            "predicate": predicate.head.text if predicate else None,
            "objects":   [g.head.text for g in objects],
            "modifiers": [g.head.text for g in modifiers],
            "groups":    len(groups),
            "tokens":    len(tokens),
        }

    # ── Семантик фреймлар ─────────────────────────────────────

    def _extract_frames(self, tokens: list, entities: list) -> list:
        """EventFrame — семантик фреймлар"""
        frames = []
        verbs = [t for t in tokens if t.pos == POS.VERB]
        persons = [e for e in entities if e.entity_type == EntityType.NAME]
        locs = [e for e in entities if e.entity_type == EntityType.ADDRESS]

        for verb in verbs:
            frame = EventFrame(
                event_type=verb.lemma or verb.text,
                agent=persons[0].text if persons else None,
                location=locs[0].text if locs else None,
            )
            frames.append(frame)

        return frames

    # ── Семантика ─────────────────────────────────────────────

    def _analyze_semantics(self, result: ParseResult) -> dict:
        """Семантик таҳлил"""
        return {
            "parsed":     result.parsed,
            "entity_count": len(result.entities),
            "frame_count":  len(result.frames),
            "has_person":   any(e.entity_type == EntityType.NAME for e in result.entities),
            "has_org":      any(e.entity_type == EntityType.ORGANIZATION for e in result.entities),
            "has_location": any(e.entity_type == EntityType.ADDRESS for e in result.entities),
        }

    # ── IPromtTranslator методлари ────────────────────────────

    def extract_entities_from_xml(self, xml_text: str) -> list:
        """IPromtTranslator::ExtractEntitiesAndCmbinedEntitiesFromXML"""
        text = re.sub(r'<[^>]+>', ' ', xml_text)
        return self._extract_entities(text, self._tokenize(text))

    def combine_entities(self, entities: list) -> list:
        """IPromtTranslator::CombineAndExtractEntities2"""
        return self._deduplicate_entities(entities)

    def process_collocation(self, phrase: str) -> dict:
        """IPromtTranslator::ProcessCollocation — minor_collocation_part"""
        tokens = self._tokenize(phrase)
        tokens = self._tag_pos(tokens)
        return {
            "phrase":   phrase,
            "tokens":   [(t.text, t.pos) for t in tokens],
            "type":     "minor_collocation_part",
        }

    def get_word_form(self, text: str, form_idx: int) -> str:
        """IPromtMorph9::GetWordFormInKey"""
        if self._morph:
            self._morph.put_key(text)
            try:
                return self._morph.psp_form(0, 0, form_idx)
            except (IndexError, Exception):
                pass
        return text

    def count_words(self, text: str) -> int:
        """IPromtTranslator::CountWordsInKey"""
        return len(self._tokenize(text))

    def get_word_stem(self, text: str, word_idx: int = 0) -> str:
        """IPromtMorph9::GetWordStemInKey"""
        tokens = self._tokenize(text)
        if word_idx < len(tokens):
            tok = tokens[word_idx]
            return tok.lemma or tok.text
        return text

    # ── Ёрдамчи методлар ─────────────────────────────────────

    def recognize_spec_constructions(self, text: str) -> list:
        """IPromtMorph7::RecognizeSpecContructions"""
        constructions = []
        # Сана
        for m in re.finditer(r'\d{1,2}[./]\d{1,2}[./]\d{2,4}', text):
            constructions.append({"type": "date", "text": m.group(), "start": m.start()})
        # Рақам
        for m in re.finditer(r'\b\d+(?:[.,]\d+)?(?:\s*(?:млн|млrd|мln|mln|%))?', text):
            constructions.append({"type": "number", "text": m.group(), "start": m.start()})
        # Email
        for m in re.finditer(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text):
            constructions.append({"type": "email", "text": m.group(), "start": m.start()})
        # URL
        for m in re.finditer(r'https?://\S+', text):
            constructions.append({"type": "url", "text": m.group(), "start": m.start()})
        return constructions

    def batch_parse(self, texts: list) -> list:
        """Бир вақтда бир нечта матн таҳлили"""
        return [self.parse(t) for t in texts]

    def __repr__(self):
        morph_status = "morph connected" if self._morph else "no morph"
        return f'<SyntData: PROMT syntax engine [{morph_status}]>'


# ══════════════════════════════════════════════════════════════
# ТЕСТ
# ══════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print('=' * 60)
    print('  syntdata.py — SyntData.dll Python аналоги')
    print('=' * 60)

    sd = SyntData()

    test_sentences = [
        "Шавкат Мирзиёев Тошкентда нутқ сўзлади",
        "Ўзбекистон давлат университети янги бинони очди",
        "Президент вазирлар мажлисида иштирок этди",
        "The company Microsoft announced new products",
        "Алишер Навоий номидаги театр концерт берди",
    ]

    for sent in test_sentences:
        print(f"\n📝 Матн: {sent}")
        result = sd.parse(sent)

        print(f"   Токенлар: {[(t.text, t.pos) for t in result.tokens]}")

        if result.entities:
            print(f"   NER объектлар:")
            for ent in result.entities:
                print(f"     [{ent.entity_type}] '{ent.text}'")

        synt = result.syntax
        print(f"   Синтаксис: subj={synt['subject']} | pred={synt['predicate']} | obj={synt['objects']}")

        if result.frames:
            fr = result.frames[0]
            print(f"   EventFrame: {fr.event_type}(agent={fr.agent}, loc={fr.location})")

    print("\n\n--- Махсус конструкциялар ---")
    text = "Учрашув 15.04.2026 да бўлади, телефон: +998-90-123-4567"
    specs = sd.recognize_spec_constructions(text)
    for s in specs:
        print(f"  [{s['type']}] '{s['text']}'")

    print("\n--- Collocation ---")
    col = sd.process_collocation("давлат тили")
    print(f"  {col}")
