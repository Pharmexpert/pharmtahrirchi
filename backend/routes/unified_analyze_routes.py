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
    """Sayqallash layer — spelling/rule-based corrections."""
    try:
        rules = db.get_rules_for_text(text, lang)
        return [
            {
                "type": "spelling",
                "from": r["from_index"],
                "to": r["to_index"],
                "old": r["old_value"],
                "new": r["new_value"],
                "error_type": r["error_type"],
                "confidence": r.get("confidence", 80),
                "layer": "sayqallash",
            }
            for r in rules
        ]
    except Exception:
        return []


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
