"""
Compound morphology for medical/pharmaceutical terms.

Decomposes biomedical terms into Greek/Latin morphemes:
  - "кардиоваскуляр" → cardio (Greek "kardia"=heart) + vascular (Latin "vasculum"=vessel)
  - "глюкокортикоид" → gluco + cort + oid (resembling)
  - "антибиотик" → anti + bio + tic
  - "гипергликемия" → hyper + glyc + emia (blood)

Uses:
  - Tilshunos: explain term meaning when user hovers
  - Drug normalizer: find related drugs by morpheme
  - NER: detect medical terms even if not in dictionary
"""
import logging
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger("compound_morphology")

# ─────────────────────────────────────────────
# Greek prefixes (medical/biological)
# ─────────────────────────────────────────────
GREEK_PREFIXES = {
    "a": "ёқ, негация (without)",
    "an": "ёқ (without)",
    "anti": "қарши (against)",
    "auto": "ўз (self)",
    "bi": "икки (two)",
    "bio": "ҳаёт (life)",
    "brady": "секин (slow)",
    "cardi": "юрак (heart)",
    "cardio": "юрак (heart)",
    "cephal": "бош (head)",
    "chrono": "вақт (time)",
    "cyt": "ҳужайра (cell)",
    "cyto": "ҳужайра (cell)",
    "derm": "тери (skin)",
    "dermato": "тери (skin)",
    "dys": "ёмон, бузилган (bad)",
    "endo": "ичида (inside)",
    "epi": "усти (upon)",
    "ergo": "иш (work)",
    "erythro": "қизил (red)",
    "eu": "яхши (good)",
    "exo": "ташқарида (outside)",
    "gastro": "меъда (stomach)",
    "gluco": "глюкоза (sugar)",
    "glyc": "глюкоза, ширин (sweet)",
    "glyco": "глюкоза (sugar)",
    "hemo": "қон (blood)",
    "hema": "қон (blood)",
    "hemato": "қон (blood)",
    "hepato": "жигар (liver)",
    "hetero": "бошқа (different)",
    "homeo": "ўхшаш (similar)",
    "homo": "бир хил (same)",
    "hydro": "сув (water)",
    "hyper": "юқори, ортиқ (above, excessive)",
    "hypo": "паст, кам (below, deficient)",
    "iso": "тенг (equal)",
    "leuk": "оқ (white)",
    "leuko": "оқ (white)",
    "lipo": "ёғ (fat)",
    "macro": "катта (large)",
    "mega": "катта (large)",
    "melan": "қора (black)",
    "meso": "ўрта (middle)",
    "meta": "кейин, ўзгариш (after, change)",
    "micro": "кичик (small)",
    "mono": "битта (one)",
    "morph": "шакл (form)",
    "myo": "мушак (muscle)",
    "necro": "ўлим (death)",
    "neo": "янги (new)",
    "nephro": "буйрак (kidney)",
    "neuro": "асаб (nerve)",
    "oligo": "оз (few)",
    "ortho": "тўғри (straight)",
    "osteo": "суяк (bone)",
    "oto": "қулоқ (ear)",
    "pan": "ҳамма (all)",
    "para": "ёнида (beside)",
    "patho": "касаллик (disease)",
    "peri": "атрофида (around)",
    "phag": "ютиш (eat)",
    "phago": "ютиш (eat)",
    "philo": "севиш (love)",
    "phlebo": "вена (vein)",
    "phobo": "қўрқиш (fear)",
    "phon": "товуш (sound)",
    "photo": "ёруғлик (light)",
    "phyto": "ўсимлик (plant)",
    "pneumo": "ўпка, нафас (lung)",
    "poly": "кўп (many)",
    "post": "кейин (after)",
    "pre": "олдин (before)",
    "pro": "олдинда (forward)",
    "pseudo": "ёлғон (false)",
    "psycho": "руҳ, ақл (mind)",
    "pulmo": "ўпка (lung)",
    "pyo": "йиринг (pus)",
    "pyro": "ўт (fire)",
    "quad": "тўрт (four)",
    "retro": "орқага (backward)",
    "rhin": "бурун (nose)",
    "rhino": "бурун (nose)",
    "sarco": "гўшт (flesh)",
    "sub": "остида (under)",
    "super": "усти (above)",
    "supra": "усти (above)",
    "syn": "билан (with)",
    "tachy": "тез (fast)",
    "thermo": "иссиқ (heat)",
    "thrombo": "лахта (clot)",
    "tox": "заҳар (poison)",
    "toxi": "заҳар (poison)",
    "trans": "орқали (across)",
    "tri": "уч (three)",
    "ultra": "ортиқ (beyond)",
    "uni": "битта (one)",
    "vaso": "томир (vessel)",
}

# ─────────────────────────────────────────────
# Greek/Latin suffixes (medical)
# ─────────────────────────────────────────────
MEDICAL_SUFFIXES = {
    "algia": "оғриқ (pain)",
    "asis": "ҳолат (condition)",
    "ase": "фермент (enzyme)",
    "ation": "жараён (process)",
    "ectomy": "кесиб олиш (surgical removal)",
    "emia": "қон ҳолати (blood condition)",
    "genic": "пайдо қилувчи (producing)",
    "gram": "ёзма (record)",
    "graph": "ёзувчи (recording instrument)",
    "graphy": "ёзиш усули (process of recording)",
    "iasis": "ҳолат (condition)",
    "ic": "тегишли (pertaining to)",
    "ide": "кимёвий бирикма (chemical compound)",
    "ine": "модда (substance)",
    "itis": "яллиғланиш (inflammation)",
    "lysis": "парчаланиш (breakdown)",
    "logy": "фан (study of)",
    "lytic": "парчаловчи (breaking down)",
    "ma": "ўсма (tumor, mass)",
    "megaly": "катталашиш (enlargement)",
    "ole": "кичик (small)",
    "oid": "ўхшаш (resembling)",
    "ol": "спирт (alcohol)",
    "oma": "ўсма (tumor)",
    "opathy": "касаллик (disease)",
    "opia": "кўриш (vision)",
    "opsy": "кўрик (visual examination)",
    "osis": "ҳолат, касаллик (condition)",
    "ostomy": "оғиз ясаш (creating an opening)",
    "otomy": "кесиш (incision)",
    "ous": "тегишли (pertaining to)",
    "pathy": "касаллик (disease)",
    "penia": "камайиш (deficiency)",
    "phagia": "ютиш (eating)",
    "phasia": "нутқ (speech)",
    "philia": "мойиллик (attraction)",
    "phobia": "қўрқиш (fear)",
    "plasia": "ўсиш (growth)",
    "plasty": "пластика (repair)",
    "plegia": "фалаж (paralysis)",
    "pnea": "нафас (breathing)",
    "rrhage": "оқиш (bursting forth)",
    "rrhea": "оқим (flow)",
    "scope": "кўриш асбоби (instrument for viewing)",
    "scopy": "кўриш усули (visual exam)",
    "stasis": "тўхтаб қолиш (stopping)",
    "stomy": "оғиз ясаш (opening)",
    "tic": "тегишли (pertaining)",
    "tomy": "кесиш (cutting)",
    "trophy": "озуқа (nourishment)",
    "uria": "сийдик ҳолати (urine condition)",
}

# Sort by length descending for greedy matching
_PREFIX_KEYS = sorted(GREEK_PREFIXES.keys(), key=len, reverse=True)
_SUFFIX_KEYS = sorted(MEDICAL_SUFFIXES.keys(), key=len, reverse=True)


def _normalize(word: str) -> str:
    """Lowercase + transliterate Cyrillic to Latin if needed."""
    word = word.lower().strip()
    try:
        import transliterate as tl
        if any("\u0400" <= ch <= "\u04FF" for ch in word):
            word = tl.to_latin(word)
    except Exception:
        pass
    return word


def decompose(word: str) -> Dict[str, Any]:
    """
    Decompose a medical term into morphemes.
    Returns: { "input": ..., "normalized": ..., "prefix": ..., "root": ..., "suffix": ..., "meaning": ... }
    """
    if not word:
        return {"input": word, "found": False}

    norm = _normalize(word)
    if len(norm) < 4:
        return {"input": word, "normalized": norm, "found": False}

    prefix = None
    prefix_meaning = None
    suffix = None
    suffix_meaning = None
    root = norm

    # Find longest matching prefix
    for p in _PREFIX_KEYS:
        if norm.startswith(p) and len(norm) > len(p) + 2:
            prefix = p
            prefix_meaning = GREEK_PREFIXES[p]
            root = norm[len(p):]
            break

    # Find longest matching suffix
    for s in _SUFFIX_KEYS:
        if root.endswith(s) and len(root) > len(s) + 1:
            suffix = s
            suffix_meaning = MEDICAL_SUFFIXES[s]
            root = root[:-len(s)]
            break

    found = bool(prefix or suffix)
    meaning_parts = []
    if prefix_meaning:
        meaning_parts.append(f"{prefix} = {prefix_meaning}")
    if root and len(root) > 1:
        meaning_parts.append(f"root = {root}")
    if suffix_meaning:
        meaning_parts.append(f"{suffix} = {suffix_meaning}")

    return {
        "input": word,
        "normalized": norm,
        "found": found,
        "prefix": prefix,
        "prefix_meaning": prefix_meaning,
        "root": root,
        "suffix": suffix,
        "suffix_meaning": suffix_meaning,
        "meaning": " + ".join(meaning_parts) if meaning_parts else norm,
    }


def explain(word: str, lang: str = "uz") -> str:
    """Human-readable explanation of a medical term."""
    d = decompose(word)
    if not d.get("found"):
        return f'"{word}" — морфемалари аниқланмади'
    parts = []
    if d.get("prefix"):
        parts.append(f'**{d["prefix"]}**: {d["prefix_meaning"]}')
    if d.get("root"):
        parts.append(f'**{d["root"]}**: ўзак (root)')
    if d.get("suffix"):
        parts.append(f'**{d["suffix"]}**: {d["suffix_meaning"]}')
    return f'{word} = {" + ".join(parts)}'


def find_related(word: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Find words sharing the same prefix or root via DB lookup."""
    d = decompose(word)
    if not d.get("found"):
        return []
    related = []
    try:
        import db
        conn = db.connect_db()
        cur = conn.cursor()
        # Look for drugs with similar INN
        if d.get("prefix"):
            cur.execute("SELECT DISTINCT inn, brand_name FROM drugs WHERE LOWER(inn) LIKE ? OR LOWER(brand_name) LIKE ? LIMIT ?",
                        (f"{d['prefix']}%", f"{d['prefix']}%", limit))
            for r in cur.fetchall():
                related.append({"name": r[0] or r[1], "via": f"prefix:{d['prefix']}"})
        conn.close()
    except Exception:
        pass
    return related[:limit]
