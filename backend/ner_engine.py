"""
Named Entity Recognition (NER) engine for Uzbek pharmaceutical text.

Uses elmurod1202/parc-ner-uzbek (or similar) to identify:
  - PERSON (doctors, authors, patients)
  - LOC (cities, hospitals, countries)
  - ORG (companies, ministries, manufacturers)
  - DRUG (custom — extracted via dictionary lookup)
  - DOSE (custom — pattern: number + mg/ml/IU)

Used in:
  - Tilshunos auto-highlighting (mark entities visually)
  - Dashboard table — entity sidebar with click-to-highlight
  - Dictionary auto-population (new drug/org names → suggest add)
  - Document indexing (search by drug/org)
"""
import os
import logging
import asyncio
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger("ner_engine")

MODEL_ID = os.getenv("NER_MODEL_ID", "elmurod1202/bertbek-ner-uznews")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")
LOCAL_MODE = os.getenv("NER_LOCAL", "1") == "1"  # Default ON — small model (~400MB)

_pipeline = None
_lock = None


def _get_lock():
    global _lock
    if _lock is None:
        import threading
        _lock = threading.Lock()
    return _lock


def _get_pipeline():
    global _pipeline
    if _pipeline is not None:
        return _pipeline
    if not LOCAL_MODE:
        return None
    try:
        with _get_lock():
            if _pipeline is None:
                from transformers import pipeline as hf_pipeline
                logger.info(f"[NER] Loading {MODEL_ID}...")
                _pipeline = hf_pipeline(
                    "ner",
                    model=MODEL_ID,
                    tokenizer=MODEL_ID,
                    aggregation_strategy="simple",
                    token=HF_TOKEN,
                )
                logger.info(f"[NER] Model READY ({MODEL_ID})")
    except Exception as e:
        logger.error(f"[NER] load failed: {e}")
        return None
    return _pipeline


def is_available() -> bool:
    try:
        from transformers import pipeline  # noqa
        return True
    except Exception:
        return False


def get_mode() -> str:
    if _pipeline is not None:
        return "loaded"
    if LOCAL_MODE:
        return "local_pending"
    return "disabled"


# ─────────────────────────────────────────────
# Dose pattern (number + medical unit)
# ─────────────────────────────────────────────
DOSE_PATTERN = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(mg|mkg|μg|µg|g|ml|ml|кг|мг|мкг|г|мл|IU|МЕ|МО|ME|%)\b",
    re.IGNORECASE,
)


def find_doses(text: str) -> List[Dict[str, Any]]:
    """Extract dose mentions: 500mg, 0.5g, 100ml, 200 МЕ, etc."""
    out = []
    for m in DOSE_PATTERN.finditer(text):
        out.append({
            "text": m.group(0),
            "value": m.group(1),
            "unit": m.group(2),
            "from": m.start(),
            "to": m.end(),
            "type": "DOSE",
        })
    return out


# ─────────────────────────────────────────────
# Drug name lookup (from dictionary table)
# ─────────────────────────────────────────────
_drug_set_cache = None


def _load_drug_set():
    global _drug_set_cache
    if _drug_set_cache is not None:
        return _drug_set_cache
    drugs = set()
    try:
        import db
        conn = db.connect_db()
        cur = conn.cursor()
        # Gather from drugs, drug_registry, annotated_words tables
        for q in [
            "SELECT DISTINCT inn FROM drugs WHERE inn IS NOT NULL",
            "SELECT DISTINCT brand_name FROM drugs WHERE brand_name IS NOT NULL",
            "SELECT DISTINCT trade_name FROM drug_registry WHERE trade_name IS NOT NULL",
            "SELECT DISTINCT inn FROM drug_registry WHERE inn IS NOT NULL",
            "SELECT DISTINCT term_uz FROM annotated_words WHERE term_uz IS NOT NULL",
            "SELECT DISTINCT term_en FROM annotated_words WHERE term_en IS NOT NULL",
            "SELECT DISTINCT term_ru FROM annotated_words WHERE term_ru IS NOT NULL",
        ]:
            try:
                cur.execute(q)
                for row in cur.fetchall():
                    val = row[0] if row else None
                    if val and isinstance(val, str) and len(val) > 2:
                        drugs.add(val.lower().strip())
            except Exception:
                pass
        conn.close()
    except Exception as e:
        logger.warning(f"[NER] drug set load failed: {e}")
    _drug_set_cache = drugs
    logger.info(f"[NER] whitelist loaded: {len(drugs)} terms")
    return drugs


def find_drugs(text: str) -> List[Dict[str, Any]]:
    """Find drug names by dictionary lookup (case-insensitive word match)."""
    drugs = _load_drug_set()
    if not drugs:
        return []
    out = []
    for m in re.finditer(r"\b[A-Za-zА-Яа-яЁёЎўҒғҚқҲҳ]+\b", text, re.UNICODE):
        word = m.group(0)
        if word.lower() in drugs and len(word) > 3:
            out.append({
                "text": word,
                "from": m.start(),
                "to": m.end(),
                "type": "DRUG",
            })
    return out


# ─────────────────────────────────────────────
# B-10: Extended NER — 30 entity types for Uzbek pharma
# Rule-based patterns (regex + keyword lists)
# ─────────────────────────────────────────────

# Chemical compounds / elements
CHEMICAL_PATTERN = re.compile(
    r"\b(NaCl|KCl|CaCO3|H2O|NaOH|HCl|H2SO4|CO2|Na2SO4|MgSO4|"
    r"натрий хлорид|калий хлорид|кальций карбонат|магний сульфат|"
    r"[A-Z][a-z]?\d*(?:\+\d+)?|"
    r"оксид|гидроксид|сульфат|нитрат|фосфат|хлорид|карбонат|бикарбонат|"
    r"ацетат|цитрат|глюконат|лактат)\b", re.IGNORECASE | re.UNICODE)

# Plant / herbal names
PLANT_KEYWORDS = {
    "алоэ", "ромашка", "валериана", "эхинацея", "женьшень", "мята",
    "шиповник", "зверобой", "календула", "подорожник", "чистотел",
    "солодка", "алтей", "тысячелистник", "пустырник", "боярышник",
    "укроп", "фенхель", "анис", "тмин", "кориандр", "шалфей",
    "лаванда", "мелисса", "базилик", "розмарин", "тимьян",
    "aloevera", "chamomile", "valerian", "echinacea", "ginseng",
}

# Anatomy / body parts
ANATOMY_KEYWORDS = {
    "юрак", "жигар", "буйрак", "ўпка", "ошқозон", "ичак", "мия",
    "бош", "кўз", "қулоқ", "бурун", "тери", "суяк", "мушак",
    "томир", "қон", "асаб", "тиш", "оғиз", "бўғим", "умуртқа",
    "бачадон", "тухумдон", "простата", "қалқонсимон", "лимфа",
    "печень", "почка", "сердце", "лёгкие", "желудок", "кишечник",
    "мозг", "глаз", "ухо", "кожа", "кость", "мышца", "нерв",
    "heart", "liver", "kidney", "lung", "stomach", "brain", "eye",
}

# Disease names
DISEASE_KEYWORDS = {
    "диабет", "гипертония", "астма", "пневмония", "бронхит",
    "гепатит", "цирроз", "анемия", "артрит", "остеопороз",
    "аллергия", "инфаркт", "инсульт", "эпилепсия", "мигрень",
    "гастрит", "язва", "колит", "холецистит", "панкреатит",
    "грипп", "ангина", "отит", "синусит", "фарингит",
    "туберкулёз", "малярия", "гельминтоз", "кандидоз",
    "diabetes", "hypertension", "asthma", "pneumonia", "hepatitis",
    "касаллик", "хасталик", "дард", "оғриқ", "яллиғланиш",
}

# Symptoms
SYMPTOM_KEYWORDS = {
    "иситма", "йўтал", "бош оғриғи", "кўнгил айниш", "қусиш",
    "диарея", "қабзият", "тошма", "қичишиш", "шишиш",
    "ҳолсизлик", "чарчоқ", "бош айланиш", "тер босиш",
    "температура", "лихорадка", "кашель", "тошнота", "рвота",
    "fever", "cough", "headache", "nausea", "vomiting", "diarrhea",
}

# Medical procedures
PROCEDURE_KEYWORDS = {
    "операция", "жарроҳлик", "трансплантация", "биопсия",
    "эндоскопия", "рентген", "узи", "мрт", "кт", "экг",
    "анализ", "текшириш", "диагностика", "терапия",
    "surgery", "biopsy", "endoscopy", "xray", "mri", "ct",
    "вакцинация", "иммунизация", "инъекция", "инфузия",
}

# Measurement units
MEASUREMENT_PATTERN = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(мм|см|м|км|кг|г|мг|мкг|л|мл|дл|"
    r"mm|cm|m|kg|g|mg|mcg|L|mL|dL|"
    r"ммоль|мкмоль|нмоль|пмоль|"
    r"mmol|umol|nmol|pmol)\b", re.IGNORECASE)

# Formulation types
FORMULATION_KEYWORDS = {
    "таблетка", "капсула", "сироп", "суспензия", "эмульсия",
    "мазь", "крем", "гель", "свеча", "суппозиторий",
    "раствор", "порошок", "аэрозоль", "спрей", "пластырь",
    "капли", "ампула", "флакон", "шприц", "ингалятор",
    "tablet", "capsule", "syrup", "suspension", "cream", "gel",
    "ointment", "suppository", "solution", "powder", "spray",
}

# Routes of administration
ROUTE_KEYWORDS = {
    "перорал", "оғиз орқали", "внутривенно", "венага",
    "внутримышечно", "мушакка", "подкожно", "тери остига",
    "ректально", "тўғри ичакка", "ингаляцион", "нафас орқали",
    "сублингвал", "тил остига", "трансдермал", "тери орқали",
    "интраназал", "бурунга", "конъюнктивал", "кўзга",
    "oral", "iv", "im", "sc", "rectal", "inhalation", "sublingual",
    "topical", "transdermal", "intranasal", "ophthalmic",
}

# Packaging
PACKAGING_KEYWORDS = {
    "блистер", "упаковка", "қути", "банка", "туба", "флакон",
    "ампула", "шиша", "пакет", "дозатор", "контейнер",
    "blister", "pack", "bottle", "vial", "ampoule", "tube",
}

# Regulatory / standards
REGULATION_KEYWORDS = {
    "гмп", "gmp", "gdp", "glp", "gcp", "gsp",
    "фармакопея", "pharmacopoeia", "usp", "bp", "ep", "jp",
    "стандарт", "сертификат", "лицензия", "регистрация",
    "who", "fda", "ema", "ich", "дсту", "гост",
}

# Concentration pattern
CONCENTRATION_PATTERN = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(%|мг/мл|mg/ml|г/л|g/L|мкг/мл|mcg/ml|"
    r"ммоль/л|mmol/L|мЭкв/л|mEq/L|МЕ/мл|IU/mL)\b", re.IGNORECASE)

# Volume pattern
VOLUME_PATTERN = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(мл|л|дл|ml|mL|L|dL|fl\.?\s*oz)\b", re.IGNORECASE)

# Weight pattern
WEIGHT_PATTERN = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(кг|г|мг|мкг|нг|кДа|kg|g|mg|mcg|µg|ng|kDa)\b", re.IGNORECASE)

# Temperature pattern
TEMPERATURE_PATTERN = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*°?\s*(C|F|К|°C|°F)\b", re.IGNORECASE)

# pH pattern
PH_PATTERN = re.compile(
    r"\bpH\s*[=:≈~]?\s*(\d+(?:[.,]\d+)?(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?)\b", re.IGNORECASE)

# Frequency / dosing schedule
FREQUENCY_PATTERN = re.compile(
    r"\b(кунига\s+\d+\s*марта|суткада\s+\d+\s*марта|ҳар\s+\d+\s*соат|"
    r"\d+\s*x\s*\d+|bid|tid|qid|qd|prn|"
    r"\d+\s*раз\s*в\s*(день|сутки)|каждые\s+\d+\s*час)\b", re.IGNORECASE | re.UNICODE)

# Duration
DURATION_PATTERN = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*(кун|ҳафта|ой|йил|соат|дақиқа|"
    r"день|дней|неделя|недель|месяц|месяцев|год|лет|час|часов|минут|"
    r"day|days|week|weeks|month|months|year|years|hour|hours|min)\b",
    re.IGNORECASE | re.UNICODE)

# Age group
AGE_GROUP_PATTERN = re.compile(
    r"\b(янги\s*туғилган|чақалоқ|бола|ўсмир|катта|кекса|"
    r"новорождённ|младен|ребёнок|подрост|взросл|пожил|"
    r"neonate|infant|child|adolescent|adult|elderly|pediatric|geriatric|"
    r"\d+[-–]\d+\s*(ёш|яш|лет|years?))\b", re.IGNORECASE | re.UNICODE)

# Date pattern
DATE_PATTERN = re.compile(
    r"\b(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}|\d{4}[./\-]\d{1,2}[./\-]\d{1,2}|"
    r"\d{1,2}\s*(январ|феврал|март|апрел|май|июн|июл|август|сентябр|октябр|ноябр|декабр)\w*\s*\d{2,4})\b",
    re.IGNORECASE | re.UNICODE)

# Time pattern
TIME_PATTERN = re.compile(
    r"\b(\d{1,2}:\d{2}(?::\d{2})?(?:\s*(?:AM|PM|am|pm))?)\b")

# Percentage pattern
PERCENTAGE_PATTERN = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*%\b")

# Country names (common in pharma context)
COUNTRY_KEYWORDS = {
    "ўзбекистон", "россия", "хитой", "ҳиндистон", "германия",
    "франция", "англия", "америка", "қўшма штатлар", "корея",
    "япония", "туркия", "покистон", "бангладеш", "миср",
    "uzbekistan", "russia", "china", "india", "germany",
    "france", "usa", "uk", "japan", "korea", "turkey",
}

# Company suffixes / pharma company indicators
COMPANY_INDICATORS = re.compile(
    r"\b\w+\s*(фарм|pharma|pharm|лабс|labs|inc|ltd|llc|ооо|оао|"
    r"гмбх|gmbh|ag|corp|co|plc|sa|srl|ab|oy)\b", re.IGNORECASE)


def _find_keyword_entities(text: str, keywords: set, entity_type: str) -> List[Dict[str, Any]]:
    """Generic keyword matcher for NER."""
    out = []
    text_lower = text.lower()
    for kw in keywords:
        idx = 0
        kw_lower = kw.lower()
        while True:
            pos = text_lower.find(kw_lower, idx)
            if pos == -1:
                break
            end = pos + len(kw)
            # Word boundary check
            before_ok = (pos == 0) or not text[pos - 1].isalnum()
            after_ok = (end >= len(text)) or not text[end].isalnum()
            if before_ok and after_ok:
                out.append({
                    "text": text[pos:end],
                    "from": pos,
                    "to": end,
                    "type": entity_type,
                })
            idx = end
    return out


def _find_pattern_entities(text: str, pattern: re.Pattern, entity_type: str) -> List[Dict[str, Any]]:
    """Generic regex pattern matcher for NER."""
    out = []
    for m in pattern.finditer(text):
        out.append({
            "text": m.group(0),
            "from": m.start(),
            "to": m.end(),
            "type": entity_type,
        })
    return out


# ─────────────────────────────────────────────
# Main NER call
# ─────────────────────────────────────────────
def extract_entities(text: str) -> List[Dict[str, Any]]:
    """
    Run all entity extractors and return unified list:
        [{ text, from, to, type, score? }, ...]
    """
    if not text or not text.strip():
        return []
    entities: List[Dict[str, Any]] = []

    # 1. ML-based NER (PERSON, LOC, ORG)
    pipe = _get_pipeline()
    if pipe:
        try:
            results = pipe(text)
            for r in results:
                word = r.get("word", "")
                start = int(r.get("start", 0))
                end = int(r.get("end", 0))
                score = float(r.get("score", 0.0))
                etype = str(r.get("entity_group", "MISC")).upper()
                # Filter out BPE subword artifacts (##...) and short garbage
                if not word or word.startswith("##") or len(word) < 2:
                    continue
                # Filter low confidence
                if score < 0.5:
                    continue
                # Use actual text span from original text (not BPE-reconstructed)
                actual_text = text[start:end].strip() if 0 <= start < end <= len(text) else word
                if not actual_text or len(actual_text) < 2:
                    continue
                entities.append({
                    "text": actual_text,
                    "from": start,
                    "to": end,
                    "type": etype,
                    "score": score,
                })
        except Exception as e:
            logger.warning(f"[NER] pipeline failed: {e}")

    # 2. Dose pattern (rule-based)
    entities.extend(find_doses(text))

    # 3. Drug dictionary lookup
    entities.extend(find_drugs(text))

    # 4. B-10: Extended 25 additional entity types (rule-based)
    # Keyword-based entities
    entities.extend(_find_keyword_entities(text, PLANT_KEYWORDS, "PLANT"))
    entities.extend(_find_keyword_entities(text, ANATOMY_KEYWORDS, "ANATOMY"))
    entities.extend(_find_keyword_entities(text, DISEASE_KEYWORDS, "DISEASE"))
    entities.extend(_find_keyword_entities(text, SYMPTOM_KEYWORDS, "SYMPTOM"))
    entities.extend(_find_keyword_entities(text, PROCEDURE_KEYWORDS, "PROCEDURE"))
    entities.extend(_find_keyword_entities(text, FORMULATION_KEYWORDS, "FORMULATION"))
    entities.extend(_find_keyword_entities(text, ROUTE_KEYWORDS, "ROUTE"))
    entities.extend(_find_keyword_entities(text, PACKAGING_KEYWORDS, "PACKAGING"))
    entities.extend(_find_keyword_entities(text, REGULATION_KEYWORDS, "REGULATION"))
    entities.extend(_find_keyword_entities(text, COUNTRY_KEYWORDS, "COUNTRY"))

    # Pattern-based entities
    entities.extend(_find_pattern_entities(text, CHEMICAL_PATTERN, "CHEMICAL"))
    entities.extend(_find_pattern_entities(text, MEASUREMENT_PATTERN, "MEASUREMENT"))
    entities.extend(_find_pattern_entities(text, CONCENTRATION_PATTERN, "CONCENTRATION"))
    entities.extend(_find_pattern_entities(text, VOLUME_PATTERN, "VOLUME"))
    entities.extend(_find_pattern_entities(text, WEIGHT_PATTERN, "WEIGHT"))
    entities.extend(_find_pattern_entities(text, TEMPERATURE_PATTERN, "TEMPERATURE"))
    entities.extend(_find_pattern_entities(text, PH_PATTERN, "PH"))
    entities.extend(_find_pattern_entities(text, FREQUENCY_PATTERN, "FREQUENCY"))
    entities.extend(_find_pattern_entities(text, DURATION_PATTERN, "DURATION"))
    entities.extend(_find_pattern_entities(text, AGE_GROUP_PATTERN, "AGE_GROUP"))
    entities.extend(_find_pattern_entities(text, DATE_PATTERN, "DATE"))
    entities.extend(_find_pattern_entities(text, TIME_PATTERN, "TIME"))
    entities.extend(_find_pattern_entities(text, PERCENTAGE_PATTERN, "PERCENTAGE"))
    entities.extend(_find_pattern_entities(text, COMPANY_INDICATORS, "COMPANY"))

    # Deduplicate overlapping entities (keep first/highest priority)
    seen_spans = set()
    unique = []
    for e in sorted(entities, key=lambda x: (x.get("from", 0), -x.get("to", 0))):
        span = (e.get("from", 0), e.get("to", 0))
        # Skip if this span overlaps with an already-seen span
        overlaps = False
        for s in seen_spans:
            if span[0] < s[1] and span[1] > s[0]:
                overlaps = True
                break
        if not overlaps:
            seen_spans.add(span)
            unique.append(e)
    entities = unique

    # Sort by position
    entities.sort(key=lambda e: (e.get("from", 0), e.get("to", 0)))
    return entities


async def extract_async(text: str) -> List[Dict[str, Any]]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, extract_entities, text)


def stats(text: str) -> Dict[str, int]:
    """Count entities by type."""
    ents = extract_entities(text)
    out = {}
    for e in ents:
        t = e.get("type", "MISC")
        out[t] = out.get(t, 0) + 1
    return out


# ─────────────────────────────────────────────
# Placeholder mechanism for translation protection
# ─────────────────────────────────────────────
def protect_entities(text: str) -> tuple:
    """Replace named entities with placeholders before translation.
    Returns: (protected_text, placeholder_map)
    """
    entities = extract_entities(text)
    if not entities:
        return text, {}
    # Deduplicate and sort by position descending (replace from end to preserve indices)
    seen = set()
    unique = []
    for e in entities:
        key = (e.get("from", 0), e.get("to", 0))
        if key not in seen:
            seen.add(key)
            unique.append(e)
    unique.sort(key=lambda e: e.get("from", 0), reverse=True)
    placeholder_map = {}
    protected = text
    for i, e in enumerate(unique):
        placeholder = f"__NE_{i}__"
        start, end = e.get("from", 0), e.get("to", 0)
        if start >= 0 and end > start:
            original = protected[start:end]
            protected = protected[:start] + placeholder + protected[end:]
            placeholder_map[placeholder] = original
    return protected, placeholder_map


def restore_entities(text: str, placeholder_map: dict) -> str:
    """Replace placeholders back with original entity text."""
    result = text
    for placeholder, original in placeholder_map.items():
        result = result.replace(placeholder, original)
    return result
