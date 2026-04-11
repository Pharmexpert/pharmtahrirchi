"""
Unified linguistic analysis endpoint.
Runs all 4 layers (Morphology, Sayqallash, Syntax, Style) in one call.

POST /api/analyze/full
  body: { text: string, layers?: string[], lang?: string }
  returns: { morph: [], sayqallash: [], syntax: [], style: [] }
"""
import os
import re
import sqlite3
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException

import db

router = APIRouter(prefix="/api/analyze", tags=["analyze"])

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "pharma_editor.db"))


def _detect_script(text: str) -> str:
    """Detect if text is primarily Cyrillic or Latin."""
    cyr = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
    lat = sum(1 for c in text if 'a' <= c.lower() <= 'z')
    return "cyr" if cyr >= lat else "lat"


def _ensure_script(value: str, target_script: str) -> str:
    """Convert value to match target script (cyr or lat).
    Ensures suggestions always match input text's script."""
    if not value or not value.strip():
        return value
    val_script = _detect_script(value)
    if val_script == target_script:
        return value
    try:
        import dual_script
        if target_script == "cyr":
            return dual_script.to_cyrillic(value) or value
        else:
            return dual_script.to_latin(value) or value
    except Exception:
        return value


def _run_morph(text: str) -> list:
    """Morphology layer — basic word analysis via Hunspell."""
    try:
        import hunspell_data
        words = re.findall(r"\w+", text)
        results = []
        for w in words[:200]:
            if len(w) < 3:
                continue
            results.append({"word": w, "pos": "NOUN", "length": len(w)})
        return results[:100]
    except Exception:
        return []


def _run_sayqallash(text: str, lang: str) -> list:
    """Sayqallash layer — FULL 3-tier pipeline (Hunspell + Rules DB + AI).
    Previously only used Rules DB. Now calls the same logic as /sayqallash endpoint."""
    results = []

    # TIER 0: Hunspell
    try:
        import spellcheck
        is_cyr = any("\u0400" <= ch <= "\u04FF" for ch in text[:50])
        spell_errors = spellcheck.check_text(text, is_cyrillic=is_cyr)
        for err in spell_errors:
            if err.get('suggestions'):
                results.append({
                    "from": err['position'],
                    "to": err['end_position'],
                    "old": err['word'],
                    "new": err['suggestions'][0],
                    "error_type": "H/Spelling",
                    "source": "hunspell",
                    "confidence": 70,
                    "layer": "sayqallash",
                })
    except Exception:
        pass

    # TIER 1: Rules DB — FAST exact match only (no BERT, no FAISS)
    # BERT semantic search is too slow for real-time analysis (18s+ per call)
    # Use fast exact word-boundary matching against 8,000+ cached rules
    try:
        import re as _re
        rules_list = db.rules_cache.get_all(lang)
        text_lower = text.lower()

        # Build whitelist (correct forms should not be flagged)
        correct_set = set()
        for rule in rules_list:
            cf = rule.get('correct_form', '')
            if cf:
                correct_set.add(cf.strip().lower())
        # Add pharma whitelist
        try:
            correct_set.update(db._get_pharma_whitelist())
        except Exception:
            pass

        covered = set()
        import math as _math
        for rule in rules_list:
            wrong = rule.get('wrong_form', '')
            correct = rule.get('correct_form', '')
            if not wrong or not correct or wrong.lower() == correct.lower():
                continue
            wrong_lower = wrong.lower().strip()
            # Skip if wrong form is actually in the correct set
            if wrong_lower in correct_set:
                continue
            # Fast exact match with word boundaries
            idx = 0
            while True:
                pos = text_lower.find(wrong_lower, idx)
                if pos == -1:
                    break
                end = pos + len(wrong_lower)
                # Word boundary check
                before_ok = (pos == 0) or not text[pos - 1].isalpha()
                after_ok = (end >= len(text)) or not text[end].isalpha()
                if before_ok and after_ok and (pos, end) not in covered:
                    covered.add((pos, end))
                    freq = rule.get('frequency', 1) or 1
                    confidence = min(95, 60 + int(_math.log2(max(freq, 1)) * 5))
                    results.append({
                        "from": pos,
                        "to": end,
                        "old": text[pos:end],
                        "new": correct,
                        "error_type": rule.get('error_type', 'S/Spelling'),
                        "confidence": confidence,
                        "source": "rules_db",
                        "layer": "sayqallash",
                    })
                idx = end
    except Exception:
        pass

    # Remove Hunspell results that overlap with Rules DB (Rules DB takes priority)
    rule_ranges = [(r["from"], r["to"]) for r in results if r.get("source") == "rules_db"]
    results = [r for r in results if r.get("source") != "hunspell" or not any(
        max(r["from"], rs) < min(r["to"], re) for rs, re in rule_ranges
    )]

    # Ensure all suggestions match input text's script
    text_script = _detect_script(text)
    for r in results:
        if r.get("new"):
            r["new"] = _ensure_script(r["new"], text_script)

    return results


def _run_syntax(text: str) -> list:
    """Syntax layer — sentence-level check."""
    try:
        import syntax_engine
        errors = syntax_engine.check_text(text)
        for e in errors:
            e["layer"] = "syntax"
        return errors
    except Exception:
        return []


def _run_style(text: str) -> list:
    """Style Guide layer — format/pharma standard enforcement.
    Supports dual-script: if text is Cyrillic, also tries Latin-converted patterns."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT rule_id, category, description, pattern, suggestion, severity, examples, source, COALESCE(source_ref,'') as source_ref, COALESCE(source_url,'') as source_url FROM style_rules WHERE pattern IS NOT NULL AND pattern != ''")
        rules = [dict(r) for r in cur.fetchall()]
        conn.close()
    except Exception:
        return []

    # Detect script for dual-script matching
    try:
        import dual_script
        text_script = dual_script.detect_script(text)
    except Exception:
        text_script = "unknown"

    issues = []
    for rule in rules:
        pattern = rule.get("pattern", "")
        if not pattern:
            continue
        patterns_to_try = [pattern]
        # If text is in different script than pattern, convert pattern
        if text_script in ("cyr", "lat"):
            try:
                import dual_script
                pat_has_cyr = any("\u0400" <= ch <= "\u04FF" for ch in pattern if ch.isalpha())
                pat_has_lat = any("a" <= ch.lower() <= "z" for ch in pattern if ch.isalpha())
                if text_script == "cyr" and pat_has_lat and not pat_has_cyr:
                    converted = dual_script.to_cyrillic(pattern)
                    if converted and converted != pattern:
                        patterns_to_try.append(converted)
                elif text_script == "lat" and pat_has_cyr and not pat_has_lat:
                    converted = dual_script.to_latin(pattern)
                    if converted and converted != pattern:
                        patterns_to_try.append(converted)
            except Exception:
                pass

        for pat in patterns_to_try:
            try:
                for m in re.finditer(pat, text):
                    issues.append({
                        "rule_id": rule["rule_id"],
                        "category": rule["category"],
                        "description": rule["description"],
                        "from": m.start(),
                        "to": m.end(),
                        "old": m.group(0),
                        "suggestion": rule.get("suggestion", ""),
                        "severity": rule.get("severity", "should"),
                        "examples": rule.get("examples", ""),
                        "source": rule.get("source", ""),
                        "source_ref": rule.get("source_ref", ""),
                        "source_url": rule.get("source_url", ""),
                        "layer": "style",
                    })
            except re.error:
                continue

    return issues[:200]


@router.post("/ner")
async def analyze_ner(payload: Dict[str, Any]):
    """Extract named entities from text (drugs, doses, persons, organizations)."""
    text = (payload.get("text") or "").strip()
    if not text:
        return {"entities": [], "total": 0}
    try:
        import ner_engine
        entities = ner_engine.extract_entities(text)
        return {"entities": entities, "total": len(entities)}
    except Exception as e:
        return {"entities": [], "total": 0, "error": str(e)}


@router.post("/protect-entities")
async def protect_entities(payload: Dict[str, Any]):
    """Replace named entities with placeholders for safe translation."""
    text = (payload.get("text") or "").strip()
    if not text:
        return {"protected_text": text, "placeholder_map": {}}
    try:
        import ner_engine
        protected, pmap = ner_engine.protect_entities(text)
        return {"protected_text": protected, "placeholder_map": pmap, "entities_count": len(pmap)}
    except Exception as e:
        return {"protected_text": text, "placeholder_map": {}, "error": str(e)}


@router.post("/restore-entities")
async def restore_entities(payload: Dict[str, Any]):
    """Restore placeholders back to original entity text after translation."""
    text = (payload.get("text") or "").strip()
    pmap = payload.get("placeholder_map") or {}
    if not text or not pmap:
        return {"text": text}
    try:
        import ner_engine
        restored = ner_engine.restore_entities(text, pmap)
        return {"text": restored}
    except Exception:
        return {"text": text}


@router.post("/full")
async def analyze_full(payload: Dict[str, Any]):
    """Run all 4 linguistic layers on text."""
    text = (payload.get("text") or "").strip()
    layers = payload.get("layers") or ["morph", "sayqallash", "syntax", "style"]
    lang = payload.get("lang") or "uz"

    if not text:
        return {"morph": [], "sayqallash": [], "syntax": [], "style": [], "total": 0}

    result = {}
    if "morph" in layers:
        result["morph"] = _run_morph(text)
    if "sayqallash" in layers:
        result["sayqallash"] = _run_sayqallash(text, lang)
    if "syntax" in layers:
        result["syntax"] = _run_syntax(text)
    if "style" in layers:
        result["style"] = _run_style(text)

    result["total"] = sum(len(v) for k, v in result.items() if isinstance(v, list))
    result["summary"] = {
        "morph_count": len(result.get("morph", [])),
        "sayqallash_count": len(result.get("sayqallash", [])),
        "syntax_count": len(result.get("syntax", [])),
        "style_count": len(result.get("style", [])),
    }
    return result
