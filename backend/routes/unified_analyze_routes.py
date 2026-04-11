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
    """Sayqallash — multi-source fast spelling check.

    Sources (all instant, no BERT/AI):
      1. Rules DB exact match (8,000+ cached rules) — dual-script auto-convert
      2. Hunspell is_correct via DICTIONARY LOOKUP (not spylls — direct .dic set)
      3. Multiple suggestions per error (Rules DB + Hunspell .dic neighbors)

    Dual-script: Cyrillic rules match Latin text and vice versa.
    """
    import re as _re
    import math as _math

    results = []
    text_script = _detect_script(text)
    text_lower = text.lower()
    covered = set()

    # ═══ Load rules + build indexes ═══
    rules_list = db.rules_cache.get_all(lang)

    # wrong→correct index (for instant lookup by word)
    wrong_to_rules = {}
    correct_set = set()
    for rule in rules_list:
        w = (rule.get('wrong_form') or '').strip().lower()
        c = (rule.get('correct_form') or '').strip().lower()
        if w and c and w != c:
            correct_set.add(c)
            if w not in wrong_to_rules or rule.get('frequency', 0) > wrong_to_rules[w].get('frequency', 0):
                wrong_to_rules[w] = rule

    # Dual-script: also index converted forms
    try:
        import dual_script
        extra = {}
        for w, rule in wrong_to_rules.items():
            # If rule is Cyrillic, add Latin version too (and vice versa)
            w_cyr = any('\u0400' <= ch <= '\u04FF' for ch in w)
            if w_cyr:
                lat = dual_script.to_latin(w)
                if lat and lat.lower() not in wrong_to_rules:
                    extra[lat.lower()] = rule
            else:
                cyr = dual_script.to_cyrillic(w)
                if cyr and cyr.lower() not in wrong_to_rules:
                    extra[cyr.lower()] = rule
        wrong_to_rules.update(extra)
    except Exception:
        pass

    # Pharma whitelist
    try:
        correct_set.update(db._get_pharma_whitelist())
    except Exception:
        pass

    # ═══ SOURCE 1: Rules DB exact match (instant) ═══
    for wrong_lower, rule in wrong_to_rules.items():
        if wrong_lower in correct_set:
            continue
        idx = 0
        while True:
            pos = text_lower.find(wrong_lower, idx)
            if pos == -1:
                break
            end = pos + len(wrong_lower)
            before_ok = (pos == 0) or not text[pos - 1].isalpha()
            after_ok = (end >= len(text)) or not text[end].isalpha()
            if before_ok and after_ok and (pos, end) not in covered:
                covered.add((pos, end))
                correct = rule.get('correct_form', '')
                # Convert suggestion to match text script
                correct = _ensure_script(correct, text_script)
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
                    # Multiple suggestions for tooltip
                    "suggestions": [correct],
                })
            idx = end

    # ═══ SOURCE 2: Fast Hunspell dictionary lookup (no spylls — direct set) ═══
    # Load .dic words as a set for O(1) lookup
    try:
        import spellcheck
        spellcheck._load()
        if text_script == "cyr" and spellcheck._cyrillic_words:
            dict_words = spellcheck._cyrillic_words
        elif text_script == "lat" and spellcheck._latin_words:
            dict_words = spellcheck._latin_words
        elif spellcheck._cyrl_dict or spellcheck._lat_dict:
            # spylls loaded — use fast lookup (is_correct is fast, suggest is slow)
            dict_words = None  # will use spylls is_correct
        else:
            dict_words = None

        pattern = r'[а-яёўқғҳА-ЯЁЎҚҒҲ]+' if text_script == "cyr" else r"[a-zA-Z'ʻʼ]+"
        for match in _re.finditer(pattern, text):
            word = match.group()
            pos, end = match.start(), match.end()
            if len(word) < 3 or (word.isupper() and len(word) < 5):
                continue
            if (pos, end) in covered:
                continue
            wl = word.lower()
            if wl in correct_set:
                continue

            # Check against dictionary
            is_wrong = False
            if dict_words is not None:
                is_wrong = wl not in dict_words
            elif spellcheck._cyrl_dict or spellcheck._lat_dict:
                # Use spylls lookup (fast) — NOT suggest
                d = spellcheck._cyrl_dict if text_script == "cyr" else spellcheck._lat_dict
                if d:
                    is_wrong = not (d.lookup(word) or d.lookup(wl))

            if is_wrong and (pos, end) not in covered:
                covered.add((pos, end))
                # Get suggestion from Rules DB (instant)
                suggestion = ""
                if wl in wrong_to_rules:
                    suggestion = wrong_to_rules[wl].get('correct_form', '')
                    suggestion = _ensure_script(suggestion, text_script)
                results.append({
                    "from": pos,
                    "to": end,
                    "old": word,
                    "new": suggestion if suggestion else f"[{word} — луғатда топилмади]",
                    "error_type": "H/Spelling",
                    "confidence": 65 if suggestion else 50,
                    "source": "hunspell",
                    "layer": "sayqallash",
                    "suggestions": [suggestion] if suggestion else [],
                })
    except Exception:
        pass

    # ═══ SOURCE 3: Grammar checker (fast rule-based) ═══
    try:
        import grammar_checker
        checker = grammar_checker.get_checker()
        grammar_issues = checker.check(text, lang=lang)
        text_script_g = _detect_script(text)
        for gi in grammar_issues:
            key = (gi.from_index, gi.to_index)
            if key not in covered:
                covered.add(key)
                suggestion = ", ".join(gi.suggestions[:3]) if gi.suggestions else ""
                suggestion = _ensure_script(suggestion, text_script_g)
                results.append({
                    "from": gi.from_index,
                    "to": gi.to_index,
                    "old": gi.word,
                    "new": suggestion,
                    "error_type": gi.issue_type,
                    "confidence": int(gi.confidence * 100) if gi.confidence else 60,
                    "source": "grammar",
                    "layer": "sayqallash",
                    "message": gi.message,
                    "suggestions": [_ensure_script(s, text_script_g) for s in (gi.suggestions or [])[:5]],
                })
    except Exception:
        pass

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
