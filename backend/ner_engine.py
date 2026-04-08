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
        # Try common drug-like tables
        for q in [
            "SELECT DISTINCT inn FROM drugs WHERE inn IS NOT NULL",
            "SELECT DISTINCT name FROM drugs WHERE name IS NOT NULL",
            "SELECT DISTINCT word FROM dictionary WHERE word IS NOT NULL LIMIT 50000",
        ]:
            try:
                cur.execute(q)
                for row in cur.fetchall():
                    val = row[0] if row else None
                    if val and isinstance(val, str) and len(val) > 2:
                        drugs.add(val.lower())
            except Exception:
                pass
        conn.close()
    except Exception as e:
        logger.warning(f"[NER] drug set load failed: {e}")
    _drug_set_cache = drugs
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
                entities.append({
                    "text": r.get("word", ""),
                    "from": int(r.get("start", 0)),
                    "to": int(r.get("end", 0)),
                    "type": str(r.get("entity_group", "MISC")).upper(),
                    "score": float(r.get("score", 0.0)),
                })
        except Exception as e:
            logger.warning(f"[NER] pipeline failed: {e}")

    # 2. Dose pattern (rule-based)
    entities.extend(find_doses(text))

    # 3. Drug dictionary lookup
    entities.extend(find_drugs(text))

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
